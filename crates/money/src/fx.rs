use time::Date;

use crate::{Currency, Money, MoneyError, round_half_up_div};

/// Valyuta kursi snapshoti (SPEC 4.2). Kurs `double` emas, kasr: 1 major `from` = `rate_num / rate_den` major `to`.
///
/// Masalan, 1 USD = 12 650,50 so'm → `rate_num = 1265050`, `rate_den = 100`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FxRate {
    from: Currency,
    to: Currency,
    rate_num: i64,
    rate_den: i64,
    date: Date,
    source: String,
}

impl FxRate {
    /// Kurs yaratadi. Valyutalar bir xil bo'lsa yoki kurs musbat bo'lmasa — [`MoneyError::InvalidRate`].
    pub fn new(
        from: Currency,
        to: Currency,
        rate_num: i64,
        rate_den: i64,
        date: Date,
        source: impl Into<String>,
    ) -> Result<Self, MoneyError> {
        if from == to || rate_num <= 0 || rate_den <= 0 {
            return Err(MoneyError::InvalidRate);
        }
        Ok(Self {
            from,
            to,
            rate_num,
            rate_den,
            date,
            source: source.into(),
        })
    }

    /// Manba valyuta.
    pub const fn from(&self) -> Currency {
        self.from
    }

    /// Maqsad valyuta.
    pub const fn to(&self) -> Currency {
        self.to
    }

    /// Kurs surati (suratning soni).
    pub const fn rate_num(&self) -> i64 {
        self.rate_num
    }

    /// Kurs maxraji.
    pub const fn rate_den(&self) -> i64 {
        self.rate_den
    }

    /// Kurs sanasi (snapshot).
    pub const fn date(&self) -> Date {
        self.date
    }

    /// Kurs manbasi (masalan, `manual`).
    pub fn source(&self) -> &str {
        &self.source
    }
}

/// `amount` ni `rate` bo'yicha konvertatsiya qiladi. `amount` valyutasi `rate.from` bo'lishi shart.
///
/// Hisob: `minor_to = minor_from × num × 10^to_digits / (den × 10^from_digits)`, yarmi noldan uzoqqa yaxlitlanadi.
pub fn convert(amount: Money, rate: &FxRate) -> Result<Money, MoneyError> {
    if amount.currency() != rate.from {
        return Err(MoneyError::CurrencyMismatch {
            expected: rate.from,
            actual: amount.currency(),
        });
    }
    let numerator = i128::from(amount.minor())
        .checked_mul(i128::from(rate.rate_num))
        .and_then(|value| value.checked_mul(i128::from(rate.to.minor_per_major())))
        .ok_or(MoneyError::Overflow)?;
    let denominator = i128::from(rate.rate_den)
        .checked_mul(i128::from(rate.from.minor_per_major()))
        .ok_or(MoneyError::Overflow)?;
    let rounded = round_half_up_div(numerator, denominator)?;
    let minor = i64::try_from(rounded).map_err(|_| MoneyError::Overflow)?;
    Ok(Money::new(minor, rate.to))
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::Month;

    fn day() -> Date {
        Date::from_calendar_date(2026, Month::October, 14).expect("to'g'ri sana")
    }

    fn usd_to_uzs(rate_num: i64, rate_den: i64) -> FxRate {
        FxRate::new(
            Currency::Usd,
            Currency::Uzs,
            rate_num,
            rate_den,
            day(),
            "test",
        )
        .expect("to'g'ri kurs")
    }

    #[test]
    fn kurs_qiymatlari_tekshiriladi() {
        assert_eq!(
            FxRate::new(Currency::Usd, Currency::Usd, 1, 1, day(), "t"),
            Err(MoneyError::InvalidRate)
        );
        assert_eq!(
            FxRate::new(Currency::Usd, Currency::Uzs, 0, 1, day(), "t"),
            Err(MoneyError::InvalidRate)
        );
        assert_eq!(
            FxRate::new(Currency::Usd, Currency::Uzs, 1, 0, day(), "t"),
            Err(MoneyError::InvalidRate)
        );
        assert_eq!(
            FxRate::new(Currency::Usd, Currency::Uzs, -1, 1, day(), "t"),
            Err(MoneyError::InvalidRate)
        );
    }

    #[test]
    fn kurs_maydonlari_saqlanadi() {
        let rate = usd_to_uzs(1_265_050, 100);
        assert_eq!(rate.from(), Currency::Usd);
        assert_eq!(rate.to(), Currency::Uzs);
        assert_eq!(rate.rate_num(), 1_265_050);
        assert_eq!(rate.rate_den(), 100);
        assert_eq!(rate.date(), day());
        assert_eq!(rate.source(), "test");
    }

    #[test]
    fn konvertatsiya_yarmi_noldan_uzoqqa() {
        let rate = usd_to_uzs(1_265_050, 100);
        let convert_minor = |minor: i64| {
            convert(Money::new(minor, Currency::Usd), &rate)
                .expect("hisoblanadi")
                .minor()
        };
        assert_eq!(convert_minor(1000), 12_650_500);
        assert_eq!(convert_minor(1), 12_651);
        assert_eq!(convert_minor(-1), -12_651);
    }

    #[test]
    fn teskari_kurs() {
        let inverse = FxRate::new(Currency::Uzs, Currency::Usd, 100, 1_265_050, day(), "t")
            .expect("to'g'ri kurs");
        let result = convert(Money::new(12_650_500, Currency::Uzs), &inverse).expect("hisoblanadi");
        assert_eq!(result, Money::new(1000, Currency::Usd));
    }

    #[test]
    fn valyuta_mos_kelmasa_xato() {
        let rate = usd_to_uzs(1_265_050, 100);
        assert_eq!(
            convert(Money::new(1000, Currency::Eur), &rate),
            Err(MoneyError::CurrencyMismatch {
                expected: Currency::Usd,
                actual: Currency::Eur,
            })
        );
    }

    #[test]
    fn konvertatsiya_chegaradan_oshsa_xato() {
        let rate = usd_to_uzs(i64::MAX, 1);
        assert_eq!(
            convert(Money::new(i64::MAX, Currency::Usd), &rate),
            Err(MoneyError::Overflow)
        );
    }
}
