use std::fmt;

use crate::MoneyError;

/// Qo'llab-quvvatlanadigan valyutalar (SPEC 4.2). Asosiy valyuta — UZS (so'm).
///
/// Hozircha barcha valyutalarda minor birlik ikki xonali: UZS uchun tiyin, qolganlari uchun sent.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Currency {
    /// O'zbek so'mi. 1 so'm = 100 tiyin.
    Uzs,
    /// AQSh dollari. 1 dollar = 100 sent.
    Usd,
    /// Yevro. 1 yevro = 100 sent.
    Eur,
    /// Rossiya rubli. 1 rubl = 100 kopeyka.
    Rub,
}

impl Currency {
    /// Minor birlik kasr xonalari soni.
    pub const fn minor_digits(self) -> usize {
        2
    }

    /// Bitta major birlikdagi minor birliklar soni (1 so'm = 100 tiyin).
    pub const fn minor_per_major(self) -> i64 {
        10_i64.pow(self.minor_digits() as u32)
    }

    /// ISO 4217 kodi.
    pub const fn iso_code(self) -> &'static str {
        match self {
            Self::Uzs => "UZS",
            Self::Usd => "USD",
            Self::Eur => "EUR",
            Self::Rub => "RUB",
        }
    }

    /// ISO kodidan valyuta. Registr muhim emas: `"usd"` ham `USD` deb o'qiladi.
    pub fn from_iso(code: &str) -> Result<Self, MoneyError> {
        match code.to_ascii_uppercase().as_str() {
            "UZS" => Ok(Self::Uzs),
            "USD" => Ok(Self::Usd),
            "EUR" => Ok(Self::Eur),
            "RUB" => Ok(Self::Rub),
            _ => Err(MoneyError::UnknownCurrency(code.to_owned())),
        }
    }
}

impl fmt::Display for Currency {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.iso_code())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ALL: [Currency; 4] = [Currency::Uzs, Currency::Usd, Currency::Eur, Currency::Rub];

    #[test]
    fn minor_birlik_ikki_xonali() {
        for currency in ALL {
            assert_eq!(currency.minor_digits(), 2);
            assert_eq!(currency.minor_per_major(), 100);
        }
    }

    #[test]
    fn iso_kodlar_va_teskari_oqish() {
        for currency in ALL {
            assert_eq!(Currency::from_iso(currency.iso_code()), Ok(currency));
            assert_eq!(currency.to_string(), currency.iso_code());
        }
        assert_eq!(Currency::from_iso("usd"), Ok(Currency::Usd));
    }

    #[test]
    fn noma_lum_valyuta_xato_beradi() {
        assert_eq!(
            Currency::from_iso("XXX"),
            Err(MoneyError::UnknownCurrency("XXX".to_owned()))
        );
    }
}
