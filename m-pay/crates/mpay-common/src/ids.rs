//! Identifikator tiplari: token, qurilma, PAN barmoq izi.

use core::fmt;

use serde::{Deserialize, Serialize};

/// Token identifikatori: `tok_` + 32 hex belgi. Maxfiy emas — logga yozish mumkin.
#[derive(Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct TokenId(String);

impl TokenId {
    pub const PREFIX: &'static str = "tok_";

    /// 16 tasodifiy baytdan.
    pub fn from_random(bytes: [u8; 16]) -> Self {
        Self(format!("{}{}", Self::PREFIX, hex::encode(bytes)))
    }

    /// Satrni tekshirib o'qiydi.
    pub fn parse(s: &str) -> Option<Self> {
        let rest = s.strip_prefix(Self::PREFIX)?;
        (rest.len() == 32 && rest.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')))
            .then(|| Self(s.to_owned()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<String> for TokenId {
    type Error = String;
    fn try_from(s: String) -> Result<Self, Self::Error> {
        Self::parse(&s).ok_or_else(|| "noto'g'ri token ID".to_owned())
    }
}

impl From<TokenId> for String {
    fn from(t: TokenId) -> Self {
        t.0
    }
}

impl fmt::Debug for TokenId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl fmt::Display for TokenId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

macro_rules! hash_id {
    ($(#[$m:meta])* $name:ident, $short:literal) => {
        $(#[$m])*
        #[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
        pub struct $name(pub [u8; 32]);

        impl $name {
            pub fn to_hex(&self) -> String {
                hex::encode(self.0)
            }

            pub fn from_hex(s: &str) -> Option<Self> {
                let mut out = [0u8; 32];
                hex::decode_to_slice(s, &mut out).ok()?;
                Some(Self(out))
            }
        }

        impl fmt::Debug for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                write!(f, concat!($short, ":{}"), &hex::encode(&self.0[..8]))
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                fmt::Debug::fmt(self, f)
            }
        }

        impl Serialize for $name {
            fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
                s.serialize_str(&self.to_hex())
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
                let s = String::deserialize(d)?;
                Self::from_hex(&s).ok_or_else(|| serde::de::Error::custom("64 hex belgi kutilgan"))
            }
        }
    };
}

hash_id!(
    /// Qurilma identifikatori: `SHA-256(attestatsiya leaf SubjectPublicKeyInfo DER)`.
    DeviceId,
    "dev"
);

hash_id!(
    /// PAN barmoq izi: `HMAC-SHA256(PAN-IDX, PAN)`. Kalitsiz qaytarib bo'lmaydi; Shield karta
    /// identifikatori sifatida ishlatadi.
    PanFingerprint,
    "pfp"
);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn token_id_format() {
        let t = TokenId::from_random([0xAB; 16]);
        assert_eq!(t.as_str().len(), 36);
        assert_eq!(TokenId::parse(t.as_str()), Some(t.clone()));
        assert!(TokenId::parse("tok_XYZ").is_none());
        assert!(TokenId::parse(&t.as_str().to_uppercase()).is_none());
        let json = serde_json::to_string(&t).unwrap();
        assert_eq!(serde_json::from_str::<TokenId>(&json).unwrap(), t);
        assert!(serde_json::from_str::<TokenId>("\"tok_1\"").is_err());
    }

    #[test]
    fn hash_ids() {
        let d = DeviceId([7; 32]);
        assert_eq!(format!("{d:?}"), "dev:0707070707070707");
        assert_eq!(DeviceId::from_hex(&d.to_hex()), Some(d));
        let json = serde_json::to_string(&d).unwrap();
        assert_eq!(serde_json::from_str::<DeviceId>(&json).unwrap(), d);
    }
}
