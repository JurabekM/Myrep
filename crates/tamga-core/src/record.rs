//! Yozuv maydonlari va yozuv xeshi (spec §3).

use serde_json::{Map, Value};

use crate::digest::Digest;
use crate::jcs::{self, JcsError};

/// RFC 9162 leaf prefiksi: yozuv xeshi Merkle barg xeshi bilan bir xil bo'ladi.
pub const LEAF_PREFIX: u8 = 0x00;

/// Yozuvchi o'zi qo'yadigan maydonlar — chaqiruvchi ularni bera olmaydi.
pub const RESERVED: [&str; 7] = ["tamga", "log", "seq", "ts", "session", "event", "prev"];

/// Spec §3.3 dagi ma'lum hodisalar. Noma'lumlari qabul qilinadi, lekin ogohlantirish beriladi.
pub const KNOWN_EVENTS: [&str; 8] = [
    "session.start",
    "session.end",
    "prompt",
    "tool.pre",
    "tool.post",
    "decision.human",
    "os.observed",
    "key.rotate",
];

/// `hash = H(0x00 || JCS(record \ "hash"))`.
pub fn record_hash(record: &Value) -> Result<Digest, JcsError> {
    let body = jcs::canonicalize_without(record, "hash")?;
    Ok(Digest::of(&[&[LEAF_PREFIX], body.as_bytes()]))
}

/// Tekshirilgan majburiy maydonlar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Header {
    pub log: String,
    pub seq: u64,
    pub ts: String,
    pub event: String,
    pub prev: Digest,
    pub hash: Digest,
}

/// Majburiy maydonlarni va ma'lum ixtiyoriy maydonlar shaklini tekshiradi (`E_FIELD` holatlari).
/// `tamga` versiyasi alohida (`E_VERSION`) tekshiriladi.
pub fn parse_header(map: &Map<String, Value>) -> Result<Header, String> {
    let s = |k: &str| -> Result<&str, String> {
        map.get(k)
            .and_then(Value::as_str)
            .ok_or_else(|| format!("`{k}` satr bo'lishi shart"))
    };
    let digest = |k: &str| -> Result<Digest, String> {
        Digest::parse(s(k)?).ok_or_else(|| format!("`{k}` sha256:<64 hex> bo'lishi shart"))
    };

    let log = s("log")?;
    if !valid_log_id(log) {
        return Err("`log` 1–128 belgi, [A-Za-z0-9._:-]".into());
    }
    let seq = map
        .get("seq")
        .and_then(Value::as_u64)
        .ok_or("`seq` manfiy bo'lmagan butun son bo'lishi shart")?;
    let ts = s("ts")?;
    if !valid_timestamp(ts) {
        return Err("`ts` YYYY-MM-DDTHH:MM:SS.sssZ shaklida bo'lishi shart".into());
    }
    if s("session")?.is_empty() {
        return Err("`session` bo'sh bo'lmasligi shart".into());
    }
    let event = s("event")?;
    if event.is_empty() {
        return Err("`event` bo'sh bo'lmasligi shart".into());
    }
    let prev = digest("prev")?;
    let hash = digest("hash")?;

    check_optional(map)?;

    Ok(Header {
        log: log.to_owned(),
        seq,
        ts: ts.to_owned(),
        event: event.to_owned(),
        prev,
        hash,
    })
}

fn check_optional(map: &Map<String, Value>) -> Result<(), String> {
    if let Some(d) = map.get("decision") {
        let verdict = d.get("verdict").and_then(Value::as_str);
        if !matches!(verdict, Some("allow" | "deny" | "ask")) {
            return Err("`decision.verdict` allow|deny|ask bo'lishi shart".into());
        }
        let by = d.get("by").and_then(Value::as_str);
        if !matches!(by, Some("policy" | "human" | "default")) {
            return Err("`decision.by` policy|human|default bo'lishi shart".into());
        }
    }
    if let Some(t) = map.get("tool") {
        if t.get("name").and_then(Value::as_str).is_none() {
            return Err("`tool.name` satr bo'lishi shart".into());
        }
        if let Some(input) = t.get("input") {
            check_payload_ref(input, "tool.input")?;
        }
    }
    if let Some(r) = map.get("result") {
        check_payload_ref(r, "result")?;
    }
    if let Some(r) = map.get("ref")
        && r.as_u64().is_none()
    {
        return Err("`ref` manfiy bo'lmagan butun son bo'lishi shart".into());
    }
    if let Some(e) = map.get("ext")
        && !e.is_object()
    {
        return Err("`ext` obyekt bo'lishi shart".into());
    }
    Ok(())
}

fn check_payload_ref(v: &Value, name: &str) -> Result<(), String> {
    let digest_ok = v
        .get("digest")
        .and_then(Value::as_str)
        .and_then(Digest::parse)
        .is_some();
    let size_ok = v.get("size").and_then(Value::as_u64).is_some();
    if digest_ok && size_ok {
        Ok(())
    } else {
        Err(format!(
            "`{name}` payload-ref {{digest, size}} bo'lishi shart"
        ))
    }
}

pub fn valid_log_id(s: &str) -> bool {
    (1..=128).contains(&s.len())
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b':' | b'-'))
}

/// `YYYY-MM-DDTHH:MM:SS.sssZ`, aynan 24 belgi, maydonlar oralig'i tekshiriladi.
pub fn valid_timestamp(s: &str) -> bool {
    let b = s.as_bytes();
    if b.len() != 24 {
        return false;
    }
    let shape = b"dddd-dd-ddTdd:dd:dd.dddZ";
    if !b.iter().zip(shape).all(|(c, p)| match p {
        b'd' => c.is_ascii_digit(),
        _ => c == p,
    }) {
        return false;
    }
    let n = |r: std::ops::Range<usize>| s[r].parse::<u32>().unwrap_or(u32::MAX);
    let (year, month, day) = (n(0..4), n(5..7), n(8..10));
    let days_in_month = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if (year % 4 == 0 && year % 100 != 0) || year % 400 == 0 => 29,
        2 => 28,
        _ => return false,
    };
    (1..=days_in_month).contains(&day) && n(11..13) < 24 && n(14..16) < 60 && n(17..19) < 60
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timestamps() {
        assert!(valid_timestamp("2026-10-17T10:41:07.118Z"));
        assert!(valid_timestamp("2024-02-29T23:59:59.999Z"));
        assert!(!valid_timestamp("2026-02-29T00:00:00.000Z"), "kabisa emas");
        assert!(
            !valid_timestamp("2026-10-17T10:41:07Z"),
            "millisekund shart"
        );
        assert!(
            !valid_timestamp("2026-10-17T10:41:07.118+05:00"),
            "faqat UTC"
        );
        assert!(!valid_timestamp("2026-13-01T00:00:00.000Z"));
        assert!(!valid_timestamp("2026-10-17T24:00:00.000Z"));
        assert!(!valid_timestamp("2026-10-17 10:41:07.118Z"));
    }

    #[test]
    fn log_ids() {
        assert!(valid_log_id("tamga:host-1.cc_session"));
        assert!(!valid_log_id(""));
        assert!(!valid_log_id("bo'sh joy"));
        assert!(!valid_log_id(&"a".repeat(129)));
    }
}
