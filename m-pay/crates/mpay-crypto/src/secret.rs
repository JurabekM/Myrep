//! Sir kalit tiplari va constant-time solishtirish.

use core::fmt;

use subtle::ConstantTimeEq;
use zeroize::Zeroizing;

/// Ikki bayt ketma-ketligini constant-time solishtiradi (uzunlik ochiq ma'lumot hisoblanadi).
pub fn ct_eq(a: &[u8], b: &[u8]) -> bool {
    a.len() == b.len() && bool::from(a.ct_eq(b))
}

macro_rules! secret_key {
    ($(#[$m:meta])* $name:ident, $n:literal) => {
        $(#[$m])*
        #[derive(Clone)]
        pub struct $name(Zeroizing<[u8; $n]>);

        impl $name {
            pub const LEN: usize = $n;

            pub fn from_bytes(b: [u8; $n]) -> Self {
                Self(Zeroizing::new(b))
            }

            /// Slice'dan (uzunlik mos kelmasa `None`).
            pub fn from_slice(s: &[u8]) -> Option<Self> {
                let mut a = Zeroizing::new([0u8; $n]);
                if s.len() != $n {
                    return None;
                }
                a.copy_from_slice(s);
                Some(Self(a))
            }

            /// Kalit baytlari — faqat kriptografik primitivga uzatish uchun.
            pub fn expose(&self) -> &[u8; $n] {
                &self.0
            }
        }

        impl PartialEq for $name {
            fn eq(&self, other: &Self) -> bool {
                ct_eq(&self.0[..], &other.0[..])
            }
        }
        impl Eq for $name {}

        impl fmt::Debug for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(concat!(stringify!($name), "(<maxfiy>)"))
            }
        }
    };
}

secret_key!(
    /// 128 bitli sir kalit (AES-128: MK_tok, LUK, SK).
    SecretKey16,
    16
);
secret_key!(
    /// 256 bitli sir kalit (DEK, PQ Link transport kalitlari).
    SecretKey32,
    32
);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn debug_is_redacted() {
        let k = SecretKey16::from_bytes([0x42; 16]);
        assert_eq!(format!("{k:?}"), "SecretKey16(<maxfiy>)");
    }

    #[test]
    fn ct_eq_works() {
        assert!(ct_eq(b"abc", b"abc"));
        assert!(!ct_eq(b"abc", b"abd"));
        assert!(!ct_eq(b"abc", b"ab"));
        assert!(SecretKey16::from_slice(&[0; 15]).is_none());
    }
}
