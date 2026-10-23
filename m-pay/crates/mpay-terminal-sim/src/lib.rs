//! `mpay-terminal-sim` — telefonsiz e2e uchun dasturiy komponentlar:
//!
//! * [`http`] — `mpay-server` HTTP client;
//! * [`wallet`] — soft-wallet (PQ Link, provisioning, OTP, LUK to'ldirish).
#![forbid(unsafe_code)]

pub mod http;
pub mod wallet;

use thiserror::Error;

/// Client xatolari.
#[derive(Debug, Error)]
pub enum WalletError {
    #[error("konfiguratsiya: {0}")]
    Config(String),
    #[error("HTTP: {0}")]
    Http(String),
    #[error("server xatosi {status} {code}: {message}")]
    Api {
        status: u16,
        code: String,
        message: String,
    },
    #[error("PQ Link: {0}")]
    PqLink(#[from] mpay_pqlink::PqLinkError),
    #[error("javobni o'qib bo'lmadi: {0}")]
    Decode(&'static str),
    #[error("PQ Link sessiyasi yo'q (avval connect)")]
    NotConnected,
}

impl WalletError {
    /// Server xato kodi (bo'lsa).
    pub fn code(&self) -> Option<&str> {
        match self {
            Self::Api { code, .. } => Some(code),
            _ => None,
        }
    }
}

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
