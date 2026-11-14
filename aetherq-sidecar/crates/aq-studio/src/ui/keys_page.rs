//! Kalitlar sahifasi: yaratish, ochiq kalit/barmoq izini ulashish, muddat holati, rotatsiya, o'chirish.

use egui::{RichText, Ui};

use crate::app::{Action, App};
use crate::keys::{self, KeyState};
use crate::theme::{self, ACCENT, AMBER, FAINT, GREEN, MUTED, RED, TEXT};
use crate::timefmt;

impl App {
    pub fn page_keys(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        theme::card(ui, |ui| {
            theme::section(ui, "Yangi kalit", "ML-DSA-65 imzo kaliti. Server va klient har biri o'z kalitiga ega bo'ladi.");
            ui.horizontal(|ui| {
                ui.label("Nomi:");
                ui.add(egui::TextEdit::singleline(&mut self.keys_ui.new_name).desired_width(220.0).hint_text("masalan, server yoki klient-pc1"));
                ui.label("Muddat:");
                ui.add(egui::DragValue::new(&mut self.keys_ui.new_days).range(1..=3650).suffix(" kun"));
                let name = self.keys_ui.new_name.trim().to_string();
                let ok = keys::valid_name(&name) && !self.keys.iter().any(|k| k.name == name);
                let b = theme::primary(ui, "+ Kalit yaratish", ok);
                let b = if ok { b } else { b.on_disabled_hover_text("Nom: lotin harflari, raqamlar, «-», «_», «.» (1–40); takrorlanmasin.") };
                if b.clicked() {
                    acts.push(Action::CreateKey(name, self.keys_ui.new_days));
                }
                if theme::secondary(ui, "📁 Papkani ochish", true).clicked() {
                    acts.push(Action::OpenFolder(self.store.keys_dir()));
                }
            });
            ui.label(
                RichText::new("Maxfiy qism (.key) faqat shu kompyuterda saqlanadi — hech kimga yubormang. Ochiq kalit (.pub) va barmoq izini ulashish xavfsiz.")
                    .size(12.0)
                    .color(FAINT),
            );
        });
        ui.add_space(10.0);

        theme::card(ui, |ui| {
            theme::section(ui, &format!("Kalitlar · {} ta", self.keys.len()), "aqctl bilan bir xil format: NAME.key, NAME.key.pub, NAME.meta.json");
            if self.keys.is_empty() {
                theme::empty_state(ui, "Kalit yo'q", "Yuqorida yangi kalit yarating yoki tez sozlash ustasidan foydalaning.");
                return;
            }
            egui::Grid::new("keys").num_columns(6).striped(true).spacing([16.0, 8.0]).show(ui, |ui| {
                for h in ["Nomi", "Barmoq izi", "Yaratilgan", "Muddati", "Ishlatilmoqda", "Amallar"] {
                    ui.label(RichText::new(h).size(12.0).color(FAINT));
                }
                ui.end_row();
                for k in &self.keys {
                    ui.label(RichText::new(&k.name).font(theme::heading(14.0)).color(TEXT));
                    ui.label(RichText::new(&k.fingerprint).monospace().color(ACCENT));
                    ui.label(RichText::new(k.created.map(|t| timefmt::local_date(t, self.engine.tz)).unwrap_or("—".into())).size(12.5).color(MUTED));
                    let (txt, col) = match (k.state(self.now), k.days_left(self.now)) {
                        (KeyState::Ok, Some(d)) => (format!("{d} kun qoldi"), GREEN),
                        (KeyState::RotateSoon, Some(d)) => (format!("{d} kun — yangilang"), AMBER),
                        (KeyState::Expired, _) => ("muddati o'tgan".to_string(), RED),
                        _ => ("muddatsiz".to_string(), FAINT),
                    };
                    theme::pill(ui, &txt, col);
                    let users: Vec<String> = self.store.cfg.profiles.iter().filter(|p| p.identity == k.name).map(|p| p.name.clone()).collect();
                    ui.add(egui::Label::new(RichText::new(if users.is_empty() { "—".into() } else { users.join(", ") }).size(12.5).color(MUTED)).truncate());
                    ui.horizontal(|ui| {
                        if theme::small(ui, "📋 Ochiq kalit", true).on_hover_text("Ochiq kalitni (hex) nusxalash").clicked() {
                            acts.push(Action::Copy(k.pub_hex(), format!("«{}» ochiq kaliti nusxalandi", k.name)));
                        }
                        if theme::small(ui, "💾 .pub", true).on_hover_text("Ochiq kalitni faylga saqlash").clicked() {
                            acts.push(Action::ExportKeyPub(k.name.clone()));
                        }
                        if theme::small(ui, "↻ Yangilash", true).on_hover_text("Rotatsiya: yangi kalit yaratib, profillarni unga o'tkazish").clicked() {
                            acts.push(Action::AskRotateKey(k.name.clone()));
                        }
                        let used = !users.is_empty();
                        let d = theme::small(ui, "🗑", !used);
                        let d = if used { d.on_disabled_hover_text("Profillarda ishlatilmoqda — avval boshqa kalit tanlang.") } else { d.on_hover_text("O'chirish") };
                        if d.clicked() {
                            acts.push(Action::AskDeleteKey(k.name.clone()));
                        }
                    });
                    ui.end_row();
                }
            });
        });
        self.acts.extend(acts);
    }
}
