use serde::{Deserialize, Serialize};

use crate::MoneyError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum Currency {
    Uzs,
    Usd,
    Eur,
    Rub,
}

impl Currency {
    /// Barcha qo'llab-quvvatlanadigan valyutalarda 2 ta kasr xonasi bor (tiyin, sent, kopeyka).
    #[must_use]
    pub const fn minor_digits(self) -> u32 {
        2
    }

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Uzs => "UZS",
            Self::Usd => "USD",
            Self::Eur => "EUR",
            Self::Rub => "RUB",
        }
    }

    /// # Errors
    /// Noma'lum kod uchun [`MoneyError::UnknownCurrency`].
    pub fn from_code(code: &str) -> Result<Self, MoneyError> {
        match code {
            "UZS" => Ok(Self::Uzs),
            "USD" => Ok(Self::Usd),
            "EUR" => Ok(Self::Eur),
            "RUB" => Ok(Self::Rub),
            other => Err(MoneyError::UnknownCurrency(other.to_owned())),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn code_roundtrip() {
        for c in [Currency::Uzs, Currency::Usd, Currency::Eur, Currency::Rub] {
            assert_eq!(Currency::from_code(c.code()).unwrap(), c);
            assert_eq!(c.minor_digits(), 2);
        }
    }

    #[test]
    fn unknown_code_is_error() {
        assert_eq!(
            Currency::from_code("GBP"),
            Err(MoneyError::UnknownCurrency("GBP".into()))
        );
    }

    #[test]
    fn serde_uses_uppercase_codes() {
        assert_eq!(serde_json::to_string(&Currency::Uzs).unwrap(), "\"UZS\"");
    }
}
