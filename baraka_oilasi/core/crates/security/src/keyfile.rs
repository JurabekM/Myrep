use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use hkdf::Hkdf;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::secrets::random_bytes;
use crate::{
    BioKek, DbKey, LockoutState, Pin, PlatformSecret, RecoveryCode, SecurityError, SECRET_LEN,
};

pub const KEYFILE_VERSION: u32 = 1;
const SALT_LEN: usize = 16;
const NONCE_LEN: usize = 24;

/// Argon2id parametrlari `keys.bin` ichida saqlanadi va qurilmada kalibrlanadi.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KdfParams {
    pub m_kib: u32,
    pub t_cost: u32,
    pub p_cost: u32,
}

impl KdfParams {
    /// Arzon Android telefonlar uchun boshlang'ich qiymat (OWASP minimumi).
    pub const ANDROID: Self = Self {
        m_kib: 19_456,
        t_cost: 2,
        p_cost: 1,
    };
    pub const DESKTOP: Self = Self {
        m_kib: 65_536,
        t_cost: 3,
        p_cost: 1,
    };
    /// Faqat testlar uchun — production'da ishlatilmaydi.
    pub const INSECURE_FAST_FOR_TESTS: Self = Self {
        m_kib: 64,
        t_cost: 1,
        p_cost: 1,
    };
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SlotKind {
    Pin,
    Recovery,
    Bio,
}

impl SlotKind {
    const fn info(self) -> &'static [u8] {
        match self {
            Self::Pin => b"baraka/kek/pin/v1",
            Self::Recovery => b"baraka/kek/recovery/v1",
            Self::Bio => b"baraka/kek/bio/v1",
        }
    }

    const fn aad(self) -> &'static [u8] {
        match self {
            Self::Pin => b"baraka/slot/v1/PIN",
            Self::Recovery => b"baraka/slot/v1/RECOVERY",
            Self::Bio => b"baraka/slot/v1/BIO",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Slot {
    kind: SlotKind,
    salt: String,
    nonce: String,
    wrapped: String,
}

/// `keys.bin`: versiya, KDF parametrlari, slotlar va qulflash holati. Sir saqlamaydi —
/// faqat wrap qilingan kalitlar; shuning uchun JSON ko'rinishida.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KeyFile {
    version: u32,
    kdf: KdfParams,
    slots: Vec<Slot>,
    lockout: LockoutState,
}

fn argon2id(
    secret: &[u8],
    salt: &[u8],
    p: KdfParams,
) -> Result<Zeroizing<[u8; SECRET_LEN]>, SecurityError> {
    let params = Params::new(p.m_kib, p.t_cost, p.p_cost, Some(SECRET_LEN))
        .map_err(|_| SecurityError::Crypto)?;
    let mut out = Zeroizing::new([0u8; SECRET_LEN]);
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
        .hash_password_into(secret, salt, &mut out[..])
        .map_err(|_| SecurityError::Crypto)?;
    Ok(out)
}

fn hkdf_kek(
    kind: SlotKind,
    ikm_parts: &[&[u8]],
) -> Result<Zeroizing<[u8; SECRET_LEN]>, SecurityError> {
    let mut ikm = Zeroizing::new(Vec::with_capacity(SECRET_LEN * 2));
    for p in ikm_parts {
        ikm.extend_from_slice(p);
    }
    let mut kek = Zeroizing::new([0u8; SECRET_LEN]);
    Hkdf::<Sha256>::new(None, &ikm)
        .expand(kind.info(), &mut kek[..])
        .map_err(|_| SecurityError::Crypto)?;
    Ok(kek)
}

fn knowledge_kek(
    kind: SlotKind,
    platform: &PlatformSecret,
    secret: &[u8],
    salt: &[u8],
    p: KdfParams,
) -> Result<Zeroizing<[u8; SECRET_LEN]>, SecurityError> {
    let stretched = argon2id(secret, salt, p)?;
    hkdf_kek(kind, &[platform.as_bytes(), &stretched[..]])
}

fn seal(
    kind: SlotKind,
    kek: &[u8; SECRET_LEN],
    salt: [u8; SALT_LEN],
    db: &DbKey,
) -> Result<Slot, SecurityError> {
    let nonce = random_bytes::<NONCE_LEN>()?;
    let cipher = XChaCha20Poly1305::new_from_slice(kek).map_err(|_| SecurityError::Crypto)?;
    let wrapped = cipher
        .encrypt(
            &XNonce::from(nonce),
            Payload {
                msg: db.as_bytes(),
                aad: kind.aad(),
            },
        )
        .map_err(|_| SecurityError::Crypto)?;
    Ok(Slot {
        kind,
        salt: hex::encode(salt),
        nonce: hex::encode(nonce),
        wrapped: hex::encode(wrapped),
    })
}

fn open(slot: &Slot, kek: &[u8; SECRET_LEN]) -> Result<DbKey, SecurityError> {
    let nonce: [u8; NONCE_LEN] = hex::decode(&slot.nonce)
        .ok()
        .and_then(|v| v.try_into().ok())
        .ok_or(SecurityError::KeyFileCorrupt)?;
    let wrapped = hex::decode(&slot.wrapped).map_err(|_| SecurityError::KeyFileCorrupt)?;
    let cipher = XChaCha20Poly1305::new_from_slice(kek).map_err(|_| SecurityError::Crypto)?;
    let plain = Zeroizing::new(
        cipher
            .decrypt(
                &XNonce::from(nonce),
                Payload {
                    msg: &wrapped,
                    aad: slot.kind.aad(),
                },
            )
            .map_err(|_| SecurityError::WrongSecret)?,
    );
    DbKey::from_slice(&plain)
}

fn salt_of(slot: &Slot) -> Result<Vec<u8>, SecurityError> {
    hex::decode(&slot.salt).map_err(|_| SecurityError::KeyFileCorrupt)
}

impl KeyFile {
    /// Yangi o'rnatish: tasodifiy DB kaliti, PIN va tiklash kodi slotlari.
    /// Tiklash kodi foydalanuvchiga **bir marta** ko'rsatiladi va saqlanmaydi.
    pub fn create(
        platform: &PlatformSecret,
        pin: &Pin,
        kdf: KdfParams,
    ) -> Result<(KeyFile, DbKey, RecoveryCode), SecurityError> {
        let db = DbKey::generate()?;
        let recovery = RecoveryCode::generate()?;
        let mut kf = KeyFile {
            version: KEYFILE_VERSION,
            kdf,
            slots: Vec::new(),
            lockout: LockoutState::default(),
        };
        kf.set_knowledge_slot(SlotKind::Pin, platform, pin.as_bytes(), &db)?;
        kf.set_knowledge_slot(SlotKind::Recovery, platform, recovery.as_bytes(), &db)?;
        Ok((kf, db, recovery))
    }

    fn set_knowledge_slot(
        &mut self,
        kind: SlotKind,
        platform: &PlatformSecret,
        secret: &[u8],
        db: &DbKey,
    ) -> Result<(), SecurityError> {
        let salt = random_bytes::<SALT_LEN>()?;
        let kek = knowledge_kek(kind, platform, secret, &salt, self.kdf)?;
        let slot = seal(kind, &kek, salt, db)?;
        self.slots.retain(|s| s.kind != kind);
        self.slots.push(slot);
        Ok(())
    }

    fn slot(&self, kind: SlotKind) -> Result<&Slot, SecurityError> {
        self.slots
            .iter()
            .find(|s| s.kind == kind)
            .ok_or(SecurityError::SlotMissing)
    }

    pub fn has_slot(&self, kind: SlotKind) -> bool {
        self.slots.iter().any(|s| s.kind == kind)
    }

    pub fn lockout(&self) -> LockoutState {
        self.lockout
    }

    /// PIN bilan ochish. Xato urinishlar `lockout` ga yoziladi — chaqiruvchi `KeyFile` ni
    /// har urinishdan keyin diskka saqlashi shart.
    pub fn unlock_with_pin(
        &mut self,
        platform: &PlatformSecret,
        pin: &Pin,
        now: i64,
    ) -> Result<DbKey, SecurityError> {
        self.lockout
            .check(now)
            .map_err(|until| SecurityError::LockedOut { until })?;
        let slot = self.slot(SlotKind::Pin)?.clone();
        let kek = knowledge_kek(
            SlotKind::Pin,
            platform,
            pin.as_bytes(),
            &salt_of(&slot)?,
            self.kdf,
        )?;
        match open(&slot, &kek) {
            Ok(db) => {
                self.lockout.reset();
                Ok(db)
            }
            Err(SecurityError::WrongSecret) => {
                self.lockout.record_failure(now);
                Err(SecurityError::WrongSecret)
            }
            Err(e) => Err(e),
        }
    }

    /// Tiklash kodi bilan ochish (PIN unutilganda). Muvaffaqiyatdan keyin yangi PIN o'rnatiladi.
    pub fn unlock_with_recovery(
        &mut self,
        platform: &PlatformSecret,
        code: &RecoveryCode,
        now: i64,
    ) -> Result<DbKey, SecurityError> {
        self.lockout
            .check(now)
            .map_err(|until| SecurityError::LockedOut { until })?;
        let slot = self.slot(SlotKind::Recovery)?.clone();
        let kek = knowledge_kek(
            SlotKind::Recovery,
            platform,
            code.as_bytes(),
            &salt_of(&slot)?,
            self.kdf,
        )?;
        match open(&slot, &kek) {
            Ok(db) => {
                self.lockout.reset();
                Ok(db)
            }
            Err(SecurityError::WrongSecret) => {
                self.lockout.record_failure(now);
                Err(SecurityError::WrongSecret)
            }
            Err(e) => Err(e),
        }
    }

    pub fn change_pin(
        &mut self,
        platform: &PlatformSecret,
        db: &DbKey,
        new_pin: &Pin,
    ) -> Result<(), SecurityError> {
        self.set_knowledge_slot(SlotKind::Pin, platform, new_pin.as_bytes(), db)
    }

    /// Yangi tiklash kodi (eskisi bekor bo'ladi).
    pub fn rotate_recovery(
        &mut self,
        platform: &PlatformSecret,
        db: &DbKey,
    ) -> Result<RecoveryCode, SecurityError> {
        let code = RecoveryCode::generate()?;
        self.set_knowledge_slot(SlotKind::Recovery, platform, code.as_bytes(), db)?;
        Ok(code)
    }

    pub fn enable_bio(&mut self, db: &DbKey, bio: &BioKek) -> Result<(), SecurityError> {
        let kek = hkdf_kek(SlotKind::Bio, &[bio.as_bytes()])?;
        let slot = seal(SlotKind::Bio, &kek, [0; SALT_LEN], db)?;
        self.slots.retain(|s| s.kind != SlotKind::Bio);
        self.slots.push(slot);
        Ok(())
    }

    pub fn disable_bio(&mut self) {
        self.slots.retain(|s| s.kind != SlotKind::Bio);
    }

    pub fn unlock_with_bio(&self, bio: &BioKek) -> Result<DbKey, SecurityError> {
        let kek = hkdf_kek(SlotKind::Bio, &[bio.as_bytes()])?;
        open(self.slot(SlotKind::Bio)?, &kek)
    }

    pub fn to_bytes(&self) -> Result<Vec<u8>, SecurityError> {
        serde_json::to_vec(self).map_err(|_| SecurityError::KeyFileCorrupt)
    }

    pub fn from_bytes(bytes: &[u8]) -> Result<Self, SecurityError> {
        let kf: KeyFile =
            serde_json::from_slice(bytes).map_err(|_| SecurityError::KeyFileCorrupt)?;
        if kf.version != KEYFILE_VERSION {
            return Err(SecurityError::KeyFileCorrupt);
        }
        Ok(kf)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const FAST: KdfParams = KdfParams::INSECURE_FAST_FOR_TESTS;

    fn setup() -> (PlatformSecret, KeyFile, DbKey, RecoveryCode) {
        let platform = PlatformSecret::generate().unwrap();
        let (kf, db, rc) =
            KeyFile::create(&platform, &Pin::parse("246810").unwrap(), FAST).unwrap();
        (platform, kf, db, rc)
    }

    #[test]
    fn both_factors_required() {
        let (platform, mut kf, db, _) = setup();
        let pin = Pin::parse("246810").unwrap();
        let opened = kf.unlock_with_pin(&platform, &pin, 0).unwrap();
        assert_eq!(opened.as_bytes(), db.as_bytes());
        // To'g'ri PIN, lekin boshqa platforma siri (keyring/Keystore yo'qolgan yoki ko'chirilgan fayl).
        let other = PlatformSecret::generate().unwrap();
        assert_eq!(
            kf.unlock_with_pin(&other, &pin, 0).map(|_| ()),
            Err(SecurityError::WrongSecret)
        );
        // To'g'ri platforma siri, noto'g'ri PIN.
        let wrong = Pin::parse("000000").unwrap();
        assert_eq!(
            kf.unlock_with_pin(&platform, &wrong, 0).map(|_| ()),
            Err(SecurityError::WrongSecret)
        );
    }

    #[test]
    fn recovery_then_change_pin() {
        let (platform, mut kf, db, rc) = setup();
        let reparsed = RecoveryCode::parse(&rc.display_grouped()).unwrap();
        let opened = kf.unlock_with_recovery(&platform, &reparsed, 0).unwrap();
        assert_eq!(opened.as_bytes(), db.as_bytes());
        let new_pin = Pin::parse("135790").unwrap();
        kf.change_pin(&platform, &opened, &new_pin).unwrap();
        assert!(kf
            .unlock_with_pin(&platform, &Pin::parse("246810").unwrap(), 0)
            .is_err());
        assert_eq!(
            kf.unlock_with_pin(&platform, &new_pin, 0)
                .unwrap()
                .as_bytes(),
            db.as_bytes()
        );
    }

    #[test]
    fn lockout_persists_through_serialization() {
        let (platform, mut kf, _, _) = setup();
        let wrong = Pin::parse("111111").unwrap();
        for _ in 0..5 {
            let _ = kf.unlock_with_pin(&platform, &wrong, 100);
        }
        let mut reloaded = KeyFile::from_bytes(&kf.to_bytes().unwrap()).unwrap();
        let right = Pin::parse("246810").unwrap();
        assert_eq!(
            reloaded.unlock_with_pin(&platform, &right, 110).map(|_| ()),
            Err(SecurityError::LockedOut { until: 130 })
        );
        assert!(reloaded.unlock_with_pin(&platform, &right, 130).is_ok());
        assert_eq!(reloaded.lockout(), LockoutState::default());
    }

    #[test]
    fn bio_slot() {
        let (_, mut kf, db, _) = setup();
        let bio = BioKek::generate().unwrap();
        kf.enable_bio(&db, &bio).unwrap();
        assert_eq!(kf.unlock_with_bio(&bio).unwrap().as_bytes(), db.as_bytes());
        assert_eq!(
            kf.unlock_with_bio(&BioKek::generate().unwrap()).map(|_| ()),
            Err(SecurityError::WrongSecret)
        );
        kf.disable_bio();
        assert_eq!(
            kf.unlock_with_bio(&bio).map(|_| ()),
            Err(SecurityError::SlotMissing)
        );
    }

    #[test]
    fn slots_are_bound_to_their_kind() {
        let (platform, kf, _, _) = setup();
        let mut swapped = kf.clone();
        // PIN slotini RECOVERY deb ko'rsatish (AAD tufayli ochilmaydi).
        for s in &mut swapped.slots {
            s.kind = if s.kind == SlotKind::Pin {
                SlotKind::Recovery
            } else {
                SlotKind::Pin
            };
        }
        assert!(swapped
            .unlock_with_pin(&platform, &Pin::parse("246810").unwrap(), 0)
            .is_err());
    }

    #[test]
    fn corrupt_keyfile() {
        assert_eq!(
            KeyFile::from_bytes(b"{}").map(|_| ()),
            Err(SecurityError::KeyFileCorrupt)
        );
        let (_, kf, _, _) = setup();
        let json = String::from_utf8(kf.to_bytes().unwrap()).unwrap();
        assert!(!json.contains("246810"));
    }

    #[test]
    fn production_params_are_accepted() {
        // Parametrlar argon2 tomonidan qabul qilinishi (hisoblamasdan).
        for p in [KdfParams::ANDROID, KdfParams::DESKTOP] {
            assert!(Params::new(p.m_kib, p.t_cost, p.p_cost, Some(SECRET_LEN)).is_ok());
        }
    }
}
