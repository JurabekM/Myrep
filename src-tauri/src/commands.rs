//! IPC chegarasi: frontend faqat shu yerdagi commandlarni chaqiradi.
//! Qoida: command ichida biznes mantiq yo'q — validatsiya → domen/storage → DTO (DESKTOP_PROMPT.md 3.2).

use serde::Serialize;
use specta::Type;
use tauri::AppHandle;

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
}
