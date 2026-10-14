use std::io::Write;
use std::path::Path;

use crate::kdf::KdfParams;
use crate::lockout::retry_after_secs;
use crate::pin::validate_pin;
use crate::{KeyFile, SecretKey, SecretStore, SecurityError};

/// Yangi kalit to'plamini yaratadi: tasodifiy DB kaliti, keyring'ga qurilma kaliti, PIN bilan o'ralgan fayl.
///
/// Tartib: avval keyring, keyin fayl. Fayl yozilmasa, keyring'dagi yangi kalit o'chiriladi (yetim kalit qolmaydi).
/// Qaytaradigan [`SecretKey`] — bazani shifrlash uchun; chaqiruvchi uni tez orada tashlashi kerak emas,
/// lekin xotirada uzoq saqlamasligi kerak.
pub fn create_vault(
    key_file: &Path,
    pin: &str,
    store: &dyn SecretStore,
    params: KdfParams,
) -> Result<SecretKey, SecurityError> {
    validate_pin(pin)?;
    if key_file.exists() {
        return Err(SecurityError::AlreadySetUp);
    }

    let db_key = SecretKey::random()?;
    let device_key = SecretKey::random()?;
    store.write(&device_key)?;

    let written = KeyFile::wrap(&db_key, pin, &device_key, params)
        .and_then(|file| write_atomic(key_file, &file.to_bytes()));
    if let Err(error) = written {
        // Fayl yozilmadi: keyring'dagi yetim kalitni o'chiramiz.
        let _ = store.delete();
        return Err(error);
    }

    tracing::info!("kalit to'plami yaratildi");
    Ok(db_key)
}

/// PIN va keyring kaliti bilan DB kalitini ochadi. Noto'g'ri urinishlar hisoblanadi va kutish qo'yiladi.
///
/// Tartib: format → lockout → keyring → PIN. Keyring kaliti yo'q bo'lsa, PIN tekshirilmaydi
/// (va urinish hisoblanmaydi): bu tizim xatosi, foydalanuvchi xatosi emas.
pub fn open_vault(
    key_file: &Path,
    pin: &str,
    store: &dyn SecretStore,
    now_unix: i64,
) -> Result<SecretKey, SecurityError> {
    validate_pin(pin)?;
    let mut file = KeyFile::from_bytes(&read_key_file(key_file)?)?;

    if let Some(wait) = retry_after_secs(file.failed_attempts, file.last_failed_unix, now_unix) {
        return Err(SecurityError::LockedOut {
            retry_after_secs: wait,
        });
    }

    let device_key = store.read()?.ok_or(SecurityError::KeyUnavailable)?;
    match file.unwrap(pin, &device_key) {
        Ok(db_key) => {
            if file.failed_attempts != 0 {
                file.failed_attempts = 0;
                file.last_failed_unix = 0;
                write_atomic(key_file, &file.to_bytes())?;
            }
            Ok(db_key)
        }
        Err(SecurityError::WrongPin) => {
            file.failed_attempts = file.failed_attempts.saturating_add(1);
            file.last_failed_unix = now_unix;
            write_atomic(key_file, &file.to_bytes())?;
            tracing::warn!(urinishlar = file.failed_attempts, "noto'g'ri PIN");
            match retry_after_secs(file.failed_attempts, file.last_failed_unix, now_unix) {
                Some(wait) => Err(SecurityError::LockedOut {
                    retry_after_secs: wait,
                }),
                None => Err(SecurityError::WrongPin),
            }
        }
        Err(other) => Err(other),
    }
}

fn read_key_file(path: &Path) -> Result<Vec<u8>, SecurityError> {
    match std::fs::read(path) {
        Ok(bytes) => Ok(bytes),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Err(SecurityError::NotSetUp),
        Err(error) => Err(SecurityError::Io(error)),
    }
}

/// Faylni atomik yozadi: avval vaqtinchalik fayl, keyin nomini almashtirish. Uzilish bo'lsa eski fayl buzilmaydi.
fn write_atomic(path: &Path, bytes: &[u8]) -> Result<(), SecurityError> {
    let temp = path.with_extension("tmp");
    {
        let mut file = std::fs::File::create(&temp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
    }
    std::fs::rename(&temp, path)?;
    Ok(())
}
