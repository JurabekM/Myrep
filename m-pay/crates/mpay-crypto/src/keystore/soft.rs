//! Dasturiy primitivlar (RustCrypto) — `MemoryKeyStore` va KDF uchun umumiy.

use aes::Aes128;
use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Nonce};
use cmac::{Cmac, Mac};
use ed25519_dalek::{Signer, SigningKey};
use hmac::Hmac;
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::CryptoError;

pub(crate) fn cmac_aes128(key: &[u8; 16], data: &[u8]) -> [u8; 16] {
    // 16 baytli kalit AES-128 uchun doim to'g'ri uzunlik.
    let mut mac = <Cmac<Aes128> as KeyInit>::new(key.into());
    mac.update(data);
    mac.finalize().into_bytes().into()
}

pub(crate) fn hmac_sha256(key: &[u8], data: &[u8]) -> Result<[u8; 32], CryptoError> {
    let mut mac = <Hmac<Sha256> as KeyInit>::new_from_slice(key)
        .map_err(|_| CryptoError::BadInput("HMAC kalit uzunligi"))?;
    mac.update(data);
    Ok(mac.finalize().into_bytes().into())
}

pub(crate) fn gcm_seal(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    pt: &[u8],
) -> Result<Vec<u8>, CryptoError> {
    let cipher = Aes256Gcm::new(key.into());
    cipher
        .encrypt(&Nonce::from(*nonce), Payload { msg: pt, aad })
        .map_err(|_| CryptoError::BadInput("AES-GCM shifrlash"))
}

pub(crate) fn gcm_open(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    ct: &[u8],
) -> Result<Zeroizing<Vec<u8>>, CryptoError> {
    let cipher = Aes256Gcm::new(key.into());
    cipher
        .decrypt(&Nonce::from(*nonce), Payload { msg: ct, aad })
        .map(Zeroizing::new)
        .map_err(|_| CryptoError::Decrypt)
}

pub(crate) fn ed25519_sign(seed: &[u8; 32], msg: &[u8]) -> [u8; 64] {
    SigningKey::from_bytes(seed).sign(msg).to_bytes()
}

pub(crate) fn ed25519_public(seed: &[u8; 32]) -> [u8; 32] {
    SigningKey::from_bytes(seed).verifying_key().to_bytes()
}
