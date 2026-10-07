use crate::Currency;

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum MoneyError {
    #[error("valyutalar mos emas: {left:?} va {right:?}")]
    CurrencyMismatch { left: Currency, right: Currency },
    #[error("arifmetik overflow")]
    Overflow,
    #[error("nisbatlar bo'sh yoki yig'indisi nol")]
    InvalidRatios,
    #[error("bazis punkt 0..=10000 oralig'ida bo'lishi kerak")]
    InvalidBasisPoints,
    #[error("kurs maxraji musbat bo'lishi kerak")]
    InvalidRate,
    #[error("noma'lum valyuta kodi: {0}")]
    UnknownCurrency(String),
    #[error("noto'g'ri summa matni: {0}")]
    Parse(String),
}
