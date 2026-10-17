//! TAMGA yadrosi: TAMGA Record 0.1 formatining ma'lumotnoma implementatsiyasi (`spec/TAMGA-RECORD-0.1.md`).
//!
//! - [`jcs`] — TR-JSON kanonikalashtirish (RFC 8785, faqat butun sonlar).
//! - [`digest`] — `sha256:<hex>` digest turi va domen-ajratilgan xeshlar.
//! - [`record`] — yozuv maydonlarini tekshirish va yozuv xeshi.
//! - [`chain`] — jurnal yozuvchi ([`chain::LogWriter`]) va zanjir verifikatori.
//! - [`merkle`] — RFC 9162 Merkle daraxti, inclusion va consistency isbotlari.
//! - [`keys`], [`checkpoint`] — gibrid Ed25519 + ML-DSA-65 imzoli checkpoint'lar.
//! - [`payload`] — tuzlangan payload majburiyati (crypto-shredding uchun).

pub mod b64;
pub mod chain;
pub mod checkpoint;
pub mod digest;
pub mod error;
pub mod jcs;
pub mod keys;
pub mod merkle;
pub mod payload;
pub mod record;

pub use digest::Digest;
pub use error::{ErrorCode, VerifyError};

/// TAMGA Record format versiyasi, crate qaysi spec bilan mos ekani.
pub const FORMAT_VERSION: &str = "0.1";

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_set() {
        assert_eq!(super::FORMAT_VERSION, "0.1");
    }
}
