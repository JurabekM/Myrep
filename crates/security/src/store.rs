use std::sync::Mutex;

use zeroize::Zeroize;

use crate::{SecretKey, SecurityError};

/// Keyring xizmati nomi (OS Credential Manager'da ko'rinadi).
pub const KEYRING_SERVICE: &str = "BarakaDaftari";
/// Keyring hisob nomi: bitta foydalanuvchi uchun bitta kalit.
pub const KEYRING_ACCOUNT: &str = "db-device-key-v1";

/// Qurilma kalitini saqlaydigan joy. Ishlab chiqarishda OS keyring, testlarda xotira.
pub trait SecretStore: Send + Sync {
    /// Saqlangan kalit. Yo'q bo'lsa — `None`.
    fn read(&self) -> Result<Option<SecretKey>, SecurityError>;
    /// Kalitni saqlaydi (oldingisini almashtiradi).
    fn write(&self, key: &SecretKey) -> Result<(), SecurityError>;
    /// Kalitni o'chiradi. Yo'q bo'lsa ham xato emas.
    fn delete(&self) -> Result<(), SecurityError>;
}

/// Xotiradagi saqlash (testlar uchun). Kalit jarayon tugagach yo'qoladi.
#[derive(Debug, Default)]
pub struct MemorySecretStore {
    slot: Mutex<Option<[u8; crate::key::KEY_LEN]>>,
}

impl MemorySecretStore {
    /// Bo'sh saqlash.
    pub fn new() -> Self {
        Self::default()
    }
}

impl SecretStore for MemorySecretStore {
    fn read(&self) -> Result<Option<SecretKey>, SecurityError> {
        let guard = self
            .slot
            .lock()
            .map_err(|_| SecurityError::Keyring("qulf zaharlangan".to_owned()))?;
        Ok(guard.map(SecretKey::from_array))
    }

    fn write(&self, key: &SecretKey) -> Result<(), SecurityError> {
        let mut guard = self
            .slot
            .lock()
            .map_err(|_| SecurityError::Keyring("qulf zaharlangan".to_owned()))?;
        *guard = Some(*key.as_bytes());
        Ok(())
    }

    fn delete(&self) -> Result<(), SecurityError> {
        let mut guard = self
            .slot
            .lock()
            .map_err(|_| SecurityError::Keyring("qulf zaharlangan".to_owned()))?;
        if let Some(bytes) = guard.as_mut() {
            bytes.zeroize();
        }
        *guard = None;
        Ok(())
    }
}

/// OS keyring (Windows'da Credential Manager, DPAPI bilan himoyalangan, faqat joriy foydalanuvchiga).
#[derive(Debug, Clone)]
pub struct KeyringSecretStore {
    service: String,
    account: String,
}

impl KeyringSecretStore {
    /// Loyiha uchun standart nom bilan saqlash.
    pub fn new() -> Self {
        Self {
            service: KEYRING_SERVICE.to_owned(),
            account: KEYRING_ACCOUNT.to_owned(),
        }
    }

    /// Boshqa nom bilan (masalan, integratsion testlar uchun, asosiy kalitga tegmaslik uchun).
    pub fn with_names(service: &str, account: &str) -> Self {
        Self {
            service: service.to_owned(),
            account: account.to_owned(),
        }
    }

    fn entry(&self) -> Result<keyring::Entry, SecurityError> {
        keyring::Entry::new(&self.service, &self.account).map_err(keyring_error)
    }
}

impl Default for KeyringSecretStore {
    fn default() -> Self {
        Self::new()
    }
}

impl SecretStore for KeyringSecretStore {
    fn read(&self) -> Result<Option<SecretKey>, SecurityError> {
        match self.entry()?.get_secret() {
            Ok(mut bytes) => {
                let key = SecretKey::from_slice(&bytes);
                bytes.zeroize();
                key.map(Some)
                    .ok_or_else(|| SecurityError::Keyring("kalit uzunligi noto'g'ri".to_owned()))
            }
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(error) => Err(keyring_error(error)),
        }
    }

    fn write(&self, key: &SecretKey) -> Result<(), SecurityError> {
        self.entry()?
            .set_secret(key.as_bytes())
            .map_err(keyring_error)
    }

    fn delete(&self) -> Result<(), SecurityError> {
        match self.entry()?.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(error) => Err(keyring_error(error)),
        }
    }
}

/// Keyring xatosini xabarga aylantiradi. Xabarda hech qachon sir qiymati bo'lmaydi.
fn keyring_error(error: keyring::Error) -> SecurityError {
    SecurityError::Keyring(error.to_string())
}
