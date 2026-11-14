//! Qurilma autentifikatsiyasi abstraksiyasi.
//!
//! Android'da implementatsiya — StrongBox'dagi P-256 kalit (Wallet SDK, M6);
//! Rust'da — sandbox `SoftDeviceKey` (`sandbox-attestation` feature).

use crate::PqLinkError;

/// Qurilmaning uzoq muddatli imzo kaliti va uning attestatsiya zanjiri.
pub trait DeviceSigner: Send + Sync {
    /// Attestatsiya zanjiri (DER, leaf birinchi).
    fn cert_chain(&self) -> Vec<Vec<u8>>;

    /// ECDSA P-256 / SHA-256 imzo (DER kodlangan).
    fn sign(&self, msg: &[u8]) -> Result<Vec<u8>, PqLinkError>;
}
