//! TR-JSON: RFC 8785 (JCS) ning faqat butun sonli qismi (spec §2.1).
//!
//! Butun sonlar bilan cheklanish RFC 8785 dagi ECMAScript son formatlash bosqichini olib tashlaydi —
//! mustaqil implementatsiyalar (masalan Python verifikatori) uchun eng xatoga moyil joy shu edi.

use serde_json::Value;

/// `2^53 - 1` — JavaScript'da aniq ifodalanadigan eng katta butun son.
pub const MAX_SAFE_INTEGER: i64 = (1 << 53) - 1;

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum JcsError {
    #[error("butun bo'lmagan son TR-JSON'da ruxsat etilmaydi: {0}")]
    NonInteger(String),
    #[error("butun son ±(2^53-1) oralig'idan tashqarida: {0}")]
    OutOfRange(String),
}

/// Qiymatning kanonik TR-JSON satri.
pub fn canonicalize(v: &Value) -> Result<String, JcsError> {
    let mut out = String::new();
    write_value(v, &mut out)?;
    Ok(out)
}

/// `v` obyektidan `key` maydonini olib tashlab kanoniklashtiradi (`JCS(v \ key)`).
/// `v` obyekt bo'lmasa, o'zini kanoniklashtiradi.
pub fn canonicalize_without(v: &Value, key: &str) -> Result<String, JcsError> {
    match v {
        Value::Object(map) if map.contains_key(key) => {
            let mut m = map.clone();
            m.remove(key);
            canonicalize(&Value::Object(m))
        }
        _ => canonicalize(v),
    }
}

fn write_value(v: &Value, out: &mut String) -> Result<(), JcsError> {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => {
            let i = if let Some(i) = n.as_i64() {
                i
            } else if n.as_u64().is_some() {
                return Err(JcsError::OutOfRange(n.to_string()));
            } else {
                return Err(JcsError::NonInteger(n.to_string()));
            };
            if !(-MAX_SAFE_INTEGER..=MAX_SAFE_INTEGER).contains(&i) {
                return Err(JcsError::OutOfRange(n.to_string()));
            }
            out.push_str(&i.to_string());
        }
        Value::String(s) => write_string(s, out),
        Value::Array(items) => {
            out.push('[');
            for (k, item) in items.iter().enumerate() {
                if k > 0 {
                    out.push(',');
                }
                write_value(item, out)?;
            }
            out.push(']');
        }
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            // RFC 8785 §3.2.3: kalitlar UTF-16 kod birliklari bo'yicha tartiblanadi.
            keys.sort_by(|a, b| a.encode_utf16().cmp(b.encode_utf16()));
            out.push('{');
            for (k, key) in keys.into_iter().enumerate() {
                if k > 0 {
                    out.push(',');
                }
                write_string(key, out);
                out.push(':');
                write_value(&map[key], out)?;
            }
            out.push('}');
        }
    }
    Ok(())
}

fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0C}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn canon(text: &str) -> Result<String, JcsError> {
        canonicalize(&serde_json::from_str(text).unwrap())
    }

    #[test]
    fn sorts_keys_by_utf16_code_units() {
        // RFC 8785 §3.2.3 namunasidagi kalitlar (qiymatlar butun songa almashtirilgan).
        // UTF-8 bayt tartibida U+FB33 (EF ..) U+1F600 (F0 ..) dan oldin keladi, UTF-16 da esa
        // keyin (D83D < FB33) — aynan shu farq tekshiriladi.
        let input =
            r#"{"\u20ac":1,"\r":2,"\ud83d\ude00":3,"\u00f6":4,"1":5,"\u0080":6,"\ufb33":7}"#;
        let got = canon(input).unwrap();
        let keys: Vec<&str> = got
            .trim_matches(|c| c == '{' || c == '}')
            .split(',')
            .map(|kv| kv.split(':').next().unwrap())
            .collect();
        assert_eq!(
            keys,
            [
                "\"\\r\"",
                "\"1\"",
                "\"\u{80}\"",
                "\"ö\"",
                "\"€\"",
                "\"😀\"",
                "\"\u{fb33}\""
            ]
        );
    }

    #[test]
    fn escapes_like_rfc8785() {
        let v = json!({"s": "a\"b\\c/\u{08}\u{0C}\n\r\t\u{01}\u{1f}\u{7f}é\u{2028}"});
        assert_eq!(
            canonicalize(&v).unwrap(),
            "{\"s\":\"a\\\"b\\\\c/\\b\\f\\n\\r\\t\\u0001\\u001f\u{7f}é\u{2028}\"}"
        );
    }

    #[test]
    fn integers_only() {
        assert_eq!(
            canon("[0,-1,9007199254740991,-9007199254740991]").unwrap(),
            "[0,-1,9007199254740991,-9007199254740991]"
        );
        assert!(matches!(canon("[1.5]"), Err(JcsError::NonInteger(_))));
        assert!(matches!(canon("[1.0]"), Err(JcsError::NonInteger(_))));
        assert!(matches!(canon("[1e2]"), Err(JcsError::NonInteger(_))));
        assert!(matches!(
            canon("[9007199254740992]"),
            Err(JcsError::OutOfRange(_))
        ));
        assert!(matches!(
            canon("[18446744073709551615]"),
            Err(JcsError::OutOfRange(_))
        ));
    }

    #[test]
    fn nested_and_whitespace() {
        assert_eq!(
            canon(r#" { "b" : [ true , null , { "z":1, "a":"x" } ], "a" : false } "#).unwrap(),
            r#"{"a":false,"b":[true,null,{"a":"x","z":1}]}"#
        );
    }

    #[test]
    fn without_removes_only_named_member() {
        let v = json!({"hash": "x", "a": {"hash": "keep"}});
        assert_eq!(
            canonicalize_without(&v, "hash").unwrap(),
            r#"{"a":{"hash":"keep"}}"#
        );
    }
}
