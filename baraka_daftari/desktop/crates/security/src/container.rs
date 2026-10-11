//! `.baraka` shifrlangan konteyner (DESKTOP_PROMPT 6.3): `Argon2id(parol) → XChaCha20-Poly1305`.
//!
//! Format (mobil ilova bilan umumiy, `spec/interchange/README.md`):
//! ```text
//! magic[8] = "BARAKA1\n" | m_kib u32 BE | t u32 BE | p u32 BE | salt[16] | nonce[24] | ciphertext+tag
//! ```
//! AAD = magic..nonce (sarlavhaning o'zi): sarlavhani o'zgartirish tekshiruvdan o'tmaydi.
//! AEAD noto'g'ri parol va buzilgan ma'lumotni farqlay olmaydi; sarlavha butunligi (magic, uzunlik,
//! KDF chegaralari) alohida tekshiriladi, shuning uchun `WrongPassword` = «parol noto'g'ri yoki
//! shifrlangan qism buzilgan».

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::{
    aead::{Aead, Payload},
    KeyInit, XChaCha20Poly1305,
};
use zeroize::Zeroizing;

use crate::{KdfParams, SecurityError};

const MAGIC: &[u8; 8] = b"BARAKA1\n";
const SALT_LEN: usize = 16;
const NONCE_LEN: usize = 24;
const HEADER_LEN: usize = 8 + 12 + SALT_LEN + NONCE_LEN;
/// Eksport parolining eng kam uzunligi (belgilar soni).
pub const MIN_PASSWORD_CHARS: usize = 8;

fn random<const N: usize>() -> Result<[u8; N], SecurityError> {
    let mut b = [0u8; N];
    getrandom::fill(&mut b).map_err(|_| SecurityError::Crypto)?;
    Ok(b)
}

fn derive(
    password: &str,
    salt: &[u8],
    kdf: KdfParams,
) -> Result<Zeroizing<[u8; 32]>, SecurityError> {
    let params =
        Params::new(kdf.m_kib, kdf.t, kdf.p, Some(32)).map_err(|_| SecurityError::Crypto)?;
    let mut key = Zeroizing::new([0u8; 32]);
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
        .hash_password_into(password.as_bytes(), salt, key.as_mut())
        .map_err(|_| SecurityError::Crypto)?;
    Ok(key)
}

fn cipher(key: &[u8; 32]) -> Result<XChaCha20Poly1305, SecurityError> {
    XChaCha20Poly1305::new_from_slice(key).map_err(|_| SecurityError::Crypto)
}

/// # Errors
/// Parol juda qisqa yoki kriptografiya xatosi.
pub fn seal(plaintext: &[u8], password: &str, kdf: KdfParams) -> Result<Vec<u8>, SecurityError> {
    if password.chars().count() < MIN_PASSWORD_CHARS {
        return Err(SecurityError::WeakPassword);
    }
    let kdf = kdf.validate()?;
    let salt = random::<SALT_LEN>()?;
    let nonce = random::<NONCE_LEN>()?;
    let mut out = Vec::with_capacity(HEADER_LEN + plaintext.len() + 16);
    out.extend_from_slice(MAGIC);
    for v in [kdf.m_kib, kdf.t, kdf.p] {
        out.extend_from_slice(&v.to_be_bytes());
    }
    out.extend_from_slice(&salt);
    out.extend_from_slice(&nonce);
    let key = derive(password, &salt, kdf)?;
    let ct = cipher(&key)?
        .encrypt(
            (&nonce).into(),
            Payload {
                msg: plaintext,
                aad: &out,
            },
        )
        .map_err(|_| SecurityError::Crypto)?;
    out.extend_from_slice(&ct);
    Ok(out)
}

/// # Errors
/// Sarlavha noto'g'ri → `Corrupt`; parol noto'g'ri (yoki shifrlangan qism buzilgan) → `WrongPassword`.
pub fn open(data: &[u8], password: &str) -> Result<Zeroizing<Vec<u8>>, SecurityError> {
    if data.len() < HEADER_LEN + 16 || &data[..8] != MAGIC {
        return Err(SecurityError::Corrupt("bu .baraka fayli emas".into()));
    }
    let word = |i: usize| -> Result<u32, SecurityError> {
        let b: [u8; 4] = data[8 + i * 4..12 + i * 4]
            .try_into()
            .map_err(|_| SecurityError::Corrupt("sarlavha".into()))?;
        Ok(u32::from_be_bytes(b))
    };
    let kdf = KdfParams {
        m_kib: word(0)?,
        t: word(1)?,
        p: word(2)?,
    }
    .validate()?;
    let salt = &data[20..20 + SALT_LEN];
    let nonce: [u8; NONCE_LEN] = data[20 + SALT_LEN..HEADER_LEN]
        .try_into()
        .map_err(|_| SecurityError::Corrupt("sarlavha".into()))?;
    let key = derive(password, salt, kdf)?;
    let pt = cipher(&key)?
        .decrypt(
            (&nonce).into(),
            Payload {
                msg: &data[HEADER_LEN..],
                aad: &data[..HEADER_LEN],
            },
        )
        .map_err(|_| SecurityError::WrongPassword)?;
    Ok(Zeroizing::new(pt))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_and_wrong_password() {
        let sealed = seal(b"salom dunyo", "parol-12345", KdfParams::fast_for_tests()).unwrap();
        assert_eq!(
            open(&sealed, "parol-12345").unwrap().as_slice(),
            b"salom dunyo"
        );
        assert_eq!(
            open(&sealed, "parol-12346").unwrap_err(),
            SecurityError::WrongPassword
        );
    }

    #[test]
    fn weak_password_rejected() {
        assert_eq!(
            seal(b"x", "qisqa", KdfParams::fast_for_tests()).unwrap_err(),
            SecurityError::WeakPassword
        );
    }

    #[test]
    fn header_tamper_and_garbage_detected() {
        let mut sealed = seal(b"abc", "parol-12345", KdfParams::fast_for_tests()).unwrap();
        assert!(matches!(
            open(b"nope", "parol-12345"),
            Err(SecurityError::Corrupt(_))
        ));
        // KDF parametri o'zgartirilsa — AAD/kalit mos kelmaydi.
        sealed[11] ^= 0x01;
        assert!(open(&sealed, "parol-12345").is_err());
        let mut sealed = seal(b"abc", "parol-12345", KdfParams::fast_for_tests()).unwrap();
        let last = sealed.len() - 1;
        sealed[last] ^= 0xff;
        assert_eq!(
            open(&sealed, "parol-12345").unwrap_err(),
            SecurityError::WrongPassword
        );
    }

    #[test]
    fn nonce_is_fresh_each_time() {
        let a = seal(b"abc", "parol-12345", KdfParams::fast_for_tests()).unwrap();
        let b = seal(b"abc", "parol-12345", KdfParams::fast_for_tests()).unwrap();
        assert_ne!(a, b);
    }
}
