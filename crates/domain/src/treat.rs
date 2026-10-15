//! «Juma shirinligi» (SPEC 2B.4): kundalik havas xarajatini rejalashtirilgan davriy ritualga aylantirish.
//!
//! Hozircha faqat haftalik davriylik (hafta kuni bo'yicha, masalan, juma). Bildirishnoma keyingi bosqichda.

use money::Money;
use time::{Date, OffsetDateTime, Weekday};

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// Rejalashtirilgan ritual: nomi, summasi va hafta kuni.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScheduledTreat {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Nomi (masalan, «Juma shirinligi»).
    pub name: String,
    /// Odatiy summa (musbat).
    pub amount: Money,
    /// Hafta kuni.
    pub weekday: Weekday,
    /// Metama'lumot.
    pub meta: Meta,
}

impl ScheduledTreat {
    /// Yangi ritual. Nomi qoidaga javob berishi, summa musbat bo'lishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        name: &str,
        amount: Money,
        weekday: Weekday,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if amount.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            name: validate_name(name)?,
            amount,
            weekday,
            meta: Meta::created(now, origin_device_id),
        })
    }

    /// Shu sanada ritual kuni keladimi.
    pub fn is_due_on(&self, date: Date) -> bool {
        date.weekday() == self.weekday
    }
}

/// Hafta kunining bazadagi indeksi: dushanba = 0, yakshanba = 6.
pub const fn weekday_index(day: Weekday) -> u8 {
    day.number_days_from_monday()
}

/// Indeksdan hafta kuni. Noto'g'ri indeks — `None`.
pub fn weekday_from_index(index: u8) -> Option<Weekday> {
    match index {
        0 => Some(Weekday::Monday),
        1 => Some(Weekday::Tuesday),
        2 => Some(Weekday::Wednesday),
        3 => Some(Weekday::Thursday),
        4 => Some(Weekday::Friday),
        5 => Some(Weekday::Saturday),
        6 => Some(Weekday::Sunday),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::{date, datetime};

    const ID: &str = "0192c000-0000-7000-8000-000000000021";
    const HOUSEHOLD: &str = "0192c000-0000-7000-8000-0000000000aa";

    fn treat(weekday: Weekday) -> ScheduledTreat {
        let now = datetime!(2026-10-15 06:00 UTC);
        ScheduledTreat::create(
            ID,
            HOUSEHOLD,
            "Juma shirinligi",
            Money::new(50_000, Currency::Uzs),
            weekday,
            now,
            "desktop",
        )
        .expect("ritual")
    }

    #[test]
    fn juma_kuni_ritual_kuni() {
        // 2026-10-16 — juma.
        let friday = treat(Weekday::Friday);
        assert!(friday.is_due_on(date!(2026 - 10 - 16)));
        assert!(!friday.is_due_on(date!(2026 - 10 - 17)));
    }

    #[test]
    fn hafta_kuni_indeksi_qaytariladi() {
        for index in 0..7 {
            let day = weekday_from_index(index).expect("kun");
            assert_eq!(weekday_index(day), index);
        }
        assert_eq!(weekday_from_index(7), None);
    }

    #[test]
    fn nol_summali_ritual_rad_etiladi() {
        let now = datetime!(2026-10-15 06:00 UTC);
        let result = ScheduledTreat::create(
            ID,
            HOUSEHOLD,
            "Juma shirinligi",
            Money::new(0, Currency::Uzs),
            Weekday::Friday,
            now,
            "desktop",
        );
        assert_eq!(result, Err(DomainError::AmountNotPositive));
    }
}
