//! Kriptografiya xatolari. Xato matnida hech qachon kalit yoki ochiq matn bo'lmaydi.

use thiserror::Error;

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum CryptoError {
    #[error("kalit topilmadi: {0}")]
    KeyNotFound(String),
    #[error("kalit allaqachon mavjud: {0}")]
    KeyExists(String),
    #[error("kalit {label} turi {actual}, kutilgan {expected}")]
    WrongKeyKind {
        label: String,
        expected: &'static str,
        actual: &'static str,
    },
    #[error("noto'g'ri kirish: {0}")]
    BadInput(&'static str),
    #[error("autentifikatsiyalangan shifrni ochib bo'lmadi")]
    Decrypt,
    #[error("tasodifiy son generatori xatosi")]
    Rng,
    #[error("HSM backend xatosi: {0}")]
    Backend(String),
}
