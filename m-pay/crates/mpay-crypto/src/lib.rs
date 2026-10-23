//! `mpay-crypto` — M-Pay kriptografiya qatlami.
//!
//! * [`keystore`] — `KeyStore` trait: kalit materialini qaytarmaydigan HSM abstraksiyasi
//!   (`MemoryKeyStore` va `pkcs11` feature bilan `Pkcs11KeyStore`);
//! * [`kdf`] — NIST SP 800-108 (counter, AES-CMAC) kalit hosil qilish;
//! * [`scheme`] — `CryptogramScheme` trait va `MPAY-AES128-CMAC-V1` (ARQC/ARPC, LUK);
//! * [`envelope`] — KEK → DEK envelope encryption (AES-256-GCM);
//! * [`index`] — PAN HMAC indeksi (barmoq izi);
//! * [`secret`], [`rng`] — sir tiplari (`Zeroizing`), OS CSPRNG, constant-time solishtirish.
//!
//! Qoida: sirlar hech qachon `Debug`/`Display` orqali chiqmaydi va logga yozilmaydi.
#![forbid(unsafe_code)]

pub mod envelope;
pub mod error;
pub mod index;
pub mod kdf;
pub mod keystore;
pub mod rng;
pub mod scheme;
pub mod secret;

pub use error::CryptoError;
pub use keystore::{KeyKind, KeyLabel, KeyStore};
pub use secret::{ct_eq, SecretKey16, SecretKey32};

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
