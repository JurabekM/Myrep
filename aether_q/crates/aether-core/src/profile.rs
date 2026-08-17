//! Profil identifikatsiyasi — spec 3-bo'lim: har bir paketning birinchi bayti.

use crate::CoreError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum AetherProfile {
    /// X25519 + ML-KEM-768 (X-Wing)
    Default = 0x01,
    /// X25519 + ML-KEM-768 + HQC-192 (Triple-Hybrid)
    Paranoid = 0x02,
    /// ML-KEM-768 Standalone
    Minimal = 0x03,
    /// Stateful Delta Compression Frame
    Compress = 0x04,
    /// Single-Pass Authenticated KEM
    AuthAkem = 0x05,
}

impl AetherProfile {
    pub const fn as_byte(self) -> u8 {
        self as u8
    }
}

impl TryFrom<u8> for AetherProfile {
    type Error = CoreError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0x01 => Ok(Self::Default),
            0x02 => Ok(Self::Paranoid),
            0x03 => Ok(Self::Minimal),
            0x04 => Ok(Self::Compress),
            0x05 => Ok(Self::AuthAkem),
            // 7.4: noma'lum profil bilan bir xil yagona xato siyosati (oracle'ga qarshi).
            _ => Err(CoreError::DecryptFailure),
        }
    }
}
