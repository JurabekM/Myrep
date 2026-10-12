//! Seyf sessiyasi: qulf holati, ochiq baza va avto-qulf. Tauri'dan mustaqil (testlanadi).

use std::path::PathBuf;

use domain::{IdGen, SystemClock, UuidV7Gen};
use security::{AutoLock, KdfParams, KeyStore, SecurityError, Vault, VaultStatus};
use services::{members, setup, Ctx, Env, ServiceError};
use storage::{Database, StorageError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VaultState {
    Uninitialized,
    Locked { retry_after_secs: u64 },
    Unlocked,
}

#[derive(Debug)]
#[allow(dead_code)] // Ichki xatolar loglanmaydi (loglarda ma'lumot bo'lmasligi uchun).
pub enum SessionError {
    Security(SecurityError),
    Storage(StorageError),
    Service(ServiceError),
    /// Ma'lumotlar bazasi ochiq emas.
    Locked,
}

impl From<SecurityError> for SessionError {
    fn from(e: SecurityError) -> Self {
        Self::Security(e)
    }
}

impl From<ServiceError> for SessionError {
    fn from(e: ServiceError) -> Self {
        Self::Service(e)
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
    ctx: Option<Ctx>,
    data_dir: PathBuf,
    kdf: KdfParams,
    autolock: AutoLock,
}

impl<S: KeyStore> Session<S> {
    #[must_use]
    pub const fn kdf(&self) -> KdfParams {
        self.kdf
    }

    #[must_use]
    pub fn new(data_dir: &std::path::Path, store: S, kdf: KdfParams, now: i64) -> Self {
        Self {
            vault: Vault::new(data_dir.join("vault.json"), store, kdf),
            db_path: data_dir.join("baraka.db"),
            db: None,
            ctx: None,
            data_dir: data_dir.to_path_buf(),
            kdf,
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
        self.open_db(key.as_bytes())?;
        self.ensure_first_member_pin(pin)?;
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
        self.open_db(key.as_bytes())?;
        self.ensure_first_member_pin(pin)?;
        self.autolock.touch(now);
        Ok(())
    }

    fn open_db(&mut self, key: &[u8; 32]) -> Result<(), SessionError> {
        let mut db = Database::open(&self.db_path, key)?;
        let device_id = device_id(&self.data_dir)?;
        let env = Env {
            clock: &SystemClock,
            ids: &UuidV7Gen,
            device_id: &device_id,
        };
        self.ctx = Some(setup::ensure_household(&mut db, &env)?);
        self.db = Some(db);
        Ok(())
    }

    /// Birinchi (asosiy) a'zoning shaxsiy PIN'i seyf PIN'i bilan bir xil boshlanadi; boshqa a'zolar
    /// o'z PIN'ini oila kengashida o'rnatadi. Allaqachon bor bo'lsa tegilmaydi.
    fn ensure_first_member_pin(&mut self, pin: &str) -> Result<(), SessionError> {
        let (Some(db), Some(ctx)) = (self.db.as_mut(), self.ctx.as_ref()) else {
            return Err(SessionError::Locked);
        };
        if members::has_pin(db.conn(), ctx, &ctx.member_id)? {
            return Ok(());
        }
        let device_id = device_id(&self.data_dir)?;
        let env = Env {
            clock: &SystemClock,
            ids: &UuidV7Gen,
            device_id: &device_id,
        };
        members::set_pin(db, &env, ctx, &ctx.member_id, pin, self.kdf)?;
        Ok(())
    }

    /// Bazani yopadi (ulanish tushadi, kalit xotiradan ketadi).
    pub fn lock(&mut self) {
        self.db = None;
        self.ctx = None;
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

    /// Faqat ochiq holatda xizmatlarni ishga tushiradi (baza, muhit va joriy xonadon bilan).
    ///
    /// # Errors
    /// Qulfli bo'lsa [`SessionError::Locked`]; xizmat xatosi.
    pub fn run<T>(
        &mut self,
        f: impl FnOnce(&mut Database, &Env<'_>, &Ctx) -> Result<T, ServiceError>,
    ) -> Result<T, SessionError> {
        let (Some(db), Some(ctx)) = (self.db.as_mut(), self.ctx.as_ref()) else {
            return Err(SessionError::Locked);
        };
        let device_id = device_id(&self.data_dir)?;
        let env = Env {
            clock: &SystemClock,
            ids: &UuidV7Gen,
            device_id: &device_id,
        };
        Ok(f(db, &env, ctx)?)
    }
}

/// Shu qurilmaning barqaror ID'si (`origin_device_id`): birinchi marta yaratiladi va faylda turadi.
fn device_id(dir: &std::path::Path) -> Result<String, SessionError> {
    let path = dir.join("device_id");
    if let Ok(existing) = std::fs::read_to_string(&path) {
        let existing = existing.trim();
        if !existing.is_empty() {
            return Ok(existing.to_owned());
        }
    }
    let id = UuidV7Gen.new_id();
    std::fs::create_dir_all(dir)
        .and_then(|()| std::fs::write(&path, &id))
        .map_err(|_| StorageError::Corrupt("device_id yozilmadi".into()))?;
    Ok(id)
}

#[cfg(test)]
mod tests {
    use security::MemoryStore;

    use super::*;

    fn session(dir: &std::path::Path) -> Session<MemoryStore> {
        Session::new(dir, MemoryStore::new(), KdfParams::fast_for_tests(), 1000)
    }

    fn locked<S: KeyStore>(s: &mut Session<S>) -> bool {
        matches!(s.run(|_, _, _| Ok(())), Err(SessionError::Locked))
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

    #[test]
    fn unlock_creates_household_once_and_device_id_is_stable() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = session(dir.path());
        s.setup("123456", 1000).unwrap();
        let first = s.run(|_, _, ctx| Ok(ctx.household_id.clone())).unwrap();
        let dev = std::fs::read_to_string(dir.path().join("device_id")).unwrap();
        assert!(!dev.trim().is_empty());
        s.lock();
        s.unlock("123456", 1001).unwrap();
        assert_eq!(
            s.run(|_, _, ctx| Ok(ctx.household_id.clone())).unwrap(),
            first
        );
        assert_eq!(
            std::fs::read_to_string(dir.path().join("device_id")).unwrap(),
            dev
        );
    }

    #[test]
    fn first_member_gets_the_vault_pin_once() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = session(dir.path());
        s.setup("123456", 1000).unwrap();
        s.run(|db, env, ctx| {
            members::verify(db, env, ctx, &ctx.member_id, "123456")?;
            // Keyingi ochilishda (boshqa PIN bilan emas) qayta yozilmaydi.
            Ok(())
        })
        .unwrap();
        s.lock();
        s.unlock("123456", 1001).unwrap();
        s.run(|db, env, ctx| members::verify(db, env, ctx, &ctx.member_id, "123456"))
            .unwrap();
    }
}
