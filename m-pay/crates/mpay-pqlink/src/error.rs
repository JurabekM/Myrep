//! PQ Link xatolari. Matnlarda kalit yoki ochiq matn bo'lmaydi.

use thiserror::Error;

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum PqLinkError {
    #[error("xabar formati noto'g'ri: {0}")]
    Malformed(&'static str),
    #[error("protokol versiyasi yoki xabar turi kutilmagan")]
    UnexpectedMessage,
    #[error("kripto to'plami qo'llab-quvvatlanmaydi")]
    UnsupportedSuite,
    #[error("server identifikatori pinlangan qiymatga mos emas")]
    ServerNotPinned,
    #[error("server imzosi noto'g'ri ({0})")]
    BadServerSignature(&'static str),
    #[error("finished MAC noto'g'ri")]
    BadFinished,
    #[error("kalit almashuvi xatosi: {0}")]
    KeyExchange(&'static str),
    #[error("qurilma attestatsiyasi rad etildi: {0}")]
    Attestation(String),
    #[error("qurilma imzosi noto'g'ri")]
    BadDeviceSignature,
    #[error("qurilma ro'yxatdan o'tmagan: {0}")]
    Enrollment(&'static str),
    #[error("sessiya topilmadi yoki muddati o'tgan")]
    UnknownSession,
    #[error("takroriy yoki tartibsiz yozuv (kutilgan seq {expected}, olingan {got})")]
    Replay { expected: u64, got: u64 },
    #[error("yozuvni ochib bo'lmadi — sessiya yopildi")]
    Decrypt,
    #[error("sessiyalar limiti to'ldi")]
    TooManySessions,
    #[error("kriptografiya xatosi: {0}")]
    Crypto(String),
}

impl From<mpay_crypto::CryptoError> for PqLinkError {
    fn from(e: mpay_crypto::CryptoError) -> Self {
        Self::Crypto(e.to_string())
    }
}
