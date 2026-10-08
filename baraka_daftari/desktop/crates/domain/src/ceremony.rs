//! Marosim rejalovchisi (SPEC 2D.8): byudjet jami, moliyalash manbalari va tasdiqlash qoidasi.
//! Vektorlar: `ceremony_totals`, `repay_months`.
use money::{round_half_up, Money, MoneyError};

use crate::FundingSource;

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CeremonyError {
    #[error("miqdor 1 dan kam yoki narx manfiy")]
    InvalidAmount,
    #[error("qarz bilan moliyalangan qatorlar bor: avval «Buni qarzsiz qanday o'tkazamiz?» muhokamasini o'tkazing")]
    DiscussionRequired,
    #[error("tasdiqlash uchun marosim sanasini belgilang")]
    DateRequired,
    #[error(transparent)]
    Money(#[from] MoneyError),
}

impl CeremonyError {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::InvalidAmount => "INVALID_AMOUNT",
            Self::DiscussionRequired => "DISCUSSION_REQUIRED",
            Self::DateRequired => "DATE_REQUIRED",
            Self::Money(_) => "MONEY",
        }
    }
}

/// Bitta byudjet qatori: `qty × unit_price`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LineInput {
    pub qty: u32,
    pub unit_price: Money,
    pub funding: FundingSource,
}

/// Qator jami.
///
/// # Errors
/// Miqdor 0, narx manfiy yoki ko'paytma sig'masa.
pub fn line_total(qty: u32, unit_price: Money) -> Result<Money, CeremonyError> {
    if qty == 0 || unit_price.minor() < 0 {
        return Err(CeremonyError::InvalidAmount);
    }
    let v = unit_price
        .minor()
        .checked_mul(i64::from(qty))
        .ok_or(MoneyError::Overflow)?;
    Ok(Money::new(v, unit_price.currency()))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CeremonyTotals {
    pub total: Money,
    pub savings: Money,
    pub family: Money,
    pub expected_gifts: Money,
    pub debt: Money,
    /// Qarz ulushi jamiga nisbatan (bp, half-up).
    pub debt_bp: u32,
}

/// Qatorlar bo'yicha jami va moliyalash manbalari.
///
/// # Errors
/// Qator yaroqsiz yoki valyuta mos kelmasa/sig'masa.
pub fn ceremony_totals(
    lines: &[LineInput],
    currency: money::Currency,
) -> Result<CeremonyTotals, CeremonyError> {
    let mut sums = [Money::new(0, currency); 4];
    for l in lines {
        let idx = match l.funding {
            FundingSource::Savings => 0,
            FundingSource::Family => 1,
            FundingSource::ExpectedGifts => 2,
            FundingSource::Debt => 3,
        };
        sums[idx] = sums[idx].checked_add(line_total(l.qty, l.unit_price)?)?;
    }
    let total = sums
        .iter()
        .try_fold(Money::new(0, currency), |a, b| a.checked_add(*b))?;
    let debt_bp = if total.minor() > 0 {
        let v = round_half_up(
            i128::from(sums[3].minor()) * 10_000,
            i128::from(total.minor()),
        )?;
        u32::try_from(v).unwrap_or(u32::MAX)
    } else {
        0
    };
    Ok(CeremonyTotals {
        total,
        savings: sums[0],
        family: sums[1],
        expected_gifts: sums[2],
        debt: sums[3],
        debt_bp,
    })
}

/// Asosiy qoida (SPEC 2D.8): qarz bilan moliyalangan qatorlar bor bo'lsa, marosimni «tasdiqlangan»
/// holatga o'tkazishdan oldin oilaviy muhokama o'tkazilgan bo'lishi shart. Sana ham shart.
///
/// # Errors
/// Muhokamasiz yoki sanasiz tasdiqlashga urinilsa.
pub fn check_ceremony_confirm(
    debt: Money,
    discussed: bool,
    has_date: bool,
) -> Result<(), CeremonyError> {
    if !has_date {
        return Err(CeremonyError::DateRequired);
    }
    if debt.minor() > 0 && !discussed {
        return Err(CeremonyError::DiscussionRequired);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    /// Qabul mezoni (D11): muhokamasiz `CONFIRMED` ga o'tib bo'lmaydi.
    #[test]
    fn debt_needs_discussion_before_confirmation() {
        assert_eq!(
            check_ceremony_confirm(uzs(1), false, true),
            Err(CeremonyError::DiscussionRequired)
        );
        assert!(check_ceremony_confirm(uzs(1), true, true).is_ok());
        assert!(
            check_ceremony_confirm(uzs(0), false, true).is_ok(),
            "qarzsiz — muhokama shart emas"
        );
        assert_eq!(
            check_ceremony_confirm(uzs(0), true, false),
            Err(CeremonyError::DateRequired)
        );
    }
}
