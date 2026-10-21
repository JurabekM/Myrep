use core::cmp::Ordering;

use crate::{Currency, MoneyError};

/// Immutable pul qiymati: `minor` — eng kichik birlikda (tiyin, sent, von).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Money {
    minor: i64,
    currency: Currency,
}

impl Money {
    pub const fn new(minor: i64, currency: Currency) -> Self {
        Self { minor, currency }
    }

    pub const fn zero(currency: Currency) -> Self {
        Self::new(0, currency)
    }

    /// Butun major birlikdan (so'm, dollar) yaratish: `from_major(8_000_000, UZS)`.
    pub fn from_major(major: i64, currency: Currency) -> Result<Self, MoneyError> {
        major
            .checked_mul(currency.minor_per_major())
            .map(|minor| Self::new(minor, currency))
            .ok_or(MoneyError::Overflow)
    }

    pub const fn minor(&self) -> i64 {
        self.minor
    }

    pub const fn currency(&self) -> Currency {
        self.currency
    }

    pub const fn is_zero(&self) -> bool {
        self.minor == 0
    }

    pub const fn is_negative(&self) -> bool {
        self.minor < 0
    }

    pub const fn is_positive(&self) -> bool {
        self.minor > 0
    }

    fn same_currency(&self, other: &Money) -> Result<(), MoneyError> {
        if self.currency == other.currency {
            Ok(())
        } else {
            Err(MoneyError::CurrencyMismatch)
        }
    }

    pub fn checked_add(self, other: Money) -> Result<Money, MoneyError> {
        self.same_currency(&other)?;
        self.minor
            .checked_add(other.minor)
            .map(|m| Money::new(m, self.currency))
            .ok_or(MoneyError::Overflow)
    }

    pub fn checked_sub(self, other: Money) -> Result<Money, MoneyError> {
        self.same_currency(&other)?;
        self.minor
            .checked_sub(other.minor)
            .map(|m| Money::new(m, self.currency))
            .ok_or(MoneyError::Overflow)
    }

    pub fn checked_neg(self) -> Result<Money, MoneyError> {
        self.minor
            .checked_neg()
            .map(|m| Money::new(m, self.currency))
            .ok_or(MoneyError::Overflow)
    }

    pub fn checked_mul(self, k: i64) -> Result<Money, MoneyError> {
        self.minor
            .checked_mul(k)
            .map(|m| Money::new(m, self.currency))
            .ok_or(MoneyError::Overflow)
    }

    /// Bir xil valyutadagi qiymatlarni solishtirish. Har xil valyuta — xato.
    pub fn compare(&self, other: &Money) -> Result<Ordering, MoneyError> {
        self.same_currency(other)?;
        Ok(self.minor.cmp(&other.minor))
    }

    pub fn min(self, other: Money) -> Result<Money, MoneyError> {
        Ok(if self.compare(&other)? == Ordering::Greater {
            other
        } else {
            self
        })
    }

    pub fn max(self, other: Money) -> Result<Money, MoneyError> {
        Ok(if self.compare(&other)? == Ordering::Less {
            other
        } else {
            self
        })
    }

    /// Manfiy qiymatni nolga tenglaydi («qutqarilgan pul» kabi ko'rsatkichlar uchun).
    pub const fn clamp_non_negative(self) -> Money {
        if self.minor < 0 {
            Money::zero(self.currency)
        } else {
            self
        }
    }

    /// Bir xil valyutadagi qiymatlar yig'indisi. Bo'sh ro'yxat — nol.
    pub fn sum<I: IntoIterator<Item = Money>>(
        items: I,
        currency: Currency,
    ) -> Result<Money, MoneyError> {
        items
            .into_iter()
            .try_fold(Money::zero(currency), |acc, m| acc.checked_add(m))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mixing_currencies_fails() {
        let uzs = Money::new(100, Currency::Uzs);
        let usd = Money::new(100, Currency::Usd);
        assert_eq!(uzs.checked_add(usd), Err(MoneyError::CurrencyMismatch));
        assert_eq!(uzs.checked_sub(usd), Err(MoneyError::CurrencyMismatch));
        assert_eq!(uzs.compare(&usd), Err(MoneyError::CurrencyMismatch));
        assert_eq!(
            Money::sum([uzs, usd], Currency::Uzs),
            Err(MoneyError::CurrencyMismatch)
        );
    }

    #[test]
    fn overflow_is_an_error() {
        let max = Money::new(i64::MAX, Currency::Uzs);
        assert_eq!(
            max.checked_add(Money::new(1, Currency::Uzs)),
            Err(MoneyError::Overflow)
        );
        assert_eq!(
            Money::new(i64::MIN, Currency::Uzs).checked_neg(),
            Err(MoneyError::Overflow)
        );
        assert_eq!(max.checked_mul(2), Err(MoneyError::Overflow));
    }

    #[test]
    fn from_major_respects_exponent() {
        assert_eq!(
            Money::from_major(8_000_000, Currency::Uzs).map(|m| m.minor()),
            Ok(800_000_000)
        );
        assert_eq!(
            Money::from_major(1_000_000, Currency::Krw).map(|m| m.minor()),
            Ok(1_000_000)
        );
    }

    #[test]
    fn clamp_and_min_max() {
        let a = Money::new(-5, Currency::Uzs);
        let b = Money::new(7, Currency::Uzs);
        assert_eq!(a.clamp_non_negative().minor(), 0);
        assert_eq!(a.min(b), Ok(a));
        assert_eq!(a.max(b), Ok(b));
    }
}
