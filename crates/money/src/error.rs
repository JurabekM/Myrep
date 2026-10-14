use crate::Currency;

/// Pul amallaridagi xatolar. [`MoneyError::code`] barqaror kod qaytaradi — vektor fayllari shu kodlarni ishlatadi.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum MoneyError {
    /// Har xil valyutadagi summa bilan amal bajarishga urinildi.
    #[error("valyutalar mos emas: {expected} kutilgan, {actual} berildi")]
    CurrencyMismatch {
        /// Kutilgan valyuta.
        expected: Currency,
        /// Berilgan valyuta.
        actual: Currency,
    },
    /// Natija 64-bitli butun son chegarasidan oshdi.
    #[error("hisob-kitob 64-bitli chegaradan oshdi")]
    Overflow,
    /// Nisbatlar bo'sh yoki ularning yig'indisi nol.
    #[error("nisbatlar noto'g'ri: bo'sh yoki yig'indisi nol")]
    InvalidRatios,
    /// Kurs noto'g'ri: valyutalar bir xil yoki kurs qiymati musbat emas.
    #[error("kurs noto'g'ri: valyutalar bir xil yoki kurs musbat emas")]
    InvalidRate,
    /// Maxraj nol yoki manfiy.
    #[error("maxraj musbat bo'lishi kerak")]
    InvalidDenominator,
    /// Noma'lum valyuta kodi.
    #[error("noma'lum valyuta kodi: {0}")]
    UnknownCurrency(String),
}

impl MoneyError {
    /// Barqaror xato kodi (SCREAMING_SNAKE_CASE).
    pub const fn code(&self) -> &'static str {
        match self {
            Self::CurrencyMismatch { .. } => "CURRENCY_MISMATCH",
            Self::Overflow => "OVERFLOW",
            Self::InvalidRatios => "INVALID_RATIOS",
            Self::InvalidRate => "INVALID_RATE",
            Self::InvalidDenominator => "INVALID_DENOMINATOR",
            Self::UnknownCurrency(_) => "UNKNOWN_CURRENCY",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn har_bir_xato_barqaror_kodga_ega() {
        let cases = [
            (
                MoneyError::CurrencyMismatch {
                    expected: Currency::Uzs,
                    actual: Currency::Usd,
                },
                "CURRENCY_MISMATCH",
            ),
            (MoneyError::Overflow, "OVERFLOW"),
            (MoneyError::InvalidRatios, "INVALID_RATIOS"),
            (MoneyError::InvalidRate, "INVALID_RATE"),
            (MoneyError::InvalidDenominator, "INVALID_DENOMINATOR"),
            (
                MoneyError::UnknownCurrency("XXX".to_owned()),
                "UNKNOWN_CURRENCY",
            ),
        ];
        for (error, code) in cases {
            assert_eq!(error.code(), code);
            assert!(!error.to_string().is_empty());
        }
    }

    #[test]
    fn valyuta_xatosi_matni_ikkala_valyutani_korsatadi() {
        let error = MoneyError::CurrencyMismatch {
            expected: Currency::Uzs,
            actual: Currency::Usd,
        };
        assert_eq!(
            error.to_string(),
            "valyutalar mos emas: UZS kutilgan, USD berildi"
        );
    }
}
