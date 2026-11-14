//! Jurnal sahifasi: filtr (tunel, daraja, matn), avto-aylantirish, nusxalash va faylga saqlash.

use egui::{RichText, Ui};

use crate::app::{Action, App, LevelFilter};
use crate::engine::{Level, LogEntry};
use crate::theme::{self, FAINT, MUTED, TEXT};
use crate::timefmt;
use crate::ui::level_color;

pub fn matches(e: &LogEntry, profile: &Option<String>, level: LevelFilter, hide_closed: bool, needle: &str) -> bool {
    if let Some(p) = profile {
        if &e.profile != p {
            return false;
        }
    }
    let lvl_ok = match level {
        LevelFilter::All => true,
        LevelFilter::Problems => e.level != Level::Info,
        LevelFilter::Errors => e.level == Level::Error,
    };
    if !lvl_ok || (hide_closed && e.msg.starts_with("Tunel yopildi")) {
        return false;
    }
    needle.is_empty()
        || e.msg.to_lowercase().contains(needle)
        || e.source.to_lowercase().contains(needle)
        || e.hint.to_lowercase().contains(needle)
}

impl App {
    pub fn page_logs(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        let needle = self.logs_ui.search.trim().to_lowercase();
        theme::card(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                let sel = self
                    .logs_ui
                    .profile
                    .as_ref()
                    .and_then(|id| self.store.cfg.profiles.iter().find(|p| &p.id == id))
                    .map(|p| p.name.clone())
                    .unwrap_or_else(|| "Barcha manbalar".into());
                egui::ComboBox::from_id_salt("log-src").selected_text(sel).width(200.0).show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.logs_ui.profile, None, "Barcha manbalar");
                    for p in &self.store.cfg.profiles {
                        ui.selectable_value(&mut self.logs_ui.profile, Some(p.id.clone()), &p.name);
                    }
                });
                let lvl = match self.logs_ui.level {
                    LevelFilter::All => "Hamma darajalar",
                    LevelFilter::Problems => "Ogohlantirish va xatolar",
                    LevelFilter::Errors => "Faqat xatolar",
                };
                egui::ComboBox::from_id_salt("log-level").selected_text(lvl).width(200.0).show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.logs_ui.level, LevelFilter::All, "Hamma darajalar");
                    ui.selectable_value(&mut self.logs_ui.level, LevelFilter::Problems, "Ogohlantirish va xatolar");
                    ui.selectable_value(&mut self.logs_ui.level, LevelFilter::Errors, "Faqat xatolar");
                });
                ui.add(egui::TextEdit::singleline(&mut self.logs_ui.search).desired_width(220.0).hint_text("🔍 qidirish…"));
                ui.checkbox(&mut self.logs_ui.hide_closed, "Yopilishlarni yashirish");
                ui.checkbox(&mut self.logs_ui.autoscroll, "Avto-aylantirish");
            });
        });
        ui.add_space(8.0);

        let rows: Vec<&LogEntry> = self
            .engine
            .log
            .iter()
            .filter(|e| matches(e, &self.logs_ui.profile, self.logs_ui.level, self.logs_ui.hide_closed, &needle))
            .collect();
        let shown = rows.len();
        let mut clear = false;
        ui.horizontal(|ui| {
            ui.label(RichText::new(format!("{shown} ta yozuv (jami {})", self.engine.log.len())).size(12.5).color(MUTED));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if theme::small(ui, "📁 Jurnal fayllari", true).on_hover_text("Kunlik jurnal fayllari papkasi").clicked() {
                    acts.push(Action::OpenFolder(self.store.logs_dir()));
                }
                if theme::small(ui, "✖ Tozalash", !self.engine.log.is_empty()).on_hover_text("Ekrandagi jurnalni tozalash (fayllar qoladi)").clicked() {
                    clear = true;
                }
                let text: String = rows.iter().map(|e| self.engine.format_entry(e) + "\n").collect();
                if theme::small(ui, "💾 Saqlash…", shown > 0).clicked() {
                    let name = format!("aq-studio-jurnal-{}.log", timefmt::stamp(self.now, self.engine.tz));
                    if let Some(path) = rfd::FileDialog::new().set_title("Jurnalni saqlash").add_filter("Jurnal", &["log", "txt"]).set_file_name(name).save_file() {
                        match std::fs::write(&path, &text) {
                            Ok(()) => acts.push(Action::Copy(String::new(), format!("Jurnal saqlandi: {}", path.display()))),
                            Err(e) => self.toasts.push(crate::app::Toast { text: format!("Saqlanmadi: {e}"), color: theme::RED, until: std::time::Instant::now() + std::time::Duration::from_secs(5) }),
                        }
                    }
                }
                if theme::small(ui, "📋 Nusxalash", shown > 0).clicked() {
                    acts.push(Action::Copy(text, format!("{shown} ta yozuv nusxalandi")));
                }
            });
        });
        ui.add_space(4.0);

        let row_h = 24.0;
        let tz = self.engine.tz;
        let height = (ui.available_height() - 8.0).max(320.0);
        theme::card(ui, |ui| {
            if rows.is_empty() {
                theme::empty_state(ui, "Yozuv yo'q", "Filtrni o'zgartiring yoki tunellarni ishga tushiring.");
                return;
            }
            egui::ScrollArea::vertical()
                .id_salt("log-rows")
                .max_height(height)
                .auto_shrink([false, false])
                .stick_to_bottom(self.logs_ui.autoscroll)
                .show_rows(ui, row_h, rows.len(), |ui, range| {
                    for e in &rows[range] {
                        ui.horizontal(|ui| {
                            ui.set_height(row_h - 4.0);
                            ui.label(RichText::new(timefmt::local_hms(e.t, tz)).monospace().size(12.0).color(FAINT));
                            let c = level_color(e.level);
                            let (r, _) = ui.allocate_exact_size(egui::vec2(8.0, 8.0), egui::Sense::hover());
                            ui.painter().circle_filled(r.center(), 4.0, if e.level == Level::Info { theme::ACCENT_DIM } else { c });
                            ui.add_sized([150.0, row_h - 4.0], egui::Label::new(RichText::new(&e.source).size(12.5).color(MUTED)).truncate());
                            let mut text = RichText::new(&e.msg).size(12.5).color(if e.level == Level::Info { TEXT } else { c });
                            if !e.hint.is_empty() {
                                text = RichText::new(format!("{}  — 💡 {}", e.msg, e.hint)).size(12.5).color(if e.level == Level::Info { TEXT } else { c });
                            }
                            ui.add(egui::Label::new(text).truncate()).on_hover_text(if e.hint.is_empty() {
                                e.msg.clone()
                            } else {
                                format!("{}\n\n💡 {}", e.msg, e.hint)
                            });
                        });
                    }
                });
        });
        if clear {
            self.engine.clear_log();
        }
        // Action::Copy bo'sh matn bilan — faqat bildirishnoma (saqlash xabari).
        for a in acts {
            match a {
                Action::Copy(t, m) if t.is_empty() => {
                    self.toasts.push(crate::app::Toast { text: m, color: theme::GREEN, until: std::time::Instant::now() + std::time::Duration::from_secs(5) })
                }
                other => self.acts.push(other),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn e(level: Level, profile: &str, msg: &str) -> LogEntry {
        LogEntry { t: 0, level, profile: profile.into(), source: "S".into(), msg: msg.into(), hint: "izoh".into() }
    }

    #[test]
    fn filters_combine() {
        let a = e(Level::Info, "p1", "Tunel yopildi (x)");
        let b = e(Level::Warn, "p1", "Ulanish rad etildi");
        let c = e(Level::Error, "p2", "Server manziliga ulanib bo'lmadi");
        assert!(matches(&a, &None, LevelFilter::All, false, ""));
        assert!(!matches(&a, &None, LevelFilter::All, true, ""), "yopilishlar yashirilsin");
        assert!(!matches(&a, &None, LevelFilter::Problems, false, ""));
        assert!(matches(&b, &Some("p1".into()), LevelFilter::Problems, false, ""));
        assert!(!matches(&b, &Some("p2".into()), LevelFilter::All, false, ""));
        assert!(!matches(&b, &None, LevelFilter::Errors, false, ""));
        assert!(matches(&c, &None, LevelFilter::Errors, false, "ulanib"));
        assert!(matches(&c, &None, LevelFilter::All, false, "izoh"), "izoh bo'yicha ham qidiradi");
        assert!(!matches(&c, &None, LevelFilter::All, false, "yo'q-narsa"));
    }
}
