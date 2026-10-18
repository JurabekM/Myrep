//! Maxfiy kalitlar ombori: Windows Credential Manager (DPAPI bilan himoyalangan) yoki fayl (faqat sinov).

use std::collections::HashMap;
use std::path::PathBuf;

use crate::{Result, StoreError, io_err};

const SERVICE: &str = "tamga";

pub trait SecretStore: Send + Sync {
    fn get(&self, name: &str) -> Result<Option<Vec<u8>>>;
    fn set(&self, name: &str, secret: &[u8]) -> Result<()>;
    /// Yozuvni o'chiradi; yo'q bo'lsa — xato emas.
    fn delete(&self, name: &str) -> Result<()>;
}

/// Tanlov: `TAMGA_SECRETS=file` bo'lsa — fayl ombori (`<home>/secrets`, sinov uchun),
/// aks holda Windows'da Credential Manager.
pub fn uses_file_store() -> bool {
    std::env::var("TAMGA_SECRETS").as_deref() == Ok("file") || !cfg!(windows)
}

pub fn default_store(home: &crate::Home) -> Result<Box<dyn SecretStore>> {
    if uses_file_store() {
        return Ok(Box::new(FileStore::new(home.root().join("secrets"))?));
    }
    #[cfg(windows)]
    {
        Ok(Box::new(CredentialStore::new()?))
    }
    #[cfg(not(windows))]
    unreachable!()
}

/// Windows Credential Manager. Yozuvlar `Local` persistence bilan (domen profilida ko'chib yurmaydi).
#[cfg(windows)]
pub struct CredentialStore;

#[cfg(windows)]
impl CredentialStore {
    pub fn new() -> Result<Self> {
        static INIT: std::sync::Once = std::sync::Once::new();
        let mut err = None;
        INIT.call_once(|| match windows_native_keyring_store::Store::new() {
            Ok(store) => keyring_core::set_default_store(store),
            Err(e) => err = Some(e.to_string()),
        });
        match err {
            Some(e) => Err(StoreError::Secret(e)),
            None => Ok(Self),
        }
    }

    fn entry(name: &str) -> Result<keyring_core::Entry> {
        let mods = HashMap::from([("persistence", "Local")]);
        keyring_core::Entry::new_with_modifiers(SERVICE, name, &mods)
            .map_err(|e| StoreError::Secret(e.to_string()))
    }
}

#[cfg(windows)]
impl SecretStore for CredentialStore {
    fn get(&self, name: &str) -> Result<Option<Vec<u8>>> {
        match Self::entry(name)?.get_secret() {
            Ok(s) => Ok(Some(s)),
            Err(keyring_core::Error::NoEntry) => Ok(None),
            Err(e) => Err(StoreError::Secret(e.to_string())),
        }
    }

    fn set(&self, name: &str, secret: &[u8]) -> Result<()> {
        Self::entry(name)?
            .set_secret(secret)
            .map_err(|e| StoreError::Secret(e.to_string()))
    }

    fn delete(&self, name: &str) -> Result<()> {
        match Self::entry(name)?.delete_credential() {
            Ok(()) | Err(keyring_core::Error::NoEntry) => Ok(()),
            Err(e) => Err(StoreError::Secret(e.to_string())),
        }
    }
}

/// Fayl ombori — himoyasiz, faqat sinov va CI uchun.
pub struct FileStore {
    dir: PathBuf,
}

impl FileStore {
    pub fn new(dir: PathBuf) -> Result<Self> {
        std::fs::create_dir_all(&dir).map_err(io_err(&dir))?;
        Ok(Self { dir })
    }
}

impl SecretStore for FileStore {
    fn get(&self, name: &str) -> Result<Option<Vec<u8>>> {
        let p = self.dir.join(name);
        match std::fs::read(&p) {
            Ok(b) => Ok(Some(b)),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(io_err(&p)(e)),
        }
    }

    fn set(&self, name: &str, secret: &[u8]) -> Result<()> {
        let p = self.dir.join(name);
        std::fs::write(&p, secret).map_err(io_err(&p))
    }

    fn delete(&self, name: &str) -> Result<()> {
        let p = self.dir.join(name);
        match std::fs::remove_file(&p) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(io_err(&p)(e)),
        }
    }
}

#[cfg(all(test, windows))]
mod tests {
    use super::*;

    /// Haqiqiy Windows Credential Manager: vaqtinchalik yozuv yaratiladi, o'qiladi va o'chiriladi.
    /// `cargo test -p tamga-store -- --ignored credential_manager`
    #[test]
    #[ignore = "foydalanuvchining Credential Manager'iga tegadi"]
    fn credential_manager_round_trip() {
        let store = CredentialStore::new().unwrap();
        let name = format!("selftest-{}", std::process::id());
        assert_eq!(store.get(&name).unwrap(), None);
        let secret: Vec<u8> = (0..64u8).collect();
        store.set(&name, &secret).unwrap();
        assert_eq!(store.get(&name).unwrap(), Some(secret));
        CredentialStore::entry(&name)
            .unwrap()
            .delete_credential()
            .unwrap();
        assert_eq!(store.get(&name).unwrap(), None, "o'chirildi");
    }
}
