//! IPC chegarasi: frontend faqat shu yerdagi commandlarni chaqiradi.
//! Qoida: command ichida biznes mantiq yo'q — validatsiya → domen/storage → DTO (DESKTOP_PROMPT.md 3.2).

use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use security::SecurityError;
use serde::Serialize;
use specta::Type;
use tauri::{AppHandle, State};
use tracing::error;

use crate::session::{Session, SessionError};

/// «Ilova haqida» DTO. Frontendga camelCase maydon nomlari bilan yetib boradi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AppInfo {
    /// Mahsulot nomi (tauri.conf.json → productName).
    pub name: String,
    /// Ilova versiyasi (tauri.conf.json → version).
    pub version: String,
    /// Operatsion tizim: "windows", "macos" yoki "linux".
    pub platform: String,
    /// Protsessor arxitekturasi: "x86_64" yoki "aarch64".
    pub arch: String,
    /// Yig'ish turi: "debug" yoki "release".
    pub build_profile: String,
}

/// Xavfsizlik holati DTO: PIN o'rnatilganmi va baza ochiqmi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct SecurityStatus {
    /// PIN o'rnatilganmi. `false` bo'lsa, birinchi ishga tushirishda sozlash ekrani ko'rsatiladi.
    pub set_up: bool,
    /// Baza ochiqmi. `false` bo'lsa, qulflash ekrani ko'rsatiladi.
    pub unlocked: bool,
}

/// Commandlar xatosi. `code` frontendda tarjima kalitiga aylanadi; PIN yoki kalit qiymati yo'q.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(tag = "code", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ApiError {
    /// PIN 6 ta raqamdan iborat emas.
    InvalidPin,
    /// PIN noto'g'ri.
    WrongPin,
    /// Juda ko'p noto'g'ri urinish: kutish davom etmoqda.
    LockedOut {
        /// Qolgan kutish vaqti (soniyalarda). `u32`: TypeScript'da `bigint` bo'lmasligi uchun
        /// (kutish eng ko'pi bilan bir soat, sig'adi).
        #[serde(rename = "retryAfterSeconds")]
        retry_after_seconds: u32,
    },
    /// PIN allaqachon o'rnatilgan.
    AlreadySetUp,
    /// PIN hali o'rnatilmagan.
    NotSetUp,
    /// Qurilma kaliti OS keyring'ida yo'q yoki bu bazaga mos emas.
    KeyUnavailable,
    /// Kutilmagan ichki xato (batafsil log'da, foydalanuvchiga umumiy xabar).
    Internal,
}

impl From<SessionError> for ApiError {
    fn from(error: SessionError) -> Self {
        match error {
            SessionError::Security(SecurityError::InvalidPin) => Self::InvalidPin,
            SessionError::Security(SecurityError::WrongPin) => Self::WrongPin,
            SessionError::Security(SecurityError::LockedOut { retry_after_secs }) => {
                Self::LockedOut {
                    retry_after_seconds: u32::try_from(retry_after_secs).unwrap_or(u32::MAX),
                }
            }
            SessionError::Security(SecurityError::AlreadySetUp) => Self::AlreadySetUp,
            SessionError::Security(SecurityError::NotSetUp) => Self::NotSetUp,
            SessionError::Security(
                SecurityError::KeyUnavailable | SecurityError::KeyringMismatch,
            ) => Self::KeyUnavailable,
            other => {
                error!(xato = %other, "xavfsizlik yoki baza amali bajarilmadi");
                Self::Internal
            }
        }
    }
}

/// Ilova ma'lumotini qaytaradi. Disk yoki tarmoqqa murojaat qilmaydi.
#[tauri::command]
#[specta::specta]
pub fn get_app_info(app: AppHandle) -> AppInfo {
    let package = app.package_info();
    build_app_info(
        &package.name,
        &package.version.to_string(),
        std::env::consts::OS,
        std::env::consts::ARCH,
        build_profile(cfg!(debug_assertions)),
    )
}

/// Joriy xavfsizlik holati.
#[tauri::command]
#[specta::specta]
pub async fn get_security_status(
    session: State<'_, Arc<Session>>,
) -> Result<SecurityStatus, ApiError> {
    let session = session.inner().clone();
    let status = run_blocking(move || Ok(session.status())).await?;
    Ok(SecurityStatus {
        set_up: status.set_up,
        unlocked: status.unlocked,
    })
}

/// Birinchi marta PIN o'rnatadi (6 raqam) va bazani ochadi.
#[tauri::command]
#[specta::specta]
pub async fn setup_pin(session: State<'_, Arc<Session>>, pin: String) -> Result<(), ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.setup(&pin)).await
}

/// PIN bilan bazani ochadi.
#[tauri::command]
#[specta::specta]
pub async fn unlock(session: State<'_, Arc<Session>>, pin: String) -> Result<(), ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.unlock(&pin, now_unix())).await
}

/// Bazani darhol qulflaydi.
#[tauri::command]
#[specta::specta]
pub async fn lock(session: State<'_, Arc<Session>>) -> Result<(), ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.lock();
        Ok(())
    })
    .await
}

/// Og'ir amalni (Argon2id, disk, keyring) UI oqimidan tashqarida bajaradi.
async fn run_blocking<T, F>(work: F) -> Result<T, ApiError>
where
    F: FnOnce() -> Result<T, SessionError> + Send + 'static,
    T: Send + 'static,
{
    let outcome = tauri::async_runtime::spawn_blocking(work)
        .await
        .map_err(|join_error| {
            error!(xato = %join_error, "fon vazifa to'xtadi");
            ApiError::Internal
        })?;
    outcome.map_err(ApiError::from)
}

/// Joriy vaqt, Unix soniyalarida (lockout hisobi uchun).
fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .and_then(|elapsed| i64::try_from(elapsed.as_secs()).ok())
        .unwrap_or(0)
}

/// DTO'ni yig'adi. AppHandle'dan ajratilgan — shu sababli testlash oson.
fn build_app_info(
    name: &str,
    version: &str,
    platform: &str,
    arch: &str,
    build_profile: &str,
) -> AppInfo {
    AppInfo {
        name: name.to_owned(),
        version: version.to_owned(),
        platform: platform.to_owned(),
        arch: arch.to_owned(),
        build_profile: build_profile.to_owned(),
    }
}

fn build_profile(debug: bool) -> &'static str {
    if debug { "debug" } else { "release" }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_info_camel_case_json_qaytaradi() {
        let info = build_app_info("Baraka Daftari", "0.1.0", "windows", "x86_64", "release");
        let json = serde_json::to_value(&info).expect("AppInfo JSON ga o'tkazilishi kerak");

        assert_eq!(json["buildProfile"], "release");
        assert_eq!(json["name"], "Baraka Daftari");
        assert_eq!(json["version"], "0.1.0");
    }

    #[test]
    fn build_profile_belgilari_togri() {
        assert_eq!(build_profile(true), "debug");
        assert_eq!(build_profile(false), "release");
    }

    #[test]
    fn xato_json_shakli_frontend_kutganidek() {
        let locked = serde_json::to_value(ApiError::LockedOut {
            retry_after_seconds: 30,
        })
        .expect("JSON");
        assert_eq!(locked["code"], "LOCKED_OUT");
        assert_eq!(locked["retryAfterSeconds"], 30);

        let wrong = serde_json::to_value(ApiError::WrongPin).expect("JSON");
        assert_eq!(wrong["code"], "WRONG_PIN");
    }

    #[test]
    fn xato_xaritalash_sir_qiymatsiz_va_tog_ri() {
        assert_eq!(
            ApiError::from(SessionError::Security(SecurityError::KeyringMismatch)),
            ApiError::KeyUnavailable
        );
        assert_eq!(
            ApiError::from(SessionError::Security(SecurityError::LockedOut {
                retry_after_secs: 60
            })),
            ApiError::LockedOut {
                retry_after_seconds: 60
            }
        );
        assert_eq!(
            ApiError::from(SessionError::Security(SecurityError::Crypto)),
            ApiError::Internal
        );
    }
}
