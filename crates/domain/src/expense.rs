//! Xarajat (SPEC 2.3): summa, kategoriya, sana va oila a'zosi.

use money::Money;
use time::{Date, OffsetDateTime};

use crate::income::normalize_note;
use crate::{DomainError, Meta, validate_uuid_v7};

/// Xarajat yaratish uchun kiritilgan ma'lumot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExpenseDraft {
    /// Xarajat qilgan a'zo (UUIDv7).
    pub member_id: String,
    /// Kategoriya (UUIDv7); `None` — kategoriyasiz (izohsiz summa shunday yoziladi).
    pub category_id: Option<String>,
    /// Summa (musbat).
    pub amount: Money,
    /// Xarajat sanasi (Toshkent kalendar sanasi).
    pub occurred_on: Date,
    /// Ixtiyoriy izoh.
    pub note: Option<String>,
}

/// Xarajat yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Expense {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Xarajat qilgan a'zo (UUIDv7).
    pub member_id: String,
    /// Kategoriya (UUIDv7) yoki `None`.
    pub category_id: Option<String>,
    /// Summa (musbat).
    pub amount: Money,
    /// Xarajat sanasi (Toshkent).
    pub occurred_on: Date,
    /// Izoh (bo'sh bo'lsa — `None`).
    pub note: Option<String>,
    /// Umumiy metama'lumot.
    pub meta: Meta,
}

impl Expense {
    /// Yangi xarajat. Identifikatorlar UUIDv7, summa musbat.
    pub fn create(
        id: &str,
        household_id: &str,
        draft: ExpenseDraft,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        validate_uuid_v7(&draft.member_id)?;
        if let Some(category) = &draft.category_id {
            validate_uuid_v7(category)?;
        }
        if draft.amount.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            member_id: draft.member_id,
            category_id: draft.category_id,
            amount: draft.amount,
            occurred_on: draft.occurred_on,
            note: normalize_note(draft.note),
            meta: Meta::created(now, origin_device_id),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::{date, datetime};

    const HOUSEHOLD: &str = "0192a000-0000-7000-8000-0000000000a1";
    const MEMBER: &str = "0192a000-0000-7000-8000-0000000000b1";
    const EXPENSE: &str = "0192a000-0000-7000-8000-0000000000e1";

    #[test]
    fn kategoriyasiz_xarajat_yaratiladi() {
        let draft = ExpenseDraft {
            member_id: MEMBER.to_owned(),
            category_id: None,
            amount: Money::new(500_000, Currency::Uzs),
            occurred_on: date!(2026 - 10 - 14),
            note: None,
        };
        let now = datetime!(2026-10-14 06:00 UTC);
        let expense = Expense::create(EXPENSE, HOUSEHOLD, draft, now, "device-1").expect("xarajat");
        assert_eq!(expense.category_id, None);
    }
}
