//! Platforma siri: OS keyring (Windows Credential Manager / macOS Keychain / Secret Service).
//!
//! Faqat debug build'da va `BARAKA_INSECURE_DEV_SECRET=1` bo'lganda — keyring'siz
//! (masalan, headless Linux) ishlab chiqish uchun fayl ishlatiladi. Release'da bu yo'l yo'q.
use std::path::{Path, PathBuf};

use baraka_app::{AppError, PlatformSecret};

const SERVICE: &str = "uz.barakaoilasi.desktop";
const ACCOUNT: &str = "platform-secret";

pub struct SecretStore {
    dev_file: Option<PathBuf>,
}

fn unavailable() -> AppError {
    AppError::new("PLATFORM_SECRET_UNAVAILABLE")
}

impl SecretStore {
    pub fn new(data_dir: &Path) -> Self {
        let dev = cfg!(debug_assertions)
            && std::env::var("BARAKA_INSECURE_DEV_SECRET").as_deref() == Ok("1");
        Self {
            dev_file: dev.then(|| data_dir.join("dev-platform-secret.bin")),
        }
    }

    /// Mavjud sirni o'qish (ochish uchun).
    pub fn load(&self) -> Result<PlatformSecret, AppError> {
        if let Some(path) = &self.dev_file {
            let bytes =
                std::fs::read(path).map_err(|_| AppError::new("PLATFORM_SECRET_MISSING"))?;
            return PlatformSecret::from_slice(&bytes).map_err(AppError::from);
        }
        let entry = keyring::Entry::new(SERVICE, ACCOUNT).map_err(|_| unavailable())?;
        match entry.get_secret() {
            Ok(bytes) => PlatformSecret::from_slice(&bytes).map_err(AppError::from),
            Err(keyring::Error::NoEntry) => Err(AppError::new("PLATFORM_SECRET_MISSING")),
            Err(_) => Err(unavailable()),
        }
    }

    /// Yangi o'rnatish: yangi sir yaratiladi va saqlanadi (eski o'rnatishdan qolgani almashtiriladi).
    pub fn create(&self) -> Result<PlatformSecret, AppError> {
        let secret = PlatformSecret::generate()?;
        if let Some(path) = &self.dev_file {
            if let Some(dir) = path.parent() {
                std::fs::create_dir_all(dir).map_err(|_| unavailable())?;
            }
            std::fs::write(path, secret.as_bytes()).map_err(|_| unavailable())?;
            return Ok(secret);
        }
        keyring::Entry::new(SERVICE, ACCOUNT)
            .and_then(|e| e.set_secret(secret.as_bytes()))
            .map_err(|_| unavailable())?;
        Ok(secret)
    }
}
