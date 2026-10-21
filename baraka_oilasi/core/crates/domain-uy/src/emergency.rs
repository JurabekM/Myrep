//! 3-qonun: qorovul pul maqsadi va qamrov (uy/SPEC 2C.3).
use baraka_money::{round_half_up, Money};

use crate::DomainError;

/// To'liq maqsad (oy) va birinchi milestone.
pub const FULL_TARGET_MONTHS: u32 = 6;
pub const FIRST_MILESTONE_MONTHS: u32 = 3;

/// `round_half_up(Σ(ZARUR+KERAK, oxirgi k oy) × N / k)`.
pub fn emergency_target(monthly_essentials: &[Money], months: u32) -> Result<Money, DomainError> {
    let first = monthly_essentials.first().ok_or(DomainError::on(
        "INSUFFICIENT_HISTORY",
        "monthly_essentials",
    ))?;
    if months == 0 {
        return Err(DomainError::on("INVALID_MONTHS", "months"));
    }
    let total = Money::sum(monthly_essentials.iter().copied(), first.currency())?;
    let k = i128::try_from(monthly_essentials.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
    let v = round_half_up(i128::from(total.minor()) * i128::from(months), k)?;
    let minor = i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))?;
    Ok(Money::new(minor, total.currency()))
}

/// Necha oylik zaxira bor — yuzdan bir oyda (140 = «1,4 oy»).
pub fn coverage_centi_months(balance: Money, monthly_average: Money) -> Result<i64, DomainError> {
    balance.compare(&monthly_average)?;
    if !monthly_average.is_positive() {
        return Err(DomainError::on("INVALID_AVERAGE", "monthly_average"));
    }
    let v = round_half_up(
        i128::from(balance.minor().max(0)) * 100,
        i128::from(monthly_average.minor()),
    )?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn documented() {
        let months = [uzs(520_000_000), uzs(500_000_000), uzs(530_000_000)];
        assert_eq!(emergency_target(&months, 6), Ok(uzs(3_100_000_000)));
        assert!(emergency_target(&[], 6).is_err());
    }

    #[test]
    fn coverage() {
        assert_eq!(
            coverage_centi_months(uzs(723_333_333), uzs(516_666_667)),
            Ok(140)
        );
        assert_eq!(coverage_centi_months(uzs(-5), uzs(100)), Ok(0));
        assert!(coverage_centi_months(uzs(5), uzs(0)).is_err());
    }
}
