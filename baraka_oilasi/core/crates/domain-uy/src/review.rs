//! 6-qonun: ochiq hisob ko'rigi va yillik yangilash (uy/SPEC 2F.3, 2F.5, 2F.6).
//!
//! * Bayonnomada o'sha paytdagi zanjir boshi (`seq`, `head`) qayd etiladi. Keyin yozuv
//!   o'zgartirilsa: xeshsiz — `ChainBroken`, xeshlar qayta hisoblangan bo'lsa — `HeadMismatch`.
//!   Vektorlar: `review_protocol`.
//! * Ko'rik muddati shartnomaning 6-savolidagi davriylikdan, yangilash eslatmasi 9-savoldagi
//!   `reviewDate` dan 30 kun oldin. Eslatmalar saqlangan sanalardan hisoblanadi — qurilma qayta
//!   yoqilganda ham yo'qolmaydi.
use baraka_journal::{compute_chain, ChainError, JournalEntry, GENESIS_HASH};
use chrono::{Days, NaiveDate};

use crate::DomainError;

/// Yillik yangilash eslatmasi shuncha kun oldin chiqadi (2F.3).
pub const RENEWAL_LEAD_DAYS: u64 = 30;
/// Ko'rik eslatmasi shuncha kun oldin chiqadi.
pub const REVIEW_LEAD_DAYS: u64 = 3;
/// 6-savolda davriylik yozilmagan bo'lsa — oyiga bir marta.
pub const DEFAULT_REVIEW_EVERY_DAYS: u32 = 30;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProtocolStatus {
    Intact,
    /// Saqlangan xesh qayta hisoblanganga mos emas (1 dan boshlanadigan tartib raqami).
    ChainBroken {
        seq: usize,
    },
    HeadMismatch,
    Truncated,
}

impl ProtocolStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Intact => "INTACT",
            Self::ChainBroken { .. } => "CHAIN_BROKEN",
            Self::HeadMismatch => "HEAD_MISMATCH",
            Self::Truncated => "TRUNCATED",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProtocolCheck {
    pub status: ProtocolStatus,
    /// Bayonnomadan keyin qo'shilgan yozuvlar (masalan, tuzatishlar).
    pub entries_after: usize,
}

/// Bayonnomadagi zanjir boshini joriy jurnal bilan solishtiradi.
pub fn check_protocol(
    entries: &[JournalEntry],
    stored: &[String],
    protocol_seq: usize,
    protocol_head: &str,
) -> Result<ProtocolCheck, DomainError> {
    if stored.len() != entries.len() {
        return Err(DomainError::new("INVALID_PROTOCOL"));
    }
    if entries.len() < protocol_seq {
        return Ok(ProtocolCheck {
            status: ProtocolStatus::Truncated,
            entries_after: 0,
        });
    }
    let after = entries.len() - protocol_seq;
    let hashes = compute_chain(entries).map_err(|e| match e {
        ChainError::InvalidEntry { .. } => DomainError::new("JOURNAL_INVALID_ENTRY"),
        _ => DomainError::new("INVALID_PROTOCOL"),
    })?;
    if let Some(i) = hashes.iter().zip(stored).position(|(a, b)| a != b) {
        return Ok(ProtocolCheck {
            status: ProtocolStatus::ChainBroken { seq: i + 1 },
            entries_after: after,
        });
    }
    let at = match protocol_seq {
        0 => GENESIS_HASH,
        n => hashes[n - 1].as_str(),
    };
    Ok(ProtocolCheck {
        status: if at == protocol_head {
            ProtocolStatus::Intact
        } else {
            ProtocolStatus::HeadMismatch
        },
        entries_after: after,
    })
}

/// Keyingi ko'rik sanasi: oxirgi ko'rik (yoki sheriklik boshi) + davriylik.
pub fn next_review_due(anchor: NaiveDate, every_days: u32) -> Option<NaiveDate> {
    let days = if every_days == 0 {
        DEFAULT_REVIEW_EVERY_DAYS
    } else {
        every_days
    };
    anchor.checked_add_days(Days::new(u64::from(days)))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reminder {
    /// Muddatgacha `days` kun qoldi.
    Upcoming {
        days: i64,
    },
    Due,
    Overdue {
        days: i64,
    },
}

impl Reminder {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Upcoming { .. } => "UPCOMING",
            Self::Due => "DUE",
            Self::Overdue { .. } => "OVERDUE",
        }
    }
}

/// `due` dan `lead_days` oldin eslatma boshlanadi; undan oldin — eslatma yo'q.
pub fn reminder(today: NaiveDate, due: NaiveDate, lead_days: u64) -> Option<Reminder> {
    let start = due.checked_sub_days(Days::new(lead_days))?;
    let diff = (due - today).num_days();
    if today < start {
        None
    } else if diff > 0 {
        Some(Reminder::Upcoming { days: diff })
    } else if diff == 0 {
        Some(Reminder::Due)
    } else {
        Some(Reminder::Overdue { days: -diff })
    }
}

/// Yillik yangilashdan keyingi ko'rib chiqish sanasi (bir yil keyin).
pub fn renewed_review_date(review_date: NaiveDate) -> Option<NaiveDate> {
    review_date.checked_add_months(chrono::Months::new(12))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap_or_default()
    }

    #[test]
    fn schedule_and_reminders() {
        assert_eq!(next_review_due(d("2026-11-01"), 30), Some(d("2026-12-01")));
        assert_eq!(next_review_due(d("2026-11-01"), 0), Some(d("2026-12-01")));
        let due = d("2027-11-01");
        assert_eq!(reminder(d("2027-10-01"), due, RENEWAL_LEAD_DAYS), None);
        assert_eq!(
            reminder(d("2027-10-02"), due, RENEWAL_LEAD_DAYS),
            Some(Reminder::Upcoming { days: 30 })
        );
        assert_eq!(reminder(due, due, 3), Some(Reminder::Due));
        assert_eq!(
            reminder(d("2027-11-05"), due, 3),
            Some(Reminder::Overdue { days: 4 })
        );
        assert_eq!(renewed_review_date(d("2027-02-28")), Some(d("2028-02-28")));
    }
}
