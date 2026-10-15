//! 4-qonun: `DEBT_RECOVERY` rejimi — 70/20/10 (uy/SPEC 2D.1).
use baraka_money::{allocate, Money, BP_ONE};

use crate::DomainError;

/// Jamg'arma ulushining eng kichik qiymati: 1%. U 0 ga tushirilmaydi.
pub const MIN_SAVINGS_BP: i64 = 100;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RecoverySplit {
    /// Ro'zg'or (ZARUR + KERAK + havas chegarasi, majburiy qarz to'lovlari shu ichida).
    pub household_bp: i64,
    /// Odatiy to'lovdan tashqari qo'shimcha qarz to'lovi.
    pub extra_debt_bp: i64,
    /// «Kelajagim» jamg'armasi.
    pub savings_bp: i64,
}

impl Default for RecoverySplit {
    fn default() -> Self {
        Self {
            household_bp: 7_000,
            extra_debt_bp: 2_000,
            savings_bp: 1_000,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RecoveryParts {
    pub household: Money,
    pub extra_debt: Money,
    pub savings: Money,
}

impl RecoverySplit {
    pub fn validate(&self) -> Result<(), DomainError> {
        let parts = [self.household_bp, self.extra_debt_bp, self.savings_bp];
        if parts.iter().any(|p| *p < 0) || parts.iter().sum::<i64>() != BP_ONE {
            return Err(DomainError::on("SPLIT_NOT_100", "split"));
        }
        if self.savings_bp < MIN_SAVINGS_BP {
            return Err(DomainError::on("SAVINGS_SHARE_TOO_LOW", "savings_bp"));
        }
        Ok(())
    }

    pub fn apply(&self, income: Money) -> Result<RecoveryParts, DomainError> {
        self.validate()?;
        let parts = allocate(
            income,
            &[self.household_bp, self.extra_debt_bp, self.savings_bp],
        )?;
        match parts.as_slice() {
            [household, extra_debt, savings] => Ok(RecoveryParts {
                household: *household,
                extra_debt: *extra_debt,
                savings: *savings,
            }),
            _ => Err(DomainError::new("INVALID_RATIOS")),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn default_split() {
        let r = RecoverySplit::default().apply(uzs(800_000_000)).unwrap();
        assert_eq!(
            (r.household, r.extra_debt, r.savings),
            (uzs(560_000_000), uzs(160_000_000), uzs(80_000_000))
        );
    }

    #[test]
    fn savings_never_zero() {
        let s = RecoverySplit {
            household_bp: 8_000,
            extra_debt_bp: 2_000,
            savings_bp: 0,
        };
        assert_eq!(
            s.validate().map_err(|e| e.code),
            Err("SAVINGS_SHARE_TOO_LOW")
        );
        let s = RecoverySplit {
            household_bp: 7_900,
            extra_debt_bp: 2_000,
            savings_bp: 100,
        };
        assert!(s.validate().is_ok());
        let s = RecoverySplit {
            household_bp: 7_000,
            extra_debt_bp: 2_000,
            savings_bp: 900,
        };
        assert_eq!(s.validate().map_err(|e| e.code), Err("SPLIT_NOT_100"));
    }
}
