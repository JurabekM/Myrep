//! A'zo PIN'i (SPEC 2B.3): har bir kattaning havas chegarasiga roziligi o'z PIN'i bilan tasdiqlanadi.
//!
//! Verifier — `tuz (16 bayt) || Argon2id(PIN, tuz) (32 bayt)`. PIN saqlanmaydi. Solishtirish doimiy vaqtda.
//! Urinishlar hisobi (lockout) saqlash qatlamida: bu modul faqat PIN'ni tekshiradi.

use rand::{TryRng, rngs::SysRng};

use crate::SecurityError;
use crate::kdf::{KdfParams, SALT_LEN, derive_pin_key};
use crate::pin::validate_pin;

/// Argon2id natijasi uzunligi (bayt).
const DERIVED_LEN: usize = 32;

/// Verifier uzunligi: tuz va hosila kalit.
pub const VERIFIER_LEN: usize = SALT_LEN + DERIVED_LEN;

/// Yangi PIN uchun verifier. PIN formati noto'g'ri bo'lsa — [`SecurityError::InvalidPin`].
pub fn create_member_verifier(pin: &str, params: KdfParams) -> Result<Vec<u8>, SecurityError> {
    validate_pin(pin)?;
    let mut salt = [0_u8; SALT_LEN];
    SysRng
        .try_fill_bytes(&mut salt)
        .map_err(|error| SecurityError::Rng(error.to_string()))?;
    let key = derive_pin_key(pin.as_bytes(), &salt, params)?;
    let mut verifier = Vec::with_capacity(VERIFIER_LEN);
    verifier.extend_from_slice(&salt);
    verifier.extend_from_slice(key.as_bytes());
    Ok(verifier)
}

/// PIN verifier bilan mosligini tekshiradi. Verifier uzunligi noto'g'ri bo'lsa — [`SecurityError::Kdf`].
pub fn verify_member_pin(
    pin: &str,
    verifier: &[u8],
    params: KdfParams,
) -> Result<bool, SecurityError> {
    validate_pin(pin)?;
    if verifier.len() != VERIFIER_LEN {
        return Err(SecurityError::Kdf);
    }
    let mut salt = [0_u8; SALT_LEN];
    salt.copy_from_slice(&verifier[..SALT_LEN]);
    let key = derive_pin_key(pin.as_bytes(), &salt, params)?;
    Ok(constant_time_eq(key.as_bytes(), &verifier[SALT_LEN..]))
}

/// Ikki baytli massivni vaqtga bog'liq bo'lmagan usulda solishtiradi.
fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    a.len() == b.len() && a.iter().zip(b).fold(0_u8, |acc, (x, y)| acc | (x ^ y)) == 0
}

#[cfg(test)]
mod tests {
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use super::*;

    const PIN: &str = "135790";

    #[test]
    fn togri_pin_mos_keladi() {
        let verifier = create_member_verifier(PIN, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");
        assert_eq!(verifier.len(), VERIFIER_LEN);
        assert!(
            verify_member_pin(PIN, &verifier, KdfParams::FAST_FOR_TESTS).expect("tekshirilsin")
        );
    }

    #[test]
    fn notogri_pin_mos_kelmaydi() {
        let verifier = create_member_verifier(PIN, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");
        assert!(
            !verify_member_pin("000000", &verifier, KdfParams::FAST_FOR_TESTS)
                .expect("tekshirilsin")
        );
    }

    #[test]
    fn bir_xil_pin_turli_tuz_bilan_turli_verifier_beradi() {
        let first = create_member_verifier(PIN, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");
        let second = create_member_verifier(PIN, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");
        assert_ne!(first, second);
    }

    #[test]
    fn format_xato_pin_kdf_ga_bormaydi() {
        let verifier = create_member_verifier(PIN, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");
        assert!(matches!(
            verify_member_pin("12", &verifier, KdfParams::FAST_FOR_TESTS),
            Err(SecurityError::InvalidPin)
        ));
        assert!(matches!(
            create_member_verifier("abc", KdfParams::FAST_FOR_TESTS),
            Err(SecurityError::InvalidPin)
        ));
    }

    #[test]
    fn buzuq_verifier_rad_etiladi() {
        assert!(matches!(
            verify_member_pin(PIN, &[0_u8; 5], KdfParams::FAST_FOR_TESTS),
            Err(SecurityError::Kdf)
        ));
    }
}
