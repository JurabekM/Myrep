//! PKCS#11 KeyStore (`pkcs11` feature) — SoftHSM2 va haqiqiy HSM'lar uchun.
//!
//! `cryptoki` xavfsiz o'rami ishlatiladi: bu crate'da `unsafe` yo'q.
//! Kalitlar yorliq (`CKA_LABEL`) bo'yicha topiladi va
//! `CKA_TOKEN=true, CKA_SENSITIVE=true, CKA_EXTRACTABLE=false` bilan yaratiladi.
//!
//! Mexanizmlar: `CKM_AES_KEY_GEN`, `CKM_AES_CMAC`, `CKM_AES_GCM`, `CKM_GENERIC_SECRET_KEY_GEN`,
//! `CKM_SHA256_HMAC`, `CKM_EC_EDWARDS_KEY_PAIR_GEN`, `CKM_EDDSA`.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Mutex, OnceLock};

use cryptoki::context::{CInitializeArgs, CInitializeFlags, Pkcs11};
use cryptoki::error::RvError;
use cryptoki::mechanism::aead::GcmParams;
use cryptoki::mechanism::eddsa::{EddsaParams, EddsaSignatureScheme};
use cryptoki::mechanism::Mechanism;
use cryptoki::object::{Attribute, AttributeType, KeyType, ObjectClass, ObjectHandle};
use cryptoki::session::{Session, UserType};
use cryptoki::types::AuthPin;
use zeroize::Zeroizing;

use super::{wrong_kind, GcmSealed, KeyKind, KeyLabel, KeyStore, HMAC_MAX_KEY, HMAC_MIN_KEY};
use crate::{rng, CryptoError};

/// Ed25519 egri chizig'i OID'i (1.3.101.112) DER ko'rinishida — `CKA_EC_PARAMS`.
const ED25519_OID_DER: [u8; 5] = [0x06, 0x03, 0x2B, 0x65, 0x70];

/// PKCS#11 ulanish sozlamalari.
pub struct Pkcs11Config {
    /// Modul yo'li (masalan `/usr/lib/softhsm/libsofthsm2.so`).
    pub module: PathBuf,
    /// Token yorlig'i (`softhsm2-util --init-token --label ...`).
    pub token_label: String,
    /// Foydalanuvchi PIN'i (muhit o'zgaruvchisidan; repoga tushmaydi).
    pub user_pin: Zeroizing<String>,
}

impl std::fmt::Debug for Pkcs11Config {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Pkcs11Config")
            .field("module", &self.module)
            .field("token_label", &self.token_label)
            .field("user_pin", &"<maxfiy>")
            .finish()
    }
}

impl Pkcs11Config {
    /// `MPAY_PKCS11_LIB`, `MPAY_PKCS11_TOKEN_LABEL`, `MPAY_PKCS11_PIN` muhit o'zgaruvchilaridan.
    pub fn from_env() -> Result<Self, CryptoError> {
        let get = |k: &str| {
            std::env::var(k).map_err(|_| CryptoError::Backend(format!("{k} o'rnatilmagan")))
        };
        Ok(Self {
            module: PathBuf::from(get("MPAY_PKCS11_LIB")?),
            token_label: get("MPAY_PKCS11_TOKEN_LABEL")?,
            user_pin: Zeroizing::new(get("MPAY_PKCS11_PIN")?),
        })
    }
}

/// PKCS#11 KeyStore. Bitta R/W sessiya `Mutex` ostida (cryptoki `Session` — `Send`, `!Sync`).
pub struct Pkcs11KeyStore {
    session: Mutex<Session>,
    token_label: String,
    // Sessiyadan keyin yopilishi uchun oxirgi maydon.
    _ctx: Pkcs11,
}

impl std::fmt::Debug for Pkcs11KeyStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Pkcs11KeyStore")
            .field("token", &self.token_label)
            .finish()
    }
}

fn be<E: std::fmt::Display>(what: &'static str) -> impl FnOnce(E) -> CryptoError {
    move |e| CryptoError::Backend(format!("{what}: {e}"))
}

impl Pkcs11KeyStore {
    /// Modulni yuklaydi, token'ni topadi va foydalanuvchi sifatida kiradi.
    pub fn open(cfg: &Pkcs11Config) -> Result<Self, CryptoError> {
        let ctx = shared_context(&cfg.module)?;
        let slot = ctx
            .get_slots_with_initialized_token()
            .map_err(be("slotlar"))?
            .into_iter()
            .find(|s| {
                ctx.get_token_info(*s)
                    .map(|i| i.label().trim_end() == cfg.token_label)
                    .unwrap_or(false)
            })
            .ok_or_else(|| CryptoError::Backend(format!("token topilmadi: {}", cfg.token_label)))?;
        let session = ctx.open_rw_session(slot).map_err(be("C_OpenSession"))?;
        let pin = AuthPin::from(cfg.user_pin.as_str().to_owned());
        // Login holati butun ilova uchun umumiy: ikkinchi sessiya uchun "allaqachon kirgan" — normal.
        match session.login(UserType::User, Some(&pin)) {
            Ok(()) | Err(cryptoki::error::Error::Pkcs11(RvError::UserAlreadyLoggedIn, _)) => {}
            Err(e) => return Err(be("C_Login")(e)),
        }
        Ok(Self {
            session: Mutex::new(session),
            token_label: cfg.token_label.clone(),
            _ctx: ctx,
        })
    }

    fn with_session<T>(
        &self,
        f: impl FnOnce(&Session) -> Result<T, CryptoError>,
    ) -> Result<T, CryptoError> {
        let s = self
            .session
            .lock()
            .map_err(|_| CryptoError::Backend("lock".into()))?;
        f(&s)
    }

    /// Yorliq bo'yicha obyekt (sinfi bilan).
    fn find(
        s: &Session,
        label: &KeyLabel,
        class: ObjectClass,
    ) -> Result<Option<ObjectHandle>, CryptoError> {
        let found = s
            .find_objects(&[
                Attribute::Class(class),
                Attribute::Label(label.as_str().as_bytes().to_vec()),
            ])
            .map_err(be("C_FindObjects"))?;
        match found.as_slice() {
            [] => Ok(None),
            [h] => Ok(Some(*h)),
            _ => Err(CryptoError::Backend(format!(
                "yorliq takrorlangan: {label}"
            ))),
        }
    }

    fn kind_of(s: &Session, label: &KeyLabel) -> Result<Option<KeyKind>, CryptoError> {
        if Self::find(s, label, ObjectClass::PRIVATE_KEY)?.is_some() {
            return Ok(Some(KeyKind::Ed25519));
        }
        let Some(h) = Self::find(s, label, ObjectClass::SECRET_KEY)? else {
            return Ok(None);
        };
        let attrs = s
            .get_attributes(h, &[AttributeType::KeyType, AttributeType::ValueLen])
            .map_err(be("C_GetAttributeValue"))?;
        let mut kt = None;
        let mut len = 0u64;
        for a in attrs {
            match a {
                Attribute::KeyType(k) => kt = Some(k),
                Attribute::ValueLen(l) => len = usize::from(l) as u64,
                _ => {}
            }
        }
        Ok(match (kt, len) {
            (Some(k), 16) if k == KeyType::AES => Some(KeyKind::Aes128),
            (Some(k), 32) if k == KeyType::AES => Some(KeyKind::Aes256),
            (Some(k), _) if k == KeyType::GENERIC_SECRET => Some(KeyKind::HmacSha256),
            _ => {
                return Err(CryptoError::Backend(format!(
                    "qo'llab-quvvatlanmaydigan kalit: {label}"
                )))
            }
        })
    }

    fn require(s: &Session, label: &KeyLabel, kind: KeyKind) -> Result<ObjectHandle, CryptoError> {
        let actual =
            Self::kind_of(s, label)?.ok_or_else(|| CryptoError::KeyNotFound(label.to_string()))?;
        if actual != kind {
            return Err(wrong_kind(label, kind, actual));
        }
        let class = if kind == KeyKind::Ed25519 {
            ObjectClass::PRIVATE_KEY
        } else {
            ObjectClass::SECRET_KEY
        };
        Self::find(s, label, class)?.ok_or_else(|| CryptoError::KeyNotFound(label.to_string()))
    }

    fn secret_template(label: &KeyLabel, kind: KeyKind) -> Vec<Attribute> {
        let mut t = vec![
            Attribute::Token(true),
            Attribute::Private(true),
            Attribute::Sensitive(true),
            Attribute::Extractable(false),
            Attribute::Label(label.as_str().as_bytes().to_vec()),
            Attribute::Sign(true),
            Attribute::Verify(true),
        ];
        if matches!(kind, KeyKind::Aes256) {
            t.push(Attribute::Encrypt(true));
            t.push(Attribute::Decrypt(true));
        }
        t
    }

    fn ed_templates(label: &KeyLabel) -> (Vec<Attribute>, Vec<Attribute>) {
        let l = label.as_str().as_bytes().to_vec();
        let public = vec![
            Attribute::Token(true),
            Attribute::Private(false),
            Attribute::Label(l.clone()),
            Attribute::EcParams(ED25519_OID_DER.to_vec()),
            Attribute::Verify(true),
        ];
        let private = vec![
            Attribute::Token(true),
            Attribute::Private(true),
            Attribute::Sensitive(true),
            Attribute::Extractable(false),
            Attribute::Label(l),
            Attribute::Sign(true),
        ];
        (public, private)
    }
}

/// Jarayon bo'yicha yagona PKCS#11 konteksti (modul yo'li bo'yicha). `C_Initialize` faqat
/// bir marta chaqiriladi; bir nechta `Pkcs11KeyStore` (masalan parallel testlar) uni bo'lishadi.
fn shared_context(module: &std::path::Path) -> Result<Pkcs11, CryptoError> {
    static CONTEXTS: OnceLock<Mutex<HashMap<PathBuf, Pkcs11>>> = OnceLock::new();
    let mut map = CONTEXTS
        .get_or_init(Default::default)
        .lock()
        .map_err(|_| CryptoError::Backend("lock".into()))?;
    if let Some(ctx) = map.get(module) {
        return Ok(ctx.clone());
    }
    let ctx = Pkcs11::new(module).map_err(be("modulni yuklash"))?;
    ctx.initialize(CInitializeArgs::new(CInitializeFlags::OS_LOCKING_OK))
        .map_err(be("C_Initialize"))?;
    map.insert(module.to_path_buf(), ctx.clone());
    Ok(ctx)
}

fn ulong(v: usize) -> Result<cryptoki::types::Ulong, CryptoError> {
    cryptoki::types::Ulong::try_from(v).map_err(be("CK_ULONG"))
}

/// `CKA_EC_POINT` qiymatidan 32 baytli Ed25519 ochiq kaliti (DER OCTET STRING yoki xom).
fn ed_point(raw: &[u8]) -> Result<[u8; 32], CryptoError> {
    let b = match raw {
        [0x04, 0x20, rest @ ..] if rest.len() == 32 => rest,
        r if r.len() == 32 => r,
        _ => return Err(CryptoError::Backend("CKA_EC_POINT formati".into())),
    };
    let mut out = [0u8; 32];
    out.copy_from_slice(b);
    Ok(out)
}

impl KeyStore for Pkcs11KeyStore {
    fn backend_name(&self) -> &'static str {
        "pkcs11"
    }

    fn ensure_key(&self, label: &KeyLabel, kind: KeyKind) -> Result<(), CryptoError> {
        self.with_session(|s| {
            if let Some(actual) = Self::kind_of(s, label)? {
                return if actual == kind {
                    Ok(())
                } else {
                    Err(wrong_kind(label, kind, actual))
                };
            }
            match kind {
                KeyKind::Aes128 | KeyKind::Aes256 => {
                    let mut t = Self::secret_template(label, kind);
                    t.push(Attribute::ValueLen(ulong(kind.material_len())?));
                    s.generate_key(&Mechanism::AesKeyGen, &t)
                        .map_err(be("AES keygen"))?;
                }
                KeyKind::HmacSha256 => {
                    let mut t = Self::secret_template(label, kind);
                    t.push(Attribute::ValueLen(ulong(32)?));
                    s.generate_key(&Mechanism::GenericSecretKeyGen, &t)
                        .map_err(be("generic secret keygen"))?;
                }
                KeyKind::Ed25519 => {
                    let (public, private) = Self::ed_templates(label);
                    s.generate_key_pair(&Mechanism::EccEdwardsKeyPairGen, &public, &private)
                        .map_err(be("Ed25519 keygen"))?;
                }
            }
            tracing::info!(label = %label, kind = kind.name(), "pkcs11: yangi kalit yaratildi");
            Ok(())
        })
    }

    fn key_kind(&self, label: &KeyLabel) -> Result<Option<KeyKind>, CryptoError> {
        self.with_session(|s| Self::kind_of(s, label))
    }

    fn import_secret(
        &self,
        label: &KeyLabel,
        kind: KeyKind,
        material: &[u8],
    ) -> Result<(), CryptoError> {
        self.with_session(|s| {
            if Self::kind_of(s, label)?.is_some() {
                return Err(CryptoError::KeyExists(label.to_string()));
            }
            match kind {
                KeyKind::Aes128 | KeyKind::Aes256 | KeyKind::HmacSha256 => {
                    let ok = match kind {
                        KeyKind::HmacSha256 => {
                            (HMAC_MIN_KEY..=HMAC_MAX_KEY).contains(&material.len())
                        }
                        _ => material.len() == kind.material_len(),
                    };
                    if !ok {
                        return Err(CryptoError::BadInput("kalit uzunligi"));
                    }
                    let kt = if kind == KeyKind::HmacSha256 {
                        KeyType::GENERIC_SECRET
                    } else {
                        KeyType::AES
                    };
                    let mut t = Self::secret_template(label, kind);
                    t.push(Attribute::Class(ObjectClass::SECRET_KEY));
                    t.push(Attribute::KeyType(kt));
                    t.push(Attribute::Value(material.to_vec()));
                    s.create_object(&t).map_err(be("C_CreateObject"))?;
                }
                KeyKind::Ed25519 => {
                    let seed: [u8; 32] = material
                        .try_into()
                        .map_err(|_| CryptoError::BadInput("kalit uzunligi"))?;
                    let pk = super::soft::ed25519_public(&seed);
                    let (mut public, mut private) = Self::ed_templates(label);
                    public.push(Attribute::Class(ObjectClass::PUBLIC_KEY));
                    public.push(Attribute::KeyType(KeyType::EC_EDWARDS));
                    public.push(Attribute::EcPoint([&[0x04, 0x20][..], &pk].concat()));
                    private.push(Attribute::Class(ObjectClass::PRIVATE_KEY));
                    private.push(Attribute::KeyType(KeyType::EC_EDWARDS));
                    private.push(Attribute::EcParams(ED25519_OID_DER.to_vec()));
                    private.push(Attribute::Value(seed.to_vec()));
                    s.create_object(&public).map_err(be("C_CreateObject pub"))?;
                    s.create_object(&private)
                        .map_err(be("C_CreateObject priv"))?;
                }
            }
            Ok(())
        })
    }

    fn aes_cmac(&self, label: &KeyLabel, data: &[u8]) -> Result<[u8; 16], CryptoError> {
        self.with_session(|s| {
            let h = Self::require(s, label, KeyKind::Aes128)?;
            let mac = s.sign(&Mechanism::AesCMac, h, data).map_err(be("CMAC"))?;
            mac.as_slice()
                .try_into()
                .map_err(|_| CryptoError::Backend("CMAC uzunligi".into()))
        })
    }

    fn aes_gcm_seal(
        &self,
        label: &KeyLabel,
        aad: &[u8],
        plaintext: &[u8],
    ) -> Result<GcmSealed, CryptoError> {
        let nonce = rng::array::<12>()?;
        self.with_session(|s| {
            let h = Self::require(s, label, KeyKind::Aes256)?;
            let mut iv = nonce;
            let params = GcmParams::new(&mut iv, aad, ulong(128)?).map_err(be("GCM params"))?;
            let ct = s
                .encrypt(&Mechanism::AesGcm(params), h, plaintext)
                .map_err(be("GCM encrypt"))?;
            Ok(GcmSealed {
                nonce,
                ciphertext: ct,
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
        self.with_session(|s| {
            let h = Self::require(s, label, KeyKind::Aes256)?;
            let mut iv = *nonce;
            let params = GcmParams::new(&mut iv, aad, ulong(128)?).map_err(be("GCM params"))?;
            s.decrypt(&Mechanism::AesGcm(params), h, ciphertext)
                .map(Zeroizing::new)
                .map_err(|_| CryptoError::Decrypt)
        })
    }

    fn hmac_sha256(&self, label: &KeyLabel, data: &[u8]) -> Result<[u8; 32], CryptoError> {
        self.with_session(|s| {
            let h = Self::require(s, label, KeyKind::HmacSha256)?;
            let mac = s
                .sign(&Mechanism::Sha256Hmac, h, data)
                .map_err(be("HMAC"))?;
            mac.as_slice()
                .try_into()
                .map_err(|_| CryptoError::Backend("HMAC uzunligi".into()))
        })
    }

    fn ed25519_sign(&self, label: &KeyLabel, msg: &[u8]) -> Result<[u8; 64], CryptoError> {
        self.with_session(|s| {
            let h = Self::require(s, label, KeyKind::Ed25519)?;
            let mech = Mechanism::Eddsa(EddsaParams::new(EddsaSignatureScheme::Pure));
            let sig = s.sign(&mech, h, msg).map_err(be("EdDSA"))?;
            sig.as_slice()
                .try_into()
                .map_err(|_| CryptoError::Backend("EdDSA uzunligi".into()))
        })
    }

    fn ed25519_public_key(&self, label: &KeyLabel) -> Result<[u8; 32], CryptoError> {
        self.with_session(|s| {
            let h = Self::find(s, label, ObjectClass::PUBLIC_KEY)?
                .ok_or_else(|| CryptoError::KeyNotFound(label.to_string()))?;
            let attrs = s
                .get_attributes(h, &[AttributeType::EcPoint])
                .map_err(be("CKA_EC_POINT"))?;
            for a in attrs {
                if let Attribute::EcPoint(p) = a {
                    return ed_point(&p);
                }
            }
            Err(CryptoError::Backend("CKA_EC_POINT yo'q".into()))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ec_point_formats() {
        let pk = [7u8; 32];
        assert_eq!(ed_point(&[&[0x04, 0x20][..], &pk].concat()).unwrap(), pk);
        assert_eq!(ed_point(&pk).unwrap(), pk);
        assert!(ed_point(&[0x04, 0x21, 1]).is_err());
    }

    #[test]
    fn config_debug_hides_pin() {
        let c = Pkcs11Config {
            module: "x".into(),
            token_label: "t".into(),
            user_pin: Zeroizing::new("1234".into()),
        };
        assert!(!format!("{c:?}").contains("1234"));
    }
}
