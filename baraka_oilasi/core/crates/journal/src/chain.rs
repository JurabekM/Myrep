use alloc::string::String;
use alloc::vec::Vec;
use core::fmt;

use sha2::{Digest, Sha256};

use crate::{canonical_json, EntryError, JournalEntry};

/// Har bir kelishuv zanjirining boshlang'ich `prev_hash` qiymati.
pub const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ChainError {
    /// Yozuvning o'zi noto'g'ri (1 dan boshlanadigan tartib raqami bilan).
    InvalidEntry { seq: usize, error: EntryError },
    /// Saqlangan xesh qayta hisoblangan bilan mos emas — birinchi buzilgan joy.
    FirstBroken { seq: usize },
    /// Yozuvlar va xeshlar soni teng emas.
    LengthMismatch,
}

impl ChainError {
    pub const fn code(&self) -> &'static str {
        match self {
            Self::InvalidEntry { .. } => "JOURNAL_INVALID_ENTRY",
            Self::FirstBroken { .. } => "JOURNAL_CHAIN_BROKEN",
            Self::LengthMismatch => "JOURNAL_LENGTH_MISMATCH",
        }
    }
}

impl fmt::Display for ChainError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl core::error::Error for ChainError {}

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push(char::from(HEX[usize::from(b >> 4)]));
        s.push(char::from(HEX[usize::from(b & 0x0F)]));
    }
    s
}

/// `hex(SHA256(prev_hash + "\n" + canonical(entry)))`.
pub fn chain_hash(prev_hash: &str, entry: &JournalEntry) -> String {
    let mut h = Sha256::new();
    h.update(prev_hash.as_bytes());
    h.update(b"\n");
    h.update(canonical_json(&entry.to_canon()).as_bytes());
    hex_lower(&h.finalize())
}

/// Butun zanjir xeshlari (genesis'dan boshlab).
pub fn compute_chain(entries: &[JournalEntry]) -> Result<Vec<String>, ChainError> {
    let mut prev = String::from(GENESIS_HASH);
    let mut out = Vec::with_capacity(entries.len());
    for (i, e) in entries.iter().enumerate() {
        e.validate()
            .map_err(|error| ChainError::InvalidEntry { seq: i + 1, error })?;
        let h = chain_hash(&prev, e);
        out.push(h.clone());
        prev = h;
    }
    Ok(out)
}

/// Saqlangan xeshlarni qayta hisoblab tekshiradi. Muvaffaqiyatda zanjir boshini
/// (`chain_head`, bo'sh zanjirda genesis) qaytaradi.
pub fn verify_chain(entries: &[JournalEntry], stored: &[String]) -> Result<String, ChainError> {
    if entries.len() != stored.len() {
        return Err(ChainError::LengthMismatch);
    }
    let mut prev = String::from(GENESIS_HASH);
    for (i, (e, s)) in entries.iter().zip(stored).enumerate() {
        e.validate()
            .map_err(|error| ChainError::InvalidEntry { seq: i + 1, error })?;
        let h = chain_hash(&prev, e);
        if &h != s {
            return Err(ChainError::FirstBroken { seq: i + 1 });
        }
        prev = h;
    }
    Ok(prev)
}

/// Bayonnoma uchun qisqa kod: birinchi 16 hex belgi, 4 ta guruh, katta harflarda (6.5).
pub fn short_code(chain_head: &str) -> String {
    let mut out = String::with_capacity(19);
    for (i, c) in chain_head.chars().take(16).enumerate() {
        if i > 0 && i % 4 == 0 {
            out.push('-');
        }
        out.push(c.to_ascii_uppercase());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{EntryKind, JournalAmount};
    use alloc::string::ToString;
    use alloc::vec;

    const AGR: &str = "0192a000-0000-7000-8000-0000000000a1";

    fn entry(
        n: u8,
        kind: EntryKind,
        party: &str,
        minor: i64,
        date: &str,
        note: &str,
    ) -> JournalEntry {
        JournalEntry {
            id: alloc::format!("0192a000-0000-7000-8000-00000000000{n}"),
            agreement_id: AGR.to_string(),
            kind,
            party_id: Some(party.to_string()),
            amount: Some(JournalAmount {
                minor,
                currency: "UZS".to_string(),
            }),
            date: date.to_string(),
            note: Some(note.to_string()),
            corrects_entry_id: None,
            refs: Vec::new(),
        }
    }

    fn documented() -> Vec<JournalEntry> {
        vec![
            entry(
                1,
                EntryKind::Contribution,
                "P1",
                300_000_000,
                "2026-10-01",
                "Anvar hissasi",
            ),
            entry(
                2,
                EntryKind::Contribution,
                "P2",
                300_000_000,
                "2026-10-01",
                "Dilshod hissasi",
            ),
            entry(
                3,
                EntryKind::ProfitDistribution,
                "P1",
                140_000_000,
                "2026-10-31",
                "1-oy foyda ulushi",
            ),
        ]
    }

    #[test]
    fn documented_hashes() {
        let hashes = compute_chain(&documented()).unwrap();
        assert_eq!(
            hashes,
            vec![
                "e6ae98e545c7438c7de424286aa8f624493748c85a7f8cd79f2c576eb4f25b9e",
                "fa5d38ce32acd7beb4128a85231bbba0f2d7fc8081bc27024c1f1c4904257b53",
                "ba06ad59d6c270a58182a304bd376535d814dd210520f8359a4969f870b26903",
            ]
        );
        assert_eq!(short_code(&hashes[0]), "E6AE-98E5-45C7-438C");
        assert_eq!(verify_chain(&documented(), &hashes), Ok(hashes[2].clone()));
    }

    #[test]
    fn tampering_is_located() {
        let hashes = compute_chain(&documented()).unwrap();
        let mut tampered = documented();
        if let Some(a) = tampered[1].amount.as_mut() {
            a.minor = 300_000_001;
        }
        assert_eq!(
            verify_chain(&tampered, &hashes),
            Err(ChainError::FirstBroken { seq: 2 })
        );
        assert_eq!(
            verify_chain(&tampered, &hashes[..2]),
            Err(ChainError::LengthMismatch)
        );
    }

    #[test]
    fn empty_chain_head_is_genesis() {
        assert_eq!(verify_chain(&[], &[]), Ok(GENESIS_HASH.to_string()));
    }
}
