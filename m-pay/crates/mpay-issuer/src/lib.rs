//! `mpay-issuer` — emitent emulyatori: ISO 8583 `0100`/`0110` subset, ARQC tekshiruvi va ARPC,
//! Shield risk skori, UZS test hisoblari, javob kodlari `00`/`05`/`51`/`59`/`91`/`Q1` (ADR-0007),
//! reversal `0400`/`0401` → `0410` va solishtirish uchun avtorizatsiyalar hisoboti (ADR-0024).
//!
//! Vault va Shield'ni faqat port trait'lari (`Detokenizer`, `RiskScorer`) orqali ko'radi.
#![forbid(unsafe_code)]

pub mod codes;
pub mod issuer;
pub mod reversal;

use thiserror::Error;

pub use codes::{Reason, ResponseCode, ReversalReason};
pub use issuer::{
    validate_request, AccountView, AuthOutcome, Issuer, IssuerConfig, ReviewAction, TestAccount,
    DEFAULT_CVM_LIMIT_MINOR,
};
pub use reversal::{IssuerRecord, ReversalOutcome};

/// Emitent xatolari (faqat xabarni umuman qayta ishlab bo'lmaydigan holatlar; biznes rad etishlar
/// `0110` javob kodi bilan qaytadi).
#[derive(Debug, Error)]
pub enum IssuerError {
    #[error("ISO 8583 formati: {0}")]
    Iso(#[from] mpay_common::iso8583::Iso8583Error),
    #[error("format: {0}")]
    Format(&'static str),
    #[error("konfiguratsiya: {0}")]
    Config(&'static str),
    #[error("kriptografiya: {0}")]
    Crypto(#[from] mpay_crypto::CryptoError),
    #[error("ma'lumotlar bazasi: {0}")]
    Db(String),
}

impl From<sqlx::Error> for IssuerError {
    fn from(e: sqlx::Error) -> Self {
        Self::Db(e.to_string())
    }
}

impl From<sqlx::migrate::MigrateError> for IssuerError {
    fn from(e: sqlx::migrate::MigrateError) -> Self {
        Self::Db(e.to_string())
    }
}

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
