//! Xato turlari. Protokol xatolari wire'dagi ALERT kodiga aylantiriladi (Python `Alert` bilan bir xil).

use std::fmt;

/// ALERT kodlari (Python `aether_q_v51/handshake.py` `Alert` bilan bir xil).
pub mod alert {
    pub const CLOSE_NOTIFY: u8 = 0x00;
    pub const NO_COMMON_VERSION: u8 = 0x28;
    pub const NO_COMMON_PROFILE: u8 = 0x29;
    pub const BAD_FINISHED: u8 = 0x2A;
    pub const DECAPS_FAILED: u8 = 0x2B;
    pub const UNEXPECTED_MESSAGE: u8 = 0x2C;
    pub const PROFILE_NOT_OFFERED: u8 = 0x2D;
    pub const DOS_REJECT: u8 = 0x2E;
    pub const BAD_SIGNATURE: u8 = 0x2F;
    pub const BAD_TICKET: u8 = 0x30;
    pub const CLIENT_AUTH_REQUIRED: u8 = 0x31;
    pub const BAD_CLIENT_AUTH: u8 = 0x32;
}

#[derive(Debug)]
pub enum AqError {
    /// Protokol alert: qarshi tomonga yuboriladi, ulanish yopiladi.
    Alert(u8),
    /// Noto'g'ri formatdagi xabar (framing, uzunlik, ortiqcha bayt).
    Malformed(&'static str),
    /// Kriptografik operatsiya xatosi (masalan, noto'g'ri kalit uzunligi).
    Crypto(&'static str),
    /// Transport AEAD tekshiruvi muvaffaqiyatsiz (record buzilgan yoki noto'g'ri kalit).
    Aead,
    /// Tarmoq I/O xatosi.
    Io(std::io::Error),
}

impl fmt::Display for AqError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AqError::Alert(c) => write!(f, "AETHER alert 0x{c:02x}"),
            AqError::Malformed(m) => write!(f, "noto'g'ri xabar: {m}"),
            AqError::Crypto(m) => write!(f, "kriptografik xato: {m}"),
            AqError::Aead => write!(f, "record AEAD tekshiruvi muvaffaqiyatsiz"),
            AqError::Io(e) => write!(f, "I/O: {e}"),
        }
    }
}

impl std::error::Error for AqError {}

impl From<std::io::Error> for AqError {
    fn from(e: std::io::Error) -> Self {
        AqError::Io(e)
    }
}

pub type Result<T> = std::result::Result<T, AqError>;
