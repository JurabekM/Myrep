//! Seans: qulflangan/ochiq holat, PIN bilan ochish, qo'lda va avtomatik qulflash.
//!
//! Bu modul Tauri'ga bog'liq emas: holat mantig'i shu yerda, commandlar esa uni chaqiradi.
//! Ochiq holatda bazaning ulanishi xotirada turadi; qulflanganda u yopiladi (DESKTOP_PROMPT.md 6.2).

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, MutexGuard, PoisonError};
use std::time::{Duration, Instant};

use security::{
    AUTO_LOCK_TIMEOUT, AutoLockPolicy, KdfParams, SecretStore, SecurityError, create_vault,
    open_vault,
};
use storage::{Database, StorageError};
use tracing::info;

/// Avto-qulflash tekshiruvi qanchalik tez-tez bajarilishi.
pub const AUTO_LOCK_TICK: Duration = Duration::from_secs(1);

/// Diskdagi fayllar: kalit fayli va shifrlangan baza.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Paths {
    /// PIN bilan o'ralgan kalit fayli (`security` crate).
    pub key_file: PathBuf,
    /// SQLCipher bilan shifrlangan ma'lumotlar bazasi.
    pub database: PathBuf,
}

impl Paths {
    /// Ma'lumotlar papkasidagi standart fayl nomlari.
    pub fn in_dir(dir: &Path) -> Self {
        Self {
            key_file: dir.join("keys.bin"),
            database: dir.join("daftar.db"),
        }
    }
}

/// Seans holati. Ochiq holatda baza ulanishi bor.
enum Phase {
    Locked,
    // Ulanish faqat yashab turishi uchun ushlanadi: qulflanganda (yoki tugaganda) yopiladi.
    // D4 dan repo'lar shu yerdan o'qiydi, shundan so'ng bu ogohlantirish olib tashlanadi.
    Unlocked(#[expect(dead_code, reason = "ulanish yopilishi uchun ushlanadi")] Database),
}

/// Joriy holat: sozlanganmi va ochiqmi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Status {
    /// PIN o'rnatilganmi (kalit fayli bormi).
    pub set_up: bool,
    /// Baza hozir ochiqmi.
    pub unlocked: bool,
}

/// Seans xatosi. Xabarlarda PIN yoki kalit bo'lmaydi.
#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    /// Kalit yoki PIN bilan bog'liq xato.
    #[error(transparent)]
    Security(#[from] SecurityError),
    /// Ma'lumotlar bazasi xatosi.
    #[error(transparent)]
    Storage(#[from] StorageError),
}

/// Ilova seansi. Bitta nusxa butun ilova uchun (Tauri holatida saqlanadi).
pub struct Session {
    paths: Paths,
    store: Arc<dyn SecretStore>,
    params: KdfParams,
    phase: Mutex<Phase>,
    auto_lock: Mutex<AutoLockPolicy>,
    started: Instant,
}

impl Session {
    /// Yangi seans: boshida qulflangan. `store` — qurilma kaliti joyi, `params` — Argon2id parametrlari.
    pub fn new(paths: Paths, store: Arc<dyn SecretStore>, params: KdfParams) -> Self {
        Self {
            paths,
            store,
            params,
            phase: Mutex::new(Phase::Locked),
            auto_lock: Mutex::new(AutoLockPolicy::new(AUTO_LOCK_TIMEOUT)),
            started: Instant::now(),
        }
    }

    /// Joriy holat.
    pub fn status(&self) -> Status {
        let unlocked = matches!(*self.phase(), Phase::Unlocked(_));
        Status {
            set_up: self.paths.key_file.exists(),
            unlocked,
        }
    }

    /// Birinchi marta PIN o'rnatadi va bazani ochiq holatda qoldiradi.
    pub fn setup(&self, pin: &str) -> Result<(), SessionError> {
        let mut phase = self.phase();
        let key = create_vault(&self.paths.key_file, pin, self.store.as_ref(), self.params)?;
        let database = Database::open(&self.paths.database, &key)?;
        *phase = Phase::Unlocked(database);
        info!("xavfsizlik sozlandi");
        Ok(())
    }

    /// PIN bilan bazani ochadi. Noto'g'ri PIN hisoblanadi; juda ko'p urinishda kutish qo'yiladi.
    /// `now_unix` — joriy vaqt (Unix soniyalarida), lockout hisobi uchun.
    pub fn unlock(&self, pin: &str, now_unix: i64) -> Result<(), SessionError> {
        let mut phase = self.phase();
        if matches!(*phase, Phase::Unlocked(_)) {
            return Ok(());
        }
        let key = open_vault(&self.paths.key_file, pin, self.store.as_ref(), now_unix)?;
        let database = Database::open(&self.paths.database, &key)?;
        *phase = Phase::Unlocked(database);
        // Foydalanuvchi PIN kiritayotgan oyna fokusda: avto-qulflash taymeri yangidan boshlanadi.
        self.auto_lock_policy().on_focus_gained();
        info!("baza ochildi");
        Ok(())
    }

    /// Bazani yopadi (ulanish yopiladi). Allaqachon qulflangan bo'lsa — hech narsa qilmaydi.
    pub fn lock(&self) {
        let mut phase = self.phase();
        if matches!(*phase, Phase::Unlocked(_)) {
            info!("baza qulflandi");
        }
        *phase = Phase::Locked;
    }

    /// Oyna fokusga kelganini yoki fokusdan tushganini bildiradi (ilova vaqti bo'yicha).
    pub fn focus_changed(&self, focused: bool) {
        self.focus_changed_at(focused, self.started.elapsed());
    }

    /// Avto-qulflash vaqti kelgan bo'lsa, bazani yopadi.
    pub fn enforce_auto_lock(&self) {
        self.enforce_auto_lock_at(self.started.elapsed());
    }

    fn focus_changed_at(&self, focused: bool, now: Duration) {
        let mut policy = self.auto_lock_policy();
        if focused {
            policy.on_focus_gained();
        } else {
            policy.on_focus_lost(now);
        }
    }

    fn enforce_auto_lock_at(&self, now: Duration) {
        let due = {
            let mut policy = self.auto_lock_policy();
            if policy.should_lock(now) {
                // Taymer qayta ishlamasin: qulflangandan keyin yana chaqirilganda ikkinchi marta qulflanmaydi.
                policy.on_focus_gained();
                true
            } else {
                false
            }
        };
        if due {
            info!("avto-qulflash: oyna uzoq vaqt fokusda emas");
            self.lock();
        }
    }

    /// Holat qulfini oladi. Qulf zaharlangan bo'lsa ham ichidagi qiymat ishlatiladi:
    /// holat oddiy (ochiq ulanish yoki yo'q), shu sababli buzilgan holat xavfli emas.
    fn phase(&self) -> MutexGuard<'_, Phase> {
        self.phase.lock().unwrap_or_else(PoisonError::into_inner)
    }

    fn auto_lock_policy(&self) -> MutexGuard<'_, AutoLockPolicy> {
        self.auto_lock
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::{LOCKOUT_THRESHOLD, MemorySecretStore};

    const PIN: &str = "123456";
    const WRONG_PIN: &str = "654321";
    const NOW: i64 = 1_800_000_000;

    /// Test papkasi: test tugagach o'chiriladi.
    struct TempDir(PathBuf);

    impl TempDir {
        fn new(name: &str) -> Self {
            let nanos = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|elapsed| elapsed.as_nanos())
                .unwrap_or(0);
            let dir = std::env::temp_dir().join(format!(
                "baraka-session-{name}-{}-{nanos}",
                std::process::id()
            ));
            std::fs::create_dir_all(&dir).expect("papka yaratilsin");
            Self(dir)
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn session(dir: &TempDir) -> (Session, Arc<MemorySecretStore>) {
        let store = Arc::new(MemorySecretStore::new());
        let shared: Arc<dyn SecretStore> = store.clone();
        let session = Session::new(Paths::in_dir(&dir.0), shared, KdfParams::FAST_FOR_TESTS);
        (session, store)
    }

    #[test]
    fn sozlash_qulflash_va_ochish_holatni_boshqaradi() {
        let dir = TempDir::new("cycle");
        let (session, _store) = session(&dir);
        assert_eq!(
            session.status(),
            Status {
                set_up: false,
                unlocked: false
            }
        );

        session.setup(PIN).expect("sozlansin");
        assert_eq!(
            session.status(),
            Status {
                set_up: true,
                unlocked: true
            }
        );

        session.lock();
        assert!(!session.status().unlocked);

        session.unlock(PIN, NOW).expect("ochilsin");
        assert!(session.status().unlocked);
    }

    #[test]
    fn ikkinchi_sozlash_rad_etiladi() {
        let dir = TempDir::new("twice");
        let (session, _store) = session(&dir);
        session.setup(PIN).expect("sozlansin");
        assert!(matches!(
            session.setup(PIN),
            Err(SessionError::Security(SecurityError::AlreadySetUp))
        ));
    }

    #[test]
    fn notogri_pin_hisoblanadi_va_kutish_qoyiladi() {
        let dir = TempDir::new("lockout");
        let (session, _store) = session(&dir);
        session.setup(PIN).expect("sozlansin");
        session.lock();

        let threshold = usize::try_from(LOCKOUT_THRESHOLD).expect("chegara musbat");
        for _ in 1..threshold {
            assert!(matches!(
                session.unlock(WRONG_PIN, NOW),
                Err(SessionError::Security(SecurityError::WrongPin))
            ));
        }
        assert!(matches!(
            session.unlock(WRONG_PIN, NOW),
            Err(SessionError::Security(SecurityError::LockedOut { .. }))
        ));

        // Kutish davom etayotganda to'g'ri PIN ham ochmaydi.
        assert!(matches!(
            session.unlock(PIN, NOW + 1),
            Err(SessionError::Security(SecurityError::LockedOut { .. }))
        ));
        assert!(!session.status().unlocked);
    }

    #[test]
    fn keyring_kaliti_yoqolsa_pin_yetmaydi() {
        let dir = TempDir::new("keyring-gone");
        let (session, store) = session(&dir);
        session.setup(PIN).expect("sozlansin");
        session.lock();

        store.delete().expect("o'chirilsin");
        assert!(matches!(
            session.unlock(PIN, NOW),
            Err(SessionError::Security(SecurityError::KeyUnavailable))
        ));
        assert!(!session.status().unlocked);
    }

    #[test]
    fn fokusdan_tushib_vaqt_otsa_avto_qulflanadi() {
        let dir = TempDir::new("auto-lock");
        let (session, _store) = session(&dir);
        session.setup(PIN).expect("sozlansin");

        let lost_at = Duration::from_secs(100);
        session.focus_changed_at(false, lost_at);

        session.enforce_auto_lock_at(lost_at + AUTO_LOCK_TIMEOUT - Duration::from_secs(1));
        assert!(session.status().unlocked);

        session.enforce_auto_lock_at(lost_at + AUTO_LOCK_TIMEOUT);
        assert!(!session.status().unlocked);
    }

    #[test]
    fn qaytib_kelgan_oyna_qulflanmaydi() {
        let dir = TempDir::new("refocus");
        let (session, _store) = session(&dir);
        session.setup(PIN).expect("sozlansin");

        session.focus_changed_at(false, Duration::from_secs(100));
        session.focus_changed_at(true, Duration::from_secs(200));
        session.enforce_auto_lock_at(Duration::from_secs(100_000));
        assert!(session.status().unlocked);
    }

    #[test]
    fn paths_standart_nomlarni_beradi() {
        let paths = Paths::in_dir(Path::new("/tmp/x"));
        assert!(paths.key_file.ends_with("keys.bin"));
        assert!(paths.database.ends_with("daftar.db"));
    }
}
