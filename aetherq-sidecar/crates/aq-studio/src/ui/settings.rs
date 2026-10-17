//! Sozlamalar sahifasi. O'zgarish darhol qo'llanadi va saqlanadi.

use egui::{RichText, Ui};

use crate::app::{Action, App};
use crate::model::Settings;
use crate::theme::{self, ACCENT, FAINT, GREEN, MUTED, RED, TEXT};

impl App {
    pub fn page_settings(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        let before = self.store.cfg.settings.clone();
        theme::card(ui, |ui| {
            theme::section(ui, "Ishga tushirish va yopish", "");
            let s = &mut self.store.cfg.settings;
            ui.checkbox(&mut s.autostart_enabled, "Dastur ochilganda «avto-start» belgilangan tunellarni ishga tushirish");
            ui.checkbox(&mut s.confirm_exit, "Tunellar ishlab turganda oynani yopishdan oldin so'rash");
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Kalitlar va jurnal", "");
            let s = &mut self.store.cfg.settings;
            ui.horizontal(|ui| {
                ui.label("Yangi kalitlar muddati:");
                ui.add(egui::DragValue::new(&mut s.key_days).range(1..=3650).suffix(" kun"));
                ui.label(RichText::new("muddatdan 14 kun oldin «yangilang» ogohlantirishi chiqadi").size(12.0).color(FAINT));
            });
            ui.horizontal(|ui| {
                ui.label("Ekrandagi jurnal hajmi:");
                ui.add(egui::DragValue::new(&mut s.log_cap).range(500..=50_000).speed(100.0).suffix(" qator"));
            });
            ui.checkbox(&mut s.log_to_file, "Jurnalni kunlik faylga ham yozish (logs\\studio-YYYYMMDD.log)");
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Standart PQ-TLS rejimi (aqctl.exe)", "Standart rejimdagi tunellar aqctl gateway jarayoni orqali ishlaydi.");
            match &self.aqctl {
                Some(p) => ui.label(RichText::new(format!("✔ Topildi: {}", p.display())).color(GREEN)),
                None => ui.label(RichText::new("✖ aqctl.exe topilmadi — standart rejim o'chiq.").color(RED)),
            };
            ui.horizontal(|ui| {
                ui.add(
                    egui::TextEdit::singleline(&mut self.store.cfg.settings.aqctl_path)
                        .desired_width(420.0)
                        .hint_text("bo'sh — dastur papkasidan avtomatik"),
                );
                if theme::small(ui, "Tanlash…", true).clicked() {
                    if let Some(p) = rfd::FileDialog::new().set_title("aqctl.exe ni tanlang").add_filter("Dastur", &["exe"]).pick_file() {
                        self.store.cfg.settings.aqctl_path = p.display().to_string();
                    }
                }
                if theme::small(ui, "Avtomatik", !self.store.cfg.settings.aqctl_path.is_empty()).clicked() {
                    self.store.cfg.settings.aqctl_path.clear();
                }
            });
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Ma'lumot papkasi", "Profillar (config.json), kalitlar (keys\\), jurnal (logs\\).");
            ui.label(RichText::new(self.store.root.display().to_string()).monospace().color(TEXT));
            ui.horizontal(|ui| {
                if theme::secondary(ui, "📁 Papkani ochish", true).clicked() {
                    acts.push(Action::OpenFolder(self.store.root.clone()));
                }
                if theme::secondary(ui, "↺ Standart sozlamalar", self.store.cfg.settings != Settings::default())
                    .on_hover_text("Faqat sozlamalar tiklanadi — profillar va kalitlar o'zgarmaydi")
                    .clicked()
                {
                    self.store.cfg.settings = Settings::default();
                }
            });
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Dastur haqida", "");
            ui.label(RichText::new(format!("AETHER-Q Sidecar Studio v{}", env!("CARGO_PKG_VERSION"))).font(theme::heading(15.0)).color(ACCENT));
            ui.label(
                RichText::new(format!(
                    "Protokol: AETHER-Q v5.1 ({:#06x}) · kalit almashinuvi ML-KEM-768 + X25519 · imzo ML-DSA-65 · transport ChaCha20-Poly1305",
                    aq_core::PROTOCOL_VERSION
                ))
                .size(12.5)
                .color(MUTED),
            );
            ui.label(
                RichText::new("Eslatma: protokol va dastur mustaqil xavfsizlik auditidan o'tmagan — ishlab chiqarishdan oldin audit tavsiya etiladi.")
                    .size(12.0)
                    .color(FAINT),
            );
        });

        if self.store.cfg.settings != before {
            let s = self.store.cfg.settings.clone();
            self.engine.set_log_options(s.log_cap, s.log_to_file);
            self.aqctl = self.store.aqctl();
            match self.store.save() {
                Ok(()) => {
                    if s.aqctl_path != before.aqctl_path || s == Settings::default() {
                        self.toast("Sozlamalar saqlandi", GREEN);
                    }
                }
                Err(e) => self.toast(e, RED),
            }
        }
        self.acts.extend(acts);
    }
}
