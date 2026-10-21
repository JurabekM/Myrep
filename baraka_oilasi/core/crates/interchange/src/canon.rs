//! Yozuvning kanonik JSON'i va xeshi. Ikkala platforma (Rust, Dart) bir xil baytlarni
//! hosil qiladi: kalitlar Unicode kod nuqtalari bo'yicha saralangan, bo'shliqsiz, UTF-8
//! (ASCII'ga qochirilmaydi), sonlar — faqat butun. Qiymatlar: `null`, butun son, satr yoki
//! `{"b64": "..."}` (BLOB). Kasr son — format xatosi (pul uchun float yo'q).
use data_encoding::BASE64;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::InterchangeError;

/// Jadval yozuvi: ustun nomi → qiymat.
pub type Row = Map<String, Value>;

/// BLOB ustun qiymati: `{"b64": "..."}`.
pub fn blob(bytes: &[u8]) -> Value {
    let mut m = Map::new();
    m.insert("b64".into(), Value::String(BASE64.encode(bytes)));
    Value::Object(m)
}

/// `{"b64": "..."}` → baytlar; boshqa shakl — `None`.
pub fn blob_bytes(v: &Value) -> Option<Vec<u8>> {
    let m = v.as_object()?;
    if m.len() != 1 {
        return None;
    }
    BASE64.decode(m.get("b64")?.as_str()?.as_bytes()).ok()
}

fn write(v: &Value, out: &mut String) -> Result<(), InterchangeError> {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                out.push_str(&i.to_string());
            } else {
                return Err(InterchangeError::Corrupt);
            }
        }
        Value::String(s) => {
            out.push_str(&serde_json::to_string(s).map_err(|_| InterchangeError::Corrupt)?);
        }
        Value::Array(a) => {
            out.push('[');
            for (i, x) in a.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write(x, out)?;
            }
            out.push(']');
        }
        Value::Object(m) => {
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort();
            out.push('{');
            for (i, k) in keys.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push_str(&serde_json::to_string(k).map_err(|_| InterchangeError::Corrupt)?);
                out.push(':');
                if let Some(x) = m.get(*k) {
                    write(x, out)?;
                }
            }
            out.push('}');
        }
    }
    Ok(())
}

/// Kanonik JSON satri.
pub fn canonical(v: &Value) -> Result<String, InterchangeError> {
    let mut out = String::new();
    write(v, &mut out)?;
    Ok(out)
}

/// Yozuv xeshi: `sha256(canonical({"r": row, "t": table}))`, kichik harfli hex.
pub fn row_hash(table: &str, row: &Row) -> Result<String, InterchangeError> {
    let mut m = Map::new();
    m.insert("t".into(), Value::String(table.into()));
    m.insert("r".into(), Value::Object(row.clone()));
    let c = canonical(&Value::Object(m))?;
    Ok(hex::encode(Sha256::digest(c.as_bytes())))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn canonical_is_sorted_and_compact() {
        let v = json!({"b": 1, "a": "oʻ\"\n", "c": null, "d": {"z": -5, "y": [1, "x"]}});
        assert_eq!(
            canonical(&v).unwrap(),
            "{\"a\":\"oʻ\\\"\\n\",\"b\":1,\"c\":null,\"d\":{\"y\":[1,\"x\"],\"z\":-5}}"
        );
        assert_eq!(
            canonical(&json!({"x": 1.5})),
            Err(InterchangeError::Corrupt)
        );
    }

    #[test]
    fn blob_round_trip_and_hash_depends_on_table() {
        let b = blob(&[0, 255, 7]);
        assert_eq!(blob_bytes(&b), Some(vec![0, 255, 7]));
        let mut row = Row::new();
        row.insert("id".into(), json!("1"));
        assert_ne!(row_hash("a", &row).unwrap(), row_hash("b", &row).unwrap());
    }
}
