//! Sessiya: o'rnatish, PIN bilan ochish, tiklash kodi, qulflash va avto-qulf (7.2–7.4).
//!
//! Android va desktop adapterlari bir xil `Session` dan foydalanadi; ular faqat platforma
//! sirini (`PlatformSecret`) beradi: desktop — OS keyring, Android — Keystore.
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, MutexGuard};

use baraka_domain_common::{Clock, IdGen};
use baraka_security::{KdfParams, KeyFile, Pin, PlatformSecret, RecoveryCode};
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};

use crate::{App, AppError, BootstrapInput, HouseholdDto};

const DB_FILE: &str = "baraka.db";
const KEY_FILE: &str = "keys.bin";
const DEVICE_FILE: &str = "device-id";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SessionStatus {
    /// `keys.bin` mavjud — ilova o'rnatilgan.
    pub initialized: bool,
    pub unlocked: bool,
    /// Qulflash tugaydigan vaqt (RFC 3339), agar ko'p xato urinish bo'lgan bo'lsa.
    pub locked_until: Option<String>,
}

/// O'rnatish natijasi. Tiklash kodi **faqat shu yerda bir marta** ko'rsatiladi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct SetupResult {
    pub household: HouseholdDto,
    pub recovery_code: String,
}

pub struct Session {
    dir: PathBuf,
    kdf: KdfParams,
    clock: Arc<dyn Clock>,
    ids: Arc<dyn IdGen>,
    idle_timeout: Duration,
    state: Mutex<State>,
}

struct State {
    app: Option<Arc<App>>,
    last_activity: DateTime<Utc>,
}

fn io_err(_: std::io::Error) -> AppError {
    AppError::new("IO_ERROR")
}

fn parse_pin(pin: &str) -> Result<Pin, AppError> {
    Pin::parse(pin).map_err(|e| AppError::on(e.code(), "pin"))
}

/// `keys.bin` ni atomik yozish: vaqtinchalik fayl → rename.
fn write_atomic(path: &Path, bytes: &[u8]) -> Result<(), AppError> {
    let tmp = path.with_extension("tmp");
    fs::write(&tmp, bytes).map_err(io_err)?;
    fs::rename(&tmp, path).map_err(io_err)
}

impl Session {
    /// `idle_timeout` — avto-qulf vaqti (desktop — 5 daqiqa, Android — 2 daqiqa).
    pub fn new(
        dir: &Path,
        kdf: KdfParams,
        idle_timeout: Duration,
        clock: Arc<dyn Clock>,
        ids: Arc<dyn IdGen>,
    ) -> Self {
        let now = clock.now();
        Self {
            dir: dir.to_path_buf(),
            kdf,
            clock,
            ids,
            idle_timeout,
            state: Mutex::new(State {
                app: None,
                last_activity: now,
            }),
        }
    }

    fn lock_state(&self) -> Result<MutexGuard<'_, State>, AppError> {
        self.state
            .lock()
            .map_err(|_| AppError::new("LOCK_POISONED"))
    }

    fn key_path(&self) -> PathBuf {
        self.dir.join(KEY_FILE)
    }

    fn read_keyfile(&self) -> Result<KeyFile, AppError> {
        let bytes = fs::read(self.key_path()).map_err(|_| AppError::new("NOT_INITIALIZED"))?;
        Ok(KeyFile::from_bytes(&bytes)?)
    }

    fn save_keyfile(&self, kf: &KeyFile) -> Result<(), AppError> {
        write_atomic(&self.key_path(), &kf.to_bytes()?)
    }

    fn device_id(&self) -> Result<String, AppError> {
        let path = self.dir.join(DEVICE_FILE);
        if let Ok(id) = fs::read_to_string(&path) {
            let id = id.trim().to_string();
            if !id.is_empty() {
                return Ok(id);
            }
        }
        let id = self.ids.new_id().to_string();
        write_atomic(&path, id.as_bytes())?;
        Ok(id)
    }

    fn open_app(&self, db_key: &baraka_security::DbKey) -> Result<Arc<App>, AppError> {
        let app = App::open(
            &self.dir.join(DB_FILE),
            db_key,
            &self.device_id()?,
            self.clock.clone(),
            self.ids.clone(),
        )?;
        Ok(Arc::new(app))
    }

    fn set_unlocked(&self, app: Arc<App>) -> Result<Arc<App>, AppError> {
        let mut st = self.lock_state()?;
        st.app = Some(app.clone());
        st.last_activity = self.clock.now();
        Ok(app)
    }

    fn remove_db_files(&self) {
        for suffix in ["", "-wal", "-shm"] {
            let _ = fs::remove_file(self.dir.join(format!("{DB_FILE}{suffix}")));
        }
    }

    pub fn status(&self) -> Result<SessionStatus, AppError> {
        let unlocked = self.lock_state()?.app.is_some();
        let (initialized, locked_until) = match self.read_keyfile() {
            Ok(kf) => {
                let until = kf.lockout().locked_until;
                let now = self.clock.now().timestamp();
                let shown = (until > now)
                    .then(|| DateTime::<Utc>::from_timestamp(until, 0).map(|d| d.to_rfc3339()))
                    .flatten();
                (true, shown)
            }
            Err(_) => (false, None),
        };
        Ok(SessionStatus {
            initialized,
            unlocked,
            locked_until,
        })
    }

    /// Birinchi o'rnatish: kalitlar, baza va xonadon.
    pub fn setup(
        &self,
        platform: &PlatformSecret,
        pin: &str,
        input: BootstrapInput,
    ) -> Result<SetupResult, AppError> {
        if self.key_path().exists() {
            return Err(AppError::new("ALREADY_INITIALIZED"));
        }
        fs::create_dir_all(&self.dir).map_err(io_err)?;
        let pin = parse_pin(pin)?;
        let (kf, db_key, recovery) = KeyFile::create(platform, &pin, self.kdf)?;
        // Oldingi muvaffaqiyatsiz o'rnatishdan qolgan (kalitsiz) baza fayllari.
        self.remove_db_files();
        let created = self.open_app(&db_key).and_then(|app| {
            let household = app.bootstrap(input)?;
            self.save_keyfile(&kf)?;
            Ok((app, household))
        });
        let (app, household) = match created {
            Ok(v) => v,
            Err(e) => {
                self.remove_db_files();
                return Err(e);
            }
        };
        self.set_unlocked(app)?;
        Ok(SetupResult {
            household,
            recovery_code: recovery.display_grouped().to_string(),
        })
    }

    pub fn unlock(&self, platform: &PlatformSecret, pin: &str) -> Result<HouseholdDto, AppError> {
        let pin = parse_pin(pin)?;
        let mut kf = self.read_keyfile()?;
        let result = kf.unlock_with_pin(platform, &pin, self.clock.now().timestamp());
        // Har urinishdan keyin qulflash holati saqlanadi (ilovani qayta ochish uni tozalamaydi).
        self.save_keyfile(&kf)?;
        let app = self.open_app(&result?)?;
        self.set_unlocked(app)?.household()
    }

    /// PIN unutilganda: tiklash kodi bilan ochish va yangi PIN o'rnatish.
    pub fn unlock_with_recovery(
        &self,
        platform: &PlatformSecret,
        code: &str,
        new_pin: &str,
    ) -> Result<HouseholdDto, AppError> {
        let new_pin = parse_pin(new_pin)?;
        let code = RecoveryCode::parse(code).map_err(|e| AppError::on(e.code(), "recoveryCode"))?;
        let mut kf = self.read_keyfile()?;
        let result = kf.unlock_with_recovery(platform, &code, self.clock.now().timestamp());
        self.save_keyfile(&kf)?;
        let db_key = result?;
        kf.change_pin(platform, &db_key, &new_pin)?;
        self.save_keyfile(&kf)?;
        let app = self.open_app(&db_key)?;
        self.set_unlocked(app)?.household()
    }

    /// Moliyaviy amaldan oldin PIN'ni qayta tasdiqlash (masalan, «Kelajagim»dan pul olish).
    pub fn confirm_pin(&self, platform: &PlatformSecret, pin: &str) -> Result<(), AppError> {
        let pin = parse_pin(pin)?;
        let mut kf = self.read_keyfile()?;
        let result = kf.unlock_with_pin(platform, &pin, self.clock.now().timestamp());
        self.save_keyfile(&kf)?;
        result.map(|_| ()).map_err(AppError::from)
    }

    /// Qulflash: ilova (va baza ulanishi, xotiradagi kalit) yopiladi.
    pub fn lock(&self) -> Result<(), AppError> {
        self.lock_state()?.app = None;
        Ok(())
    }

    /// Ochiq ilova. Har chaqiruv harakat vaqtini yangilaydi.
    pub fn app(&self) -> Result<Arc<App>, AppError> {
        let mut st = self.lock_state()?;
        st.last_activity = self.clock.now();
        st.app.clone().ok_or(AppError::new("LOCKED"))
    }

    /// Avto-qulf: harakatsizlik `idle_timeout` dan oshsa, qulflaydi va `true` qaytaradi.
    pub fn lock_if_idle(&self) -> Result<bool, AppError> {
        let mut st = self.lock_state()?;
        if st.app.is_some() && self.clock.now() - st.last_activity >= self.idle_timeout {
            st.app = None;
            return Ok(true);
        }
        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::NewMemberInput;
    use baraka_domain_common::{FixedClock, UuidV7Gen};

    fn input() -> BootstrapInput {
        BootstrapInput {
            household_name: "Nilufarlar".into(),
            device_name: "Noutbuk".into(),
            platform: "windows".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![NewMemberInput {
                display_name: "Nilufar".into(),
                role: "ADULT".into(),
            }],
        }
    }

    fn session(dir: &Path, clock: Arc<FixedClock>) -> Session {
        Session::new(
            dir,
            KdfParams::INSECURE_FAST_FOR_TESTS,
            Duration::minutes(5),
            clock,
            Arc::new(UuidV7Gen),
        )
    }

    #[test]
    fn full_lifecycle() {
        let dir = tempfile::tempdir().unwrap();
        let clock = Arc::new(FixedClock::new(Utc::now()));
        let platform = PlatformSecret::generate().unwrap();
        let s = session(dir.path(), clock.clone());
        assert!(!s.status().unwrap().initialized);
        assert_eq!(s.app().err().map(|e| e.code), Some("LOCKED".to_string()));

        let setup = s.setup(&platform, "112233", input()).unwrap();
        assert_eq!(setup.recovery_code.len(), 29);
        assert!(s.setup(&platform, "112233", input()).is_err());
        assert!(s.status().unwrap().unlocked);

        // Avto-qulf.
        clock.advance(Duration::minutes(4));
        assert!(!s.lock_if_idle().unwrap());
        clock.advance(Duration::minutes(5));
        assert!(s.lock_if_idle().unwrap());
        assert!(s.app().is_err());

        // Yangi jarayon (qayta ishga tushirish) — faqat PIN + platforma siri bilan ochiladi.
        drop(s);
        let s = session(dir.path(), clock.clone());
        assert!(s.status().unwrap().initialized);
        assert_eq!(
            s.unlock(&PlatformSecret::generate().unwrap(), "112233")
                .unwrap_err()
                .code,
            "WRONG_SECRET"
        );
        let h = s.unlock(&platform, "112233").unwrap();
        assert_eq!(h.name, "Nilufarlar");

        // PIN unutildi → tiklash kodi.
        s.lock().unwrap();
        s.unlock_with_recovery(&platform, &setup.recovery_code.to_lowercase(), "445566")
            .unwrap();
        s.lock().unwrap();
        assert!(s.unlock(&platform, "112233").is_err());
        assert!(s.unlock(&platform, "445566").is_ok());
        assert!(s.confirm_pin(&platform, "445566").is_ok());
    }

    #[test]
    fn failed_setup_leaves_no_orphan_database() {
        let dir = tempfile::tempdir().unwrap();
        let clock = Arc::new(FixedClock::new(Utc::now()));
        let platform = PlatformSecret::generate().unwrap();
        let s = session(dir.path(), clock);
        let mut bad = input();
        bad.members.clear(); // kamida bitta ADULT kerak
        assert_eq!(
            s.setup(&platform, "112233", bad).unwrap_err().code,
            "ADULT_REQUIRED"
        );
        assert!(!dir.path().join(DB_FILE).exists());
        assert!(!s.status().unwrap().initialized);
        assert!(s.setup(&platform, "112233", input()).is_ok());
    }

    #[test]
    fn lockout_survives_restart() {
        let dir = tempfile::tempdir().unwrap();
        let clock = Arc::new(FixedClock::new(Utc::now()));
        let platform = PlatformSecret::generate().unwrap();
        session(dir.path(), clock.clone())
            .setup(&platform, "112233", input())
            .unwrap();
        let s = session(dir.path(), clock.clone());
        for _ in 0..5 {
            let _ = s.unlock(&platform, "000000");
        }
        let s = session(dir.path(), clock.clone());
        assert!(s.status().unwrap().locked_until.is_some());
        assert_eq!(
            s.unlock(&platform, "112233").unwrap_err().code,
            "LOCKED_OUT"
        );
        clock.advance(Duration::seconds(31));
        assert!(s.unlock(&platform, "112233").is_ok());
    }
}
