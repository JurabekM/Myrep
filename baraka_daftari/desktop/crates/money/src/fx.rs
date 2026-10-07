use crate::{round_half_up, Currency, Money, MoneyError};

/// Kurs snapshoti. `rate_num / rate_den` — `from` ning 1 minor birligi nechta `to` minor birligiga teng.
/// (Ikkala tomonda ham 2 xona bo'lgani uchun minor↔minor nisbati asosiy birliklar nisbatiga teng.)
/// `date` va `source` audit uchun, ISO-8601 matn.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FxRate {
    pub from: Currency,
    pub to: Currency,
    pub rate_num: i64,
    pub rate_den: i64,
    pub date: String,
    pub source: String,
}

impl FxRate {
    /// Konvertatsiya, natija half-up yaxlitlanadi.
    ///
    /// # Errors
    /// `amount` valyutasi `from` ga teng bo'lmasa, kurs yaroqsiz bo'lsa yoki overflow bo'lsa.
    pub fn convert(&self, amount: Money) -> Result<Money, MoneyError> {
        if amount.currency() != self.from {
            return Err(MoneyError::CurrencyMismatch {
                left: amount.currency(),
                right: self.from,
            });
        }
        if self.rate_num <= 0 || self.rate_den <= 0 {
            return Err(MoneyError::InvalidRate);
        }
        let num = i128::from(amount.minor())
            .checked_mul(i128::from(self.rate_num))
            .ok_or(MoneyError::Overflow)?;
        Ok(Money::new(
            round_half_up(num, i128::from(self.rate_den))?,
            self.to,
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rate(num: i64, den: i64) -> FxRate {
        FxRate {
            from: Currency::Usd,
            to: Currency::Uzs,
            rate_num: num,
            rate_den: den,
            date: "2026-01-01".into(),
            source: "manual".into(),
        }
    }

    #[test]
    fn converts_and_rounds_half_up() {
        let m = Money::new(10_000, Currency::Usd);
        assert_eq!(
            rate(1_265_050, 100).convert(m).unwrap(),
            Money::new(126_505_000, Currency::Uzs)
        );
        assert_eq!(
            rate(1, 2)
                .convert(Money::new(3, Currency::Usd))
                .unwrap()
                .minor(),
            2
        );
    }

    #[test]
    fn wrong_source_currency_is_error() {
        let m = Money::new(100, Currency::Eur);
        assert!(matches!(
            rate(1, 1).convert(m),
            Err(MoneyError::CurrencyMismatch { .. })
        ));
    }

    #[test]
    fn invalid_rate_is_error() {
        let m = Money::new(100, Currency::Usd);
        assert_eq!(rate(0, 1).convert(m), Err(MoneyError::InvalidRate));
        assert_eq!(rate(1, 0).convert(m), Err(MoneyError::InvalidRate));
    }
}
