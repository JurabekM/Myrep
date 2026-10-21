//! 1-qonun: har daromaddan «Kelajagim» ulushi (uy/SPEC 2.1–2.2).
use baraka_money::{percent_of, Money};

use crate::DomainError;

/// Avto-ulush qoidasi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AllocationRule {
    /// Daromadning foizi, basis points'da (500 = 5%, 1000 = 10%).
    Percent(i64),
    /// Har daromaddan qat'iy summa (daromaddan oshmaydi).
    Fixed(Money),
}

/// Daromad kiritilganda taklif qilinadigan ulush.
pub fn suggest_share(income: Money, rule: AllocationRule) -> Result<Money, DomainError> {
    if !income.is_positive() {
        return Err(DomainError::on("INCOME_NOT_POSITIVE", "income"));
    }
    match rule {
        AllocationRule::Percent(bp) => Ok(percent_of(income, bp)?),
        AllocationRule::Fixed(amount) => {
            if amount.is_negative() {
                return Err(DomainError::on("FIXED_SHARE_NEGATIVE", "amount"));
            }
            Ok(amount.min(income)?)
        }
    }
}

/// Progressiv rejim: ketma-ket N hafta ajratilsa, ulushni oshirish taklif qilinadi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProgressivePolicy {
    pub weeks_required: u32,
    pub step_bp: i64,
    pub max_bp: i64,
}

impl Default for ProgressivePolicy {
    fn default() -> Self {
        Self {
            weeks_required: 4,
            step_bp: 100,
            max_bp: 2_000,
        }
    }
}

/// Yangi ulush taklifi (bp) yoki `None` — taklif yo'q.
pub fn progressive_suggestion(
    current_bp: i64,
    consecutive_weeks: u32,
    policy: ProgressivePolicy,
) -> Option<i64> {
    if consecutive_weeks < policy.weeks_required || current_bp >= policy.max_bp {
        return None;
    }
    Some((current_bp + policy.step_bp).min(policy.max_bp))
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn shares() {
        assert_eq!(
            suggest_share(uzs(800_000_000), AllocationRule::Percent(1000)),
            Ok(uzs(80_000_000))
        );
        assert_eq!(
            suggest_share(uzs(20_000_000), AllocationRule::Fixed(uzs(30_000_000))),
            Ok(uzs(20_000_000))
        );
        assert!(suggest_share(uzs(0), AllocationRule::Percent(500)).is_err());
        assert!(suggest_share(
            uzs(100),
            AllocationRule::Fixed(Money::new(1, Currency::Usd))
        )
        .is_err());
    }

    #[test]
    fn progressive() {
        let p = ProgressivePolicy::default();
        assert_eq!(progressive_suggestion(500, 4, p), Some(600));
        assert_eq!(progressive_suggestion(500, 3, p), None);
        assert_eq!(progressive_suggestion(1_950, 8, p), Some(2_000));
        assert_eq!(progressive_suggestion(2_000, 8, p), None);
    }
}
