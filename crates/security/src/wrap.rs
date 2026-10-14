use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{Key, XChaCha20Poly1305, XNonce};
use rand::{TryRng, rngs::SysRng};
use zeroize::Zeroizing;

use crate::kdf::{KdfParams, SALT_LEN, derive_pin_key};
use crate::key::KEY_LEN;
use crate::{SecretKey, SecurityError};

/// Nonce uzunligi (XChaCha20-Poly1305): 24 bayt.
const NONCE_LEN: usize = 24;
/// Ichki qatlam: DB kaliti (32) + autentifikatsiya tegi (16).
const INNER_CT_LEN: usize = KEY_LEN + 16;
/// Tashqi qatlam: ichki qatlam (48) + autentifikatsiya tegi (16).
const OUTER_CT_LEN: usize = INNER_CT_LEN + 16;
/// Fayl sarlavhasi: magic (8) + KDF parametrlari (12) + tuz (16). Ikkala qatlam uchun AAD.
const HEADER_LEN: usize = 8 + 12 + SALT_LEN;
/// Kalit faylining to'liq uzunligi (bayt).
pub const FILE_LEN: usize =
    HEADER_LEN + 4 + 8 + NONCE_LEN + INNER_CT_LEN + NONCE_LEN + OUTER_CT_LEN;

const MAGIC: &[u8; 8] = b"BDKEY001";

/// Kalit fayli: DB kalitining ikki qatlamli o'ralgan shakli va lockout holati.
///
/// Ikkilamchi ma'lumotlar (tuz, nonce'lar, shifrmatn) sir emas, lekin ularsiz kalit ochilmaydi.
/// Lockout maydonlari (`failed_attempts`, `last_failed_unix`) faylda ochiq turadi: ularni o'zgartirish
/// faqat kutishni qisqartiradi, kalitni ochmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyFile {
    /// Argon2id parametrlari.
    pub params: KdfParams,
    /// PIN kalitining tuzi.
    pub salt: [u8; SALT_LEN],
    /// Ketma-ket noto'g'ri PIN urinishlari soni.
    pub failed_attempts: u32,
    /// Oxirgi noto'g'ri urinish vaqti (Unix soniyalarida).
    pub last_failed_unix: i64,
    nonce_inner: [u8; NONCE_LEN],
    ct_inner: [u8; INNER_CT_LEN],
    nonce_outer: [u8; NONCE_LEN],
    ct_outer: [u8; OUTER_CT_LEN],
}

impl KeyFile {
    /// DB kalitini PIN va keyring kaliti bilan ikki qatlamda o'raydi.
    pub fn wrap(
        db_key: &SecretKey,
        pin: &str,
        device_key: &SecretKey,
        params: KdfParams,
    ) -> Result<Self, SecurityError> {
        let salt = random_array::<SALT_LEN>()?;
        let nonce_inner = random_array::<NONCE_LEN>()?;
        let nonce_outer = random_array::<NONCE_LEN>()?;
        let header = header_bytes(params, &salt);

        let pin_key = derive_pin_key(pin.as_bytes(), &salt, params)?;
        let inner = seal(&pin_key, &nonce_inner, db_key.as_bytes(), &header)?;
        let outer = seal(device_key, &nonce_outer, &inner, &header)?;

        Ok(Self {
            params,
            salt,
            failed_attempts: 0,
            last_failed_unix: 0,
            nonce_inner,
            ct_inner: to_array(&inner)?,
            nonce_outer,
            ct_outer: to_array(&outer)?,
        })
    }

    /// Avval keyring kaliti bilan tashqi qatlamni, keyin PIN bilan ichki qatlamni ochadi.
    /// Keyring kaliti noto'g'ri bo'lsa — [`SecurityError::KeyringMismatch`], PIN noto'g'ri bo'lsa — [`SecurityError::WrongPin`].
    pub fn unwrap(&self, pin: &str, device_key: &SecretKey) -> Result<SecretKey, SecurityError> {
        let header = header_bytes(self.params, &self.salt);
        let inner = open(device_key, &self.nonce_outer, &self.ct_outer, &header)
            .map_err(|_| SecurityError::KeyringMismatch)?;

        let pin_key = derive_pin_key(pin.as_bytes(), &self.salt, self.params)?;
        let db_key_bytes = Zeroizing::new(
            open(&pin_key, &self.nonce_inner, &inner, &header)
                .map_err(|_| SecurityError::WrongPin)?,
        );
        SecretKey::from_slice(&db_key_bytes).ok_or(SecurityError::CorruptKeyFile)
    }

    /// Faylga yoziladigan bayt ketma-ketligi (aniq [`FILE_LEN`] bayt).
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(FILE_LEN);
        bytes.extend_from_slice(&header_bytes(self.params, &self.salt));
        bytes.extend_from_slice(&self.failed_attempts.to_le_bytes());
        bytes.extend_from_slice(&self.last_failed_unix.to_le_bytes());
        bytes.extend_from_slice(&self.nonce_inner);
        bytes.extend_from_slice(&self.ct_inner);
        bytes.extend_from_slice(&self.nonce_outer);
        bytes.extend_from_slice(&self.ct_outer);
        bytes
    }

    /// Fayl baytlaridan o'qiydi. Uzunlik yoki magic noto'g'ri bo'lsa — [`SecurityError::CorruptKeyFile`].
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, SecurityError> {
        if bytes.len() != FILE_LEN || &bytes[..8] != MAGIC {
            return Err(SecurityError::CorruptKeyFile);
        }
        let params = KdfParams {
            m_cost_kib: u32::from_le_bytes(to_array(&bytes[8..12])?),
            t_cost: u32::from_le_bytes(to_array(&bytes[12..16])?),
            p_cost: u32::from_le_bytes(to_array(&bytes[16..20])?),
        };
        let mut offset = 20;
        let salt = take::<SALT_LEN>(bytes, &mut offset)?;
        let failed_attempts = u32::from_le_bytes(take(bytes, &mut offset)?);
        let last_failed_unix = i64::from_le_bytes(take(bytes, &mut offset)?);
        let nonce_inner = take::<NONCE_LEN>(bytes, &mut offset)?;
        let ct_inner = take::<INNER_CT_LEN>(bytes, &mut offset)?;
        let nonce_outer = take::<NONCE_LEN>(bytes, &mut offset)?;
        let ct_outer = take::<OUTER_CT_LEN>(bytes, &mut offset)?;

        Ok(Self {
            params,
            salt,
            failed_attempts,
            last_failed_unix,
            nonce_inner,
            ct_inner,
            nonce_outer,
            ct_outer,
        })
    }
}

fn header_bytes(params: KdfParams, salt: &[u8; SALT_LEN]) -> [u8; HEADER_LEN] {
    let mut header = [0_u8; HEADER_LEN];
    header[..8].copy_from_slice(MAGIC);
    header[8..12].copy_from_slice(&params.m_cost_kib.to_le_bytes());
    header[12..16].copy_from_slice(&params.t_cost.to_le_bytes());
    header[16..20].copy_from_slice(&params.p_cost.to_le_bytes());
    header[20..].copy_from_slice(salt);
    header
}

fn seal(
    key: &SecretKey,
    nonce: &[u8; NONCE_LEN],
    plaintext: &[u8],
    aad: &[u8],
) -> Result<Vec<u8>, SecurityError> {
    let key = Key::from(*key.as_bytes());
    let cipher = XChaCha20Poly1305::new(&key);
    cipher
        .encrypt(
            &XNonce::from(*nonce),
            Payload {
                msg: plaintext,
                aad,
            },
        )
        .map_err(|_| SecurityError::Crypto)
}

fn open(
    key: &SecretKey,
    nonce: &[u8; NONCE_LEN],
    ciphertext: &[u8],
    aad: &[u8],
) -> Result<Vec<u8>, SecurityError> {
    let key = Key::from(*key.as_bytes());
    let cipher = XChaCha20Poly1305::new(&key);
    cipher
        .decrypt(
            &XNonce::from(*nonce),
            Payload {
                msg: ciphertext,
                aad,
            },
        )
        .map_err(|_| SecurityError::Crypto)
}

fn random_array<const N: usize>() -> Result<[u8; N], SecurityError> {
    let mut bytes = [0_u8; N];
    SysRng
        .try_fill_bytes(&mut bytes)
        .map_err(|error| SecurityError::Rng(error.to_string()))?;
    Ok(bytes)
}

fn to_array<const N: usize>(bytes: &[u8]) -> Result<[u8; N], SecurityError> {
    bytes.try_into().map_err(|_| SecurityError::Crypto)
}

fn take<const N: usize>(bytes: &[u8], offset: &mut usize) -> Result<[u8; N], SecurityError> {
    let end = *offset + N;
    let slice = bytes
        .get(*offset..end)
        .ok_or(SecurityError::CorruptKeyFile)?;
    *offset = end;
    to_array(slice).map_err(|_| SecurityError::CorruptKeyFile)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(byte: u8) -> SecretKey {
        SecretKey::from_array([byte; KEY_LEN])
    }

    #[test]
    fn fayl_uzunligi_va_qayta_oqish() {
        let file = KeyFile::wrap(&key(7), "135790", &key(9), KdfParams::FAST_FOR_TESTS)
            .expect("o'rash ishlashi kerak");
        let bytes = file.to_bytes();
        assert_eq!(bytes.len(), FILE_LEN);
        assert_eq!(KeyFile::from_bytes(&bytes).expect("o'qilsin"), file);
    }

    #[test]
    fn to_gri_pin_va_keyring_kaliti_db_kalitini_beradi() {
        let db = key(7);
        let file =
            KeyFile::wrap(&db, "135790", &key(9), KdfParams::FAST_FOR_TESTS).expect("o'rash");
        let opened = file.unwrap("135790", &key(9)).expect("ochilsin");
        assert_eq!(opened.as_bytes(), db.as_bytes());
    }

    #[test]
    fn notogri_pin_wrong_pin_qaytaradi() {
        let file =
            KeyFile::wrap(&key(7), "135790", &key(9), KdfParams::FAST_FOR_TESTS).expect("o'rash");
        assert!(matches!(
            file.unwrap("000000", &key(9)),
            Err(SecurityError::WrongPin)
        ));
    }

    #[test]
    fn notogri_keyring_kaliti_mismatch_qaytaradi() {
        let file =
            KeyFile::wrap(&key(7), "135790", &key(9), KdfParams::FAST_FOR_TESTS).expect("o'rash");
        assert!(matches!(
            file.unwrap("135790", &key(8)),
            Err(SecurityError::KeyringMismatch)
        ));
    }

    #[test]
    fn buzilgan_fayl_aniqlanadi() {
        let file =
            KeyFile::wrap(&key(7), "135790", &key(9), KdfParams::FAST_FOR_TESTS).expect("o'rash");
        let mut bytes = file.to_bytes();
        bytes[0] = b'X';
        assert!(matches!(
            KeyFile::from_bytes(&bytes),
            Err(SecurityError::CorruptKeyFile)
        ));
        assert!(matches!(
            KeyFile::from_bytes(&bytes[..10]),
            Err(SecurityError::CorruptKeyFile)
        ));
    }

    #[test]
    fn kalit_debug_da_chiqmaydi() {
        let text = format!("{:?}", key(0x42));
        assert!(!text.contains("42"));
        assert!(text.contains("yashirin"));
    }
}
