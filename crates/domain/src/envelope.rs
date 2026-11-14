//! Konvertlar (SPEC 2B.6): haftalik limitli virtual konvertlar («Bozor», «Yo'lkira», «Havas»).
//!
//! Naqd rejimda konvertga qancha pul solish kerakligini ilova aytadi; hafta oxirida qoldiq kiritiladi.
//! Karta bilan qilingan xarajat ham konvertdan ayriladi (`category_id` orqali).

use money::Money;
use time::OffsetDateTime;

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// Haftalik konvert.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Envelope {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Nomi.
    pub name: String,
    /// Haftalik limit (musbat).
    pub weekly_limit: Money,
    /// Bog'langan kategoriya (UUIDv7), bo'lsa — shu kategoriyadagi xarajat konvertdan ayriladi.
    pub category_id: Option<String>,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Envelope {
    /// Yangi konvert. Limit musbat bo'lishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        name: &str,
        weekly_limit: Money,
        category_id: Option<String>,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if let Some(category) = &category_id {
            validate_uuid_v7(category)?;
        }
        if weekly_limit.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            name: validate_name(name)?,
            weekly_limit,
            category_id,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Konvert qoldig'i: limit − sarflangan. Manfiy bo'lsa 0 (qoldiq yo'q, ayblov yo'q).
pub fn leftover(limit: Money, spent: Money) -> Money {
    let remaining = limit.minor().saturating_sub(spent.minor()).max(0);
    Money::new(remaining, limit.currency())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn qoldiq_manfiy_bolmaydi() {
        assert_eq!(leftover(uzs(500_000), uzs(120_000)), uzs(380_000));
        assert_eq!(leftover(uzs(500_000), uzs(700_000)), uzs(0));
    }
}
