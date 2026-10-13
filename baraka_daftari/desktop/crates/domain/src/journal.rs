//! 6-qonun: kelishuv jurnali — faqat qo'shiladigan (append-only) yozuvlar va xesh-zanjir (SPEC 2F.6,
//! `DESKTOP_PROMPT` 5.3 `journal_chain`). Sof hisob; saqlash va DB triggerlari `storage` da.
//!
//! - `hash_n = hex(SHA256(prevHash + "\n" + canonical(entry_n)))`, kichik harflarda. Genesis `prevHash` — 64 ta `0`.
//! - `canonical` — RFC 8785 (JCS): kalitlar UTF-16 kod birliklari bo'yicha tartiblanadi, bo'sh joy yo'q. Sonlar
//!   rad etiladi: pul va boshqa son qiymatlari satr sifatida yoziladi (mobil va desktop bir xil xesh chiqaradi).
//! - Xeshga yozuv mazmuni kiradi. Yozilgan vaqt va qurilma metama'lumot: xeshga kirmaydi (OPEN_QUESTIONS 92).
use money::Money;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::JournalKind;

/// Zanjirning boshlang'ich xeshi: 64 ta `0`.
pub const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
pub enum JournalError {
    /// JCS'da sonlar ishlatilmaydi: pul va son qiymatlari satr ko'rinishida bo'lishi shart.
    #[error("jurnal qiymatida son bo'lmasin: pul va sonlar satr sifatida yoziladi")]
    NumberNotAllowed,
}

impl JournalError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::NumberNotAllowed => "NUMBER_NOT_ALLOWED",
        }
    }
}

/// Xeshlanadigan yozuv mazmuni. Tartib raqami (`seq`) xeshga kirmaydi: u zanjirdagi o'rni bilan aniqlanadi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HashedEntry {
    pub id: String,
    pub agreement_id: String,
    pub kind: JournalKind,
    pub party_id: Option<String>,
    pub amount: Option<Money>,
    /// `YYYY-MM-DD`.
    pub date: String,
    pub note: String,
    /// Manba yozuv identifikatori (masalan, venture yozuvi yoki qarz to'lovi).
    pub reference: Option<String>,
    /// Tuzatilayotgan asl yozuv identifikatori (faqat `CORRECTION`).
    pub corrects: Option<String>,
}

/// RFC 8785 (JCS) kanonik satr. Sonlar uchun xato qaytaradi.
///
/// # Errors
/// Qiymat ichida son (butun yoki kasr) bo'lsa [`JournalError::NumberNotAllowed`].
pub fn canonical(value: &Value) -> Result<String, JournalError> {
    let mut out = String::new();
    write_value(value, &mut out)?;
    Ok(out)
}

fn write_value(value: &Value, out: &mut String) -> Result<(), JournalError> {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(_) => return Err(JournalError::NumberNotAllowed),
        Value::String(s) => write_string(s, out),
        Value::Array(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write_value(item, out)?;
            }
            out.push(']');
        }
        Value::Object(map) => write_object(map, out)?,
    }
    Ok(())
}

fn write_object(map: &Map<String, Value>, out: &mut String) -> Result<(), JournalError> {
    let mut keys: Vec<&String> = map.keys().collect();
    // JCS: tartiblash UTF-8 bayt emas, UTF-16 kod birliklari bo'yicha (non-BMP belgilar BMP'dan oldin).
    keys.sort_by(|a, b| a.encode_utf16().cmp(b.encode_utf16()));
    out.push('{');
    for (i, key) in keys.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        write_string(key, out);
        out.push(':');
        if let Some(v) = map.get(*key) {
            write_value(v, out)?;
        }
    }
    out.push('}');
    Ok(())
}

/// JCS satr escape: `"` va `\`, boshqaruv belgilari (`< 0x20`) — qisqa shakl yoki `\u00xx` (kichik harf).
/// Boshqa belgilar (jumladan ʻ, ʼ va emoji) xom UTF-8 holida qoladi.
fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{08}' => out.push_str("\\b"),
            '\u{09}' => out.push_str("\\t"),
            '\u{0a}' => out.push_str("\\n"),
            '\u{0c}' => out.push_str("\\f"),
            '\u{0d}' => out.push_str("\\r"),
            c if u32::from(c) < 0x20 => out.push_str(&format!("\\u{:04x}", u32::from(c))),
            c => out.push(c),
        }
    }
    out.push('"');
}

/// Xeshlanadigan JSON qiymati. Maydonlar faqat mavjud bo'lsa qo'shiladi (`None` — kalit yo'q).
#[must_use]
pub fn entry_value(e: &HashedEntry) -> Value {
    let mut m = Map::new();
    m.insert("id".into(), Value::String(e.id.clone()));
    m.insert("agreementId".into(), Value::String(e.agreement_id.clone()));
    m.insert("kind".into(), Value::String(e.kind.as_str().into()));
    m.insert("date".into(), Value::String(e.date.clone()));
    m.insert("note".into(), Value::String(e.note.clone()));
    if let Some(p) = &e.party_id {
        m.insert("partyId".into(), Value::String(p.clone()));
    }
    if let Some(a) = e.amount {
        let mut amount = Map::new();
        amount.insert("minor".into(), Value::String(a.minor().to_string()));
        amount.insert("currency".into(), Value::String(a.currency().code().into()));
        m.insert("amount".into(), Value::Object(amount));
    }
    if let Some(r) = &e.reference {
        m.insert("ref".into(), Value::String(r.clone()));
    }
    if let Some(c) = &e.corrects {
        m.insert("corrects".into(), Value::String(c.clone()));
    }
    Value::Object(m)
}

/// Bitta yozuvning kanonik satri.
///
/// # Errors
/// Son qiymati bo'lsa (bu yerda bunday bo'lmaydi, ammo kelajakdagi maydonlar uchun himoya).
pub fn entry_canonical(e: &HashedEntry) -> Result<String, JournalError> {
    canonical(&entry_value(e))
}

/// `hex(SHA256(prevHash + "\n" + canonical))`, kichik harflarda.
#[must_use]
pub fn link_hash(prev_hash: &str, canonical_entry: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(prev_hash.as_bytes());
    hasher.update(b"\n");
    hasher.update(canonical_entry.as_bytes());
    hex(hasher.finalize().as_slice())
}

/// Matnning SHA-256 xeshi (hex, kichik harf). Kelishuv versiyasi mazmuni uchun.
#[must_use]
pub fn sha256_hex(text: &str) -> String {
    hex(Sha256::digest(text.as_bytes()).as_slice())
}

/// Bitta yozuvning xeshi (oldingi xesh bilan).
///
/// # Errors
/// [`entry_canonical`] dagi xato.
pub fn entry_hash(prev_hash: &str, e: &HashedEntry) -> Result<String, JournalError> {
    Ok(link_hash(prev_hash, &entry_canonical(e)?))
}

/// Zanjir boshi — oxirgi yozuvning xeshi. Bo'sh zanjir uchun genesis.
///
/// # Errors
/// [`entry_hash`] dagi xato.
pub fn chain_head(entries: &[HashedEntry]) -> Result<String, JournalError> {
    let mut prev = GENESIS_HASH.to_owned();
    for e in entries {
        prev = entry_hash(&prev, e)?;
    }
    Ok(prev)
}

/// Saqlangan xeshlar bilan solishtiradi (`entries[i] = (yozuv, saqlangan xesh)`).
/// Birinchi buzilgan yozuvning tartib raqamini (1 dan boshlab) qaytaradi; zanjir to'g'ri bo'lsa `None`.
///
/// # Errors
/// [`entry_hash`] dagi xato.
pub fn first_broken(entries: &[(HashedEntry, String)]) -> Result<Option<usize>, JournalError> {
    let mut prev = GENESIS_HASH.to_owned();
    for (i, (entry, stored)) in entries.iter().enumerate() {
        let expected = entry_hash(&prev, entry)?;
        if &expected != stored {
            return Ok(Some(i + 1));
        }
        prev = expected;
    }
    Ok(None)
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use money::{Currency, Money};
    use serde_json::json;

    use super::*;

    fn entry(id: &str, minor: i64, note: &str) -> HashedEntry {
        HashedEntry {
            id: id.into(),
            agreement_id: "0192a000-0000-7000-8000-0000000000a1".into(),
            kind: JournalKind::Contribution,
            party_id: Some("P1".into()),
            amount: Some(Money::new(minor, Currency::Uzs)),
            date: "2026-10-01".into(),
            note: note.into(),
            reference: None,
            corrects: None,
        }
    }

    #[test]
    fn keys_are_sorted_by_utf16_code_units() {
        // U+1F600 (surrogat juftligi D83D…) U+FF5E dan oldin turishi kerak; UTF-8 tartibi buni aks ettiradi.
        let v = json!({"\u{ff5e}": "a", "\u{1f600}": "b"});
        assert_eq!(
            canonical(&v).unwrap(),
            "{\"\u{1f600}\":\"b\",\"\u{ff5e}\":\"a\"}"
        );
    }

    #[test]
    fn uzbek_letters_stay_raw_and_controls_are_escaped() {
        let v = json!({"note": "oʻzbek gʻalla \"x\" \\ \n\u{1}"});
        assert_eq!(
            canonical(&v).unwrap(),
            "{\"note\":\"oʻzbek gʻalla \\\"x\\\" \\\\ \\n\\u0001\"}"
        );
    }

    #[test]
    fn numbers_are_rejected() {
        assert_eq!(
            canonical(&json!({"minor": 300000000})),
            Err(JournalError::NumberNotAllowed)
        );
        assert_eq!(
            canonical(&json!([1.5])),
            Err(JournalError::NumberNotAllowed)
        );
    }

    #[test]
    fn empty_chain_is_genesis() {
        assert_eq!(chain_head(&[]).unwrap(), GENESIS_HASH);
        assert_eq!(GENESIS_HASH.len(), 64);
    }

    #[test]
    fn chain_head_depends_on_order_and_content() {
        let a = entry("0192a000-0000-7000-8000-000000000001", 300_000_000, "A");
        let b = entry("0192a000-0000-7000-8000-000000000002", 300_000_000, "B");
        let ab = chain_head(&[a.clone(), b.clone()]).unwrap();
        let ba = chain_head(&[b.clone(), a.clone()]).unwrap();
        assert_ne!(ab, ba);
        let tampered = entry("0192a000-0000-7000-8000-000000000002", 300_000_001, "B");
        assert_ne!(ab, chain_head(&[a, tampered]).unwrap());
    }

    #[test]
    fn first_broken_points_at_the_tampered_entry() {
        let e1 = entry("0192a000-0000-7000-8000-000000000001", 1, "1");
        let e2 = entry("0192a000-0000-7000-8000-000000000002", 2, "2");
        let e3 = entry("0192a000-0000-7000-8000-000000000003", 3, "3");
        let h1 = entry_hash(GENESIS_HASH, &e1).unwrap();
        let h2 = entry_hash(&h1, &e2).unwrap();
        let h3 = entry_hash(&h2, &e3).unwrap();
        let good = vec![
            (e1.clone(), h1.clone()),
            (e2.clone(), h2),
            (e3.clone(), h3.clone()),
        ];
        assert_eq!(first_broken(&good).unwrap(), None);
        let mut bad = e2;
        bad.amount = Some(Money::new(3, Currency::Uzs));
        let broken = vec![(e1, h1), (bad, good[1].1.clone()), (e3, h3)];
        assert_eq!(first_broken(&broken).unwrap(), Some(2));
    }

    #[test]
    fn hashes_are_lowercase_hex_of_64_chars() {
        let h = link_hash(GENESIS_HASH, "{}");
        assert_eq!(h.len(), 64);
        assert!(h
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()));
    }
}
