//! Majburiyatlar (SPEC 2.5): doimiy to'lovlar — ijara, kredit, kommunal, telefon, benzin.
//!
//! Har majburiyat tegishli kategoriyaga bog'lanadi: o'sha kategoriyada yozilgan xarajat majburiyatni
//! qoplaydi, faqat yozilmagan qismi «to'langan deb faraz qilinadi» (ikki marta hisoblamaslik).

use money::Money;
use time::OffsetDateTime;

use crate::category::CategoryKey;
use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// Majburiyat turi. Turi standart kategoriyaga bog'lanadi ([`ObligationKind::default_category`]).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ObligationKind {
    /// Ijara (uy egasi).
    Rent,
    /// Kredit (bank).
    Credit,
    /// Kommunal xizmatlar.
    Utility,
    /// Telefon.
    Phone,
    /// Yoqilg'i.
    Fuel,
    /// Boshqa.
    Other,
}

impl ObligationKind {
    /// Bazada saqlanadigan kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Rent => "RENT",
            Self::Credit => "CREDIT",
            Self::Utility => "UTILITY",
            Self::Phone => "PHONE",
            Self::Fuel => "FUEL",
            Self::Other => "OTHER",
        }
    }

    /// Koddan tur; noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "RENT" => Some(Self::Rent),
            "CREDIT" => Some(Self::Credit),
            "UTILITY" => Some(Self::Utility),
            "PHONE" => Some(Self::Phone),
            "FUEL" => Some(Self::Fuel),
            "OTHER" => Some(Self::Other),
            _ => None,
        }
    }

    /// Shu tur uchun standart kategoriya kaliti.
    pub const fn default_category(self) -> CategoryKey {
        match self {
            Self::Rent => CategoryKey::Rent,
            Self::Credit => CategoryKey::Credit,
            Self::Utility => CategoryKey::Utilities,
            Self::Phone => CategoryKey::Phone,
            Self::Fuel => CategoryKey::Fuel,
            Self::Other => CategoryKey::Other,
        }
    }
}

/// Majburiyat yaratish uchun kiritilgan ma'lumot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObligationDraft {
    /// Nomi: «Ijara», «Bank krediti» va boshqalar.
    pub title: String,
    /// Turi.
    pub kind: ObligationKind,
    /// Oylik summa (musbat).
    pub amount: Money,
    /// To'lov kuni (1..31); `None` — belgilanmagan.
    pub due_day: Option<u8>,
    /// Bog'langan kategoriya (UUIDv7); `None` — standart kategoriya ishlatiladi.
    pub category_id: Option<String>,
}

/// Majburiyat yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Obligation {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Nomi.
    pub title: String,
    /// Turi.
    pub kind: ObligationKind,
    /// Oylik summa (musbat).
    pub amount: Money,
    /// To'lov kuni (1..31).
    pub due_day: Option<u8>,
    /// Bog'langan kategoriya (UUIDv7) yoki `None`.
    pub category_id: Option<String>,
    /// Faolmi (o'chirilgan majburiyat hisobga olinmaydi).
    pub active: bool,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Obligation {
    /// Yangi majburiyat. Summa musbat, kun 1..31, identifikatorlar UUIDv7.
    pub fn create(
        id: &str,
        household_id: &str,
        draft: ObligationDraft,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if let Some(category) = &draft.category_id {
            validate_uuid_v7(category)?;
        }
        if draft.amount.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if let Some(day) = draft.due_day
            && !(1..=31).contains(&day)
        {
            return Err(DomainError::InvalidDay);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            title: validate_name(&draft.title)?,
            kind: draft.kind,
            amount: draft.amount,
            due_day: draft.due_day,
            category_id: draft.category_id,
            active: true,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency::Uzs;
    use time::macros::datetime;

    const HOUSEHOLD: &str = "0192a000-0000-7000-8000-0000000000a1";
    const OBLIGATION: &str = "0192a000-0000-7000-8000-0000000000f1";

    #[test]
    fn tur_kodi_va_standart_kategoriya() {
        assert_eq!(
            ObligationKind::from_code("UTILITY"),
            Some(ObligationKind::Utility)
        );
        assert_eq!(
            ObligationKind::Utility.default_category(),
            CategoryKey::Utilities
        );
    }

    #[test]
    fn kun_1_dan_31_gacha() {
        let draft = |day| ObligationDraft {
            title: "Ijara".to_owned(),
            kind: ObligationKind::Rent,
            amount: Money::new(150_000_000, Uzs),
            due_day: Some(day),
            category_id: None,
        };
        let now = datetime!(2026-10-14 06:00 UTC);
        assert_eq!(
            Obligation::create(OBLIGATION, HOUSEHOLD, draft(32), now, "device-1"),
            Err(DomainError::InvalidDay)
        );
        assert!(Obligation::create(OBLIGATION, HOUSEHOLD, draft(31), now, "device-1").is_ok());
    }
}
