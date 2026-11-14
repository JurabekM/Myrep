//! AETHER-Q Sidecar Studio — sidecar tunellarini sozlash va boshqarish uchun grafik dastur.
//!
//! AETHER-Q tunellari shu jarayon ichida ishlaydi (`aq_sidecar::runtime`); standart PQ-TLS rejimi uchun
//! `aqctl gateway` bola jarayoni ishga tushiriladi. Sozlamalar va kalitlar: `%APPDATA%\AETHER-Q\Studio`
//! (sinov uchun `AQ_STUDIO_HOME` bilan almashtiriladi).

// Windows'da konsol oynasi ochilmasin (release).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod diag;
mod engine;
mod gateway;
mod icons;
mod keys;
mod model;
mod store;
mod theme;
mod timefmt;
mod ui;

#[cfg(test)]
mod tests_ui;

fn icon() -> Option<egui::IconData> {
    let img = image::load_from_memory(include_bytes!("../assets/icon-256.png")).ok()?.into_rgba8();
    let (w, h) = img.dimensions();
    Some(egui::IconData { rgba: img.into_raw(), width: w, height: h })
}

fn main() -> eframe::Result<()> {
    if std::env::args().nth(1).as_deref() == Some("--version") {
        // Release exe konsolsiz (windows subsystem): chiqish ko'rinishi uchun chaqirgan konsolga ulanamiz.
        #[cfg(windows)]
        // SAFETY: argumentsiz Win32 chaqiruvi; konsol bo'lmasa shunchaki 0 qaytaradi.
        unsafe {
            windows_sys::Win32::System::Console::AttachConsole(windows_sys::Win32::System::Console::ATTACH_PARENT_PROCESS);
        }
        println!("aq-studio {}", env!("CARGO_PKG_VERSION"));
        return Ok(());
    }
    let mut viewport = egui::ViewportBuilder::default()
        .with_title("AETHER-Q Sidecar Studio")
        .with_app_id("aetherq-sidecar-studio")
        // 125% masshtabli 1920×1080 ekranning ish maydoni 1536×824 (mantiqiy) — oyna sarlavhasi bilan sig'sin.
        .with_inner_size([1280.0, 720.0])
        .with_min_inner_size([1000.0, 600.0]);
    if let Some(i) = icon() {
        viewport = viewport.with_icon(i);
    }
    // Markazda ochiladi: Windows o'zi tanlagan pog'onali joyda oyna pastki qismi vazifalar paneli ostida qolardi.
    let options = eframe::NativeOptions { viewport, centered: true, ..Default::default() };
    let root = store::default_root();
    eframe::run_native(
        "AETHER-Q Sidecar Studio",
        options,
        Box::new(move |cc| {
            theme::install_fonts(&cc.egui_ctx);
            theme::apply(&cc.egui_ctx);
            Ok(Box::new(app::App::new(root)))
        }),
    )
}
