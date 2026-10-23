//! Xotiradagi KeyStore — **faqat sandbox va testlar uchun**.
//!
//! Ikki rejim:
//! * [`MemoryKeyStore::random`] — har kalit OS CSPRNG'dan (jarayon tugagach yo'qoladi);
//! * [`MemoryKeyStore::from_seed`] — kalitlar dev-urug'dan deterministik hosil qilinadi:
//!   `HKDF-SHA256(salt = "mpay-memory-keystore-v1", ikm = seed, info = tur ‖ 0x00 ‖ yorliq)`.
//!   Shu tufayli server qayta ishga tushganda DB'dagi shifrlangan ma'lumot o'qiladi.

use std::collections::HashMap;
use std::sync::RwLock;

use hkdf::Hkdf;
use sha2::Sha256;
use zeroize::Zeroizing;

use super::{soft, wrong_kind, GcmSealed, KeyKind, KeyLabel, KeyStore, HMAC_MAX_KEY, HMAC_MIN_KEY};
use crate::{rng, CryptoError};

struct Entry {
    kind: KeyKind,
    material: Zeroizing<Vec<u8>>,
}

/// Xotiradagi KeyStore.
pub struct MemoryKeyStore {
    seed: Option<Zeroizing<[u8; 32]>>,
    keys: RwLock<HashMap<KeyLabel, Entry>>,
}

impl std::fmt::Debug for MemoryKeyStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let n = self.keys.read().map(|k| k.len()).unwrap_or(0);
        f.debug_struct("MemoryKeyStore")
            .field("deterministic", &self.seed.is_some())
            .field("keys", &n)
            .finish()
    }
}

impl MemoryKeyStore {
    /// Tasodifiy kalitlar bilan.
    pub fn random() -> Self {
        Self {
            seed: None,
            keys: RwLock::new(HashMap::new()),
        }
    }

    /// Dev-urug'dan deterministik kalitlar bilan.
    pub fn from_seed(seed: [u8; 32]) -> Self {
        Self {
            seed: Some(Zeroizing::new(seed)),
            keys: RwLock::new(HashMap::new()),
        }
    }

    fn new_material(
        &self,
        label: &KeyLabel,
        kind: KeyKind,
    ) -> Result<Zeroizing<Vec<u8>>, CryptoError> {
        let mut out = Zeroizing::new(vec![0u8; kind.material_len()]);
        match &self.seed {
            Some(seed) => {
                let hk = Hkdf::<Sha256>::new(Some(b"mpay-memory-keystore-v1"), &seed[..]);
                let mut info = Vec::with_capacity(32);
                info.extend_from_slice(kind.name().as_bytes());
                info.push(0);
                info.extend_from_slice(label.as_str().as_bytes());
                hk.expand(&info, &mut out)
                    .map_err(|_| CryptoError::BadInput("HKDF uzunligi"))?;
            }
            None => rng::fill(&mut out)?,
        }
        Ok(out)
    }

    fn with_key<T>(
        &self,
        label: &KeyLabel,
        kind: KeyKind,
        f: impl FnOnce(&[u8]) -> Result<T, CryptoError>,
    ) -> Result<T, CryptoError> {
        let keys = self
            .keys
            .read()
            .map_err(|_| CryptoError::Backend("lock".into()))?;
        let e = keys
            .get(label)
            .ok_or_else(|| CryptoError::KeyNotFound(label.to_string()))?;
        if e.kind != kind {
            return Err(wrong_kind(label, kind, e.kind));
        }
        f(&e.material)
    }
}

fn fixed<const N: usize>(b: &[u8]) -> Result<Zeroizing<[u8; N]>, CryptoError> {
    let mut a = Zeroizing::new([0u8; N]);
    if b.len() != N {
        return Err(CryptoError::BadInput("kalit uzunligi"));
    }
    a.copy_from_slice(b);
    Ok(a)
}

impl KeyStore for MemoryKeyStore {
    fn backend_name(&self) -> &'static str {
        "memory"
    }

    fn ensure_key(&self, label: &KeyLabel, kind: KeyKind) -> Result<(), CryptoError> {
        if let Some(existing) = self.key_kind(label)? {
            return if existing == kind {
                Ok(())
            } else {
                Err(wrong_kind(label, kind, existing))
            };
        }
        let material = self.new_material(label, kind)?;
        let mut keys = self
            .keys
            .write()
            .map_err(|_| CryptoError::Backend("lock".into()))?;
        keys.entry(label.clone())
            .or_insert(Entry { kind, material });
        Ok(())
    }

    fn key_kind(&self, label: &KeyLabel) -> Result<Option<KeyKind>, CryptoError> {
        let keys = self
            .keys
            .read()
            .map_err(|_| CryptoError::Backend("lock".into()))?;
        Ok(keys.get(label).map(|e| e.kind))
    }

    fn import_secret(
        &self,
        label: &KeyLabel,
        kind: KeyKind,
        material: &[u8],
    ) -> Result<(), CryptoError> {
        let ok_len = match kind {
            KeyKind::HmacSha256 => (HMAC_MIN_KEY..=HMAC_MAX_KEY).contains(&material.len()),
            _ => material.len() == kind.material_len(),
        };
        if !ok_len {
            return Err(CryptoError::BadInput("kalit uzunligi"));
        }
        let mut keys = self
            .keys
            .write()
            .map_err(|_| CryptoError::Backend("lock".into()))?;
        if keys.contains_key(label) {
            return Err(CryptoError::KeyExists(label.to_string()));
        }
        keys.insert(
            label.clone(),
            Entry {
                kind,
                material: Zeroizing::new(material.to_vec()),
            },
        );
        Ok(())
    }

    fn aes_cmac(&self, label: &KeyLabel, data: &[u8]) -> Result<[u8; 16], CryptoError> {
        self.with_key(label, KeyKind::Aes128, |k| {
            Ok(soft::cmac_aes128(&*fixed::<16>(k)?, data))
        })
    }

    fn aes_gcm_seal(
        &self,
        label: &KeyLabel,
        aad: &[u8],
        plaintext: &[u8],
    ) -> Result<GcmSealed, CryptoError> {
        let nonce = rng::array::<12>()?;
        self.with_key(label, KeyKind::Aes256, |k| {
            Ok(GcmSealed {
                nonce,
                ciphertext: soft::gcm_seal(&*fixed::<32>(k)?, &nonce, aad, plaintext)?,
            })
        })
    }

    fn aes_gcm_open(
        &self,
        label: &KeyLabel,
        nonce: &[u8; 12],
        aad: &[u8],
        ciphertext: &[u8],
    ) -> Result<Zeroizing<Vec<u8>>, CryptoError> {
        self.with_key(label, KeyKind::Aes256, |k| {
            soft::gcm_open(&*fixed::<32>(k)?, nonce, aad, ciphertext)
        })
    }

    fn hmac_sha256(&self, label: &KeyLabel, data: &[u8]) -> Result<[u8; 32], CryptoError> {
        self.with_key(label, KeyKind::HmacSha256, |k| soft::hmac_sha256(k, data))
    }

    fn ed25519_sign(&self, label: &KeyLabel, msg: &[u8]) -> Result<[u8; 64], CryptoError> {
        self.with_key(label, KeyKind::Ed25519, |k| {
            Ok(soft::ed25519_sign(&*fixed::<32>(k)?, msg))
        })
    }

    fn ed25519_public_key(&self, label: &KeyLabel) -> Result<[u8; 32], CryptoError> {
        self.with_key(label, KeyKind::Ed25519, |k| {
            Ok(soft::ed25519_public(&*fixed::<32>(k)?))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seeded_store_is_deterministic() {
        let a = MemoryKeyStore::from_seed([1; 32]);
        let b = MemoryKeyStore::from_seed([1; 32]);
        let c = MemoryKeyStore::from_seed([2; 32]);
        let l = KeyLabel::new(KeyLabel::IMK_AC);
        for s in [&a, &b, &c] {
            s.ensure_key(&l, KeyKind::Aes128).unwrap();
        }
        let m = |s: &MemoryKeyStore| s.aes_cmac(&l, b"x").unwrap();
        assert_eq!(m(&a), m(&b));
        assert_ne!(m(&a), m(&c));
    }

    #[test]
    fn kind_mismatch_rejected() {
        let s = MemoryKeyStore::random();
        let l = KeyLabel::new("k");
        s.ensure_key(&l, KeyKind::Aes256).unwrap();
        assert!(matches!(
            s.aes_cmac(&l, b""),
            Err(CryptoError::WrongKeyKind { .. })
        ));
        assert!(matches!(
            s.ensure_key(&l, KeyKind::Aes128),
            Err(CryptoError::WrongKeyKind { .. })
        ));
        assert!(matches!(
            s.import_secret(&l, KeyKind::Aes256, &[0; 32]),
            Err(CryptoError::KeyExists(_))
        ));
        assert!(matches!(
            s.hmac_sha256(&KeyLabel::new("none"), b""),
            Err(CryptoError::KeyNotFound(_))
        ));
    }

    #[test]
    fn gcm_roundtrip_and_tamper() {
        let s = MemoryKeyStore::random();
        let l = KeyLabel::new(KeyLabel::KEK);
        s.ensure_key(&l, KeyKind::Aes256).unwrap();
        let sealed = s.aes_gcm_seal(&l, b"aad", b"secret").unwrap();
        assert_eq!(
            &s.aes_gcm_open(&l, &sealed.nonce, b"aad", &sealed.ciphertext)
                .unwrap()[..],
            b"secret"
        );
        assert_eq!(
            s.aes_gcm_open(&l, &sealed.nonce, b"aaX", &sealed.ciphertext),
            Err(CryptoError::Decrypt)
        );
        let mut bad = sealed.ciphertext.clone();
        bad[0] ^= 1;
        assert_eq!(
            s.aes_gcm_open(&l, &sealed.nonce, b"aad", &bad),
            Err(CryptoError::Decrypt)
        );
        // Har shifrlashda yangi nonce.
        assert_ne!(s.aes_gcm_seal(&l, b"", b"x").unwrap().nonce, sealed.nonce);
    }

    #[test]
    fn debug_hides_material() {
        let s = MemoryKeyStore::from_seed([9; 32]);
        s.ensure_key(&KeyLabel::new("a"), KeyKind::Aes128).unwrap();
        assert_eq!(
            format!("{s:?}"),
            "MemoryKeyStore { deterministic: true, keys: 1 }"
        );
    }
}
