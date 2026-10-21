//! K7 — savdo mollari zakoti hisobi (SPEC 8.3). **Hisob, fatvo emas**: baholash usuli, nisob va bazaga
//! nima kirishi ulamo tasdig'ini kutadi (OQ-D5, OQ-D7).
//!
//! Baza = tovar + naqd va hisobdagi pul + umidli nasiya − yaqin muddatli qarzlar; nisob = oltin narxi (1 g) ×
//! gramm. Zakot = `percent_of(baza, 250 bp)`, agar baza ≥ nisob va hawl to'lgan bo'lsa.
//!
//! Vektorlar: `spec/test-vectors/kk_zakat.json`.
use baraka_money::{percent_of, Money};

use crate::DomainError;

pub const ZAKAT_BP: i64 = 250;
pub const DEFAULT_NISAB_GRAMS: u32 = 85;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ZakatInput {
    pub stock: Money,
    pub cash: Money,
    pub receivables: Money,
    pub debts: Money,
    pub gold_price: Money,
    pub nisab_grams: u32,
    pub hawl_complete: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ZakatReason {
    BaseNotPositive,
    BelowNisab,
    HawlNotComplete,
}

impl ZakatReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::BaseNotPositive => "BASE_NOT_POSITIVE",
            Self::BelowNisab => "BELOW_NISAB",
            Self::HawlNotComplete => "HAWL_NOT_COMPLETE",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ZakatResult {
    pub base: Money,
    pub nisab: Money,
    pub zakat: Money,
    /// `None` — zakot hisoblandi.
    pub reason: Option<ZakatReason>,
}

pub fn zakat(i: &ZakatInput) -> Result<ZakatResult, DomainError> {
    if [i.stock, i.cash, i.receivables, i.debts]
        .iter()
        .any(Money::is_negative)
    {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "amount"));
    }
    if !i.gold_price.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "goldPrice"));
    }
    if !(1..=1000).contains(&i.nisab_grams) {
        return Err(DomainError::on("INVALID_NISAB", "nisabGrams"));
    }
    let base = i
        .stock
        .checked_add(i.cash)?
        .checked_add(i.receivables)?
        .checked_sub(i.debts)?;
    let nisab = Money::new(
        i.gold_price
            .minor()
            .checked_mul(i64::from(i.nisab_grams))
            .ok_or(DomainError::new("OVERFLOW"))?,
        i.gold_price.currency(),
    );
    let reason = if !base.is_positive() {
        Some(ZakatReason::BaseNotPositive)
    } else if base.compare(&nisab)?.is_lt() {
        Some(ZakatReason::BelowNisab)
    } else if !i.hawl_complete {
        Some(ZakatReason::HawlNotComplete)
    } else {
        None
    };
    let zakat = match reason {
        None => percent_of(base, ZAKAT_BP)?,
        Some(_) => Money::zero(base.currency()),
    };
    Ok(ZakatResult {
        base,
        nisab,
        zakat,
        reason,
    })
}
