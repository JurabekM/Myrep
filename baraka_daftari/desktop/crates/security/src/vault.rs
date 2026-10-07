use std::{fs, path::PathBuf, time::SystemTime};

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::{
    aead::{Aead, Payload},
    KeyInit, XChaCha20Poly1305,
};
use hkdf::Hkdf;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::{lockout_delay_secs, KeyStore, SecretKey, SecurityError};

const FILE_VERSION: u32 = 1;
const AAD: &[u8] = b"baraka/db-key-wrap/v1";
const HKDF_INFO: &[u8] = b"baraka/kek/v1";
const NONCE_LEN: usize = 24;
const SALT_LEN: usize = 16;

pub trait UnixClock {
    fn unix_now(&self) -> i64;
}

pub struct SystemUnixClock;

impl UnixClock for SystemUnixClock {
    fn unix_now(&self) -> i64 {
        SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct KdfParams {
    pub m_kib: u32,
    pub t: u32,
    pub p: u32,
}

impl KdfParams {
    /// Ishlab chiqarish: 64 MiB, 3 o'tish, 1 oqim.
    #[must_use]
    pub const fn production() -> Self {
        Self {
            m_kib: 64 * 1024,
            t: 3,
            p: 1,
        }
    }

    /// Faqat testlar uchun (tez).
    #[must_use]
    pub const fn fast_for_tests() -> Self {
        Self {
            m_kib: 8,
            t: 1,
            p: 1,
        }
    }

    /// Fayldan o'qilgan parametrlar DoS uchun cheklanadi.
    fn validate(self) -> Result<Self, SecurityError> {
        if self.m_kib < 8
            || self.m_kib > 1 << 20
            || self.t == 0
            || self.t > 10
            || self.p == 0
            || self.p > 8
        {
            return Err(SecurityError::Corrupt("KDF parametrlari yaroqsiz".into()));
        }
        Ok(self)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VaultStatus {
    Uninitialized,
    /// `retry_after_secs == 0` bo'lsa PIN kiritish mumkin.
    Locked {
        retry_after_secs: u64,
    },
}

#[derive(Serialize, Deserialize)]
struct VaultFile {
    version: u32,
    kdf: KdfParams,
    salt: String,
    nonce: String,
    wrapped: String,
    failures: u32,
    locked_until: i64,
}

/// PIN + keyring bilan DB kalitini boshqaradi.
pub struct Vault<S: KeyStore, C: UnixClock = SystemUnixClock> {
    path: PathBuf,
    store: S,
    kdf: KdfParams,
    clock: C,
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

fn unhex(s: &str) -> Result<Vec<u8>, SecurityError> {
    if !s.len().is_multiple_of(2) || !s.is_ascii() {
        return Err(SecurityError::Corrupt("hex noto'g'ri".into()));
    }
    (0..s.len())
        .step_by(2)
        .map(|i| {
            u8::from_str_radix(&s[i..i + 2], 16)
                .map_err(|_| SecurityError::Corrupt("hex noto'g'ri".into()))
        })
        .collect()
}

fn random<const N: usize>() -> Result<[u8; N], SecurityError> {
    let mut b = [0u8; N];
    getrandom::fill(&mut b).map_err(|_| SecurityError::Crypto)?;
    Ok(b)
}

fn valid_pin(pin: &str) -> bool {
    pin.len() == 6 && pin.bytes().all(|b| b.is_ascii_digit())
}

/// `KEK = HKDF-SHA256(salt = qurilma siri, ikm = Argon2id(PIN, salt))`.
fn derive_kek(
    pin: &str,
    salt: &[u8],
    device_secret: &[u8],
    kdf: KdfParams,
) -> Result<Zeroizing<[u8; 32]>, SecurityError> {
    let params =
        Params::new(kdf.m_kib, kdf.t, kdf.p, Some(32)).map_err(|_| SecurityError::Crypto)?;
    let argon = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
    let mut pin_key = Zeroizing::new([0u8; 32]);
    argon
        .hash_password_into(pin.as_bytes(), salt, pin_key.as_mut())
        .map_err(|_| SecurityError::Crypto)?;
    let mut kek = Zeroizing::new([0u8; 32]);
    Hkdf::<Sha256>::new(Some(device_secret), pin_key.as_ref())
        .expand(HKDF_INFO, kek.as_mut())
        .map_err(|_| SecurityError::Crypto)?;
    Ok(kek)
}

impl<S: KeyStore> Vault<S> {
    #[must_use]
    pub fn new(path: PathBuf, store: S, kdf: KdfParams) -> Self {
        Self {
            path,
            store,
            kdf,
            clock: SystemUnixClock,
        }
    }
}

impl<S: KeyStore, C: UnixClock> Vault<S, C> {
    #[must_use]
    pub const fn with_clock(path: PathBuf, store: S, kdf: KdfParams, clock: C) -> Self {
        Self {
            path,
            store,
            kdf,
            clock,
        }
    }

    #[must_use]
    pub fn is_initialized(&self) -> bool {
        self.path.exists()
    }

    /// # Errors
    /// Fayl o'qilmasa yoki buzilgan bo'lsa.
    pub fn status(&self) -> Result<VaultStatus, SecurityError> {
        if !self.is_initialized() {
            return Ok(VaultStatus::Uninitialized);
        }
        let file = self.read()?;
        Ok(VaultStatus::Locked {
            retry_after_secs: self.retry_after(&file),
        })
    }

    /// Birinchi ishga tushirish: tasodifiy DB kaliti va qurilma siri yaratiladi.
    ///
    /// # Errors
    /// PIN noto'g'ri formatda, seyf mavjud, yoki keyring/fayl xatosi.
    pub fn setup(&self, pin: &str) -> Result<SecretKey, SecurityError> {
        if !valid_pin(pin) {
            return Err(SecurityError::InvalidPin);
        }
        if self.is_initialized() {
            return Err(SecurityError::AlreadyInitialized);
        }
        let db_key = SecretKey::from_bytes(random::<32>()?);
        let device_secret = Zeroizing::new(random::<32>()?);
        let salt = random::<SALT_LEN>()?;
        let nonce = random::<NONCE_LEN>()?;

        let kek = derive_kek(pin, &salt, device_secret.as_ref(), self.kdf)?;
        let wrapped = XChaCha20Poly1305::new_from_slice(kek.as_ref())
            .map_err(|_| SecurityError::Crypto)?
            .encrypt(
                (&nonce).into(),
                Payload {
                    msg: db_key.as_bytes(),
                    aad: AAD,
                },
            )
            .map_err(|_| SecurityError::Crypto)?;

        // Avval keyring, keyin fayl: fayl bor, keyring yo'q holat "KeyringMissing" bo'ladi.
        self.store.set(device_secret.as_ref())?;
        self.write(&VaultFile {
            version: FILE_VERSION,
            kdf: self.kdf,
            salt: hex(&salt),
            nonce: hex(&nonce),
            wrapped: hex(&wrapped),
            failures: 0,
            locked_until: 0,
        })?;
        Ok(db_key)
    }

    /// PIN bo'yicha DB kalitini ochadi. Xato PIN urinishlari hisoblanadi va kutish o'sib boradi.
    ///
    /// # Errors
    /// [`SecurityError::Locked`], [`SecurityError::WrongPin`], [`SecurityError::KeyringMissing`] va h.k.
    pub fn unlock(&self, pin: &str) -> Result<SecretKey, SecurityError> {
        if !self.is_initialized() {
            return Err(SecurityError::NotInitialized);
        }
        let mut file = self.read()?;
        let wait = self.retry_after(&file);
        if wait > 0 {
            return Err(SecurityError::Locked {
                retry_after_secs: wait,
            });
        }
        // PIN formati noto'g'ri bo'lsa ham urinish hisoblanadi (formatni tekshirish orqali taxmin qilishni qiyinlashtirish).
        // Keyring yo'qligi PIN xatosi emas: urinish hisoblanmaydi.
        let device_secret = self.store.get()?.ok_or(SecurityError::KeyringMissing)?;

        let salt = unhex(&file.salt)?;
        let nonce: [u8; NONCE_LEN] = unhex(&file.nonce)?
            .try_into()
            .map_err(|_| SecurityError::Corrupt("nonce uzunligi".into()))?;
        let wrapped = unhex(&file.wrapped)?;

        let opened = valid_pin(pin)
            .then(|| derive_kek(pin, &salt, device_secret.as_slice(), file.kdf.validate()?))
            .transpose()?
            .and_then(|kek| {
                XChaCha20Poly1305::new_from_slice(kek.as_ref())
                    .ok()?
                    .decrypt(
                        (&nonce).into(),
                        Payload {
                            msg: &wrapped,
                            aad: AAD,
                        },
                    )
                    .ok()
            });

        if let Some(plain) = opened {
            let plain = Zeroizing::new(plain);
            let bytes: [u8; 32] = plain
                .as_slice()
                .try_into()
                .map_err(|_| SecurityError::Corrupt("kalit uzunligi".into()))?;
            if file.failures != 0 || file.locked_until != 0 {
                file.failures = 0;
                file.locked_until = 0;
                self.write(&file)?;
            }
            return Ok(SecretKey::from_bytes(bytes));
        }

        file.failures = file.failures.saturating_add(1);
        let delay = lockout_delay_secs(file.failures);
        file.locked_until = if delay == 0 {
            0
        } else {
            self.clock.unix_now().saturating_add_unsigned(delay)
        };
        self.write(&file)?;
        Err(SecurityError::WrongPin)
    }

    fn retry_after(&self, file: &VaultFile) -> u64 {
        file.locked_until
            .saturating_sub(self.clock.unix_now())
            .max(0)
            .unsigned_abs()
    }

    fn read(&self) -> Result<VaultFile, SecurityError> {
        let text = fs::read_to_string(&self.path).map_err(|e| SecurityError::Io(e.to_string()))?;
        let file: VaultFile =
            serde_json::from_str(&text).map_err(|e| SecurityError::Corrupt(e.to_string()))?;
        if file.version != FILE_VERSION {
            return Err(SecurityError::Corrupt(format!(
                "noma'lum versiya {}",
                file.version
            )));
        }
        Ok(file)
    }

    /// Atomik yozish: vaqtinchalik fayl → rename.
    fn write(&self, file: &VaultFile) -> Result<(), SecurityError> {
        if let Some(dir) = self.path.parent() {
            fs::create_dir_all(dir).map_err(|e| SecurityError::Io(e.to_string()))?;
        }
        let tmp = self.path.with_extension("tmp");
        let json =
            serde_json::to_string(file).map_err(|e| SecurityError::Corrupt(e.to_string()))?;
        fs::write(&tmp, json).map_err(|e| SecurityError::Io(e.to_string()))?;
        fs::rename(&tmp, &self.path).map_err(|e| SecurityError::Io(e.to_string()))
    }
}

impl<T: UnixClock + ?Sized> UnixClock for &T {
    fn unix_now(&self) -> i64 {
        (**self).unix_now()
    }
}
