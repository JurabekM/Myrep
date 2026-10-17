//! Boshqaruv paneli: KPI, grafik, tunellar va oxirgi hodisalar.

use egui::{RichText, Ui};

use crate::app::{Action, App, Page};
use crate::engine::Level;
use crate::model::Role;
use crate::theme::{self, ACCENT, AMBER, BLUE, FAINT, GREEN, MUTED, RED, TEXT, VIOLET};
use crate::timefmt;
use crate::ui::wizard::Scenario;
use crate::ui::{level_color, status_of};

impl App {
    pub fn page_dashboard(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        if self.store.cfg.profiles.is_empty() {
            welcome(ui, &mut acts);
            self.acts.extend(acts);
            return;
        }
        let t = self.engine.totals();
        let (running, all) = (self.engine.running_count(), self.store.cfg.profiles.len());
        let w = theme::kpi_width(ui, 3);
        ui.horizontal(|ui| {
            theme::kpi(ui, w, "Ishlayotgan tunellar", &format!("{running} / {all}"), "profillardan ishlab turgani", if running > 0 { GREEN } else { FAINT });
            theme::kpi(ui, w, "Faol ulanishlar", &theme::group(t.active.unwrap_or(0)), "hozir ochiq tunellar", ACCENT);
            let res = match (t.resumed, t.total) {
                (Some(r), n) if n > 0 => format!("resumption {:.0}%", r as f64 * 100.0 / n as f64),
                _ => "muvaffaqiyatli handshake'lar".into(),
            };
            theme::kpi(ui, w, "Jami ulanishlar", &theme::group(t.total), &res, BLUE);
        });
        ui.add_space(4.0);
        ui.horizontal(|ui| {
            let (p50, p99) = (t.hs_p50.map(|v| format!("{v:.1} ms")), t.hs_p99.map(|v| format!("p99 {v:.1} ms")));
            theme::kpi(ui, w, "Handshake (p50)", p50.as_deref().unwrap_or("—"), p99.as_deref().unwrap_or("post-kvant kalit almashinuvi"), VIOLET);
            let traffic = format!("↑ {}  ↓ {}", theme::fmt_bytes(t.to_net.unwrap_or(0)), theme::fmt_bytes(t.from_net.unwrap_or(0)));
            theme::kpi(ui, w, "Shifrlangan trafik", &traffic, "tarmoqqa / tarmoqdan", TEXT);
            theme::kpi(ui, w, "Rad etilgan / xatolar", &theme::group(t.failed), "kalit, allowlist yoki tarmoq", if t.failed > 0 { AMBER } else { FAINT });
        });
        ui.add_space(10.0);

        theme::card(ui, |ui| {
            theme::section(ui, "Faollik", "Oxirgi 2 daqiqa: soniyasiga yangi ulanishlar va ochiq tunellar soni");
            let rate: Vec<f64> = self.engine.total_rate.iter().copied().collect();
            let act: Vec<f64> = self.engine.total_active.iter().copied().collect();
            theme::line_chart(ui, &[(&rate, ACCENT, "yangi ulanish/s"), (&act, VIOLET, "faol ulanish")], "soniya", 170.0);
        });
        ui.add_space(10.0);

        ui.columns(2, |cols| {
            theme::card(&mut cols[0], |ui| {
                theme::section(ui, "Tunellar", "Bir bosishda yoqish yoki o'chirish");
                for p in &self.store.cfg.profiles {
                    let (st, col) = status_of(&self.engine, &p.id);
                    let running = self.engine.is_running(&p.id);
                    ui.horizontal(|ui| {
                        let (r, _) = ui.allocate_exact_size(egui::vec2(10.0, 10.0), egui::Sense::hover());
                        ui.painter().circle_filled(r.center(), 5.0, col);
                        let name = ui.add(
                            egui::Label::new(RichText::new(&p.name).font(theme::heading(14.0)).color(TEXT)).sense(egui::Sense::click()),
                        );
                        if name.on_hover_text(format!("{} · {}", st, p.route())).clicked() {
                            acts.push(Action::Select(p.id.clone()));
                            acts.push(Action::Goto(Page::Tunnels));
                        }
                        theme::badge(ui, p.role.label(), if p.role == Role::Server { BLUE } else { VIOLET });
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if running {
                                if theme::small(ui, "■ To'xtatish", true).clicked() {
                                    acts.push(Action::Stop(p.id.clone()));
                                }
                            } else if theme::small(ui, "▶ Ishga tushirish", true).clicked() {
                                acts.push(Action::Start(p.id.clone()));
                            }
                            if let Some(l) = self.engine.live(&p.id) {
                                ui.label(RichText::new(format!("{} faol · {} jami", l.active.map(|a| a.to_string()).unwrap_or("—".into()), l.total)).size(12.0).color(MUTED));
                            }
                        });
                    });
                    ui.label(RichText::new(p.route()).size(12.0).color(FAINT).monospace());
                    ui.add_space(4.0);
                }
            });
            theme::card(&mut cols[1], |ui| {
                ui.horizontal(|ui| {
                    theme::section(ui, "Oxirgi hodisalar", "");
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Min), |ui| {
                        if theme::small(ui, "Jurnalni ochish →", true).clicked() {
                            acts.push(Action::Goto(Page::Logs));
                        }
                    });
                });
                let tz = self.engine.tz;
                let recent: Vec<_> = self.engine.log.iter().rev().take(9).collect();
                if recent.is_empty() {
                    ui.label(RichText::new("Hozircha hodisa yo'q.").color(MUTED));
                }
                for e in recent {
                    ui.horizontal(|ui| {
                        ui.label(RichText::new(timefmt::local_hms(e.t, tz)).size(11.5).color(FAINT).monospace());
                        let c = level_color(e.level);
                        ui.add(egui::Label::new(RichText::new(&e.msg).size(12.5).color(if e.level == Level::Info { TEXT } else { c })).truncate())
                            .on_hover_text(if e.hint.is_empty() { e.msg.clone() } else { format!("{}\n\n{}", e.msg, e.hint) });
                    });
                }
            });
        });
        self.acts.extend(acts);
    }
}

fn welcome(ui: &mut Ui, acts: &mut Vec<Action>) {
    theme::card_with(ui, theme::CARD, ACCENT.gamma_multiply(0.5), |ui| {
        ui.add_space(6.0);
        ui.label(RichText::new("Xush kelibsiz! Birinchi tunelni yarating").font(theme::heading(22.0)).color(TEXT));
        ui.add(
            egui::Label::new(
                RichText::new(
                    "AETHER-Q Sidecar ilovangiz kodini o'zgartirmasdan uning tarmoq trafigini post-kvant shifrlangan tunel \
                     orqali o'tkazadi: ML-KEM-768 + X25519 kalit almashinuvi va ML-DSA-65 imzo. Boshlash uchun stsenariyni tanlang:",
                )
                .color(MUTED),
            )
            .wrap(),
        );
        ui.add_space(12.0);
        ui.horizontal_wrapped(|ui| {
            if theme::primary(ui, "▶  Bitta kompyuterda sinash", true).clicked() {
                acts.push(Action::OpenWizard(Some(Scenario::Demo)));
            }
            if theme::secondary(ui, "🛡  Server: ilovamni himoyalash", true).clicked() {
                acts.push(Action::OpenWizard(Some(Scenario::Server)));
            }
            if theme::secondary(ui, "🔌  Klient: serverga ulanish", true).clicked() {
                acts.push(Action::OpenWizard(Some(Scenario::Client)));
            }
        });
        ui.add_space(8.0);
        ui.label(RichText::new("Tajribali foydalanuvchi bo'lsangiz — yuqoridagi «+ Yangi tunel» bilan qo'lda sozlang.").size(12.5).color(FAINT));
    });
    ui.add_space(12.0);
    ui.columns(3, |c| {
        for (col, (t, d, color)) in c.iter_mut().zip([
            ("1. Kalit", "Har tomon o'z ML-DSA-65 kalitiga ega. Maxfiy qismi shu kompyuterdan chiqmaydi.", ACCENT),
            ("2. Almashinuv", "Server taklif faylini yuboradi, klient ruxsat so'rovini qaytaradi — hech qanday hex yoki buyruq yo'q.", VIOLET),
            ("3. Tunel", "Ilova mahalliy portga ulanadi; sidecar trafikni shifrlab serverga uzatadi.", GREEN),
        ]) {
            theme::card(col, |ui| {
                ui.label(RichText::new(t).font(theme::heading(15.0)).color(color));
                ui.add(egui::Label::new(RichText::new(d).size(12.5).color(MUTED)).wrap());
            });
        }
    });
    let _ = RED;
}
