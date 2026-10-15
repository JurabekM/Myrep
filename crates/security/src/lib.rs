//! Kalit boshqaruvi: PIN, Argon2id, ikki qatlamli o'rash, OS keyring, lockout va avto-qulflash.
//!
//! Model (DESKTOP_PROMPT.md 6.2): DB kaliti tasodifiy 256 bit. U ikki qatlamda o'raladi —
//! ichki qatlam PIN'dan Argon2id bilan hosil qilingan kalit bilan, tashqi qatlam esa OS keyring'dagi
//! kalit bilan. Shunda faqat PIN ham, faqat keyring ham yetarli emas.

mod auto_lock;
mod container;
mod error;
mod kdf;
mod key;
mod lockout;
mod member_pin;
mod pin;
mod store;
mod vault;
mod wrap;

pub use auto_lock::{AUTO_LOCK_TIMEOUT, AutoLockPolicy};
pub use container::{MIN_PASSWORD_CHARS, open_container, seal_container, validate_password};
pub use error::SecurityError;
pub use kdf::{KdfParams, SALT_LEN};
pub use key::SecretKey;
pub use lockout::{LOCKOUT_THRESHOLD, lockout_delay_secs, retry_after_secs};
pub use member_pin::{VERIFIER_LEN, create_member_verifier, verify_member_pin};
pub use pin::{PIN_LEN, validate_pin};
pub use store::{KeyringSecretStore, MemorySecretStore, SecretStore};
pub use vault::{create_vault, open_vault};
pub use wrap::{FILE_LEN, KeyFile};
