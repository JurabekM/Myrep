//! `mpay-terminal-sim` — telefonsiz e2e uchun dasturiy komponentlar:
//!
//! * [`apdu`] — APDU tiplari va `ApduTransport` trait (loopback; keyin PC/SC — ACR122U);
//! * [`card`] — loopback soft-karta (M-Pay Test Scheme applet'i, HCE o'rinbosari);
//! * [`terminal`] — terminal yadrosi (PPSE → AID → GPO);
//! * [`http`] — `mpay-server` HTTP client;
//! * [`wallet`] — soft-wallet (PQ Link, provisioning, OTP, LUK to'ldirish).
#![forbid(unsafe_code)]

pub mod apdu;
pub mod card;
pub mod http;
pub mod state;
pub mod terminal;
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
    /// Karta/terminal APDU darajasida rad etdi (masalan `6986` — CDCVM kerak).
    #[error("karta: {0}")]
    Card(String),
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
