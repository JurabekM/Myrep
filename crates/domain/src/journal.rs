//! Append-only jurnal va xesh-zanjir (SPEC 2F.6, DESKTOP_PROMPT D8A).
//!
//! Har bir yozuv oldingi xeshga bog'lanadi: `hash_n = hex(SHA256(hash_{n-1} + "\n" + JCS(entry_n)))`.
//! Genesis xesh — 64 ta `0`. `JCS` — RFC 8785 kanonik JSON: kalitlar tartibi qat'iy, bo'shliqsiz, pul —
//! satr (`"minor": "300000000"`). Mobil ilova bilan bitma-bit bir xil (`journal_chain.json`).
//!
//! Yozuvni o'zgartirish yoki o'chirish mumkin emas — tuzatish faqat `CORRECTION` yozuvi bilan.
//! DB darajasida bu `BEFORE UPDATE/DELETE` triggerlari bilan ham ta'minlanadi (storage crate).

use money::{Currency, Money};
use sha2::{Digest, Sha256};
use time::Date;

/// Genesis xesh: 64 ta nol (birinchi yozuvning oldingi xeshi).
pub const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

/// Jurnal yozuvi turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JournalKind {
    /// Boshlang'ich balans (og'zaki kelishuv yozib olinganda, `effective_from` o'tmishda bo'lishi mumkin).
    OpeningBalance,
    /// Hissa qo'shish.
    Contribution,
    /// Foyda taqsimoti.
    ProfitDistribution,
    /// Qarz to'lovi (tilxat bo'yicha).
    LoanPayment,
    /// Oldingi yozuvni tuzatish (yangi yozuv; eskisi o'zgarmaydi).
    Correction,
}

impl JournalKind {
    /// Bazadagi va vektordagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::OpeningBalance => "OPENING_BALANCE",
            Self::Contribution => "CONTRIBUTION",
            Self::ProfitDistribution => "PROFIT_DISTRIBUTION",
            Self::LoanPayment => "LOAN_PAYMENT",
            Self::Correction => "CORRECTION",
        }
    }

    /// Koddan tur. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "OPENING_BALANCE" => Some(Self::OpeningBalance),
            "CONTRIBUTION" => Some(Self::Contribution),
            "PROFIT_DISTRIBUTION" => Some(Self::ProfitDistribution),
            "LOAN_PAYMENT" => Some(Self::LoanPayment),
            "CORRECTION" => Some(Self::Correction),
            _ => None,
        }
    }
}

/// Jurnal yozuvi (xesh zanjirining bir bo'g'ini).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JournalEntry {
    /// UUIDv7.
    pub id: String,
    /// Kelishuv (UUIDv7).
    pub agreement_id: String,
    /// Tur.
    pub kind: JournalKind,
    /// Tomon identifikatori (kelishuvdagi `parties[].id`).
    pub party_id: String,
    /// Summa (musbat). Yo'nalish turdan.
    pub amount: Money,
    /// Sana (Toshkent kalendari).
    pub date: Date,
    /// Izoh, bo'lsa. Yo'q bo'lsa JCS'da kalit yozilmaydi.
    pub note: Option<String>,
}

/// JSON satri: RFC 8785 bo'yicha — `"`, `\` va boshqaruv belgilari qochlanadi, qolgani UTF-8 bo'yicha.
fn json_string(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for character in value.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{08}' => out.push_str("\\b"),
            '\t' => out.push_str("\\t"),
            '\n' => out.push_str("\\n"),
            '\u{0c}' => out.push_str("\\f"),
            '\r' => out.push_str("\\r"),
            control if (control as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", control as u32));
            }
            other => out.push(other),
        }
    }
    out.push('"');
    out
}

/// Sana `YYYY-MM-DD` ko'rinishida (kalendar sanasi, vaqt zonasisiz).
fn date_text(date: Date) -> String {
    format!(
        "{:04}-{:02}-{:02}",
        date.year(),
        u8::from(date.month()),
        date.day()
    )
}

fn currency_code(currency: Currency) -> &'static str {
    currency.iso_code()
}

/// Yozuvning kanonik JSON'i (JCS). Kalitlar: `agreementId, amount{currency,minor}, date, id, kind, note, partyId`.
pub fn canonical(entry: &JournalEntry) -> String {
    let mut out = String::from("{");
    out.push_str(&format!(
        "\"agreementId\":{},",
        json_string(&entry.agreement_id)
    ));
    out.push_str(&format!(
        "\"amount\":{{\"currency\":{},\"minor\":{}}},",
        json_string(currency_code(entry.amount.currency())),
        json_string(&entry.amount.minor().to_string())
    ));
    out.push_str(&format!(
        "\"date\":{},",
        json_string(&date_text(entry.date))
    ));
    out.push_str(&format!("\"id\":{},", json_string(&entry.id)));
    out.push_str(&format!("\"kind\":{},", json_string(entry.kind.code())));
    if let Some(note) = &entry.note {
        out.push_str(&format!("\"note\":{},", json_string(note)));
    }
    out.push_str(&format!("\"partyId\":{}", json_string(&entry.party_id)));
    out.push('}');
    out
}

/// Bitta xesh qadami: `hex(SHA256(prev + "\n" + canonical(entry)))`.
pub fn link_hash(previous: &str, entry: &JournalEntry) -> String {
    let mut hasher = Sha256::new();
    hasher.update(previous.as_bytes());
    hasher.update(b"\n");
    hasher.update(canonical(entry).as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Yozuvlar zanjirining barcha xeshlari, tartib bilan.
pub fn chain_hashes(entries: &[JournalEntry]) -> Vec<String> {
    let mut previous = GENESIS_HASH.to_owned();
    let mut out = Vec::with_capacity(entries.len());
    for entry in entries {
        let hash = link_hash(&previous, entry);
        previous.clone_from(&hash);
        out.push(hash);
    }
    out
}

/// Zanjir buzilgan joy. `first_broken` — 1 dan boshlangan tartib raqami (birinchi noto'g'ri yozuv).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ChainBroken {
    /// Birinchi buzilgan yozuv (1 dan).
    pub first_broken: usize,
}

/// Zanjirni saqlangan xeshlar bilan solishtiradi. Qayta hisoblangan xesh saqlangan xeshga teng bo'lishi shart.
/// Yozuvlar soni va xeshlar soni teng bo'lmasa ham buzilish qayd etiladi.
pub fn verify_chain(entries: &[JournalEntry], stored: &[String]) -> Result<(), ChainBroken> {
    let recomputed = chain_hashes(entries);
    for (index, expected) in recomputed.iter().enumerate() {
        if stored.get(index) != Some(expected) {
            return Err(ChainBroken {
                first_broken: index + 1,
            });
        }
    }
    if stored.len() > recomputed.len() {
        return Err(ChainBroken {
            first_broken: recomputed.len() + 1,
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::date;

    fn entry(id: &str, party: &str, minor: i64, note: Option<&str>) -> JournalEntry {
        JournalEntry {
            id: id.to_owned(),
            agreement_id: "0192a000-0000-7000-8000-0000000000a1".to_owned(),
            kind: JournalKind::Contribution,
            party_id: party.to_owned(),
            amount: Money::new(minor, Currency::Uzs),
            date: date!(2026 - 10 - 01),
            note: note.map(str::to_owned),
        }
    }

    #[test]
    fn jcs_kalit_tartibi_va_izoh_yo_qligi() {
        let with_note = entry(
            "0192a000-0000-7000-8000-000000000001",
            "P1",
            5,
            Some("a\"b"),
        );
        assert_eq!(
            canonical(&with_note),
            "{\"agreementId\":\"0192a000-0000-7000-8000-0000000000a1\",\"amount\":{\"currency\":\"UZS\",\"minor\":\"5\"},\"date\":\"2026-10-01\",\"id\":\"0192a000-0000-7000-8000-000000000001\",\"kind\":\"CONTRIBUTION\",\"note\":\"a\\\"b\",\"partyId\":\"P1\"}"
        );
        let without = entry("0192a000-0000-7000-8000-000000000001", "P1", 5, None);
        assert!(!canonical(&without).contains("note"));
    }

    #[test]
    fn zanjir_buzilganda_birinchi_buzilgan_aniqlanadi() {
        let entries = [
            entry("0192a000-0000-7000-8000-000000000001", "P1", 10, None),
            entry("0192a000-0000-7000-8000-000000000002", "P2", 20, None),
        ];
        let stored = chain_hashes(&entries);
        assert_eq!(verify_chain(&entries, &stored), Ok(()));

        let mut tampered = entries.clone();
        tampered[1].amount = Money::new(21, Currency::Uzs);
        assert_eq!(
            verify_chain(&tampered, &stored),
            Err(ChainBroken { first_broken: 2 })
        );
    }

    #[test]
    fn kengaytirilgan_xesh_ortiqcha_xeshda_buziladi() {
        let entries = [entry(
            "0192a000-0000-7000-8000-000000000001",
            "P1",
            10,
            None,
        )];
        let mut stored = chain_hashes(&entries);
        stored.push("x".to_owned());
        assert_eq!(
            verify_chain(&entries, &stored),
            Err(ChainBroken { first_broken: 2 })
        );
    }
}
