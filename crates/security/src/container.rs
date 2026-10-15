//! `.baraka` almashish konteyneri (DESKTOP_PROMPT 6.3, D14): Argon2id(parol) → XChaCha20-Poly1305.
//!
//! Tartib: magic (8) + KDF parametrlari (12) + tuz (16) + nonce (24) + shifrmatn (+16 teg).
//! Sarlavha (magic + parametrlar + tuz) — AAD: uni o'zgartirib bo'lmaydi. Parol xato bo'lsa teg mos kelmaydi —
//! [`SecurityError::WrongPassword`]. Format mobil ilova bilan umumiy (`spec/interchange/README.md`).

use zeroize::Zeroizing;

use crate::kdf::{KdfParams, SALT_LEN, derive_pin_key};
use crate::wrap::{open, random_array, seal};
use crate::SecurityError;

const MAGIC: &[u8; 8] = b"BARAKA01";
const NONCE_LEN: usize = 24;
const HEADER_LEN: usize = 8 + 12 + SALT_LEN;
/// Eng qisqa yaroqli fayl: sarlavha + nonce + teg.
const MIN_LEN: usize = HEADER_LEN + NONCE_LEN + 16;
/// Parol uzunligi chegarasi (belgilar).
pub const MIN_PASSWORD_CHARS: usize = 8;

fn header(params: KdfParams, salt: &[u8; SALT_LEN]) -> [u8; HEADER_LEN] {
    let mut out = [0_u8; HEADER_LEN];
    out[..8].copy_from_slice(MAGIC);
    out[8..12].copy_from_slice(&params.m_cost_kib.to_le_bytes());
    out[12..16].copy_from_slice(&params.t_cost.to_le_bytes());
    out[16..20].copy_from_slice(&params.p_cost.to_le_bytes());
    out[20..].copy_from_slice(salt);
    out
}

/// Parolni tekshiradi: kamida 8 belgi, bo'sh joylar hisobga olinmaydi.
pub fn validate_password(password: &str) -> Result<(), SecurityError> {
    if password.trim().chars().count() < MIN_PASSWORD_CHARS {
        return Err(SecurityError::WeakPassword);
    }
    Ok(())
}

/// Ochiq matnni parol bilan muhrlaydi; natija — fayl baytlari.
pub fn seal_container(
    password: &str,
    params: KdfParams,
    plaintext: &[u8],
) -> Result<Vec<u8>, SecurityError> {
    validate_password(password)?;
    let salt = random_array::<SALT_LEN>()?;
    let nonce = random_array::<NONCE_LEN>()?;
    let head = header(params, &salt);
    let key = derive_pin_key(password.trim().as_bytes(), &salt, params)?;
    let ciphertext = seal(&key, &nonce, plaintext, &head)?;
    let mut out = Vec::with_capacity(HEADER_LEN + NONCE_LEN + ciphertext.len());
    out.extend_from_slice(&head);
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ciphertext);
    Ok(out)
}

/// Fayl baytlarini parol bilan ochadi. Format buzilgan — [`SecurityError::CorruptContainer`],
/// parol noto'g'ri — [`SecurityError::WrongPassword`].
pub fn open_container(password: &str, bytes: &[u8]) -> Result<Zeroizing<Vec<u8>>, SecurityError> {
    if bytes.len() < MIN_LEN || &bytes[..8] != MAGIC {
        return Err(SecurityError::CorruptContainer);
    }
    let params = KdfParams {
        m_cost_kib: u32::from_le_bytes(slice4(&bytes[8..12])?),
        t_cost: u32::from_le_bytes(slice4(&bytes[12..16])?),
        p_cost: u32::from_le_bytes(slice4(&bytes[16..20])?),
    };
    let mut salt = [0_u8; SALT_LEN];
    salt.copy_from_slice(&bytes[20..HEADER_LEN]);
    let mut nonce = [0_u8; NONCE_LEN];
    nonce.copy_from_slice(&bytes[HEADER_LEN..HEADER_LEN + NONCE_LEN]);
    let head = header(params, &salt);
    let key = derive_pin_key(password.trim().as_bytes(), &salt, params)?;
    let plaintext = open(&key, &nonce, &bytes[HEADER_LEN + NONCE_LEN..], &head)
        .map_err(|_| SecurityError::WrongPassword)?;
    Ok(Zeroizing::new(plaintext))
}

fn slice4(bytes: &[u8]) -> Result<[u8; 4], SecurityError> {
    bytes
        .try_into()
        .map_err(|_| SecurityError::CorruptContainer)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn muhrlash_va_ochish_parol_bilan() {
        let bytes = seal_container("juda-sirli-parol", KdfParams::FAST_FOR_TESTS, b"{\"a\":1}")
            .expect("muhr");
        assert_eq!(&bytes[..8], b"BARAKA01");
        let plain = open_container("juda-sirli-parol", &bytes).expect("ochildi");
        assert_eq!(&**plain, b"{\"a\":1}");
        assert!(matches!(
            open_container("boshqa-parol-123", &bytes),
            Err(SecurityError::WrongPassword)
        ));
        assert!(matches!(
            open_container("juda-sirli-parol", &bytes[..20]),
            Err(SecurityError::CorruptContainer)
        ));
        assert!(matches!(
            seal_container("qisqa", KdfParams::FAST_FOR_TESTS, b"x"),
            Err(SecurityError::WeakPassword)
        ));
    }

    #[test]
    fn sarlavha_ozgartirilsa_ochilmaydi() {
        let mut bytes =
            seal_container("juda-sirli-parol", KdfParams::FAST_FOR_TESTS, b"salom").expect("muhr");
        bytes[21] ^= 0x01;
        assert!(matches!(
            open_container("juda-sirli-parol", &bytes),
            Err(SecurityError::WrongPassword)
        ));
    }
}
