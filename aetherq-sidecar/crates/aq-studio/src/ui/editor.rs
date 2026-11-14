//! Profil muharriri (modal oyna): rol, rejim, manzillar, kalitlar va xavfsizlik — jonli tekshiruv bilan.

use egui::{RichText, Ui};

use crate::app::App;
use crate::keys;
use crate::model::{self, Mode, Profile, Role};
use crate::theme::{self, ACCENT, AMBER, BORDER, CARD_HI, FAINT, MUTED, RED, TEXT};
use crate::ui::{field, fp_of_hex, port_edit};

pub enum Outcome {
    Open,
    Cancel,
    Save(Profile),
}

pub struct Editor {
    pub p: Profile,
    pub is_new: bool,
    /// Tinglash doirasi: true — tarmoqdan (0.0.0.0), false — faqat shu kompyuter (127.0.0.1).
    network: bool,
    listen_port: u16,
    target_host: String,
    target_port: u16,
    import_text: String,
    import_msg: Option<Result<String, String>>,
    new_key: String,
    key_msg: Option<Result<String, String>>,
}

impl Editor {
    pub fn new(mut p: Profile, is_new: bool, app: &App) -> Editor {
        let (lh, lp) = model::split_host_port(&p.listen).unwrap_or(("127.0.0.1".into(), 7000));
        let (th, tp) = model::split_host_port(&p.target).unwrap_or((String::new(), if p.role == Role::Server { 8080 } else { 9443 }));
        if is_new && p.identity.is_empty() {
            // Mos nomli kalit bo'lsa — uni taklif qilamiz.
            let want = if p.role == Role::Server { "server" } else { "klient" };
            if let Some(k) = app.keys.iter().find(|k| k.name.starts_with(want)) {
                p.identity = k.name.clone();
            }
        }
        let base = if p.role == Role::Server { "server".to_string() } else { default_client_key() };
        let new_key = keys::suggest_name(&app.key_names(), &base);
        Editor {
            network: lh == "0.0.0.0" || lh == "::",
            listen_port: lp,
            target_host: th,
            target_port: tp,
            p,
            is_new,
            import_text: String::new(),
            import_msg: None,
            new_key,
            key_msg: None,
        }
    }

    fn sync(&mut self) {
        let host = if self.network { "0.0.0.0" } else { "127.0.0.1" };
        self.p.listen = format!("{host}:{}", self.listen_port);
        let th = self.target_host.trim();
        let th = if th.contains(':') && !th.starts_with('[') { format!("[{th}]") } else { th.to_string() };
        self.p.target = format!("{th}:{}", self.target_port);
    }

    fn set_role(&mut self, role: Role) {
        if self.p.role == role {
            return;
        }
        self.p.role = role;
        match role {
            Role::Server => {
                self.network = true;
                self.listen_port = 9443;
                self.target_host = "127.0.0.1".into();
                self.target_port = 8080;
            }
            Role::Client => {
                self.network = false;
                self.listen_port = 7000;
                self.target_host.clear();
                self.target_port = 9443;
            }
        }
    }

    /// Klient: taklif (JSON) yoki server ochiq kaliti (hex/.pub) — maydonlarni to'ldiradi.
    pub fn apply_import(&mut self, text: &str) -> Result<String, String> {
        let t = text.trim();
        if t.starts_with('{') {
            let inv = keys::parse_invite(t)?;
            let (h, port) = model::split_host_port(&inv.address).ok_or("manzil noto'g'ri")?;
            self.p.server_pub = inv.server_pub.clone();
            self.p.server_label = inv.name.clone();
            self.p.mode = inv.mode;
            self.target_host = h;
            self.target_port = port;
            if self.p.name.trim().is_empty() {
                self.p.name = inv.name.clone();
            }
            Ok(format!("Taklif qabul qilindi: «{}», {} · barmoq izi {}", inv.name, inv.address, inv.fingerprint))
        } else {
            let line = t.lines().map(str::trim).find(|l| !l.is_empty() && !l.starts_with('#')).unwrap_or("");
            let pk = model::parse_pub_hex(line).ok_or("Taklif (JSON) yoki 3904 belgili server ochiq kaliti kerak.")?;
            self.p.server_pub = aq_core::identity::to_hex(&pk);
            Ok(format!("Server kaliti qabul qilindi · barmoq izi {}", keys::fingerprint(&pk)))
        }
    }

    pub fn show(&mut self, ctx: &egui::Context, app: &mut App) -> Outcome {
        let mut out = Outcome::Open;
        let max_h = ctx.content_rect().height() * 0.86;
        let resp = egui::Modal::new(egui::Id::new("profile-editor")).show(ctx, |ui| {
            ui.set_width(660.0);
            ui.label(
                RichText::new(if self.is_new { "Yangi tunel" } else { "Tunelni tahrirlash" }).font(theme::heading(20.0)).color(TEXT),
            );
            ui.label(RichText::new("O'zgarishlar saqlangach, ishlab turgan tunel avtomatik qayta ishga tushadi.").size(12.5).color(MUTED));
            ui.add_space(8.0);
            egui::ScrollArea::vertical().max_height(max_h - 170.0).auto_shrink([false, true]).show(ui, |ui| {
                self.body(ui, app);
            });
            self.sync();
            let issues = model::validate(&self.p, &app.key_names(), &app.store.cfg.profiles, app.aqctl.is_some());
            let blocking = issues.iter().any(|i| i.blocking);
            ui.add_space(6.0);
            for i in &issues {
                let (c, sym) = if i.blocking { (RED, "✖") } else { (AMBER, "⚠") };
                ui.add(egui::Label::new(RichText::new(format!("{sym} {}", i.msg)).size(12.5).color(c)).wrap());
            }
            ui.add_space(10.0);
            ui.horizontal(|ui| {
                let save = theme::primary(ui, if self.is_new { "Yaratish" } else { "Saqlash" }, !blocking);
                let save = if blocking { save.on_disabled_hover_text("Avval qizil bilan belgilangan muammolarni tuzating.") } else { save };
                if save.clicked() {
                    out = Outcome::Save(self.p.clone());
                }
                if theme::secondary(ui, "Bekor qilish", true).clicked() {
                    out = Outcome::Cancel;
                }
            });
        });
        if resp.should_close() && matches!(out, Outcome::Open) {
            out = Outcome::Cancel;
        }
        out
    }

    fn body(&mut self, ui: &mut Ui, app: &mut App) {
        field(ui, "Nomi", "Ro'yxatda va jurnalda ko'rinadi.");
        ui.add(egui::TextEdit::singleline(&mut self.p.name).hint_text("masalan, Ofis serveri").desired_width(f32::INFINITY));
        ui.add_space(10.0);

        field(ui, "Rol", "");
        ui.horizontal(|ui| {
            for (role, title, sub) in [
                (Role::Server, "Server", "Ilovamni himoyalash: tarmoqdan tunelni qabul qilib, ilovaga uzatadi"),
                (Role::Client, "Klient", "Serverga ulanish: mahalliy portni tunel orqali serverga uzatadi"),
            ] {
                if choice_card(ui, self.p.role == role, title, sub, 312.0).clicked() {
                    self.set_role(role);
                }
            }
        });
        ui.add_space(10.0);

        field(ui, "Rejim", "");
        ui.horizontal(|ui| {
            ui.radio_value(&mut self.p.mode, Mode::AetherQ, "AETHER-Q (asosiy, tavsiya)");
            ui.radio_value(&mut self.p.mode, Mode::Standard, "Standart PQ-TLS (TLS 1.3 + X25519MLKEM768)");
        });
        if self.p.mode == Mode::Standard {
            let txt = match &app.aqctl {
                Some(p) => format!("aqctl topildi: {}", p.display()),
                None => "aqctl.exe topilmadi — Sozlamalarda yo'lini ko'rsating.".into(),
            };
            ui.label(RichText::new(txt).size(12.0).color(if app.aqctl.is_some() { FAINT } else { RED }));
        }
        ui.add_space(10.0);

        match self.p.role {
            Role::Server => self.server_fields(ui, app),
            Role::Client => self.client_fields(ui, app),
        }

        ui.add_space(10.0);
        field(ui, "Qo'shimcha", "");
        if self.p.mode == Mode::AetherQ {
            ui.checkbox(&mut self.p.resumption, "Session resumption — qayta ulanish tezroq (server imzosi o'tkazib yuboriladi)");
        }
        if self.p.role == Role::Server && self.p.mode == Mode::AetherQ {
            ui.horizontal(|ui| {
                ui.label("PoW (DoS himoyasi):");
                ui.add(egui::Slider::new(&mut self.p.pow, 0..=20).text("qiyinlik"));
            });
            ui.label(
                RichText::new("0 — o'chiq. 8–12: klient har ulanishda kichik hisob bajaradi; ko'p soxta ulanishli hujumni sekinlashtiradi.")
                    .size(12.0)
                    .color(MUTED),
            );
        }
        ui.checkbox(&mut self.p.autostart, "Dastur ochilganda avtomatik ishga tushirish");
    }

    fn key_picker(&mut self, ui: &mut Ui, app: &mut App, allow_none: bool) {
        let label = if self.p.identity.is_empty() { "— kalitsiz —".to_string() } else { self.p.identity.clone() };
        ui.horizontal(|ui| {
            egui::ComboBox::from_id_salt("identity")
                .selected_text(label)
                .width(260.0)
                .show_ui(ui, |ui| {
                    if allow_none {
                        ui.selectable_value(&mut self.p.identity, String::new(), "— kalitsiz —");
                    }
                    for k in &app.keys {
                        ui.selectable_value(&mut self.p.identity, k.name.clone(), format!("{}  ·  {}", k.name, k.fingerprint));
                    }
                });
            if let Some(k) = app.key(&self.p.identity) {
                ui.label(RichText::new(format!("barmoq izi {}", k.fingerprint)).size(12.0).color(FAINT));
            }
        });
        ui.horizontal(|ui| {
            ui.label(RichText::new("yoki yangi:").size(12.5).color(MUTED));
            ui.add(egui::TextEdit::singleline(&mut self.new_key).desired_width(180.0).hint_text("kalit nomi"));
            if theme::small(ui, "Kalit yaratish", keys::valid_name(self.new_key.trim())).clicked() {
                let days = app.store.cfg.settings.key_days;
                match app.create_key(&self.new_key, days) {
                    Ok(k) => {
                        self.p.identity = k.name.clone();
                        self.key_msg = Some(Ok(format!("«{}» yaratildi ({})", k.name, k.fingerprint)));
                        self.new_key = keys::next_name(&app.key_names(), &k.name);
                    }
                    Err(e) => self.key_msg = Some(Err(e)),
                }
            }
        });
        if let Some(m) = &self.key_msg {
            let (t, c) = match m {
                Ok(t) => (t.as_str(), theme::GREEN),
                Err(t) => (t.as_str(), RED),
            };
            ui.label(RichText::new(t).size(12.0).color(c));
        }
    }

    fn server_fields(&mut self, ui: &mut Ui, app: &mut App) {
        field(ui, "Tunel porti", "Klientlar shu portga ulanadi (Windows Firewall so'rasa — ruxsat bering).");
        ui.horizontal(|ui| {
            port_edit(ui, &mut self.listen_port);
            ui.radio_value(&mut self.network, true, "Tarmoqdan qabul qilish (0.0.0.0)");
            ui.radio_value(&mut self.network, false, "Faqat shu kompyuter (127.0.0.1)");
        });
        ui.add_space(8.0);
        field(ui, "Klientlar uchun manzil", "Taklif fayliga yoziladi (IP yoki domen). Bo'sh — avtomatik: shu kompyuterning asosiy IP manzili.");
        let hint = if self.network { app.diag.primary_ip.clone().unwrap_or_else(|| "192.168.1.10".into()) } else { "127.0.0.1".into() };
        ui.add(egui::TextEdit::singleline(&mut self.p.public_host).desired_width(260.0).hint_text(hint));
        ui.add_space(8.0);
        field(ui, "Himoyalanadigan ilova manzili", "Tunel ichidan kelgan ulanishlar shu manzilga uzatiladi (odatda shu kompyuterdagi ilova).");
        ui.horizontal(|ui| {
            ui.add(egui::TextEdit::singleline(&mut self.target_host).desired_width(220.0).hint_text("127.0.0.1"));
            ui.label(":");
            port_edit(ui, &mut self.target_port);
        });
        ui.add_space(8.0);
        field(ui, "Server kaliti (identity)", "Klientlar serverni shu kalit bo'yicha taniydi (taklif faylida yuboriladi).");
        self.key_picker(ui, app, false);
        ui.add_space(8.0);
        ui.checkbox(&mut self.p.require_client_auth, "Klient kaliti talab qilinsin (faqat allowlist'dagilar ulana oladi) — tavsiya");
        ui.label(
            RichText::new(format!(
                "Allowlist'da {} ta klient. Klientlarni profil sahifasida «Ruxsat so'rovini import qilish» bilan qo'shasiz.",
                self.p.allow.len()
            ))
            .size(12.0)
            .color(MUTED),
        );
    }

    fn client_fields(&mut self, ui: &mut Ui, app: &mut App) {
        field(ui, "Server taklifi", "Server administratori yuborgan .aqinvite fayli: manzil va server kaliti o'zi to'ladi.");
        ui.horizontal(|ui| {
            if theme::secondary(ui, "📂 Taklif faylini tanlash…", true).clicked() {
                if let Some(path) = rfd::FileDialog::new()
                    .set_title("Server taklif faylini tanlang")
                    .add_filter("AETHER-Q taklifi", &["aqinvite", "json", "pub", "txt"])
                    .pick_file()
                {
                    self.import_msg = Some(std::fs::read_to_string(&path).map_err(|e| e.to_string()).and_then(|t| self.apply_import(&t)));
                }
            }
            ui.label(RichText::new("yoki matnini quyidagiga joylang:").size(12.5).color(MUTED));
        });
        ui.horizontal(|ui| {
            ui.add(
                egui::TextEdit::multiline(&mut self.import_text)
                    .desired_rows(2)
                    .desired_width(500.0)
                    .hint_text("{\"format\":\"aetherq-invite/1\", …} yoki server ochiq kaliti (hex)"),
            );
            if theme::small(ui, "Qo'llash", !self.import_text.trim().is_empty()).clicked() {
                let t = self.import_text.clone();
                self.import_msg = Some(self.apply_import(&t));
                if matches!(self.import_msg, Some(Ok(_))) {
                    self.import_text.clear();
                }
            }
        });
        if let Some(m) = &self.import_msg {
            let (t, c) = match m {
                Ok(t) => (t.as_str(), theme::GREEN),
                Err(t) => (t.as_str(), RED),
            };
            ui.add(egui::Label::new(RichText::new(t).size(12.5).color(c)).wrap());
        }
        ui.add_space(8.0);
        field(ui, "Server manzili", "Server kompyuterining IP manzili yoki nomi va tunel porti.");
        ui.horizontal(|ui| {
            ui.add(egui::TextEdit::singleline(&mut self.target_host).desired_width(260.0).hint_text("192.168.1.10"));
            ui.label(":");
            port_edit(ui, &mut self.target_port);
        });
        ui.horizontal(|ui| {
            ui.label(RichText::new("Server kaliti barmoq izi:").size(12.5).color(MUTED));
            ui.label(RichText::new(fp_of_hex(&self.p.server_pub)).monospace().color(ACCENT));
            if !self.p.server_label.is_empty() {
                ui.label(RichText::new(format!("(«{}»)", self.p.server_label)).size(12.5).color(MUTED));
            }
        });
        ui.label(
            RichText::new("Barmoq izini server administratori bilan telefonda solishtiring — soxta taklifdan himoya.")
                .size(12.0)
                .color(FAINT),
        );
        ui.add_space(8.0);
        field(ui, "Mahalliy port", "Ilovangiz (brauzer, dastur) shu manzilga ulanadi — trafik tunel orqali serverga ketadi.");
        ui.horizontal(|ui| {
            ui.label(RichText::new(if self.network { "0.0.0.0 :" } else { "127.0.0.1 :" }).monospace());
            port_edit(ui, &mut self.listen_port);
            ui.checkbox(&mut self.network, "Tarmoqdagi boshqa kompyuterlarga ham ochiq");
        });
        ui.add_space(8.0);
        field(ui, "Klient kaliti (identity)", "Server klientni shu kalit bo'yicha taniydi — ruxsat so'rovida yuboriladi.");
        self.key_picker(ui, app, true);
    }
}

/// Klient kaliti uchun standart nom: `klient-<kompyuter-nomi>`.
pub fn default_client_key() -> String {
    let host: String = crate::app::safe_file_name(&crate::diag::hostname()).to_lowercase().chars().take(24).collect();
    format!("klient-{host}")
}

/// Tanlanadigan kartochka (rol tanlash uchun).
pub fn choice_card(ui: &mut Ui, selected: bool, title: &str, sub: &str, width: f32) -> egui::Response {
    let fill = if selected { ACCENT.gamma_multiply(0.12) } else { CARD_HI };
    let stroke = if selected { ACCENT } else { BORDER };
    let r = egui::Frame::new()
        .fill(fill)
        .stroke(egui::Stroke::new(if selected { 1.5 } else { 1.0 }, stroke))
        .corner_radius(egui::CornerRadius::same(10))
        .inner_margin(egui::Margin::symmetric(12, 10))
        .show(ui, |ui| {
            ui.set_width(width - 26.0);
            ui.horizontal(|ui| {
                let (rr, _) = ui.allocate_exact_size(egui::vec2(16.0, 16.0), egui::Sense::hover());
                ui.painter().circle_stroke(rr.center(), 7.0, egui::Stroke::new(1.5, if selected { ACCENT } else { FAINT }));
                if selected {
                    ui.painter().circle_filled(rr.center(), 4.0, ACCENT);
                }
                ui.label(RichText::new(title).font(theme::heading(14.5)).color(TEXT));
            });
            ui.add(egui::Label::new(RichText::new(sub).size(12.0).color(MUTED)).wrap());
        })
        .response;
    let r = r.interact(egui::Sense::click());
    r.widget_info(|| egui::WidgetInfo::selected(egui::WidgetType::RadioButton, true, selected, title));
    r.on_hover_cursor(egui::CursorIcon::PointingHand)
}
