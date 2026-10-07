//! Seyf sessiyasi: qulf holati, ochiq baza va avto-qulf. Tauri'dan mustaqil (testlanadi).

use std::path::PathBuf;

use security::{AutoLock, KdfParams, KeyStore, SecurityError, Vault, VaultStatus};
use storage::{Database, StorageError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VaultState {
    Uninitialized,
    Locked { retry_after_secs: u64 },
    Unlocked,
}

#[derive(Debug)]
#[allow(dead_code)] // Storage(..) ichki xatosi hozircha loglanmaydi (loglarda ma'lumot bo'lmasligi uchun).
pub enum SessionError {
    Security(SecurityError),
    Storage(StorageError),
    /// Ma'lumotlar bazasi ochiq emas.
    Locked,
}

impl From<SecurityError> for SessionError {
    fn from(e: SecurityError) -> Self {
        Self::Security(e)
    }
}

impl From<StorageError> for SessionError {
    fn from(e: StorageError) -> Self {
        Self::Storage(e)
    }
}

pub struct Session<S: KeyStore> {
    vault: Vault<S>,
    db_path: PathBuf,
    db: Option<Database>,
    autolock: AutoLock,
}

impl<S: KeyStore> Session<S> {
    #[must_use]
    pub fn new(data_dir: &std::path::Path, store: S, kdf: KdfParams, now: i64) -> Self {
        Self {
            vault: Vault::new(data_dir.join("vault.json"), store, kdf),
            db_path: data_dir.join("baraka.db"),
            db: None,
            autolock: AutoLock::new(AutoLock::DEFAULT_TIMEOUT_SECS, now),
        }
    }

    /// # Errors
    /// Seyf fayli o'qilmasa.
    pub fn state(&self) -> Result<VaultState, SessionError> {
        if self.db.is_some() {
            return Ok(VaultState::Unlocked);
        }
        Ok(match self.vault.status()? {
            VaultStatus::Uninitialized => VaultState::Uninitialized,
            VaultStatus::Locked { retry_after_secs } => VaultState::Locked { retry_after_secs },
        })
    }

    /// Birinchi ishga tushirish: seyf yaratiladi va baza ochiladi.
    ///
    /// # Errors
    /// PIN formati, keyring yoki baza xatosi.
    pub fn setup(&mut self, pin: &str, now: i64) -> Result<(), SessionError> {
        let key = self.vault.setup(pin)?;
        self.db = Some(Database::open(&self.db_path, key.as_bytes())?);
        self.autolock.touch(now);
        Ok(())
    }

    /// # Errors
    /// Noto'g'ri PIN, kutish vaqti, keyring yoki baza xatosi.
    pub fn unlock(&mut self, pin: &str, now: i64) -> Result<(), SessionError> {
        if self.db.is_some() {
            return Ok(());
        }
        let key = self.vault.unlock(pin)?;
        self.db = Some(Database::open(&self.db_path, key.as_bytes())?);
        self.autolock.touch(now);
        Ok(())
    }

    /// Bazani yopadi (ulanish tushadi, kalit xotiradan ketadi).
    pub fn lock(&mut self) {
        self.db = None;
    }

    /// Foydalanuvchi faolligi (avto-qulf hisoblagichini yangilaydi).
    pub const fn touch(&mut self, now: i64) {
        self.autolock.touch(now);
    }

    /// Davriy tekshiruv. Qulflansa `true`.
    pub fn tick(&mut self, now: i64) -> bool {
        if self.db.is_some() && self.autolock.should_lock(now) {
            self.lock();
            return true;
        }
        false
    }

    #[allow(dead_code)] // Sozlamalar ekrani (D4+) ishlatadi.
    pub const fn set_autolock_timeout(&mut self, secs: u64) {
        self.autolock.set_timeout(secs);
    }

    /// Faqat ochiq holatda baza bilan ishlash.
    #[allow(dead_code)] // Domen commandlari (D4+) ishlatadi.
    ///
    /// # Errors
    /// Qulfli bo'lsa [`SessionError::Locked`].
    pub fn with_db<T>(
        &mut self,
        f: impl FnOnce(&mut Database) -> Result<T, StorageError>,
    ) -> Result<T, SessionError> {
        let db = self.db.as_mut().ok_or(SessionError::Locked)?;
        Ok(f(db)?)
    }
}

#[cfg(test)]
mod tests {
    use security::MemoryStore;

    use super::*;

    fn session(dir: &std::path::Path) -> Session<MemoryStore> {
        Session::new(dir, MemoryStore::new(), KdfParams::fast_for_tests(), 1000)
    }

    fn locked<S: KeyStore>(s: &mut Session<S>) -> bool {
        matches!(s.with_db(|_| Ok(())), Err(SessionError::Locked))
    }

    #[test]
    fn full_lifecycle() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = session(dir.path());
        assert_eq!(s.state().unwrap(), VaultState::Uninitialized);
        assert!(locked(&mut s));

        s.setup("123456", 1000).unwrap();
        assert_eq!(s.state().unwrap(), VaultState::Unlocked);
        assert!(!locked(&mut s));

        s.lock();
        assert_eq!(
            s.state().unwrap(),
            VaultState::Locked {
                retry_after_secs: 0
            }
        );
        assert!(locked(&mut s));
        assert!(matches!(
            s.unlock("000000", 1000),
            Err(SessionError::Security(SecurityError::WrongPin))
        ));
        s.unlock("123456", 1001).unwrap();
        assert_eq!(s.state().unwrap(), VaultState::Unlocked);
    }

    #[test]
    fn autolock_closes_the_database() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = session(dir.path());
        s.setup("123456", 1000).unwrap();
        assert!(!s.tick(1299));
        s.touch(1299);
        assert!(!s.tick(1500));
        assert!(s.tick(1599));
        assert!(locked(&mut s));
        assert!(!s.tick(9999), "allaqachon qulflangan");
    }

    #[test]
    fn timeout_is_configurable() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = session(dir.path());
        s.setup("123456", 1000).unwrap();
        s.set_autolock_timeout(10);
        assert!(s.tick(1010));
    }
}
