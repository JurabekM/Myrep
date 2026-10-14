// Tauri build skripti: har bir command uchun aniq ruxsat (permission) generatsiya qilinadi.
// Yangi command qo'shsangiz, bu ro'yxatga va capabilities/default.json ga qo'shing (ADR, 10-bo'lim).
fn main() -> Result<(), Box<dyn std::error::Error>> {
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "get_app_info",
            "get_security_status",
            "setup_pin",
            "unlock",
            "lock",
        ]),
    ))?;
    Ok(())
}
