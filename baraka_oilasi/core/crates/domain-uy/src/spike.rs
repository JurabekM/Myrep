//! 6-qonun: «katta foyda» ogohlantirishi (uy/SPEC 2F.7). Butun sonlarda, bo'lishsiz.
use baraka_money::Money;

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SpikePolicy {
    /// Rejaga nisbatan chegara (15000 = 150%).
    pub plan_threshold_bp: i64,
    /// Oxirgi 3 davr o'rtachasiga nisbatan chegara (20000 = 200%).
    pub history_threshold_bp: i64,
}

impl Default for SpikePolicy {
    fn default() -> Self {
        Self {
            plan_threshold_bp: 15_000,
            history_threshold_bp: 20_000,
        }
    }
}

/// `alert = actual > 0 && (A || B)`:
/// * A: `plan > 0` va `actual × 10000 ≥ plan × plan_threshold_bp`;
/// * B: oxirgi 3 davr ma'lum, `S > 0` va `actual × 3 × 10000 ≥ S × history_threshold_bp`.
pub fn profit_spike(
    plan: Option<Money>,
    last_three: Option<[Money; 3]>,
    actual: Money,
    policy: SpikePolicy,
) -> Result<bool, DomainError> {
    let a = i128::from(actual.minor());
    let cond_a = match plan {
        Some(p) => {
            actual.compare(&p)?;
            p.is_positive()
                && a * 10_000 >= i128::from(p.minor()) * i128::from(policy.plan_threshold_bp)
        }
        None => false,
    };
    let cond_b = match last_three {
        Some(h) => {
            let mut s: i128 = 0;
            for m in h {
                actual.compare(&m)?;
                s += i128::from(m.minor());
            }
            s > 0 && a * 3 * 10_000 >= s * i128::from(policy.history_threshold_bp)
        }
        None => false,
    };
    Ok(actual.is_positive() && (cond_a || cond_b))
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn documented_vectors() {
        let p = SpikePolicy::default();
        let h = Some([uzs(100_000_000), uzs(120_000_000), uzs(110_000_000)]);
        assert_eq!(
            profit_spike(Some(uzs(100_000_000)), None, uzs(150_000_000), p),
            Ok(true)
        );
        assert_eq!(
            profit_spike(Some(uzs(100_000_000)), None, uzs(149_999_999), p),
            Ok(false)
        );
        assert_eq!(profit_spike(None, h, uzs(220_000_000), p), Ok(true));
        assert_eq!(profit_spike(None, h, uzs(219_999_999), p), Ok(false));
        assert_eq!(
            profit_spike(Some(uzs(100_000_000)), None, uzs(-50_000_000), p),
            Ok(false)
        );
    }
}
