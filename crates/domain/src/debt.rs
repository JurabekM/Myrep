//! Nasiya daftari (SPEC 2.5): do'kondagi qarzlar — kimga va qancha qoldiq.
//!
//! D4 da faqat asosiy qoldiq va qisman to'lovlar. Foiz, qarz tilxati va friction — D9 da.

use money::Money;
use time::{Date, OffsetDateTime};

use crate::income::normalize_note;
use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// Nasiya: do'kondan olingan qarz.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ShopDebt {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Do'kon yoki kimga qarzdor.
    pub creditor: String,
    /// Asl summa (musbat).
    pub principal: Money,
    /// Qarz olingan sana.
    pub incurred_on: Date,
    /// Izoh.
    pub note: Option<String>,
    /// Metama'lumot.
    pub meta: Meta,
}

impl ShopDebt {
    /// Izohni qo'yadi (bo'sh bo'lsa — `None`).
    pub fn with_note(mut self, note: Option<String>) -> Self {
        self.note = normalize_note(note);
        self
    }

    /// Yangi nasiya. Summa musbat, kreditor nomi qoidaga javob berishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        creditor: &str,
        principal: Money,
        incurred_on: Date,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if principal.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            creditor: validate_name(creditor)?,
            principal,
            incurred_on,
            note: None,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Nasiyaga qisman to'lov.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DebtPayment {
    /// UUIDv7.
    pub id: String,
    /// Nasiya (UUIDv7).
    pub debt_id: String,
    /// To'lov summasi (musbat).
    pub amount: Money,
    /// To'lov sanasi.
    pub paid_on: Date,
    /// Metama'lumot.
    pub meta: Meta,
}

/// Qoldiq: asl summa − to'lovlar yig'indisi.
pub fn outstanding(principal: Money, payments: &[Money]) -> Result<Money, DomainError> {
    let mut paid = Money::zero(principal.currency());
    for payment in payments {
        paid = paid.checked_add(*payment)?;
    }
    Ok(principal.checked_sub(paid)?)
}

/// To'lovni tekshiradi: musbat va qoldiqdan oshmaydi.
pub fn validate_payment(outstanding: Money, amount: Money) -> Result<(), DomainError> {
    if amount.minor() <= 0 {
        return Err(DomainError::AmountNotPositive);
    }
    if outstanding.checked_sub(amount)?.minor() < 0 {
        return Err(DomainError::DebtOverpaid);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency::Uzs;

    #[test]
    fn qoldiq_va_ortiqcha_tolov() {
        let principal = Money::new(500_000, Uzs);
        let left = outstanding(principal, &[Money::new(200_000, Uzs)]).expect("qoldiq");
        assert_eq!(left.minor(), 300_000);
        assert_eq!(
            validate_payment(left, Money::new(300_001, Uzs)),
            Err(DomainError::DebtOverpaid)
        );
        assert_eq!(validate_payment(left, Money::new(300_000, Uzs)), Ok(()));
    }
}
