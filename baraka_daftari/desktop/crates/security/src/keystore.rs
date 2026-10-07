use std::sync::Mutex;

use zeroize::Zeroizing;

use crate::SecurityError;

/// Qurilma siri saqlanadigan joy (OS keyring yoki testda xotira).
pub trait KeyStore {
    /// # Errors
    /// Saqlash tizimi xato bersa. Yozuv yo'q bo'lsa `Ok(None)`.
    fn get(&self) -> Result<Option<Zeroizing<Vec<u8>>>, SecurityError>;
    /// # Errors
    /// Saqlash tizimi xato bersa.
    fn set(&self, secret: &[u8]) -> Result<(), SecurityError>;
    /// # Errors
    /// Saqlash tizimi xato bersa. Yozuv yo'q bo'lsa ham `Ok`.
    fn delete(&self) -> Result<(), SecurityError>;
}

/// Windows Credential Manager (DPAPI) / macOS Keychain / Linux Secret Service.
pub struct KeyringStore {
    entry: keyring::Entry,
}

impl KeyringStore {
    /// # Errors
    /// Entry yaratib bo'lmasa.
    pub fn new(service: &str, user: &str) -> Result<Self, SecurityError> {
        let entry = keyring::Entry::new(service, user)
            .map_err(|e| SecurityError::Keyring(e.to_string()))?;
        Ok(Self { entry })
    }
}

impl KeyStore for KeyringStore {
    fn get(&self) -> Result<Option<Zeroizing<Vec<u8>>>, SecurityError> {
        match self.entry.get_secret() {
            Ok(v) => Ok(Some(Zeroizing::new(v))),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(SecurityError::Keyring(e.to_string())),
        }
    }

    fn set(&self, secret: &[u8]) -> Result<(), SecurityError> {
        self.entry
            .set_secret(secret)
            .map_err(|e| SecurityError::Keyring(e.to_string()))
    }

    fn delete(&self) -> Result<(), SecurityError> {
        match self.entry.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(SecurityError::Keyring(e.to_string())),
        }
    }
}

/// Faqat testlar va keyring bo'lmagan muhitlar uchun.
#[derive(Default)]
pub struct MemoryStore(Mutex<Option<Vec<u8>>>);

impl MemoryStore {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, Option<Vec<u8>>> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}

impl KeyStore for MemoryStore {
    fn get(&self) -> Result<Option<Zeroizing<Vec<u8>>>, SecurityError> {
        Ok(self.lock().clone().map(Zeroizing::new))
    }

    fn set(&self, secret: &[u8]) -> Result<(), SecurityError> {
        *self.lock() = Some(secret.to_vec());
        Ok(())
    }

    fn delete(&self) -> Result<(), SecurityError> {
        *self.lock() = None;
        Ok(())
    }
}

impl<T: KeyStore + ?Sized> KeyStore for &T {
    fn get(&self) -> Result<Option<Zeroizing<Vec<u8>>>, SecurityError> {
        (**self).get()
    }
    fn set(&self, secret: &[u8]) -> Result<(), SecurityError> {
        (**self).set(secret)
    }
    fn delete(&self) -> Result<(), SecurityError> {
        (**self).delete()
    }
}
