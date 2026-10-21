use crate::{round_half_up, Currency, Money, MoneyError};

/// Valyuta kursi: **1 major `from` = `rate_num / rate_den` major `to`** (5.6).
/// Sana va manba (`date`, `source`) domen/saqlash qatlamida yuritiladi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FxRate {
    pub from: Currency,
    pub to: Currency,
    pub rate_num: i64,
    pub rate_den: i64,
}

/// `minor_to = round_half_up(minor × rate_num × 10^exp(to) / (rate_den × 10^exp(from)))`.
pub fn convert(amount: Money, rate: &FxRate) -> Result<Money, MoneyError> {
    if amount.currency() != rate.from {
        return Err(MoneyError::CurrencyMismatch);
    }
    if rate.rate_num <= 0 || rate.rate_den <= 0 {
        return Err(MoneyError::InvalidRate);
    }
    let num = i128::from(amount.minor())
        .checked_mul(i128::from(rate.rate_num))
        .and_then(|v| v.checked_mul(i128::from(rate.to.minor_per_major())))
        .ok_or(MoneyError::Overflow)?;
    let den = i128::from(rate.rate_den)
        .checked_mul(i128::from(rate.from.minor_per_major()))
        .ok_or(MoneyError::Overflow)?;
    let minor = round_half_up(num, den)?;
    let minor = i64::try_from(minor).map_err(|_| MoneyError::Overflow)?;
    Ok(Money::new(minor, rate.to))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn documented_cases() {
        let usd = FxRate {
            from: Currency::Usd,
            to: Currency::Uzs,
            rate_num: 12_650,
            rate_den: 1,
        };
        assert_eq!(
            convert(Money::new(10_000, Currency::Usd), &usd),
            Ok(Money::new(126_500_000, Currency::Uzs))
        );
        let krw = FxRate {
            from: Currency::Krw,
            to: Currency::Uzs,
            rate_num: 91,
            rate_den: 10,
        };
        assert_eq!(
            convert(Money::new(1_000_000, Currency::Krw), &krw),
            Ok(Money::new(910_000_000, Currency::Uzs))
        );
        // UZS -> KRW: 1 so'm = 10/91 von; 9 100 so'm = 1000 von
        let back = FxRate {
            from: Currency::Uzs,
            to: Currency::Krw,
            rate_num: 10,
            rate_den: 91,
        };
        assert_eq!(
            convert(Money::new(910_000, Currency::Uzs), &back),
            Ok(Money::new(1_000, Currency::Krw))
        );
    }

    #[test]
    fn errors() {
        let rate = FxRate {
            from: Currency::Eur,
            to: Currency::Uzs,
            rate_num: 1,
            rate_den: 1,
        };
        assert_eq!(
            convert(Money::new(1, Currency::Usd), &rate),
            Err(MoneyError::CurrencyMismatch)
        );
        let bad = FxRate {
            from: Currency::Usd,
            to: Currency::Uzs,
            rate_num: 0,
            rate_den: 1,
        };
        assert_eq!(
            convert(Money::new(1, Currency::Usd), &bad),
            Err(MoneyError::InvalidRate)
        );
    }
}
