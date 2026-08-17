//! AETHER-Q v4 protokol mantig'i — spec 3, 4, 5, 7-bo'limlar.
//! Kripto-primitivlarga faqat `aether_primitives` trait'lari orqali murojaat qilinadi.

pub mod akem;
pub mod combiner;
pub mod labels;
pub mod profile;
pub mod ratchet;
pub mod record;
pub mod replay;

use zeroize::Zeroizing;

/// Maxfiy baytlar — Drop bo'lganda avtomatik tozalanadi (S3 talabi).
pub type Secret = Zeroizing<Vec<u8>>;

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum CoreError {
    /// S2/7.4: barcha dekriptsiya/verifikatsiya xatolari uchun yagona umumiy xato turi —
    /// buzuq ciphertext, soxta imzo, noma'lum profil, replay va AEAD tag mos kelmasligi
    /// tashqi tomondan farqlanmasligi SHART (oracle hujumlariga qarshi himoya).
    #[error("AETHER_DECRYPT_FAILURE")]
    DecryptFailure,
}
