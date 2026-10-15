//! Kalit iyerarxiyasi (`docs/BARAKA_OILASI.md`, 7.2–7.4).
//!
//! ```text
//! DB_KEY (32 bayt, OS RNG) — SQLCipher kaliti; faqat xotirada, zeroize
//!   └─ har bir slotda XChaCha20-Poly1305 bilan wrap qilinadi:
//!      PIN      : KEK = HKDF(PLATFORM_SECRET ‖ Argon2id(PIN), "baraka/kek/pin/v1")
//!      RECOVERY : KEK = HKDF(PLATFORM_SECRET ‖ Argon2id(RECOVERY_CODE), "baraka/kek/recovery/v1")
//!      BIO      : KEK = platforma bergan 32 bayt (Keystore + CryptoObject / Windows Hello)
//! ```
//! Bazani ochish uchun **ikkala omil ham** kerak: platforma siri va PIN (yoki tiklash kodi).
#![deny(clippy::float_arithmetic)]

mod error;
mod keyfile;
mod lockout;
mod secrets;

pub use error::SecurityError;
pub use keyfile::{KdfParams, KeyFile, SlotKind, KEYFILE_VERSION};
pub use lockout::{lockout_seconds, LockoutState, FREE_ATTEMPTS};
pub use secrets::{BioKek, DbKey, Pin, PlatformSecret, RecoveryCode, SECRET_LEN};
