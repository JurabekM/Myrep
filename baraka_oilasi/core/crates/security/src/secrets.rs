use std::fmt;

use data_encoding::BASE32_NOPAD;
use zeroize::{Zeroize, Zeroizing};

use crate::SecurityError;

pub const SECRET_LEN: usize = 32;
/// Tiklash kodi: 15 bayt (120 bit) → 24 ta base32 belgi.
const RECOVERY_BYTES: usize = 15;

pub(crate) fn random_bytes<const N: usize>() -> Result<[u8; N], SecurityError> {
    let mut b = [0u8; N];
    getrandom::fill(&mut b).map_err(|_| SecurityError::Random)?;
    Ok(b)
}

macro_rules! secret32 {
    ($(#[$m:meta])* $name:ident) => {
        $(#[$m])*
        #[derive(Clone, Zeroize)]
        #[zeroize(drop)]
        pub struct $name([u8; SECRET_LEN]);

        impl $name {
            pub fn from_bytes(bytes: [u8; SECRET_LEN]) -> Self {
                Self(bytes)
            }

            pub fn from_slice(bytes: &[u8]) -> Result<Self, SecurityError> {
                let arr: [u8; SECRET_LEN] = bytes.try_into().map_err(|_| SecurityError::KeyFileCorrupt)?;
                Ok(Self(arr))
            }

            pub fn generate() -> Result<Self, SecurityError> {
                Ok(Self(random_bytes::<SECRET_LEN>()?))
            }

            pub fn as_bytes(&self) -> &[u8; SECRET_LEN] {
                &self.0
            }
        }

        impl fmt::Debug for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(concat!(stringify!($name), "(***)"))
            }
        }
    };
}

secret32!(
    /// SQLCipher bazasining kaliti.
    DbKey
);
secret32!(
    /// Qurilmaga bog'langan sir: Android — Keystore bilan wrap qilingan, desktop — OS keyring.
    PlatformSecret
);
secret32!(
    /// Biometriya bilan ochiladigan platforma kalitidan olingan KEK.
    BioKek
);

impl DbKey {
    /// SQLCipher uchun xom kalit: `x'…64 hex…'` (PRAGMA key orqali).
    pub fn sqlcipher_pragma_value(&self) -> Zeroizing<String> {
        Zeroizing::new(format!("x'{}'", hex::encode(self.0)))
    }
}

/// 6 xonali PIN. Xotirada tozalanadi.
#[derive(Clone, Zeroize)]
#[zeroize(drop)]
pub struct Pin(String);

impl Pin {
    pub fn parse(s: &str) -> Result<Self, SecurityError> {
        if s.len() == 6 && s.bytes().all(|b| b.is_ascii_digit()) {
            Ok(Self(s.to_string()))
        } else {
            Err(SecurityError::PinFormat)
        }
    }

    pub(crate) fn as_bytes(&self) -> &[u8] {
        self.0.as_bytes()
    }
}

impl fmt::Debug for Pin {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("Pin(***)")
    }
}

/// Tiklash kodi: `ABCD-EFGH-IJKL-MNOP-QRST-UVWX` (24 base32 belgi, ~120 bit).
#[derive(Clone, Zeroize)]
#[zeroize(drop)]
pub struct RecoveryCode(String);

impl RecoveryCode {
    pub(crate) fn generate() -> Result<Self, SecurityError> {
        let bytes = Zeroizing::new(random_bytes::<RECOVERY_BYTES>()?);
        Ok(Self(BASE32_NOPAD.encode(&bytes[..])))
    }

    /// Foydalanuvchi kiritgan kod: katta-kichik harf, chiziqcha va bo'shliqlar e'tiborga olinmaydi.
    pub fn parse(s: &str) -> Result<Self, SecurityError> {
        let norm: String = s
            .chars()
            .filter(|c| !matches!(c, '-' | ' ' | '\u{00A0}'))
            .map(|c| c.to_ascii_uppercase())
            .collect();
        let decoded = BASE32_NOPAD
            .decode(norm.as_bytes())
            .map_err(|_| SecurityError::RecoveryCodeFormat)?;
        if decoded.len() != RECOVERY_BYTES {
            return Err(SecurityError::RecoveryCodeFormat);
        }
        Ok(Self(norm))
    }

    /// Ko'rsatish uchun 4 tadan guruhlangan ko'rinish.
    pub fn display_grouped(&self) -> Zeroizing<String> {
        let mut out = String::with_capacity(29);
        for (i, c) in self.0.chars().enumerate() {
            if i > 0 && i % 4 == 0 {
                out.push('-');
            }
            out.push(c);
        }
        Zeroizing::new(out)
    }

    pub(crate) fn as_bytes(&self) -> &[u8] {
        self.0.as_bytes()
    }
}

impl fmt::Debug for RecoveryCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("RecoveryCode(***)")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pin_format() {
        assert!(Pin::parse("123456").is_ok());
        for bad in ["12345", "1234567", "12a456", "", "١٢٣٤٥٦"] {
            assert_eq!(
                Pin::parse(bad).map(|_| ()),
                Err(SecurityError::PinFormat),
                "{bad}"
            );
        }
    }

    #[test]
    fn recovery_code_roundtrip() {
        let code = RecoveryCode::generate().unwrap();
        let shown = code.display_grouped();
        assert_eq!(shown.len(), 29);
        let parsed = RecoveryCode::parse(&shown.to_lowercase()).unwrap();
        assert_eq!(parsed.as_bytes(), code.as_bytes());
        assert!(RecoveryCode::parse("ABCD").is_err());
    }

    #[test]
    fn debug_never_leaks() {
        let k = DbKey::from_bytes([7; 32]);
        assert_eq!(format!("{k:?}"), "DbKey(***)");
        assert_eq!(format!("{:?}", Pin::parse("123456").unwrap()), "Pin(***)");
    }
}
