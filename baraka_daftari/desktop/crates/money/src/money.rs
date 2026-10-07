use serde::{Deserialize, Serialize};

use crate::{Currency, MoneyError};

/// Immutable pul qiymati: `minor` — eng kichik birlikda (tiyin).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Money {
    minor: i64,
    currency: Currency,
}

impl Money {
    #[must_use]
    pub const fn new(minor: i64, currency: Currency) -> Self {
        Self { minor, currency }
    }

    #[must_use]
    pub const fn zero(currency: Currency) -> Self {
        Self::new(0, currency)
    }

    #[must_use]
    pub const fn minor(self) -> i64 {
        self.minor
    }

    #[must_use]
    pub const fn currency(self) -> Currency {
        self.currency
    }

    /// # Errors
    /// Valyuta mos kelmasa yoki overflow bo'lsa.
    pub fn checked_add(self, rhs: Self) -> Result<Self, MoneyError> {
        self.same_currency(rhs)?;
        let minor = self
            .minor
            .checked_add(rhs.minor)
            .ok_or(MoneyError::Overflow)?;
        Ok(Self::new(minor, self.currency))
    }

    /// # Errors
    /// Valyuta mos kelmasa yoki overflow bo'lsa.
    pub fn checked_sub(self, rhs: Self) -> Result<Self, MoneyError> {
        self.same_currency(rhs)?;
        let minor = self
            .minor
            .checked_sub(rhs.minor)
            .ok_or(MoneyError::Overflow)?;
        Ok(Self::new(minor, self.currency))
    }

    /// # Errors
    /// Overflow bo'lsa.
    pub fn checked_neg(self) -> Result<Self, MoneyError> {
        let minor = self.minor.checked_neg().ok_or(MoneyError::Overflow)?;
        Ok(Self::new(minor, self.currency))
    }

    #[must_use]
    pub const fn is_negative(self) -> bool {
        self.minor < 0
    }

    fn same_currency(self, rhs: Self) -> Result<(), MoneyError> {
        if self.currency == rhs.currency {
            Ok(())
        } else {
            Err(MoneyError::CurrencyMismatch {
                left: self.currency,
                right: rhs.currency,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_same_currency() {
        let a = Money::new(100, Currency::Uzs);
        let b = Money::new(50, Currency::Uzs);
        assert_eq!(a.checked_add(b).unwrap().minor(), 150);
        assert_eq!(a.checked_sub(b).unwrap().minor(), 50);
    }

    #[test]
    fn mixed_currency_is_error() {
        let a = Money::new(100, Currency::Uzs);
        let b = Money::new(100, Currency::Usd);
        assert_eq!(
            a.checked_add(b),
            Err(MoneyError::CurrencyMismatch {
                left: Currency::Uzs,
                right: Currency::Usd
            })
        );
        assert!(a.checked_sub(b).is_err());
    }

    #[test]
    fn accessors_and_zero() {
        let z = Money::zero(Currency::Eur);
        assert_eq!(
            (z.minor(), z.currency(), z.is_negative()),
            (0, Currency::Eur, false)
        );
        assert!(Money::new(-1, Currency::Eur).is_negative());
        assert_eq!(
            Money::new(5, Currency::Uzs).checked_neg().unwrap().minor(),
            -5
        );
    }

    #[test]
    fn overflow_is_error() {
        let a = Money::new(i64::MAX, Currency::Uzs);
        assert_eq!(
            a.checked_add(Money::new(1, Currency::Uzs)),
            Err(MoneyError::Overflow)
        );
        assert_eq!(
            Money::new(i64::MIN, Currency::Uzs).checked_neg(),
            Err(MoneyError::Overflow)
        );
    }
}
