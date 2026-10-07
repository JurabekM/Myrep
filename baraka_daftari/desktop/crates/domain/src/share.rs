//! Daromaddan "o'zingga to'la" ulushi (SPEC 2.1, 2.2).
use money::{percent_of, Money, MoneyError};

pub const START_BP: u32 = 500;
pub const TARGET_BP: u32 = 1000;
pub const RATE_STEP_BP: u32 = 100;
/// Ulushni oshirishni taklif qilishdan oldin shuncha hafta ketma-ket va shu stavkada bo'lish kerak.
pub const WEEKS_BEFORE_INCREASE: u32 = 4;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShareRule {
    /// Daromadning bazis punkt (500 = 5%) ulushi.
    Percent { bp: u32 },
    /// Oyiga aniq summa: shu oy ajratilgani chiqarib tashlanadi.
    MonthlyFixed { target: Money },
}

/// Bitta daromad uchun taklif qilinadigan ulush. Hech qachon daromaddan ko'p yoki manfiy bo'lmaydi.
///
/// # Errors
/// Valyuta mos kelmasa yoki `bp > 10000` bo'lsa.
pub fn suggest_share(
    rule: ShareRule,
    income: Money,
    allocated_this_month: Money,
) -> Result<Money, MoneyError> {
    if income.minor() <= 0 {
        return Ok(Money::zero(income.currency()));
    }
    match rule {
        ShareRule::Percent { bp } => percent_of(income, bp),
        ShareRule::MonthlyFixed { target } => {
            let remaining = target.checked_sub(allocated_this_month)?;
            let capped = remaining.minor().clamp(0, income.minor());
            if remaining.currency() != income.currency() {
                return Err(MoneyError::CurrencyMismatch {
                    left: remaining.currency(),
                    right: income.currency(),
                });
            }
            Ok(Money::new(capped, income.currency()))
        }
    }
}

/// Progressiv rejim: yetarlicha barqaror bo'lgan bo'lsa, ulushni bir qadam oshirishni taklif qiladi.
#[must_use]
pub fn suggest_rate_increase(
    current_bp: u32,
    streak_weeks: u32,
    weeks_at_current_rate: u32,
) -> Option<u32> {
    (current_bp < TARGET_BP
        && streak_weeks >= WEEKS_BEFORE_INCREASE
        && weeks_at_current_rate >= WEEKS_BEFORE_INCREASE)
        .then(|| (current_bp + RATE_STEP_BP).min(TARGET_BP))
}

#[cfg(test)]
mod tests {
    use money::Currency;

    use super::*;

    fn m(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn percent_rule() {
        let s = suggest_share(ShareRule::Percent { bp: 500 }, m(800_000_000), m(0)).unwrap();
        assert_eq!(s.minor(), 40_000_000);
        assert_eq!(
            suggest_share(ShareRule::Percent { bp: 1000 }, m(12345), m(0))
                .unwrap()
                .minor(),
            1235
        );
    }

    #[test]
    fn fixed_rule_stops_when_target_reached_and_never_exceeds_income() {
        let rule = ShareRule::MonthlyFixed { target: m(300) };
        assert_eq!(suggest_share(rule, m(1000), m(0)).unwrap().minor(), 300);
        assert_eq!(suggest_share(rule, m(1000), m(250)).unwrap().minor(), 50);
        assert_eq!(suggest_share(rule, m(1000), m(300)).unwrap().minor(), 0);
        assert_eq!(suggest_share(rule, m(1000), m(999)).unwrap().minor(), 0);
        assert_eq!(suggest_share(rule, m(100), m(0)).unwrap().minor(), 100);
    }

    #[test]
    fn non_positive_income_gets_nothing() {
        assert_eq!(
            suggest_share(ShareRule::Percent { bp: 500 }, m(0), m(0))
                .unwrap()
                .minor(),
            0
        );
        assert_eq!(
            suggest_share(ShareRule::Percent { bp: 500 }, m(-5), m(0))
                .unwrap()
                .minor(),
            0
        );
    }

    #[test]
    fn fixed_rule_currency_mismatch() {
        let rule = ShareRule::MonthlyFixed {
            target: Money::new(5, Currency::Usd),
        };
        assert!(suggest_share(rule, m(100), m(0)).is_err());
    }

    #[test]
    fn progressive_increase() {
        assert_eq!(suggest_rate_increase(500, 4, 4), Some(600));
        assert_eq!(suggest_rate_increase(500, 3, 9), None);
        assert_eq!(suggest_rate_increase(500, 9, 3), None);
        assert_eq!(suggest_rate_increase(950, 9, 9), Some(1000));
        assert_eq!(suggest_rate_increase(1000, 99, 99), None);
    }
}
