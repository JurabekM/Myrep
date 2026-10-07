//! Kalit boshqaruvi (DESKTOP_PROMPT 6.2).
//!
//! DB kaliti (256-bit, `OsRng`) faqat **o'ralgan** holda diskda turadi. O'rash kaliti ikki omildan
//! hosil bo'ladi: PIN (Argon2id) va OS keyring'dagi qurilma siri (HKDF). Shuning uchun:
//! - keyring yozuvi o'chirilsa, faqat PIN bilan ochib bo'lmaydi;
//! - keyring buzilsa yoki olib qo'yilsa ham, PIN'siz ochib bo'lmaydi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod autolock;
mod error;
mod keystore;
mod lockout;
mod secret;
mod vault;

pub use autolock::AutoLock;
pub use error::SecurityError;
pub use keystore::{KeyStore, KeyringStore, MemoryStore};
pub use lockout::lockout_delay_secs;
pub use secret::SecretKey;
pub use vault::{KdfParams, UnixClock, Vault, VaultStatus};
