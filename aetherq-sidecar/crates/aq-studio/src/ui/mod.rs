//! UI sahifalari va modal oynalar. Har bir sahifa `App` ustida alohida `impl` blokida.

pub mod dashboard;
pub mod diagnostics;
pub mod editor;
pub mod help;
pub mod keys_page;
pub mod logs;
pub mod settings;
pub mod tunnels;
pub mod wizard;

use egui::{RichText, Ui};

use crate::theme::{self, MUTED, TEXT};

/// Forma maydoni sarlavhasi va (ixtiyoriy) izohi.
pub fn field(ui: &mut Ui, title: &str, hint: &str) {
    ui.label(RichText::new(title).font(theme::heading(13.5)).color(TEXT));
    if !hint.is_empty() {
        ui.add(egui::Label::new(RichText::new(hint).size(12.0).color(MUTED)).wrap());
    }
}

/// Port maydoni (1..65535).
pub fn port_edit(ui: &mut Ui, port: &mut u16) -> egui::Response {
    ui.add(egui::DragValue::new(port).range(1..=65535).speed(1.0))
}

/// Ochiq kalit (hex) uchun barmoq izi yoki "—".
pub fn fp_of_hex(hex: &str) -> String {
    crate::model::parse_pub_hex(hex).map(|k| crate::keys::fingerprint(&k)).unwrap_or_else(|| "—".into())
}

/// Profil holati matni va rangi.
pub fn status_of(engine: &crate::engine::Engine, id: &str) -> (String, egui::Color32) {
    use crate::engine::Status;
    match engine.status(id) {
        Status::Running => ("Ishlamoqda".into(), theme::GREEN),
        Status::Starting => ("Ishga tushmoqda…".into(), theme::AMBER),
        Status::Stopped => ("To'xtagan".into(), theme::FAINT),
        Status::Failed(_) => ("Xato".into(), theme::RED),
    }
}

pub fn level_color(l: crate::engine::Level) -> egui::Color32 {
    match l {
        crate::engine::Level::Info => theme::MUTED,
        crate::engine::Level::Warn => theme::AMBER,
        crate::engine::Level::Error => theme::RED,
    }
}

/// Bir qatorli kalit-qiymat (kartochkalarda).
pub fn kv(ui: &mut Ui, k: &str, v: &str) {
    ui.horizontal(|ui| {
        ui.label(RichText::new(k).size(12.5).color(MUTED));
        ui.add(egui::Label::new(RichText::new(v).size(13.0).color(TEXT)).truncate());
    });
}
