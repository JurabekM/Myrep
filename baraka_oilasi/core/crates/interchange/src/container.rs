//! Shifrlangan konteyner (8.3).
//!
//! ```text
//! BARAKA-EXPORT\n
//! {"formatVersion":1,"aead":"xchacha20poly1305","kdf":{...},"salt":"…","nonce":"…"}\n
//! <shifrlangan JSON Lines + 16 bayt teg>
//! ```
//! Kalit = Argon2id(NFC(parol), salt, kdf) — 32 bayt. Birinchi ikki qator (sehrli satr va
//! sarlavha, `\n` lari bilan) AEAD uchun AAD: sarlavhadagi bitta bayt o'zgarsa ham ochilmaydi.
use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use serde::{Deserialize, Serialize};
use unicode_normalization::UnicodeNormalization;
use zeroize::Zeroizing;

use crate::{InterchangeError, FORMAT_VERSION};

pub const MAGIC: &[u8] = b"BARAKA-EXPORT\n";
pub const SALT_LEN: usize = 16;
pub const NONCE_LEN: usize = 24;
pub const KEY_LEN: usize = 32;
/// Foydalanuvchi paroli kamida shuncha belgi.
pub const MIN_PASSWORD_CHARS: usize = 8;
const AEAD: &str = "xchacha20poly1305";
/// Begona fayl sarlavhasidagi KDF parametrlari bilan qurilmani «qotirib» qo'ymaslik uchun.
const MAX_M_KIB: u32 = 262_144;
const MAX_T_COST: u32 = 10;
const MAX_P_COST: u32 = 4;
const MAX_HEADER_BYTES: usize = 1024;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Kdf {
    pub alg: KdfAlg,
    pub m_kib: u32,
    pub t_cost: u32,
    pub p_cost: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum KdfAlg {
    #[serde(rename = "argon2id")]
    Argon2id,
}

impl Kdf {
    /// Desktop va Android uchun standart (keys.bin dagi DESKTOP bilan bir xil).
    pub const STANDARD: Self = Self::argon2id(65_536, 3, 1);
    /// Faqat testlar va KAT vektorlari uchun.
    pub const INSECURE_FAST_FOR_TESTS: Self = Self::argon2id(64, 1, 1);

    pub const fn argon2id(m_kib: u32, t_cost: u32, p_cost: u32) -> Self {
        Self {
            alg: KdfAlg::Argon2id,
            m_kib,
            t_cost,
            p_cost,
        }
    }

    fn check(&self) -> Result<(), InterchangeError> {
        let ok = (1..=MAX_P_COST).contains(&self.p_cost)
            && (1..=MAX_T_COST).contains(&self.t_cost)
            && self.m_kib >= 8 * self.p_cost
            && self.m_kib <= MAX_M_KIB;
        if ok {
            Ok(())
        } else {
            Err(InterchangeError::KdfParams)
        }
    }
}

/// Ochiq sarlavha (maydonlar tartibi — formatning bir qismi: AAD baytlari shundan).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Header {
    pub format_version: u32,
    pub aead: String,
    pub kdf: Kdf,
    pub salt: String,
    pub nonce: String,
}

fn derive_key(
    password: &str,
    salt: &[u8],
    kdf: &Kdf,
) -> Result<Zeroizing<[u8; KEY_LEN]>, InterchangeError> {
    kdf.check()?;
    let normalized = Zeroizing::new(password.nfc().collect::<String>());
    let params = Params::new(kdf.m_kib, kdf.t_cost, kdf.p_cost, Some(KEY_LEN))
        .map_err(|_| InterchangeError::KdfParams)?;
    let mut key = Zeroizing::new([0u8; KEY_LEN]);
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
        .hash_password_into(normalized.as_bytes(), salt, &mut key[..])
        .map_err(|_| InterchangeError::Crypto)?;
    Ok(key)
}

/// Parol talabi: kamida 8 belgi (bo'shliqlar hisobga olinmaydi).
pub fn check_password(password: &str) -> Result<(), InterchangeError> {
    if password.trim().chars().count() < MIN_PASSWORD_CHARS {
        Err(InterchangeError::WeakPassword)
    } else {
        Ok(())
    }
}

fn random<const N: usize>() -> Result<[u8; N], InterchangeError> {
    let mut b = [0u8; N];
    getrandom::fill(&mut b).map_err(|_| InterchangeError::Random)?;
    Ok(b)
}

/// Tasodifiy salt va nonce bilan shifrlash.
pub fn seal(plaintext: &[u8], password: &str, kdf: Kdf) -> Result<Vec<u8>, InterchangeError> {
    check_password(password)?;
    seal_with(plaintext, password, kdf, random()?, random()?)
}

/// Deterministik shifrlash (KAT vektorlari uchun). Production'da [`seal`] ishlatiladi.
pub fn seal_with(
    plaintext: &[u8],
    password: &str,
    kdf: Kdf,
    salt: [u8; SALT_LEN],
    nonce: [u8; NONCE_LEN],
) -> Result<Vec<u8>, InterchangeError> {
    let header = Header {
        format_version: FORMAT_VERSION,
        aead: AEAD.into(),
        kdf,
        salt: hex::encode(salt),
        nonce: hex::encode(nonce),
    };
    let mut out = MAGIC.to_vec();
    out.extend(serde_json::to_vec(&header).map_err(|_| InterchangeError::Corrupt)?);
    out.push(b'\n');
    let key = derive_key(password, &salt, &kdf)?;
    let cipher =
        XChaCha20Poly1305::new_from_slice(&key[..]).map_err(|_| InterchangeError::Crypto)?;
    let sealed = cipher
        .encrypt(
            &XNonce::from(nonce),
            Payload {
                msg: plaintext,
                aad: &out,
            },
        )
        .map_err(|_| InterchangeError::Crypto)?;
    out.extend(sealed);
    Ok(out)
}

/// Sarlavhani shifr ochmasdan o'qiydi (fayl turi va KDF parametrlarini ko'rsatish uchun).
pub fn read_header(bytes: &[u8]) -> Result<(Header, usize), InterchangeError> {
    let rest = bytes
        .strip_prefix(MAGIC)
        .ok_or(InterchangeError::NotBaraka)?;
    let end = rest
        .iter()
        .take(MAX_HEADER_BYTES)
        .position(|b| *b == b'\n')
        .ok_or(InterchangeError::Corrupt)?;
    let value: serde_json::Value =
        serde_json::from_slice(&rest[..end]).map_err(|_| InterchangeError::Corrupt)?;
    // Avval versiya: kelajakdagi format yangi maydonlar bilan kelsa ham aniq xato bo'lsin.
    match value
        .get("formatVersion")
        .and_then(serde_json::Value::as_u64)
    {
        Some(v) if v == u64::from(FORMAT_VERSION) => {}
        Some(_) => return Err(InterchangeError::VersionUnsupported),
        None => return Err(InterchangeError::Corrupt),
    }
    let header: Header = serde_json::from_value(value).map_err(|_| InterchangeError::Corrupt)?;
    if header.aead != AEAD {
        return Err(InterchangeError::VersionUnsupported);
    }
    Ok((header, MAGIC.len() + end + 1))
}

/// Ochish. Noto'g'ri parol yoki o'zgartirilgan fayl — `INTERCHANGE_BAD_PASSWORD`.
pub fn open(
    bytes: &[u8],
    password: &str,
) -> Result<(Header, Zeroizing<Vec<u8>>), InterchangeError> {
    let (header, body) = read_header(bytes)?;
    let salt = hex::decode(&header.salt).map_err(|_| InterchangeError::Corrupt)?;
    let nonce: [u8; NONCE_LEN] = hex::decode(&header.nonce)
        .ok()
        .and_then(|v| v.try_into().ok())
        .ok_or(InterchangeError::Corrupt)?;
    if salt.len() != SALT_LEN {
        return Err(InterchangeError::Corrupt);
    }
    let key = derive_key(password, &salt, &header.kdf)?;
    let cipher =
        XChaCha20Poly1305::new_from_slice(&key[..]).map_err(|_| InterchangeError::Crypto)?;
    let plain = cipher
        .decrypt(
            &XNonce::from(nonce),
            Payload {
                msg: &bytes[body..],
                aad: &bytes[..body],
            },
        )
        .map_err(|_| InterchangeError::BadPassword)?;
    Ok((header, Zeroizing::new(plain)))
}

#[cfg(test)]
mod tests {
    use super::*;

    const FAST: Kdf = Kdf::INSECURE_FAST_FOR_TESTS;

    #[test]
    fn round_trip_and_errors() {
        let sealed = seal(b"{\"kind\":\"meta\"}\n", "maxfiy-parol", FAST).unwrap();
        let (h, plain) = open(&sealed, "maxfiy-parol").unwrap();
        assert_eq!(h.kdf, FAST);
        assert_eq!(&plain[..], b"{\"kind\":\"meta\"}\n");
        assert_eq!(
            open(&sealed, "boshqa-parol").err(),
            Some(InterchangeError::BadPassword)
        );
        assert_eq!(
            seal(b"x", "qisqa", FAST),
            Err(InterchangeError::WeakPassword)
        );
        assert_eq!(
            open(b"PK\x03\x04", "x").err(),
            Some(InterchangeError::NotBaraka)
        );
    }

    #[test]
    fn header_is_authenticated() {
        let sealed = seal(b"data", "maxfiy-parol", FAST).unwrap();
        // tCost 1 → 2: sarlavha AAD bo'lgani uchun ochilmaydi (to'g'ri parol bilan ham).
        let text = String::from_utf8_lossy(&sealed[..200]).to_string();
        let pos = text.find("\"tCost\":1").unwrap() + "\"tCost\":".len();
        let mut tampered = sealed.clone();
        tampered[pos] = b'2';
        assert_eq!(
            open(&tampered, "maxfiy-parol").err(),
            Some(InterchangeError::BadPassword)
        );
        // Shifrlangan qismdagi bitta bayt.
        let mut flipped = sealed.clone();
        let last = flipped.len() - 1;
        flipped[last] ^= 1;
        assert_eq!(
            open(&flipped, "maxfiy-parol").err(),
            Some(InterchangeError::BadPassword)
        );
    }

    #[test]
    fn header_limits() {
        let mut sealed = seal(b"data", "maxfiy-parol", FAST).unwrap();
        let text = String::from_utf8_lossy(&sealed[..60]).to_string();
        let pos = text.find("\"formatVersion\":1").unwrap() + "\"formatVersion\":".len();
        sealed[pos] = b'9';
        assert_eq!(
            open(&sealed, "maxfiy-parol").err(),
            Some(InterchangeError::VersionUnsupported)
        );
        let huge = seal_with(
            b"d",
            "maxfiy-parol",
            Kdf::argon2id(1 << 30, 1, 1),
            [0; 16],
            [0; 24],
        );
        assert_eq!(huge.err(), Some(InterchangeError::KdfParams));
    }

    #[test]
    fn password_is_nfc_normalized() {
        // «oʻ» ning ikki xil yozilishi: NFC dan keyin bir xil kalit.
        let composed = "Qo\u{2018}rg\u{2018}on-2026-\u{00e9}";
        let decomposed = "Qo\u{2018}rg\u{2018}on-2026-e\u{0301}";
        let sealed = seal(b"x", composed, FAST).unwrap();
        assert!(open(&sealed, decomposed).is_ok());
    }
}
