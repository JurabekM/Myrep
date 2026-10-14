//! Oylik audit hisoboti (SPEC 2.3): audit yakunida davr uchun o'zgarmas surat.
//!
//! Hisobot bir marta yoziladi va o'zgartirilmaydi: keyinchalik kategoriya yoki majburiyat o'zgarsa
//! ham, o'tgan oyning raqamlari shu suratda qoladi.

use money::{Currency, Money};
use time::OffsetDateTime;

use crate::calendar::DateRange;
use crate::ledger::MonthLedger;
use crate::{DomainError, Meta, validate_uuid_v7};

/// Oy yakunidagi audit surati.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MonthlyReport {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Hisobot davri.
    pub period: DateRange,
    /// Valyuta.
    pub currency: Currency,
    /// Jami daromad.
    pub income: Money,
    /// Yozilgan xarajatlar.
    pub expenses: Money,
    /// Majburiyatlar jami.
    pub obligations_total: Money,
    /// Majburiyatlarning yozilmagan qismi.
    pub obligations_unrecorded: Money,
    /// Sof jamg'arma («Kelajagim»).
    pub net_savings: Money,
    /// Izohsiz qolgan summa.
    pub unexplained: Money,
    /// Metama'lumot.
    pub meta: Meta,
}

impl MonthlyReport {
    /// Hisobot suratini [`MonthLedger`] dan yig'adi. Hisob-kitob ledger'da, bu yerda faqat yig'iladi.
    pub fn from_ledger(
        id: &str,
        household_id: &str,
        ledger: &MonthLedger,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            period: ledger.period,
            currency: ledger.currency,
            income: ledger.income,
            expenses: ledger.expenses,
            obligations_total: ledger.obligations_total()?,
            obligations_unrecorded: ledger.obligations_unrecorded()?,
            net_savings: ledger.net_savings()?,
            unexplained: ledger.unexplained()?,
            meta: Meta::created(now, origin_device_id),
        })
    }
}
