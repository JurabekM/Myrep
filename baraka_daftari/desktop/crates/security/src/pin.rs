//! A'zoning shaxsiy PIN tekshiruvchisi (havas chegarasiga rozilik uchun). PIN o'zi saqlanmaydi.
use argon2::{Algorithm, Argon2, Params, Version};
use subtle::ConstantTimeEq;
use zeroize::Zeroizing;

use crate::{KdfParams, SecurityError};

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

fn unhex(s: &str) -> Option<Vec<u8>> {
    if !s.len().is_multiple_of(2) || !s.is_ascii() {
        return None;
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).ok())
        .collect()
}

fn derive(pin: &str, salt: &[u8], kdf: KdfParams) -> Result<Zeroizing<[u8; 32]>, SecurityError> {
    let params =
        Params::new(kdf.m_kib, kdf.t, kdf.p, Some(32)).map_err(|_| SecurityError::Crypto)?;
    let mut out = Zeroizing::new([0u8; 32]);
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
        .hash_password_into(pin.as_bytes(), salt, out.as_mut())
        .map_err(|_| SecurityError::Crypto)?;
    Ok(out)
}

/// Aniq 6 ta ASCII raqam.
#[must_use]
pub fn is_valid_pin(pin: &str) -> bool {
    pin.len() == 6 && pin.bytes().all(|b| b.is_ascii_digit())
}

/// `v1$m$t$p$<salt hex>$<hash hex>` ko'rinishidagi tekshiruvchi.
///
/// # Errors
/// PIN formati noto'g'ri bo'lsa yoki tizim tasodifiyligi/KDF ishlamasa.
pub fn hash_pin(pin: &str, kdf: KdfParams) -> Result<String, SecurityError> {
    if !is_valid_pin(pin) {
        return Err(SecurityError::InvalidPin);
    }
    let mut salt = [0u8; 16];
    getrandom::fill(&mut salt).map_err(|_| SecurityError::Crypto)?;
    let key = derive(pin, &salt, kdf)?;
    Ok(format!(
        "v1${}${}${}${}${}",
        kdf.m_kib,
        kdf.t,
        kdf.p,
        hex(&salt),
        hex(key.as_ref())
    ))
}

/// Doimiy vaqtda solishtiradi. Buzilgan yozuv yoki noto'g'ri PIN — `false`.
#[must_use]
pub fn verify_pin(pin: &str, stored: &str) -> bool {
    if !is_valid_pin(pin) {
        return false;
    }
    let parts: Vec<&str> = stored.split('$').collect();
    let [version, m, t, p, salt, hash] = parts.as_slice() else {
        return false;
    };
    if *version != "v1" {
        return false;
    }
    let (Ok(m_kib), Ok(t), Ok(p)) = (m.parse::<u32>(), t.parse::<u32>(), p.parse::<u32>()) else {
        return false;
    };
    // Saqlangan parametrlar ham cheklanadi (DoS).
    if !(8..=1 << 20).contains(&m_kib) || !(1..=10).contains(&t) || !(1..=8).contains(&p) {
        return false;
    }
    let (Some(salt), Some(expected)) = (unhex(salt), unhex(hash)) else {
        return false;
    };
    let Ok(actual) = derive(pin, &salt, KdfParams { m_kib, t, p }) else {
        return false;
    };
    actual.as_ref().ct_eq(expected.as_slice()).into()
}

#[cfg(test)]
mod tests {
    use super::*;

    const FAST: KdfParams = KdfParams::fast_for_tests();

    #[test]
    fn roundtrip_and_rejects_wrong_pin() {
        let h = hash_pin("123456", FAST).unwrap();
        assert!(h.starts_with("v1$"));
        assert!(!h.contains("123456"));
        assert!(verify_pin("123456", &h));
        assert!(!verify_pin("654321", &h));
        assert!(!verify_pin("12345", &h));
        assert!(!verify_pin("12345a", &h));
    }

    #[test]
    fn same_pin_hashes_differently_thanks_to_salt() {
        assert_ne!(
            hash_pin("111111", FAST).unwrap(),
            hash_pin("111111", FAST).unwrap()
        );
    }

    #[test]
    fn invalid_pin_cannot_be_hashed() {
        for bad in ["", "12345", "1234567", "12345a", "١٢٣٤٥٦"] {
            assert_eq!(hash_pin(bad, FAST), Err(SecurityError::InvalidPin), "{bad}");
        }
    }

    #[test]
    fn corrupt_or_hostile_records_are_false_not_panics() {
        let good = hash_pin("123456", FAST).unwrap();
        for bad in [
            "".to_owned(),
            "v2$8$1$1$aa$bb".to_owned(),
            "v1$8$1$1$zz$bb".to_owned(),
            "v1$4000000000$1$1$aa$bb".to_owned(),
            "v1$8$0$1$aa$bb".to_owned(),
            good.replace("v1$8$1$1", "v1$8$1"),
            good[..good.len() - 2].to_owned(),
        ] {
            assert!(!verify_pin("123456", &bad), "{bad}");
        }
    }
}
