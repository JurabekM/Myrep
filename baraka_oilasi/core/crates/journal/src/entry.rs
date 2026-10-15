use alloc::string::{String, ToString};
use alloc::vec::Vec;
use core::fmt;

use crate::CanonValue;

/// Jurnal yozuvi turi. Matn ko'rinishi xeshlanadi va o'zgarmaydi.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum EntryKind {
    Contribution,
    Expense,
    Revenue,
    ProfitDistribution,
    LossAllocation,
    Repayment,
    OpeningBalance,
    DutyIncident,
    ReviewAck,
    Correction,
}

impl EntryKind {
    pub const ALL: [EntryKind; 10] = [
        Self::Contribution,
        Self::Expense,
        Self::Revenue,
        Self::ProfitDistribution,
        Self::LossAllocation,
        Self::Repayment,
        Self::OpeningBalance,
        Self::DutyIncident,
        Self::ReviewAck,
        Self::Correction,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Contribution => "CONTRIBUTION",
            Self::Expense => "EXPENSE",
            Self::Revenue => "REVENUE",
            Self::ProfitDistribution => "PROFIT_DISTRIBUTION",
            Self::LossAllocation => "LOSS_ALLOCATION",
            Self::Repayment => "REPAYMENT",
            Self::OpeningBalance => "OPENING_BALANCE",
            Self::DutyIncident => "DUTY_INCIDENT",
            Self::ReviewAck => "REVIEW_ACK",
            Self::Correction => "CORRECTION",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.iter().copied().find(|k| k.as_str() == s)
    }
}

/// Jurnaldagi summa. `minor` kanonik ko'rinishda string bo'ladi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct JournalAmount {
    pub minor: i64,
    pub currency: String,
}

/// Xeshlanadigan maydonlar to'plami (whitelist v1, 6.2).
/// `household_id`, `space_id`, `seq`, `created_at` va boshqalar saqlash qatlamida turadi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct JournalEntry {
    pub id: String,
    pub agreement_id: String,
    pub kind: EntryKind,
    pub party_id: Option<String>,
    pub amount: Option<JournalAmount>,
    /// Lokal sana, `YYYY-MM-DD`.
    pub date: String,
    pub note: Option<String>,
    pub corrects_entry_id: Option<String>,
    pub refs: Vec<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EntryError {
    MissingId,
    MissingAgreementId,
    InvalidDate,
    CorrectionTargetRequired,
    CorrectionTargetNotAllowed,
    EmptyOptionalField,
}

impl EntryError {
    pub const fn code(&self) -> &'static str {
        match self {
            Self::MissingId => "JOURNAL_MISSING_ID",
            Self::MissingAgreementId => "JOURNAL_MISSING_AGREEMENT",
            Self::InvalidDate => "JOURNAL_INVALID_DATE",
            Self::CorrectionTargetRequired => "JOURNAL_CORRECTION_TARGET_REQUIRED",
            Self::CorrectionTargetNotAllowed => "JOURNAL_CORRECTION_TARGET_NOT_ALLOWED",
            Self::EmptyOptionalField => "JOURNAL_EMPTY_OPTIONAL_FIELD",
        }
    }
}

impl fmt::Display for EntryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl core::error::Error for EntryError {}

fn is_valid_date(d: &str) -> bool {
    let b = d.as_bytes();
    if b.len() != 10 || b[4] != b'-' || b[7] != b'-' {
        return false;
    }
    let digits = |r: core::ops::Range<usize>| b[r].iter().all(u8::is_ascii_digit);
    if !(digits(0..4) && digits(5..7) && digits(8..10)) {
        return false;
    }
    let num = |r: core::ops::Range<usize>| {
        b[r].iter()
            .fold(0u32, |acc, c| acc * 10 + u32::from(c - b'0'))
    };
    let (y, m, day) = (num(0..4), num(5..7), num(8..10));
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let max_day = match m {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => return false,
    };
    (1..=max_day).contains(&day)
}

impl JournalEntry {
    /// Yozuvni xeshlashdan oldin tekshiradi.
    pub fn validate(&self) -> Result<(), EntryError> {
        if self.id.is_empty() {
            return Err(EntryError::MissingId);
        }
        if self.agreement_id.is_empty() {
            return Err(EntryError::MissingAgreementId);
        }
        if !is_valid_date(&self.date) {
            return Err(EntryError::InvalidDate);
        }
        let empty = |o: &Option<String>| o.as_deref().is_some_and(str::is_empty);
        if empty(&self.party_id) || empty(&self.note) || empty(&self.corrects_entry_id) {
            return Err(EntryError::EmptyOptionalField);
        }
        match (self.kind, &self.corrects_entry_id) {
            (EntryKind::Correction, None) => Err(EntryError::CorrectionTargetRequired),
            (k, Some(_)) if k != EntryKind::Correction => {
                Err(EntryError::CorrectionTargetNotAllowed)
            }
            _ => Ok(()),
        }
    }

    /// Whitelist bo'yicha kanonik qiymat. Bo'sh ixtiyoriy maydonlar kalit sifatida yozilmaydi.
    pub fn to_canon(&self) -> CanonValue {
        let str_ = |s: &str| CanonValue::Str(s.to_string());
        let mut fields = Vec::with_capacity(9);
        fields.push(("id".to_string(), str_(&self.id)));
        fields.push(("agreementId".to_string(), str_(&self.agreement_id)));
        fields.push(("kind".to_string(), str_(self.kind.as_str())));
        if let Some(p) = &self.party_id {
            fields.push(("partyId".to_string(), str_(p)));
        }
        if let Some(a) = &self.amount {
            fields.push((
                "amount".to_string(),
                CanonValue::Obj(alloc::vec![
                    ("minor".to_string(), CanonValue::Str(a.minor.to_string())),
                    ("currency".to_string(), str_(&a.currency)),
                ]),
            ));
        }
        fields.push(("date".to_string(), str_(&self.date)));
        if let Some(n) = &self.note {
            fields.push(("note".to_string(), str_(n)));
        }
        if let Some(c) = &self.corrects_entry_id {
            fields.push(("correctsEntryId".to_string(), str_(c)));
        }
        if !self.refs.is_empty() {
            fields.push((
                "refs".to_string(),
                CanonValue::Arr(self.refs.iter().map(|r| str_(r)).collect()),
            ));
        }
        CanonValue::Obj(fields)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base() -> JournalEntry {
        JournalEntry {
            id: "e1".into(),
            agreement_id: "a1".into(),
            kind: EntryKind::Contribution,
            party_id: None,
            amount: None,
            date: "2026-10-01".into(),
            note: None,
            corrects_entry_id: None,
            refs: Vec::new(),
        }
    }

    #[test]
    fn dates() {
        for ok in ["2026-10-01", "2024-02-29", "2000-02-29"] {
            assert!(is_valid_date(ok), "{ok}");
        }
        for bad in [
            "2026-1-01",
            "2026-13-01",
            "2026-02-29",
            "1900-02-29",
            "2026-04-31",
            "abcd-ef-gh",
        ] {
            assert!(!is_valid_date(bad), "{bad}");
        }
    }

    #[test]
    fn correction_rules() {
        let mut e = base();
        assert_eq!(e.validate(), Ok(()));
        e.kind = EntryKind::Correction;
        assert_eq!(e.validate(), Err(EntryError::CorrectionTargetRequired));
        e.corrects_entry_id = Some("e0".into());
        assert_eq!(e.validate(), Ok(()));
        e.kind = EntryKind::Expense;
        assert_eq!(e.validate(), Err(EntryError::CorrectionTargetNotAllowed));
    }

    #[test]
    fn empty_optional_rejected() {
        let mut e = base();
        e.note = Some(String::new());
        assert_eq!(e.validate(), Err(EntryError::EmptyOptionalField));
    }

    #[test]
    fn kinds_roundtrip() {
        for k in EntryKind::ALL {
            assert_eq!(EntryKind::parse(k.as_str()), Some(k));
        }
    }
}
