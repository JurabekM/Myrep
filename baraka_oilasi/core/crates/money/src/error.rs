use core::fmt;

/// Pul amallaridagi xatolar. `code()` — adapterlar va vektorlar uchun barqaror kod.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MoneyError {
    CurrencyMismatch,
    Overflow,
    InvalidRatios,
    InvalidBasisPoints,
    InvalidRate,
    DivisionByZero,
    UnknownCurrency,
    Parse(ParseError),
}

/// Foydalanuvchi kiritgan summani o'qishdagi xatolar.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ParseError {
    Empty,
    InvalidCharacter,
    TooManyDecimals,
    MisplacedSeparator,
}

impl MoneyError {
    pub const fn code(&self) -> &'static str {
        match self {
            Self::CurrencyMismatch => "CURRENCY_MISMATCH",
            Self::Overflow => "OVERFLOW",
            Self::InvalidRatios => "INVALID_RATIOS",
            Self::InvalidBasisPoints => "INVALID_BP",
            Self::InvalidRate => "INVALID_RATE",
            Self::DivisionByZero => "DIVISION_BY_ZERO",
            Self::UnknownCurrency => "UNKNOWN_CURRENCY",
            Self::Parse(ParseError::Empty) => "PARSE_EMPTY",
            Self::Parse(ParseError::InvalidCharacter) => "PARSE_INVALID_CHARACTER",
            Self::Parse(ParseError::TooManyDecimals) => "PARSE_TOO_MANY_DECIMALS",
            Self::Parse(ParseError::MisplacedSeparator) => "PARSE_MISPLACED_SEPARATOR",
        }
    }
}

impl fmt::Display for MoneyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl core::error::Error for MoneyError {}
