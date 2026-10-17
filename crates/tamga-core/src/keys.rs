//! Gibrid kalitlar: Ed25519 (RFC 8032) + ML-DSA-65 (FIPS 204) — spec §7.2–7.3.

use ml_dsa::{EncodedSignature, EncodedVerifyingKey, MlDsa65, Seed};
use serde_json::{Value, json};

use crate::digest::{Digest, to_hex};
use crate::{AAR_VERSION, b64};

pub const KEY_DOMAIN: &[u8] = b"TAMGA-KEY-v1\0";
/// FIPS 204 kontekst satri: imzo boshqa maqsadda qayta ishlatilmasligi uchun.
pub const ML_DSA_CONTEXT: &[u8] = b"tamga-checkpoint";

pub const ED25519_PK_LEN: usize = 32;
pub const ED25519_SIG_LEN: usize = 64;
pub const ML_DSA_65_PK_LEN: usize = 1952;
pub const ML_DSA_65_SIG_LEN: usize = 3309;

/// Ikkala maxfiy kalit. 32 baytlik urug'lardan deterministik tiklanadi.
pub struct SigningKeys {
    ed: ed25519_dalek::SigningKey,
    ml: ml_dsa::SigningKey<MlDsa65>,
}

impl SigningKeys {
    /// `ed_seed` — RFC 8032 maxfiy kaliti, `ml_seed` — FIPS 204 ξ urug'i.
    pub fn from_seeds(ed_seed: &[u8; 32], ml_seed: &[u8; 32]) -> Self {
        let xi = Seed::from(*ml_seed);
        Self {
            ed: ed25519_dalek::SigningKey::from_bytes(ed_seed),
            ml: ml_dsa::SigningKey::<MlDsa65>::from_seed(&xi),
        }
    }

    pub fn public(&self) -> PublicKeys {
        PublicKeys {
            ed: self.ed.verifying_key(),
            ml: self.ml.expanded_key().verifying_key(),
        }
    }

    /// Ikkala imzo. ML-DSA deterministik variantda (`rnd` = 0) — test vektorlari takrorlanadigan
    /// bo'lishi uchun. Daemon (F2) hedged variantga o'tadi; tekshirish ikkalasi uchun bir xil.
    pub fn sign(&self, message: &[u8]) -> HybridSignature {
        use ed25519_dalek::Signer as _;
        let ed = self.ed.sign(message).to_bytes();
        let ml = self
            .ml
            .expanded_key()
            .sign_deterministic(message, ML_DSA_CONTEXT)
            .expect("kontekst 255 baytdan qisqa")
            .encode();
        HybridSignature {
            ed,
            ml: ml.to_vec(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HybridSignature {
    pub ed: [u8; ED25519_SIG_LEN],
    pub ml: Vec<u8>,
}

/// Ikkala ochiq kalit.
#[derive(Clone)]
pub struct PublicKeys {
    ed: ed25519_dalek::VerifyingKey,
    ml: ml_dsa::VerifyingKey<MlDsa65>,
}

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum KeyError {
    #[error("ochiq kalit fayli noto'g'ri: {0}")]
    Format(String),
    #[error("`key` identifikatori ochiq kalitlarga mos emas")]
    IdMismatch,
}

impl PublicKeys {
    pub fn from_bytes(ed: &[u8], ml: &[u8]) -> Result<Self, KeyError> {
        let ed: [u8; ED25519_PK_LEN] = ed
            .try_into()
            .map_err(|_| KeyError::Format("ed25519 kaliti 32 bayt emas".into()))?;
        let ed = ed25519_dalek::VerifyingKey::from_bytes(&ed)
            .map_err(|_| KeyError::Format("ed25519 kaliti egri chiziqda emas".into()))?;
        let ml = EncodedVerifyingKey::<MlDsa65>::try_from(ml)
            .map_err(|_| KeyError::Format("ml-dsa-65 kaliti 1952 bayt emas".into()))?;
        Ok(Self {
            ed,
            ml: ml_dsa::VerifyingKey::<MlDsa65>::decode(&ml),
        })
    }

    pub fn ed_bytes(&self) -> [u8; ED25519_PK_LEN] {
        self.ed.to_bytes()
    }

    pub fn ml_bytes(&self) -> Vec<u8> {
        self.ml.encode().to_vec()
    }

    /// `"k:" || hex(H("TAMGA-KEY-v1" || 0x00 || pk_ed || pk_ml))[..32]`
    pub fn key_id(&self) -> String {
        let d = Digest::of(&[KEY_DOMAIN, &self.ed_bytes(), &self.ml_bytes()]);
        format!("k:{}", &to_hex(&d.0)[..32])
    }

    pub fn to_json(&self) -> Value {
        json!({
            "aar": AAR_VERSION,
            "type": "public-key",
            "key": self.key_id(),
            "ed25519": b64::encode(&self.ed_bytes()),
            "ml-dsa-65": b64::encode(&self.ml_bytes()),
        })
    }

    /// Ochiq kalit faylini o'qiydi va `key` identifikatorini qayta hisoblab tekshiradi.
    pub fn from_json(v: &Value) -> Result<Self, KeyError> {
        let field = |k: &str| {
            v.get(k)
                .and_then(Value::as_str)
                .ok_or_else(|| KeyError::Format(format!("`{k}` yo'q")))
        };
        if field("aar")? != AAR_VERSION || field("type")? != "public-key" {
            return Err(KeyError::Format("aar/type noto'g'ri".into()));
        }
        let ed = b64::decode(field("ed25519")?)
            .ok_or_else(|| KeyError::Format("ed25519 base64url emas".into()))?;
        let ml = b64::decode(field("ml-dsa-65")?)
            .ok_or_else(|| KeyError::Format("ml-dsa-65 base64url emas".into()))?;
        let pk = Self::from_bytes(&ed, &ml)?;
        if pk.key_id() != field("key")? {
            return Err(KeyError::IdMismatch);
        }
        Ok(pk)
    }

    /// Gibrid AND: ikkala imzo ham haqiqiy bo'lishi shart. Ed25519 qat'iy rejimda
    /// (kanonik S, kichik tartibli kalitlar rad etiladi).
    pub fn verify(&self, message: &[u8], ed_sig: &[u8], ml_sig: &[u8]) -> bool {
        let ed_ok = <[u8; ED25519_SIG_LEN]>::try_from(ed_sig).is_ok_and(|s| {
            self.ed
                .verify_strict(message, &ed25519_dalek::Signature::from_bytes(&s))
                .is_ok()
        });
        let ml_ok = EncodedSignature::<MlDsa65>::try_from(ml_sig)
            .ok()
            .and_then(|enc| ml_dsa::Signature::<MlDsa65>::decode(&enc))
            .is_some_and(|s| self.ml.verify_with_context(message, ML_DSA_CONTEXT, &s));
        ed_ok && ml_ok
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn keys() -> SigningKeys {
        SigningKeys::from_seeds(&[7; 32], &[9; 32])
    }

    #[test]
    fn sizes_and_round_trip() {
        let k = keys();
        let pk = k.public();
        assert_eq!(pk.ml_bytes().len(), ML_DSA_65_PK_LEN);
        let sig = k.sign(b"salom");
        assert_eq!(sig.ml.len(), ML_DSA_65_SIG_LEN);
        assert!(pk.verify(b"salom", &sig.ed, &sig.ml));
        assert_eq!(k.sign(b"salom"), sig, "deterministik");

        let back = PublicKeys::from_json(&pk.to_json()).unwrap();
        assert_eq!(back.key_id(), pk.key_id());
        assert!(pk.key_id().starts_with("k:") && pk.key_id().len() == 34);
    }

    #[test]
    fn ed25519_rfc8032_test_1() {
        use ed25519_dalek::Signer as _;
        let hex = |s: &str| -> Vec<u8> {
            (0..s.len())
                .step_by(2)
                .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
                .collect()
        };
        let sk: [u8; 32] = hex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
            .try_into()
            .unwrap();
        let k = ed25519_dalek::SigningKey::from_bytes(&sk);
        assert_eq!(
            k.verifying_key().to_bytes().to_vec(),
            hex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        );
        assert_eq!(
            k.sign(b"").to_bytes().to_vec(),
            hex(
                "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
            )
        );
    }

    #[test]
    fn hybrid_and_requires_both() {
        let k = keys();
        let pk = k.public();
        let sig = k.sign(b"m");
        let mut bad_ed = sig.ed;
        bad_ed[0] ^= 1;
        let mut bad_ml = sig.ml.clone();
        bad_ml[100] ^= 1;
        assert!(
            !pk.verify(b"m", &bad_ed, &sig.ml),
            "faqat ML-DSA yetarli emas"
        );
        assert!(
            !pk.verify(b"m", &sig.ed, &bad_ml),
            "faqat Ed25519 yetarli emas"
        );
        assert!(!pk.verify(b"M", &sig.ed, &sig.ml));
        assert!(!pk.verify(b"m", &sig.ed[..63], &sig.ml));
        assert!(!pk.verify(b"m", &sig.ed, &sig.ml[..3308]));
    }

    #[test]
    fn ml_dsa_context_is_bound() {
        let k = keys();
        let sig =
            k.ml.expanded_key()
                .sign_deterministic(b"m", b"boshqa-kontekst")
                .unwrap()
                .encode();
        let ed = k.sign(b"m").ed;
        assert!(
            !k.public().verify(b"m", &ed, &sig),
            "boshqa kontekstdagi imzo o'tmaydi"
        );
    }

    #[test]
    fn key_file_tamper_is_detected() {
        let pk = keys().public();
        let mut v = pk.to_json();
        v["key"] = "k:00000000000000000000000000000000".into();
        assert_eq!(PublicKeys::from_json(&v).err(), Some(KeyError::IdMismatch));
        let other = SigningKeys::from_seeds(&[1; 32], &[9; 32]).public();
        let mut v = pk.to_json();
        v["ed25519"] = b64::encode(&other.ed_bytes()).into();
        assert_eq!(PublicKeys::from_json(&v).err(), Some(KeyError::IdMismatch));
    }
}
