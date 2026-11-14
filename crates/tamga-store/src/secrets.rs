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
    // Xizmat konteksti: Credential Manager virtual hisobda ishonchli emas — DPAPI fayl ombori.
    #[cfg(windows)]
    if home.is_service() {
        return Ok(Box::new(DpapiFileStore::new(home.root().join("secrets"))?));
    }
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

/// Xizmat konteksti ombori: har sir alohida `<nom>.dpapi` fayli, DPAPI (mashina doirasi) bilan
/// shifrlangan va nomga bog'langan (entropy). Maxfiylik papka ACL'iga tayanadi: o'rnatuvchi uni
/// faqat xizmat hisobi, SYSTEM va administratorlarga ochiq qiladi.
#[cfg(windows)]
pub struct DpapiFileStore {
    dir: PathBuf,
}

#[cfg(windows)]
impl DpapiFileStore {
    pub fn new(dir: PathBuf) -> Result<Self> {
        std::fs::create_dir_all(&dir).map_err(io_err(&dir))?;
        Ok(Self { dir })
    }

    fn path(&self, name: &str) -> PathBuf {
        self.dir.join(format!("{name}.dpapi"))
    }

    fn entropy(name: &str) -> Vec<u8> {
        format!("tamga-secret:{name}").into_bytes()
    }
}

#[cfg(windows)]
impl SecretStore for DpapiFileStore {
    fn get(&self, name: &str) -> Result<Option<Vec<u8>>> {
        let p = self.path(name);
        let ct = match std::fs::read(&p) {
            Ok(b) => b,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(io_err(&p)(e)),
        };
        tamga_win::service::dpapi_unprotect(&ct, &Self::entropy(name))
            .map(Some)
            .map_err(|e| StoreError::Secret(format!("{}: {e}", p.display())))
    }

    fn set(&self, name: &str, secret: &[u8]) -> Result<()> {
        let ct = tamga_win::service::dpapi_protect(secret, &Self::entropy(name))
            .map_err(|e| StoreError::Secret(e.to_string()))?;
        // Atomar: vaqtinchalik fayl + almashtirish (yiqilishda yarim yozilgan kalit qolmasin).
        let p = self.path(name);
        let tmp = p.with_extension("dpapi.tmp");
        std::fs::write(&tmp, ct).map_err(io_err(&tmp))?;
        std::fs::rename(&tmp, &p).map_err(io_err(&p))
    }

    fn delete(&self, name: &str) -> Result<()> {
        let p = self.path(name);
        match std::fs::remove_file(&p) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(io_err(&p)(e)),
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

    #[test]
    fn dpapi_store_round_trip_is_encrypted_and_name_bound() {
        let dir = std::env::temp_dir().join(format!("tamga-dpapi-{}", std::process::id()));
        std::fs::remove_dir_all(&dir).ok();
        let s = DpapiFileStore::new(dir.clone()).unwrap();
        assert_eq!(s.get("signing-seed-v1").unwrap(), None);
        let secret: Vec<u8> = (0..64u8).collect();
        s.set("signing-seed-v1", &secret).unwrap();
        assert_eq!(s.get("signing-seed-v1").unwrap(), Some(secret.clone()));
        let raw = std::fs::read(dir.join("signing-seed-v1.dpapi")).unwrap();
        assert!(
            !raw.windows(8).any(|w| w == &secret[..8]),
            "diskda ochiq emas"
        );
        // Boshqa nomga ko'chirilgan fayl ochilmaydi (entropy nomga bog'langan).
        std::fs::copy(
            dir.join("signing-seed-v1.dpapi"),
            dir.join("vault-master-v1.dpapi"),
        )
        .unwrap();
        assert!(s.get("vault-master-v1").is_err());
        s.delete("signing-seed-v1").unwrap();
        s.delete("signing-seed-v1").unwrap();
        assert_eq!(s.get("signing-seed-v1").unwrap(), None);
        std::fs::remove_dir_all(dir).ok();
    }

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
