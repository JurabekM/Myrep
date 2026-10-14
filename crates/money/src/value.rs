use crate::{Currency, MoneyError};

/// Pul miqdori: butun minor birliklar (tiyin, sent) va valyuta. Qiymat obyekti — o'zgarmas.
///
/// `minor` — eng kichik birliklar soni: 8 000 000 so'm = `800000000` tiyin.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Money {
    minor: i64,
    currency: Currency,
}

impl Money {
    /// Minor birliklardan summa yaratadi.
    pub const fn new(minor: i64, currency: Currency) -> Self {
        Self { minor, currency }
    }

    /// Nol summa.
    pub const fn zero(currency: Currency) -> Self {
        Self { minor: 0, currency }
    }

    /// Minor birliklar soni (tiyin, sent).
    pub const fn minor(self) -> i64 {
        self.minor
    }

    /// Valyuta.
    pub const fn currency(self) -> Currency {
        self.currency
    }

    /// Qo'shish. Valyutalar mos kelmasa yoki natija chegaradan oshsa — xato.
    pub fn checked_add(self, other: Self) -> Result<Self, MoneyError> {
        self.ensure_same_currency(other)?;
        let minor = self
            .minor
            .checked_add(other.minor)
            .ok_or(MoneyError::Overflow)?;
        Ok(Self::new(minor, self.currency))
    }

    /// Ayirish. Valyutalar mos kelmasa yoki natija chegaradan oshsa — xato.
    pub fn checked_sub(self, other: Self) -> Result<Self, MoneyError> {
        self.ensure_same_currency(other)?;
        let minor = self
            .minor
            .checked_sub(other.minor)
            .ok_or(MoneyError::Overflow)?;
        Ok(Self::new(minor, self.currency))
    }

    fn ensure_same_currency(self, other: Self) -> Result<(), MoneyError> {
        if self.currency == other.currency {
            Ok(())
        } else {
            Err(MoneyError::CurrencyMismatch {
                expected: self.currency,
                actual: other.currency,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn yaratish_va_maydonlar() {
        let amount = Money::new(800_000_050, Currency::Uzs);
        assert_eq!(amount.minor(), 800_000_050);
        assert_eq!(amount.currency(), Currency::Uzs);
        assert_eq!(Money::zero(Currency::Usd).minor(), 0);
    }

    #[test]
    fn bir_xil_valyutada_qoshish_va_ayirish() {
        assert_eq!(uzs(150).checked_add(uzs(50)), Ok(uzs(200)));
        assert_eq!(uzs(150).checked_sub(uzs(200)), Ok(uzs(-50)));
    }

    #[test]
    fn valyuta_aralashuvi_xato_beradi() {
        let usd = Money::new(100, Currency::Usd);
        let expected = MoneyError::CurrencyMismatch {
            expected: Currency::Uzs,
            actual: Currency::Usd,
        };
        assert_eq!(uzs(100).checked_add(usd), Err(expected.clone()));
        assert_eq!(uzs(100).checked_sub(usd), Err(expected));
    }

    #[test]
    fn chegaradan_oshish_xato_beradi() {
        assert_eq!(uzs(i64::MAX).checked_add(uzs(1)), Err(MoneyError::Overflow));
        assert_eq!(uzs(i64::MIN).checked_sub(uzs(1)), Err(MoneyError::Overflow));
    }
}
