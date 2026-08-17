//! AEAD wrapper'i — 7.2-bo'lim: ChaCha20-Poly1305 (standart), AES-256-GCM (muqobil).

use crate::PrimitiveError;
use aes_gcm::Aes256Gcm;
use chacha20poly1305::aead::{Aead as _, KeyInit, Payload};
use chacha20poly1305::ChaCha20Poly1305;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AeadAlgorithm {
    ChaCha20Poly1305,
    Aes256Gcm,
}

pub fn seal(
    alg: AeadAlgorithm,
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    plaintext: &[u8],
) -> Result<Vec<u8>, PrimitiveError> {
    let payload = Payload { msg: plaintext, aad };
    match alg {
        AeadAlgorithm::ChaCha20Poly1305 => {
            let cipher = ChaCha20Poly1305::new_from_slice(key)
                .map_err(|_| PrimitiveError::InvalidEncoding)?;
            cipher
                .encrypt(nonce.into(), payload)
                .map_err(|_| PrimitiveError::OperationFailed)
        }
        AeadAlgorithm::Aes256Gcm => {
            let cipher = Aes256Gcm::new_from_slice(key).map_err(|_| PrimitiveError::InvalidEncoding)?;
            cipher
                .encrypt(nonce.into(), payload)
                .map_err(|_| PrimitiveError::OperationFailed)
        }
    }
}

pub fn open(
    alg: AeadAlgorithm,
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    ciphertext: &[u8],
) -> Result<Vec<u8>, PrimitiveError> {
    let payload = Payload { msg: ciphertext, aad };
    // S2/7.4: yagona umumiy xato turi qaytariladi — tag mismatch va boshqa
    // dekriptsiya xatolari farqlanmaydi (oracle hujumlariga qarshi himoya).
    match alg {
        AeadAlgorithm::ChaCha20Poly1305 => {
            let cipher = ChaCha20Poly1305::new_from_slice(key)
                .map_err(|_| PrimitiveError::AeadAuthFailed)?;
            cipher
                .decrypt(nonce.into(), payload)
                .map_err(|_| PrimitiveError::AeadAuthFailed)
        }
        AeadAlgorithm::Aes256Gcm => {
            let cipher =
                Aes256Gcm::new_from_slice(key).map_err(|_| PrimitiveError::AeadAuthFailed)?;
            cipher
                .decrypt(nonce.into(), payload)
                .map_err(|_| PrimitiveError::AeadAuthFailed)
        }
    }
}
