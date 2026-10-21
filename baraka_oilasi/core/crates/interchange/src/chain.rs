//! Kelishuv jurnali importi (6.6). Kelgan zanjir to'liq qayta hisoblanadi (telefondan kelgan
//! xeshlar desktopda ham mos kelishi shart), keyin mahalliy nusxa bilan solishtiriladi.
//! Ayrilish (fork) — import to'xtaydi; hech qachon avtomatik birlashtirilmaydi.
use baraka_journal::{compute_chain, JournalEntry};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ChainOutcome {
    /// Ikkala tomonda bir xil.
    Same,
    /// Kelgan zanjir mahalliyning davomi: `from` (1 dan) dan boshlab yangi yozuvlar qo'shiladi.
    Append { from: usize },
    /// Mahalliy zanjir uzunroq, kelgani uning boshlang'ich qismi — hech narsa qilinmaydi.
    LocalAhead,
    /// `seq` dagi yozuv ikki tomonda farq qiladi — ayrilish.
    Fork { seq: usize },
    /// Kelgan zanjirdagi xesh qayta hisoblanganiga mos emas (fayldagi yozuv o'zgartirilgan).
    Tampered { seq: usize },
}

/// `local` — mahalliy xeshlar (seq tartibida), `incoming` va `incoming_hashes` — fayldagi
/// yozuvlar (seq 1 dan uzluksiz, tartiblangan).
pub fn check(
    local: &[String],
    incoming: &[JournalEntry],
    incoming_hashes: &[String],
) -> ChainOutcome {
    if incoming.len() != incoming_hashes.len() {
        return ChainOutcome::Tampered { seq: 1 };
    }
    let computed = match compute_chain(incoming) {
        Ok(h) => h,
        Err(_) => return ChainOutcome::Tampered { seq: 1 },
    };
    if let Some(i) = computed
        .iter()
        .zip(incoming_hashes)
        .position(|(a, b)| a != b)
    {
        return ChainOutcome::Tampered { seq: i + 1 };
    }
    if let Some(i) = local.iter().zip(&computed).position(|(a, b)| a != b) {
        return ChainOutcome::Fork { seq: i + 1 };
    }
    match computed.len().cmp(&local.len()) {
        std::cmp::Ordering::Equal => ChainOutcome::Same,
        std::cmp::Ordering::Less => ChainOutcome::LocalAhead,
        std::cmp::Ordering::Greater => ChainOutcome::Append {
            from: local.len() + 1,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_journal::{EntryKind, JournalAmount};

    fn entry(id: &str, minor: i64) -> JournalEntry {
        JournalEntry {
            id: id.into(),
            agreement_id: "a1".into(),
            kind: EntryKind::Revenue,
            party_id: None,
            amount: Some(JournalAmount {
                minor,
                currency: "UZS".into(),
            }),
            date: "2026-11-05".into(),
            note: None,
            corrects_entry_id: None,
            refs: Vec::new(),
        }
    }

    #[test]
    fn outcomes() {
        let base = vec![entry("e1", 100), entry("e2", 200), entry("e3", 300)];
        let h = compute_chain(&base).unwrap_or_default();
        assert_eq!(check(&h, &base, &h), ChainOutcome::Same);
        assert_eq!(check(&h[..1], &base, &h), ChainOutcome::Append { from: 2 });
        assert_eq!(check(&h, &base[..2], &h[..2]), ChainOutcome::LocalAhead);
        // Mahalliy 2-yozuv boshqacha — ayrilish.
        let mut other = base.clone();
        other[1] = entry("e2b", 250);
        let oh = compute_chain(&other).unwrap_or_default();
        assert_eq!(check(&oh, &base, &h), ChainOutcome::Fork { seq: 2 });
        // Fayldagi summa o'zgartirilgan, xesh esa eski.
        let mut forged = base.clone();
        forged[2] = entry("e3", 999);
        assert_eq!(check(&h, &forged, &h), ChainOutcome::Tampered { seq: 3 });
    }
}
