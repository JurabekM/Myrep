//! TAMGA Studio — Tauri qobig'i. F0: faqat ilova haqida ma'lumot beradigan command.

use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct AppInfo {
    pub version: &'static str,
    pub format_version: &'static str,
}

#[tauri::command]
fn app_info() -> AppInfo {
    AppInfo {
        version: env!("CARGO_PKG_VERSION"),
        format_version: tamga_core::FORMAT_VERSION,
    }
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![app_info])
        .run(tauri::generate_context!())
        .expect("TAMGA Studio ishga tushmadi");
}
