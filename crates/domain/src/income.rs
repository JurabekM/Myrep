//! Daromad (SPEC 2.1): manba, kanal, sana, oila a'zosi va summa.

use money::Money;
use time::{Date, OffsetDateTime};

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// To'lov kanali: naqd yoki karta.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Channel {
    /// Naqd pul.
    Cash,
    /// Plastik karta.
    Card,
}

impl Channel {
    /// Bazada saqlanadigan kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Cash => "CASH",
            Self::Card => "CARD",
        }
    }

    /// Koddan kanal; noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "CASH" => Some(Self::Cash),
            "CARD" => Some(Self::Card),
            _ => None,
        }
    }
}

/// Daromad yaratish uchun kiritilgan ma'lumot (identifikator va metama'lumotsiz).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IncomeDraft {
    /// Daromad olgan oila a'zosi (UUIDv7).
    pub member_id: String,
    /// Manba: «Kunlik ish», «Buyurtma», «Oylik» va boshqalar.
    pub source: String,
    /// Kanal: naqd yoki karta.
    pub channel: Channel,
    /// Summa (musbat).
    pub amount: Money,
    /// Daromad sanasi (Toshkent kalendar sanasi).
    pub occurred_on: Date,
    /// Ixtiyoriy izoh.
    pub note: Option<String>,
}

/// Daromad yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Income {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Daromad olgan a'zo (UUIDv7).
    pub member_id: String,
    /// Manba nomi.
    pub source: String,
    /// Kanal.
    pub channel: Channel,
    /// Summa (musbat).
    pub amount: Money,
    /// Daromad sanasi (Toshkent).
    pub occurred_on: Date,
    /// Izoh (bo'sh bo'lsa — `None`).
    pub note: Option<String>,
    /// Umumiy metama'lumot.
    pub meta: Meta,
}

impl Income {
    /// Yangi daromad. Identifikatorlar UUIDv7, summa musbat, manba qoidaga javob berishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        draft: IncomeDraft,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        validate_uuid_v7(&draft.member_id)?;
        if draft.amount.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            member_id: draft.member_id,
            source: validate_name(&draft.source)?,
            channel: draft.channel,
            amount: draft.amount,
            occurred_on: draft.occurred_on,
            note: normalize_note(draft.note),
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Izohni tozalaydi: bo'sh (faqat bo'shliqli) izoh — `None`.
pub(crate) fn normalize_note(note: Option<String>) -> Option<String> {
    note.map(|text| text.trim().to_owned())
        .filter(|text| !text.is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::{date, datetime};

    const HOUSEHOLD: &str = "0192a000-0000-7000-8000-0000000000a1";
    const MEMBER: &str = "0192a000-0000-7000-8000-0000000000b1";
    const INCOME: &str = "0192a000-0000-7000-8000-0000000000d1";

    fn draft(minor: i64) -> IncomeDraft {
        IncomeDraft {
            member_id: MEMBER.to_owned(),
            source: "Kunlik ish".to_owned(),
            channel: Channel::Cash,
            amount: Money::new(minor, Currency::Uzs),
            occurred_on: date!(2026 - 10 - 14),
            note: Some("   ".to_owned()),
        }
    }

    #[test]
    fn daromad_yaratiladi_va_izoh_tozalanadi() {
        let now = datetime!(2026-10-14 06:00 UTC);
        let income = Income::create(INCOME, HOUSEHOLD, draft(15_000_000), now, "device-1")
            .expect("to'g'ri daromad");
        assert_eq!(income.note, None);
        assert_eq!(income.source, "Kunlik ish");
        assert_eq!(income.channel.code(), "CASH");
    }

    #[test]
    fn nol_summa_rad_etiladi() {
        let now = datetime!(2026-10-14 06:00 UTC);
        assert_eq!(
            Income::create(INCOME, HOUSEHOLD, draft(0), now, "device-1"),
            Err(DomainError::AmountNotPositive)
        );
    }

    #[test]
    fn kanal_kodi_qaytarilib_oqiladi() {
        assert_eq!(Channel::from_code("CARD"), Some(Channel::Card));
        assert_eq!(Channel::from_code("X"), None);
    }
}
