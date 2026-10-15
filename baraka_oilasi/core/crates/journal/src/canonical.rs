use alloc::string::String;
use alloc::vec::Vec;

/// Jurnalda ruxsat etilgan JSON qiymatlari: faqat string, massiv va obyekt.
/// `null`, son va mantiqiy qiymatlar tipda umuman yo'q (6.2).
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CanonValue {
    Str(String),
    Arr(Vec<CanonValue>),
    Obj(Vec<(String, CanonValue)>),
}

fn write_string(out: &mut String, s: &str) {
    const HEX: &[u8; 16] = b"0123456789abcdef";
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
            c if (c as u32) < 0x20 => {
                let v = c as u32;
                out.push_str("\\u00");
                out.push(char::from(HEX[(v >> 4) as usize]));
                out.push(char::from(HEX[(v & 0xF) as usize]));
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

fn utf16_key(s: &str) -> Vec<u16> {
    s.encode_utf16().collect()
}

fn write_value(out: &mut String, value: &CanonValue) {
    match value {
        CanonValue::Str(s) => write_string(out, s),
        CanonValue::Arr(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write_value(out, item);
            }
            out.push(']');
        }
        CanonValue::Obj(fields) => {
            let mut sorted: Vec<&(String, CanonValue)> = fields.iter().collect();
            sorted.sort_by_key(|(k, _)| utf16_key(k));
            out.push('{');
            for (i, (k, v)) in sorted.into_iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write_string(out, k);
                out.push(':');
                write_value(out, v);
            }
            out.push('}');
        }
    }
}

/// RFC 8785 bo'yicha kanonik JSON matni.
pub fn canonical_json(value: &CanonValue) -> String {
    let mut out = String::new();
    write_value(&mut out, value);
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloc::vec;

    fn s(v: &str) -> CanonValue {
        CanonValue::Str(v.into())
    }

    #[test]
    fn sorts_keys_and_escapes() {
        let v = CanonValue::Obj(vec![
            ("b".into(), s("x\"y\\z\n\u{01}")),
            ("a".into(), CanonValue::Arr(vec![s("1"), s("oʻgʻ")])),
        ]);
        assert_eq!(
            canonical_json(&v),
            "{\"a\":[\"1\",\"oʻgʻ\"],\"b\":\"x\\\"y\\\\z\\n\\u0001\"}"
        );
    }

    #[test]
    fn utf16_ordering_differs_from_utf8() {
        // U+FF61 UTF-8 da U+1F600 dan kichik, UTF-16 da esa katta (surrogat 0xD83D < 0xFF61).
        let v = CanonValue::Obj(vec![
            ("\u{FF61}".into(), s("1")),
            ("\u{1F600}".into(), s("2")),
        ]);
        assert_eq!(
            canonical_json(&v),
            "{\"\u{1F600}\":\"2\",\"\u{FF61}\":\"1\"}"
        );
    }
}
