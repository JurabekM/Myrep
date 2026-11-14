//! Diagnostika sahifasi: tunel sinovi, manzilga ulanish, port tekshiruvi, ichki sinov serveri,
//! kripto o'z-o'zini tekshirish va tizim ma'lumoti.

use std::time::Duration;

use egui::{RichText, Ui};

use crate::app::{local_dial_addr, open_path, Action, App};
use crate::diag::{self, Task, TestServer};
use crate::model::Role;
use crate::theme::{self, ACCENT, FAINT, GREEN, MUTED, RED, TEXT};

fn result_line(ui: &mut Ui, r: &Result<String, String>) {
    match r {
        Ok(t) => ui.add(egui::Label::new(RichText::new(format!("✔ {t}")).color(GREEN)).wrap()),
        Err(e) => ui.add(egui::Label::new(RichText::new(format!("✖ {e}")).color(RED)).wrap()),
    };
}

impl App {
    pub fn page_diagnostics(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        ui.columns(2, |cols| {
            // --- Chap ustun
            let ui = &mut cols[0];
            theme::card(ui, |ui| {
                theme::section(ui, "Tunelni sinash", "Klient tuneli orqali HTTP so'rov: javob kelsa — butun zanjir ishlayapti.");
                let clients: Vec<(String, String, String)> = self
                    .store
                    .cfg
                    .profiles
                    .iter()
                    .filter(|p| p.role == Role::Client)
                    .map(|p| (p.id.clone(), p.name.clone(), p.listen.clone()))
                    .collect();
                if clients.is_empty() {
                    ui.label(RichText::new("Klient profili yo'q.").color(MUTED));
                } else {
                    if self.diag.probe_profile.as_ref().map(|id| !clients.iter().any(|c| &c.0 == id)).unwrap_or(true) {
                        self.diag.probe_profile = Some(clients[0].0.clone());
                    }
                    let cur = self.diag.probe_profile.clone().unwrap_or_default();
                    let cur_name = clients.iter().find(|c| c.0 == cur).map(|c| c.1.clone()).unwrap_or_default();
                    ui.horizontal(|ui| {
                        egui::ComboBox::from_id_salt("probe-prof").selected_text(cur_name).width(190.0).show_ui(ui, |ui| {
                            for (id, name, _) in &clients {
                                ui.selectable_value(&mut self.diag.probe_profile, Some(id.clone()), name);
                            }
                        });
                        ui.add(egui::TextEdit::singleline(&mut self.diag.probe_path).desired_width(90.0).hint_text("/"));
                        let busy = self.diag.probe_task.is_some();
                        if theme::primary(ui, if busy { "Sinalmoqda…" } else { "Sinash" }, !busy).clicked() {
                            if !self.engine.is_running(&cur) {
                                acts.push(Action::Start(cur.clone()));
                            }
                            let addr = clients.iter().find(|c| c.0 == cur).map(|c| local_dial_addr(&c.2)).unwrap_or_default();
                            let path = self.diag.probe_path.clone();
                            self.diag.probe_result = None;
                            self.diag.probe_task = Some(Task::spawn(move || {
                                // Tunel hozirgina ishga tushirilgan bo'lsa — tinglovchi tayyor bo'lishiga qisqa vaqt.
                                std::thread::sleep(Duration::from_millis(150));
                                diag::http_probe(&addr, &path)
                            }));
                        }
                    });
                    match &self.diag.probe_result {
                        Some(Ok(p)) => {
                            ui.label(RichText::new(format!("✔ {} · {:.1} ms · {} bayt", p.status_line, p.ms, p.bytes)).color(GREEN));
                            if !p.preview.is_empty() {
                                ui.add(egui::Label::new(RichText::new(p.preview.trim()).monospace().size(12.0).color(MUTED)).wrap());
                            }
                        }
                        Some(Err(e)) => {
                            ui.add(egui::Label::new(RichText::new(format!("✖ {e}")).color(RED)).wrap());
                        }
                        None => {}
                    }
                }
            });
            ui.add_space(8.0);
            theme::card(ui, |ui| {
                theme::section(ui, "Manzilga ulanish (TCP)", "Server yoki ilova ishlayaptimi va tarmoq/firewall ochiqmi — tekshiradi.");
                ui.horizontal(|ui| {
                    ui.add(egui::TextEdit::singleline(&mut self.diag.reach_addr).desired_width(220.0).hint_text("192.168.1.10:9443"));
                    let busy = self.diag.reach_task.is_some();
                    if theme::primary(ui, if busy { "Tekshirilmoqda…" } else { "Tekshirish" }, !busy).clicked() {
                        let a = self.diag.reach_addr.clone();
                        self.diag.reach_result = None;
                        self.diag.reach_task = Some(Task::spawn(move || diag::tcp_reach(&a, Duration::from_secs(5))));
                    }
                });
                if let Some(r) = &self.diag.reach_result {
                    result_line(ui, &r.as_ref().map(|ms| format!("Ulanish o'rnatildi: {ms:.2} ms")).map_err(|e| e.clone()));
                }
            });
            ui.add_space(8.0);
            theme::card(ui, |ui| {
                theme::section(ui, "Port bo'shmi?", "Tunel uchun tanlangan port boshqa dastur tomonidan band emasligini tekshiradi.");
                ui.horizontal(|ui| {
                    ui.add(egui::TextEdit::singleline(&mut self.diag.port_addr).desired_width(220.0).hint_text("0.0.0.0:9443"));
                    if theme::primary(ui, "Tekshirish", true).clicked() {
                        let a = self.diag.port_addr.clone();
                        self.diag.port_result = Some(diag::port_free(&a).map(|()| format!("{} bo'sh — ishlatish mumkin", a.trim())));
                    }
                });
                if let Some(r) = &self.diag.port_result {
                    result_line(ui, r);
                }
            });

            // --- O'ng ustun
            let ui = &mut cols[1];
            theme::card(ui, |ui| {
                theme::section(ui, "Ichki sinov serveri", "Haqiqiy ilova o'rniga: har so'rovga JSON javob beradi. Server profilining «ilova manzili» sifatida ishlating.");
                match &self.diag.test_server {
                    Some(s) => {
                        let addr = s.addr.to_string();
                        theme::pill(ui, &format!("Ishlamoqda: {addr} · {} so'rov", s.requests.load(std::sync::atomic::Ordering::Relaxed)), GREEN);
                        ui.horizontal(|ui| {
                            if theme::danger(ui, "■ To'xtatish", true).clicked() {
                                if let Some(s) = self.diag.test_server.take() {
                                    s.stop();
                                }
                            }
                            if theme::secondary(ui, "🌐 Brauzerda ochish", true).clicked() {
                                open_path(std::path::Path::new(&format!("http://{addr}/")));
                            }
                        });
                    }
                    None => {
                        ui.horizontal(|ui| {
                            ui.add(egui::TextEdit::singleline(&mut self.diag.test_addr).desired_width(200.0));
                            if theme::primary(ui, "▶ Ishga tushirish", true).clicked() {
                                match TestServer::start(&self.diag.test_addr) {
                                    Ok(s) => {
                                        self.diag.test_error = None;
                                        self.diag.test_server = Some(s);
                                    }
                                    Err(e) => self.diag.test_error = Some(e),
                                }
                            }
                        });
                        if let Some(e) = &self.diag.test_error {
                            ui.add(egui::Label::new(RichText::new(format!("✖ {e}")).color(RED)).wrap());
                        }
                    }
                }
            });
            ui.add_space(8.0);
            theme::card(ui, |ui| {
                theme::section(ui, "Kripto o'z-o'zini tekshirish", "20 ta to'liq handshake (ML-KEM-768 + X25519, ML-DSA-65, mutual auth) va record shifrlash — xotirada.");
                let busy = self.diag.crypto_task.is_some();
                ui.horizontal(|ui| {
                    if theme::primary(ui, if busy { "Bajarilmoqda…" } else { "Tekshirish" }, !busy).clicked() {
                        self.diag.crypto_result = None;
                        self.diag.crypto_task = Some(Task::spawn(|| diag::crypto_selftest(20)));
                    }
                });
                if let Some(r) = &self.diag.crypto_result {
                    result_line(ui, &r.as_ref().map(|ms| format!("Kriptografiya to'g'ri ishlayapti · {ms:.2} ms / handshake")).map_err(|e| e.clone()));
                }
            });
            ui.add_space(8.0);
            theme::card(ui, |ui| {
                theme::section(ui, "Tizim", "");
                crate::ui::kv(ui, "Kompyuter:", &diag::hostname());
                crate::ui::kv(ui, "Asosiy IP:", self.diag.primary_ip.as_deref().unwrap_or("aniqlanmadi"));
                crate::ui::kv(ui, "Ma'lumot papkasi:", &self.store.root.display().to_string());
                let aq = self.aqctl.as_ref().map(|p| p.display().to_string()).unwrap_or_else(|| "topilmadi (standart rejim ishlamaydi)".into());
                crate::ui::kv(ui, "aqctl.exe:", &aq);
                ui.add_space(4.0);
                ui.label(
                    RichText::new("Boshqa kompyuterlar serverga ulana olmasa: Windows Firewall'da tunel portiga kirish ruxsatini tekshiring.")
                        .size(12.0)
                        .color(FAINT),
                );
                let _ = (ACCENT, TEXT);
            });
        });
        self.acts.extend(acts);
    }
}
