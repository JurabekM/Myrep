use crate::MoneyError;

/// Qo'llab-quvvatlanadigan valyutalar. Har birining kasr xonasi soni (`exponent`) bor:
/// «hamma valyuta 2 xonali» degan taxmin taqiqlanadi (5.1).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Currency {
    Uzs,
    Usd,
    Eur,
    Rub,
    Kzt,
    Try,
    Gbp,
    Krw,
}

impl Currency {
    pub const ALL: [Currency; 8] = [
        Self::Uzs,
        Self::Usd,
        Self::Eur,
        Self::Rub,
        Self::Kzt,
        Self::Try,
        Self::Gbp,
        Self::Krw,
    ];

    pub const fn code(self) -> &'static str {
        match self {
            Self::Uzs => "UZS",
            Self::Usd => "USD",
            Self::Eur => "EUR",
            Self::Rub => "RUB",
            Self::Kzt => "KZT",
            Self::Try => "TRY",
            Self::Gbp => "GBP",
            Self::Krw => "KRW",
        }
    }

    /// Minor birlikdagi kasr xonalari soni (UZS = 2 — tiyin, KRW = 0).
    pub const fn exponent(self) -> u32 {
        match self {
            Self::Krw => 0,
            _ => 2,
        }
    }

    /// `10^exponent` — bitta major birlikdagi minor birliklar soni.
    pub const fn minor_per_major(self) -> i64 {
        10_i64.pow(self.exponent())
    }

    pub fn from_code(code: &str) -> Result<Self, MoneyError> {
        Self::ALL
            .iter()
            .copied()
            .find(|c| c.code() == code)
            .ok_or(MoneyError::UnknownCurrency)
    }
}
