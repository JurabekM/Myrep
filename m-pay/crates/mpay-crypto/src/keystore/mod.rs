//! `KeyStore` — HSM abstraksiyasi (ADR-0003).
//!
//! Trait kalit materialini **qaytarmaydi**: faqat operatsiyalar yorliq (label) bo'yicha.
//! Istisno — [`KeyStore::import_secret`] (KAT testlari va migratsiya uchun, kalit kiritiladi,
//! lekin chiqarilmaydi).

use core::fmt;

use zeroize::Zeroizing;

use crate::CryptoError;

pub mod conformance;
pub mod memory;
#[cfg(feature = "pkcs11")]
pub mod pkcs11;
pub(crate) mod soft;

pub use memory::MemoryKeyStore;
#[cfg(feature = "pkcs11")]
pub use pkcs11::{Pkcs11Config, Pkcs11KeyStore};

/// HMAC kalitining minimal uzunligi (SHA-256 chiqishi; SoftHSM2 ham shuni talab qiladi).
pub const HMAC_MIN_KEY: usize = 32;
/// HMAC kalitining maksimal uzunligi.
pub const HMAC_MAX_KEY: usize = 256;

/// Kalit turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KeyKind {
    /// AES-128: CMAC (IMK-AC).
    Aes128,
    /// AES-256: AES-GCM (KEK).
    Aes256,
    /// HMAC-SHA256 umumiy sir (PAN indeksi).
    HmacSha256,
    /// Ed25519 imzo kaliti.
    Ed25519,
}

impl KeyKind {
    pub fn name(self) -> &'static str {
        match self {
            Self::Aes128 => "AES-128",
            Self::Aes256 => "AES-256",
            Self::HmacSha256 => "HMAC-SHA256",
            Self::Ed25519 => "Ed25519",
        }
    }

    /// Generatsiya qilinadigan material uzunligi.
    pub fn material_len(self) -> usize {
        match self {
            Self::Aes128 => 16,
            Self::Aes256 | Self::HmacSha256 | Self::Ed25519 => 32,
        }
    }
}

/// Kalit yorlig'i (maxfiy emas).
#[derive(Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct KeyLabel(String);

impl KeyLabel {
    /// Emitent master kaliti (ARQC, `MPAY-AES128-CMAC-V1`).
    pub const IMK_AC: &'static str = "mpay.imk-ac.v1";
    /// Ma'lumotlar bazasi DEK'larini o'rovchi KEK.
    pub const KEK: &'static str = "mpay.kek.v1";
    /// PAN HMAC indeksi kaliti.
    pub const PAN_INDEX: &'static str = "mpay.pan-idx.v1";
    /// PQ Link server Ed25519 imzo kaliti.
    pub const SERVER_ED25519: &'static str = "mpay.srv-ed25519.v1";
    /// Qurilmani ro'yxatdan o'tkazish nonce'lari MAC kaliti (HMAC-SHA256; ko'p instansiyada umumiy).
    pub const ENROLL_NONCE: &'static str = "mpay.enroll-nonce.v1";

    pub fn new(s: impl Into<String>) -> Self {
        Self(s.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Debug for KeyLabel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl fmt::Display for KeyLabel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl From<&str> for KeyLabel {
    fn from(s: &str) -> Self {
        Self(s.to_owned())
    }
}

/// AES-GCM bilan muhrlangan ma'lumot.
#[derive(Clone, PartialEq, Eq)]
pub struct GcmSealed {
    pub nonce: [u8; 12],
    /// Shifrmatn ‖ 16 baytli teg.
    pub ciphertext: Vec<u8>,
}

impl fmt::Debug for GcmSealed {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "GcmSealed({} bayt)", self.ciphertext.len())
    }
}

/// HSM abstraksiyasi.
pub trait KeyStore: Send + Sync + fmt::Debug {
    /// Backend nomi (`memory`, `pkcs11`).
    fn backend_name(&self) -> &'static str;

    /// Kalit mavjud bo'lmasa yaratadi; mavjud bo'lsa turini tekshiradi.
    fn ensure_key(&self, label: &KeyLabel, kind: KeyKind) -> Result<(), CryptoError>;

    /// Kalit turi (yo'q bo'lsa `None`).
    fn key_kind(&self, label: &KeyLabel) -> Result<Option<KeyKind>, CryptoError>;

    /// Tashqi kalit materialini kiritadi (KAT testlari, migratsiya). Mavjud yorliq — xato.
    fn import_secret(
        &self,
        label: &KeyLabel,
        kind: KeyKind,
        material: &[u8],
    ) -> Result<(), CryptoError>;

    /// AES-CMAC (AES-128 kalit).
    fn aes_cmac(&self, label: &KeyLabel, data: &[u8]) -> Result<[u8; 16], CryptoError>;

    /// AES-256-GCM shifrlash; nonce backend ichida CSPRNG bilan generatsiya qilinadi.
    fn aes_gcm_seal(
        &self,
        label: &KeyLabel,
        aad: &[u8],
        plaintext: &[u8],
    ) -> Result<GcmSealed, CryptoError>;

    /// AES-256-GCM ochish.
    fn aes_gcm_open(
        &self,
        label: &KeyLabel,
        nonce: &[u8; 12],
        aad: &[u8],
        ciphertext: &[u8],
    ) -> Result<Zeroizing<Vec<u8>>, CryptoError>;

    /// HMAC-SHA256.
    fn hmac_sha256(&self, label: &KeyLabel, data: &[u8]) -> Result<[u8; 32], CryptoError>;

    /// Ed25519 imzo (sof Ed25519, RFC 8032).
    fn ed25519_sign(&self, label: &KeyLabel, msg: &[u8]) -> Result<[u8; 64], CryptoError>;

    /// Ed25519 ochiq kaliti.
    fn ed25519_public_key(&self, label: &KeyLabel) -> Result<[u8; 32], CryptoError>;
}

/// Sandbox uchun standart kalitlarni yaratadi (mavjud bo'lsa o'zgartirmaydi).
pub fn ensure_standard_keys(ks: &dyn KeyStore) -> Result<(), CryptoError> {
    ks.ensure_key(&KeyLabel::new(KeyLabel::IMK_AC), KeyKind::Aes128)?;
    ks.ensure_key(&KeyLabel::new(KeyLabel::KEK), KeyKind::Aes256)?;
    ks.ensure_key(&KeyLabel::new(KeyLabel::PAN_INDEX), KeyKind::HmacSha256)?;
    ks.ensure_key(&KeyLabel::new(KeyLabel::SERVER_ED25519), KeyKind::Ed25519)?;
    Ok(())
}

pub(crate) fn wrong_kind(label: &KeyLabel, expected: KeyKind, actual: KeyKind) -> CryptoError {
    CryptoError::WrongKeyKind {
        label: label.to_string(),
        expected: expected.name(),
        actual: actual.name(),
    }
}
