//! Tunellar sahifasi: chapda profillar ro'yxati, o'ngda tanlangan profil tafsiloti (statistika, kalit
//! almashinuvi, allowlist, CLI ekvivalenti, hodisalar).

use std::path::Path;

use egui::{RichText, Ui};

use crate::app::{local_dial_addr, Action, App};
use crate::engine::Status;
use crate::model::{Mode, Profile, Role};
use crate::theme::{self, ACCENT, AMBER, BLUE, BORDER, CARD, FAINT, GREEN, MUTED, RED, TEXT, VIOLET};
use crate::timefmt;
use crate::ui::{fp_of_hex, level_color, status_of};

/// Profilning CLI ekvivalenti (bir xil sozlamalar bilan qo'lda ishga tushirish uchun).
pub fn cli_command(p: &Profile, keys_dir: &Path) -> String {
    let key = |n: &str| format!("\"{}\"", keys_dir.join(format!("{n}.key")).display());
    let mut c = match (p.mode, p.role) {
        (Mode::AetherQ, Role::Server) => format!("aq-sidecar.exe serve --listen {} --upstream {} --identity {}", p.listen, p.target, key(&p.identity)),
        (Mode::AetherQ, Role::Client) => format!("aq-sidecar.exe connect --listen {} --peer {} --server-pub {}", p.listen, p.target, p.server_pub.trim()),
        (Mode::Standard, Role::Server) => format!("aqctl.exe gateway serve --listen {} --upstream {} --identity {}", p.listen, p.target, key(&p.identity)),
        (Mode::Standard, Role::Client) => format!("aqctl.exe gateway connect --listen {} --peer {} --server-pub {}", p.listen, p.target, p.server_pub.trim()),
    };
    match p.role {
        Role::Server => {
            if p.require_client_auth {
                c.push_str(" --require-client-auth --allow allow.txt");
            }
            if p.mode == Mode::AetherQ {
                if !p.resumption {
                    c.push_str(" --no-resume");
                }
                if p.pow > 0 {
                    c.push_str(&format!(" --pow {}", p.pow));
                }
            }
        }
        Role::Client => {
            if !p.identity.is_empty() {
                c.push_str(&format!(" --identity {}", key(&p.identity)));
            }
            if p.mode == Mode::AetherQ && p.resumption {
                c.push_str(" --resume");
            }
        }
    }
    c
}

impl App {
    pub fn page_tunnels(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        if self.store.cfg.profiles.is_empty() {
            theme::card(ui, |ui| {
                theme::empty_state(ui, "Hali tunel yo'q", "«Tez sozlash ustasi» bilan 1 daqiqada yarating yoki «+ Yangi tunel» bilan qo'lda sozlang.");
                ui.vertical_centered(|ui| {
                    if theme::primary(ui, "✨ Tez sozlash ustasini ochish", true).clicked() {
                        acts.push(Action::OpenWizard(None));
                    }
                });
            });
            self.acts.extend(acts);
            return;
        }
        if self.selected.as_ref().map(|s| self.profile(s).is_none()).unwrap_or(true) {
            self.selected = self.store.cfg.profiles.first().map(|p| p.id.clone());
        }
        let selected = self.selected.clone().unwrap_or_default();
        let total_w = ui.available_width();
        let list_w = (total_w * 0.36).clamp(300.0, 400.0);
        ui.horizontal_top(|ui| {
            ui.allocate_ui_with_layout(egui::vec2(list_w, 0.0), egui::Layout::top_down(egui::Align::Min), |ui| {
                ui.set_width(list_w);
                for p in &self.store.cfg.profiles {
                    profile_card(ui, self, p, p.id == selected, &mut acts);
                    ui.add_space(6.0);
                }
                ui.horizontal(|ui| {
                    if theme::small(ui, "+ Server", true).on_hover_text("Ilovani himoyalovchi server profili").clicked() {
                        acts.push(Action::NewProfile(Role::Server));
                    }
                    if theme::small(ui, "+ Klient", true).on_hover_text("Serverga ulanuvchi klient profili").clicked() {
                        acts.push(Action::NewProfile(Role::Client));
                    }
                });
            });
            ui.add_space(8.0);
            ui.vertical(|ui| {
                ui.set_width(ui.available_width());
                if let Some(p) = self.profile(&selected).cloned() {
                    self.detail(ui, &p, &mut acts);
                }
            });
        });
        self.acts.extend(acts);
    }

    fn detail(&mut self, ui: &mut Ui, p: &Profile, acts: &mut Vec<Action>) {
        let running = self.engine.is_running(&p.id);
        let (st, col) = status_of(&self.engine, &p.id);
        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label(RichText::new(&p.name).font(theme::heading(19.0)).color(TEXT));
                theme::pill(ui, &st, col);
            });
            ui.horizontal(|ui| {
                theme::badge(ui, p.role.label(), if p.role == Role::Server { BLUE } else { VIOLET });
                theme::badge(ui, p.mode.label(), ACCENT);
                if p.autostart {
                    theme::badge(ui, "avto-start", FAINT);
                }
            });
            ui.add_space(4.0);
            let route = match p.role {
                Role::Server => format!("Tarmoqdan {} → ilova {}", p.listen, p.target),
                Role::Client => format!("Ilovangiz {} → tunel → server {}", local_dial_addr(&p.listen), p.target),
            };
            ui.label(RichText::new(route).color(MUTED));
            ui.add_space(6.0);
            ui.horizontal_wrapped(|ui| {
                if running {
                    if theme::danger(ui, "■ To'xtatish", true).clicked() {
                        acts.push(Action::Stop(p.id.clone()));
                    }
                } else if theme::primary(ui, "▶ Ishga tushirish", true).clicked() {
                    acts.push(Action::Start(p.id.clone()));
                }
                if theme::secondary(ui, "✏ Tahrirlash", true).clicked() {
                    acts.push(Action::Edit(p.id.clone()));
                }
                if p.role == Role::Client && theme::secondary(ui, "🔎 Sinash", true).on_hover_text("Tunel orqali GET / so'rovi").clicked() {
                    acts.push(Action::Test(p.id.clone()));
                }
                if theme::secondary(ui, "Nusxa olish", true).on_hover_text("Profil nusxasi (port +1)").clicked() {
                    acts.push(Action::Duplicate(p.id.clone()));
                }
                if theme::secondary(ui, "🗑 O'chirish", true).clicked() {
                    acts.push(Action::AskDelete(p.id.clone()));
                }
            });
            if let Status::Failed(e) = self.engine.status(&p.id) {
                ui.add(egui::Label::new(RichText::new(format!("✖ {e}")).color(RED)).wrap());
            }
            if let Some((m, h)) = self.engine.last_error.get(&p.id) {
                ui.add(egui::Label::new(RichText::new(format!("Oxirgi muammo: {m}")).size(12.5).color(AMBER)).wrap());
                if !h.is_empty() {
                    ui.add(egui::Label::new(RichText::new(format!("💡 {h}")).size(12.5).color(TEXT)).wrap());
                }
            }
            if let Some((_, r)) = self.probe_results.iter().find(|(id, _)| id == &p.id) {
                match r {
                    Ok(pr) => ui.label(RichText::new(format!("✔ Oxirgi sinov: {} · {:.1} ms", pr.status_line, pr.ms)).size(12.5).color(GREEN)),
                    Err(e) => ui.add(egui::Label::new(RichText::new(format!("✖ Oxirgi sinov: {e}")).size(12.5).color(RED)).wrap()),
                };
            }
            if self.probes.iter().any(|(id, _)| id == &p.id) {
                ui.label(RichText::new("Sinalmoqda…").size(12.5).color(MUTED));
            }
        });
        ui.add_space(8.0);

        if let Some(l) = self.engine.live(&p.id) {
            let w = theme::kpi_width(ui, 4);
            ui.horizontal(|ui| {
                theme::kpi(ui, w, "Faol", &l.active.map(|a| a.to_string()).unwrap_or("—".into()), "ochiq tunellar", ACCENT);
                theme::kpi(ui, w, "Jami", &theme::group(l.total), &l.resumed.map(|r| format!("{r} resumption")).unwrap_or_default(), BLUE);
                theme::kpi(
                    ui,
                    w,
                    "Handshake",
                    &l.hs_p50.map(|v| format!("{v:.1} ms")).unwrap_or("—".into()),
                    &l.hs_p99.map(|v| format!("p99 {v:.1} ms")).unwrap_or("o'rtacha".into()),
                    VIOLET,
                );
                theme::kpi(ui, w, "Rad / xato", &l.failed.to_string(), &l.uptime.map(|u| format!("ishlamoqda {}", theme::fmt_duration(u.as_secs()))).unwrap_or_default(), if l.failed > 0 { AMBER } else { FAINT });
            });
            ui.add_space(4.0);
            theme::card(ui, |ui| {
                let traffic = match (l.to_net, l.from_net) {
                    (Some(a), Some(b)) => format!("Trafik: ↑ {} tarmoqqa · ↓ {} tarmoqdan", theme::fmt_bytes(a), theme::fmt_bytes(b)),
                    _ => "Trafik: bu rejimda klient tomonida o'lchanmaydi".into(),
                };
                ui.label(RichText::new(traffic).size(12.5).color(MUTED));
                let rate: Vec<f64> = self.engine.rate.get(&p.id).map(|q| q.iter().copied().collect()).unwrap_or_default();
                let act: Vec<f64> = self.engine.active.get(&p.id).map(|q| q.iter().copied().collect()).unwrap_or_default();
                theme::line_chart(ui, &[(&rate, ACCENT, "yangi ulanish/s"), (&act, VIOLET, "faol")], "soniya", 130.0);
            });
            ui.add_space(8.0);
        }

        match p.role {
            Role::Server => self.server_exchange(ui, p, acts),
            Role::Client => self.client_exchange(ui, p, acts),
        }
        ui.add_space(8.0);

        theme::card(ui, |ui| {
            theme::section(ui, "Buyruq qatori ekvivalenti", "Xuddi shu tunelni GUI'siz (masalan, server xizmati sifatida) ishga tushirish uchun.");
            let cmd = cli_command(p, &self.store.keys_dir());
            ui.add(egui::Label::new(RichText::new(&cmd).monospace().size(12.0).color(TEXT)).wrap());
            if theme::small(ui, "📋 Buyruqni nusxalash", true).clicked() {
                acts.push(Action::Copy(cmd, "Buyruq nusxalandi".into()));
            }
        });
        ui.add_space(8.0);

        theme::card(ui, |ui| {
            theme::section(ui, "Shu tunel hodisalari", "");
            let tz = self.engine.tz;
            let mine: Vec<_> = self.engine.log.iter().rev().filter(|e| e.profile == p.id).take(12).collect();
            if mine.is_empty() {
                ui.label(RichText::new("Hodisa yo'q. Tunelni ishga tushiring.").color(MUTED));
            }
            for e in mine {
                ui.horizontal(|ui| {
                    ui.label(RichText::new(timefmt::local_hms(e.t, tz)).monospace().size(11.5).color(FAINT));
                    ui.add(egui::Label::new(RichText::new(&e.msg).size(12.5).color(if e.level == crate::engine::Level::Info { TEXT } else { level_color(e.level) })).truncate())
                        .on_hover_text(if e.hint.is_empty() { e.msg.clone() } else { format!("{}\n\n{}", e.msg, e.hint) });
                });
            }
        });
    }

    fn server_exchange(&mut self, ui: &mut Ui, p: &Profile, acts: &mut Vec<Action>) {
        theme::card(ui, |ui| {
            theme::section(ui, "Klientlarga taklif", "Taklif fayli server manzili va ochiq kalitini o'z ichiga oladi — klient uni import qiladi.");
            if let Some(k) = self.key(&p.identity) {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("Server kaliti:").size(12.5).color(MUTED));
                    ui.label(RichText::new(format!("{} · {}", k.name, k.fingerprint)).monospace().color(ACCENT));
                });
            }
            ui.horizontal(|ui| {
                if theme::secondary(ui, "💾 Taklif faylini saqlash…", true).clicked() {
                    acts.push(Action::SaveInvite(p.id.clone()));
                }
                if theme::secondary(ui, "📋 Taklifni nusxalash", true).clicked() {
                    acts.push(Action::CopyInvite(p.id.clone()));
                }
            });
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            let sub = if p.require_client_auth {
                "Faqat shu ro'yxatdagi klientlar ulana oladi. Klient yuborgan ruxsat so'rovini import qiling."
            } else {
                "Klient kaliti talab qilinmaydi (tahrirlashda yoqing) — ro'yxat hozir ishlatilmaydi."
            };
            theme::section(ui, &format!("Allowlist · {} ta klient", p.allow.len()), sub);
            if p.allow.is_empty() {
                ui.label(RichText::new("Hozircha hech kim qo'shilmagan.").color(FAINT));
            } else {
                egui::Grid::new(("allow", &p.id)).num_columns(4).striped(true).spacing([14.0, 6.0]).show(ui, |ui| {
                    for h in ["Nomi", "Barmoq izi", "Qo'shilgan", ""] {
                        ui.label(RichText::new(h).size(12.0).color(FAINT));
                    }
                    ui.end_row();
                    for (i, a) in p.allow.iter().enumerate() {
                        ui.label(RichText::new(&a.label).color(TEXT));
                        ui.label(RichText::new(fp_of_hex(&a.pub_hex)).monospace().color(ACCENT));
                        let added = crate::timefmt::parse_rfc3339(&a.added).map(|t| timefmt::local_date(t, self.engine.tz)).unwrap_or("—".into());
                        ui.label(RichText::new(added).size(12.5).color(MUTED));
                        if theme::small(ui, "Olib tashlash", true).clicked() {
                            acts.push(Action::AskRemoveAllow(p.id.clone(), i));
                        }
                        ui.end_row();
                    }
                });
            }
            ui.add_space(6.0);
            ui.horizontal(|ui| {
                if theme::primary(ui, "📂 Ruxsat so'rovini import qilish…", true).clicked() {
                    acts.push(Action::ImportAllowFile(p.id.clone()));
                }
            });
            ui.horizontal(|ui| {
                ui.add(egui::TextEdit::singleline(&mut self.allow_text).desired_width(320.0).hint_text("yoki so'rov JSON / ochiq kalit (hex)"));
                ui.add(egui::TextEdit::singleline(&mut self.allow_label).desired_width(140.0).hint_text("nom (ixtiyoriy)"));
                if theme::small(ui, "Qo'shish", !self.allow_text.trim().is_empty()).clicked() {
                    acts.push(Action::AddAllowText(p.id.clone()));
                }
            });
        });
    }

    fn client_exchange(&mut self, ui: &mut Ui, p: &Profile, acts: &mut Vec<Action>) {
        theme::card(ui, |ui| {
            theme::section(ui, "Server", "");
            crate::ui::kv(ui, "Nomi:", if p.server_label.is_empty() { "—" } else { &p.server_label });
            crate::ui::kv(ui, "Manzil:", &p.target);
            ui.horizontal(|ui| {
                ui.label(RichText::new("Pinned kalit:").size(12.5).color(MUTED));
                ui.label(RichText::new(fp_of_hex(&p.server_pub)).monospace().color(ACCENT));
            });
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Serverga ruxsat so'rovi", "Server administratori uni allowlist'ga qo'shgach, ulanish ishlaydi.");
            match self.key(&p.identity) {
                Some(k) => {
                    ui.horizontal(|ui| {
                        ui.label(RichText::new("Klient kaliti:").size(12.5).color(MUTED));
                        ui.label(RichText::new(format!("{} · {}", k.name, k.fingerprint)).monospace().color(VIOLET));
                    });
                    ui.horizontal(|ui| {
                        if theme::secondary(ui, "💾 Ruxsat so'rovini saqlash…", true).clicked() {
                            acts.push(Action::SaveRequest(p.id.clone()));
                        }
                        if theme::secondary(ui, "📋 Nusxalash", true).clicked() {
                            acts.push(Action::CopyRequest(p.id.clone()));
                        }
                    });
                }
                None => {
                    ui.label(RichText::new("Klient kaliti tanlanmagan — tahrirlashda kalit tanlang (server talab qilsa, usiz ulanib bo'lmaydi).").size(12.5).color(AMBER));
                }
            }
        });
    }
}

fn profile_card(ui: &mut Ui, app: &App, p: &Profile, selected: bool, acts: &mut Vec<Action>) {
    let (st, col) = status_of(&app.engine, &p.id);
    let border = if selected { ACCENT } else { BORDER };
    let resp = egui::Frame::new()
        .fill(if selected { ACCENT.gamma_multiply(0.07) } else { CARD })
        .stroke(egui::Stroke::new(if selected { 1.5 } else { 1.0 }, border))
        .corner_radius(egui::CornerRadius::same(12))
        .inner_margin(egui::Margin::symmetric(14, 12))
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            ui.horizontal(|ui| {
                let (r, _) = ui.allocate_exact_size(egui::vec2(10.0, 10.0), egui::Sense::hover());
                ui.painter().circle_filled(r.center(), 5.0, col);
                ui.add(egui::Label::new(RichText::new(&p.name).font(theme::heading(15.0)).color(TEXT)).truncate());
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if app.engine.is_running(&p.id) {
                        if theme::small(ui, "■", true).on_hover_text("To'xtatish").clicked() {
                            acts.push(Action::Stop(p.id.clone()));
                        }
                    } else if theme::small(ui, "▶", true).on_hover_text("Ishga tushirish").clicked() {
                        acts.push(Action::Start(p.id.clone()));
                    }
                });
            });
            ui.horizontal(|ui| {
                theme::badge(ui, p.role.label(), if p.role == Role::Server { BLUE } else { VIOLET });
                theme::badge(ui, if p.mode == Mode::AetherQ { "AETHER-Q" } else { "Standart" }, ACCENT);
                ui.label(RichText::new(&st).size(12.0).color(col));
            });
            ui.label(RichText::new(p.route()).size(12.0).monospace().color(FAINT));
            if let Some(l) = app.engine.live(&p.id) {
                ui.label(
                    RichText::new(format!(
                        "{} faol · {} jami · {} rad{}",
                        l.active.map(|a| a.to_string()).unwrap_or("—".into()),
                        l.total,
                        l.failed,
                        l.hs_p50.map(|v| format!(" · {v:.1} ms")).unwrap_or_default()
                    ))
                    .size(12.0)
                    .color(MUTED),
                );
            }
        })
        .response;
    let resp = resp.interact(egui::Sense::click());
    resp.widget_info(|| egui::WidgetInfo::selected(egui::WidgetType::SelectableLabel, true, selected, format!("Profil: {}", p.name)));
    if resp.on_hover_cursor(egui::CursorIcon::PointingHand).clicked() {
        acts.push(Action::Select(p.id.clone()));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cli_command_matches_sidecar_flags() {
        let mut s = Profile::new(Role::Server);
        s.identity = "srv".into();
        s.pow = 8;
        let c = cli_command(&s, Path::new("K"));
        assert!(c.starts_with("aq-sidecar.exe serve --listen 0.0.0.0:9443 --upstream 127.0.0.1:8080 --identity"));
        assert!(c.contains("--require-client-auth --allow allow.txt") && c.contains("--pow 8"));
        let mut k = Profile::new(Role::Client);
        k.target = "10.0.0.1:9443".into();
        k.server_pub = "ab".into();
        k.identity = "pc".into();
        let c = cli_command(&k, Path::new("K"));
        assert!(c.contains("connect --listen 127.0.0.1:7000 --peer 10.0.0.1:9443 --server-pub ab") && c.ends_with("--resume"));
        k.mode = Mode::Standard;
        assert!(cli_command(&k, Path::new("K")).starts_with("aqctl.exe gateway connect"));
    }
}
