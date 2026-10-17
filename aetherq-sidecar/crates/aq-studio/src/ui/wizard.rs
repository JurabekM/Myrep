//! Tez sozlash ustasi: uch stsenariy — bitta kompyuterda sinash, server (ilovani himoyalash), klient.

use egui::{RichText, Ui};

use crate::app::{local_dial_addr, Action, App, Page};
use crate::diag::{self, HttpProbe, Task, TestServer};
use crate::keys::{self, Invite};
use crate::model::{self, AllowEntry, Mode, Profile, Role};
use crate::theme::{self, ACCENT, BLUE, FAINT, GREEN, MUTED, RED, TEXT, VIOLET};
use crate::timefmt;
use crate::ui::editor::{choice_card, default_client_key};
use crate::ui::{field, port_edit};

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Scenario {
    Demo,
    Server,
    Client,
}

#[derive(PartialEq, Eq)]
enum Step {
    Choose,
    Form,
    Done,
}

pub struct Wizard {
    step: Step,
    scenario: Scenario,
    demo_builtin: bool,
    demo_app: String,
    srv_name: String,
    srv_app_host: String,
    srv_app_port: u16,
    srv_port: u16,
    srv_network: bool,
    srv_public: String,
    srv_mode: Mode,
    srv_auth: bool,
    srv_check: Option<Task<Result<f64, String>>>,
    srv_check_result: Option<Result<f64, String>>,
    cli_text: String,
    cli_invite: Option<Invite>,
    cli_msg: Option<Result<String, String>>,
    cli_port: u16,
    cli_name: String,
    /// Yaratilgan profillar (server, klient).
    created: Vec<String>,
    error: Option<String>,
    probe: Option<Task<Result<HttpProbe, String>>>,
    probe_result: Option<Result<HttpProbe, String>>,
    allow_text: String,
}

/// `from..=to` oralig'idagi birinchi bo'sh mahalliy port.
fn free_port(host: &str, from: u16, to: u16) -> Option<u16> {
    (from..=to).find(|p| diag::port_free(&format!("{host}:{p}")).is_ok())
}

impl Wizard {
    pub fn new(scenario: Option<Scenario>, app: &App) -> Wizard {
        let host = diag::hostname();
        Wizard {
            step: if scenario.is_some() { Step::Form } else { Step::Choose },
            scenario: scenario.unwrap_or(Scenario::Demo),
            demo_builtin: true,
            demo_app: "127.0.0.1:8080".into(),
            srv_name: format!("Server ({host})"),
            srv_app_host: "127.0.0.1".into(),
            srv_app_port: 8080,
            srv_port: free_port("0.0.0.0", 9443, 9499).unwrap_or(9443),
            srv_network: true,
            srv_public: app.diag.primary_ip.clone().unwrap_or_else(|| "127.0.0.1".into()),
            srv_mode: Mode::AetherQ,
            srv_auth: true,
            srv_check: None,
            srv_check_result: None,
            cli_text: String::new(),
            cli_invite: None,
            cli_msg: None,
            cli_port: free_port("127.0.0.1", 7000, 7099).unwrap_or(7000),
            cli_name: String::new(),
            created: Vec::new(),
            error: None,
            probe: None,
            probe_result: None,
            allow_text: String::new(),
        }
    }

    pub fn poll(&mut self) {
        if let Some(r) = self.probe.as_ref().and_then(|t| t.poll()) {
            self.probe_result = Some(r);
            self.probe = None;
        }
        if let Some(r) = self.srv_check.as_ref().and_then(|t| t.poll()) {
            self.srv_check_result = Some(r);
            self.srv_check = None;
        }
    }

    /// Ochiq qolsa true.
    pub fn show(&mut self, ctx: &egui::Context, app: &mut App) -> bool {
        let mut keep = true;
        let max_h = ctx.content_rect().height() * 0.88;
        let resp = egui::Modal::new(egui::Id::new("wizard")).show(ctx, |ui| {
            ui.set_width(720.0);
            ui.horizontal(|ui| {
                ui.label(RichText::new("Tez sozlash ustasi").font(theme::heading(20.0)).color(TEXT));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    let steps = ["Tanlash", "Sozlash", "Tayyor"];
                    let cur = match self.step {
                        Step::Choose => 0,
                        Step::Form => 1,
                        Step::Done => 2,
                    };
                    for (i, s) in steps.iter().enumerate().rev() {
                        let c = if i == cur { ACCENT } else if i < cur { GREEN } else { FAINT };
                        ui.label(RichText::new(format!("{}. {s}", i + 1)).size(12.5).color(c));
                    }
                });
            });
            ui.add_space(8.0);
            egui::ScrollArea::vertical().max_height(max_h - 120.0).auto_shrink([false, true]).show(ui, |ui| {
                match self.step {
                    Step::Choose => self.choose(ui),
                    Step::Form => self.form(ui, app),
                    Step::Done => self.done(ui, app),
                }
            });
            if let Some(e) = &self.error {
                ui.add(egui::Label::new(RichText::new(format!("✖ {e}")).color(RED)).wrap());
            }
            ui.add_space(8.0);
            ui.horizontal(|ui| {
                match self.step {
                    Step::Choose => {}
                    Step::Form => {
                        let (label, enabled) = self.create_label();
                        if theme::primary(ui, label, enabled).clicked() {
                            self.error = None;
                            match self.create(app) {
                                Ok(()) => self.step = Step::Done,
                                Err(e) => self.error = Some(e),
                            }
                        }
                        if theme::secondary(ui, "← Orqaga", true).clicked() {
                            self.step = Step::Choose;
                            self.error = None;
                        }
                    }
                    Step::Done => {
                        if theme::primary(ui, "Tayyor", true).clicked() {
                            keep = false;
                            app.acts.push(Action::Goto(Page::Tunnels));
                            if let Some(id) = self.created.last() {
                                app.acts.push(Action::Select(id.clone()));
                            }
                        }
                    }
                }
                if self.step != Step::Done && theme::secondary(ui, "Yopish", true).clicked() {
                    keep = false;
                }
            });
        });
        if resp.should_close() && self.step != Step::Done {
            keep = false;
        }
        keep
    }

    fn create_label(&self) -> (&'static str, bool) {
        match self.scenario {
            Scenario::Demo => ("▶ Yaratish va ishga tushirish", self.demo_builtin || model::split_host_port(&self.demo_app).is_some()),
            Scenario::Server => ("Serverni yaratish", !self.srv_name.trim().is_empty() && !self.srv_app_host.trim().is_empty()),
            Scenario::Client => ("Klientni yaratish", self.cli_invite.is_some()),
        }
    }

    fn choose(&mut self, ui: &mut Ui) {
        ui.label(RichText::new("Nima qilmoqchisiz?").color(MUTED));
        ui.add_space(6.0);
        for (s, title, sub) in [
            (
                Scenario::Demo,
                "▶  Bitta kompyuterda sinab ko'rish",
                "Hammasi avtomatik: kalitlar, sinov ilovasi, server va klient tunellari. Natijani brauzerda ko'rasiz.",
            ),
            (
                Scenario::Server,
                "🛡  Server: ilovamni himoyalash",
                "Shu kompyuterdagi ilovaga faqat ruxsat berilgan klientlar AETHER-Q tunel orqali ulanadi.",
            ),
            (
                Scenario::Client,
                "🔌  Klient: serverga ulanish",
                "Server administratori yuborgan taklif fayli bilan ulanasiz; ilovangiz mahalliy portga ulanadi.",
            ),
        ] {
            if choice_card(ui, false, title, sub, 700.0).clicked() {
                self.scenario = s;
                self.step = Step::Form;
            }
            ui.add_space(4.0);
        }
    }

    fn form(&mut self, ui: &mut Ui, app: &mut App) {
        match self.scenario {
            Scenario::Demo => {
                ui.label(RichText::new("Bitta kompyuterda to'liq zanjir").font(theme::heading(16.0)).color(TEXT));
                chain(ui, &["Brauzer", "Klient sidecar", "AETHER-Q tunel", "Server sidecar", "Ilova"]);
                ui.add_space(8.0);
                field(ui, "Himoyalanadigan ilova", "");
                ui.radio_value(&mut self.demo_builtin, true, "Ichki sinov serveri (tavsiya — hech narsa o'rnatish shart emas)");
                ui.radio_value(&mut self.demo_builtin, false, "O'z ilovam (masalan, Aether_new monoliti):");
                if !self.demo_builtin {
                    ui.add(egui::TextEdit::singleline(&mut self.demo_app).desired_width(240.0).hint_text("127.0.0.1:8080"));
                }
                ui.add_space(6.0);
                ui.label(
                    RichText::new("Yaratiladi: «demo-server» va «demo-klient» kalitlari, «Demo server» va «Demo klient» profillari (bo'sh portlar avtomatik tanlanadi).")
                        .size(12.5)
                        .color(MUTED),
                );
            }
            Scenario::Server => {
                field(ui, "Server nomi", "Klientlarga taklif faylida ko'rinadi.");
                ui.add(egui::TextEdit::singleline(&mut self.srv_name).desired_width(360.0));
                ui.add_space(6.0);
                field(ui, "Himoyalanadigan ilova", "Shu kompyuterdagi ilova manzili (masalan, veb-server yoki API).");
                ui.horizontal(|ui| {
                    ui.add(egui::TextEdit::singleline(&mut self.srv_app_host).desired_width(200.0));
                    ui.label(":");
                    port_edit(ui, &mut self.srv_app_port);
                    if theme::small(ui, "Tekshirish", self.srv_check.is_none()).clicked() {
                        let a = format!("{}:{}", self.srv_app_host.trim(), self.srv_app_port);
                        self.srv_check = Some(Task::spawn(move || diag::tcp_reach(&a, std::time::Duration::from_secs(3))));
                    }
                });
                match &self.srv_check_result {
                    Some(Ok(ms)) => {
                        ui.label(RichText::new(format!("✔ Ilova javob beryapti ({ms:.1} ms)")).size(12.5).color(GREEN));
                    }
                    Some(Err(e)) => {
                        ui.add(
                            egui::Label::new(
                                RichText::new(format!("⚠ Ilova hozir javob bermayapti: {e}. Tunel baribir yaratiladi — ilova ishga tushgach ulanishlar o'tadi."))
                                    .size(12.5)
                                    .color(theme::AMBER),
                            )
                            .wrap(),
                        );
                    }
                    None if self.srv_check.is_some() => {
                        ui.label(RichText::new("Tekshirilmoqda…").size(12.5).color(MUTED));
                    }
                    None => {}
                }
                ui.add_space(6.0);
                field(ui, "Tunel porti", "Klientlar ulanadigan port.");
                let was_network = self.srv_network;
                ui.horizontal(|ui| {
                    port_edit(ui, &mut self.srv_port);
                    ui.radio_value(&mut self.srv_network, true, "Tarmoqdan (0.0.0.0)");
                    ui.radio_value(&mut self.srv_network, false, "Faqat shu kompyuter");
                });
                // Doira o'zgarsa, taklifdagi manzil ham mos bo'lsin (lokal server — 127.0.0.1).
                if was_network != self.srv_network {
                    self.srv_public = if self.srv_network {
                        app.diag.primary_ip.clone().unwrap_or_else(|| "127.0.0.1".into())
                    } else {
                        "127.0.0.1".into()
                    };
                }
                field(ui, "Klientlar uchun manzil", "Taklif fayliga yoziladi: klientlar serverga shu IP yoki nom orqali ulanadi.");
                ui.add(egui::TextEdit::singleline(&mut self.srv_public).desired_width(240.0));
                ui.add_space(6.0);
                field(ui, "Rejim", "");
                ui.horizontal(|ui| {
                    ui.radio_value(&mut self.srv_mode, Mode::AetherQ, "AETHER-Q (tavsiya)");
                    ui.radio_value(&mut self.srv_mode, Mode::Standard, "Standart PQ-TLS");
                });
                ui.checkbox(&mut self.srv_auth, "Faqat ruxsat berilgan klientlar (allowlist) — tavsiya");
            }
            Scenario::Client => {
                field(ui, "1. Server taklifi", "Server administratori yuborgan .aqinvite faylini tanlang yoki matnini joylang.");
                ui.horizontal(|ui| {
                    if theme::secondary(ui, "📂 Taklif faylini tanlash…", true).clicked() {
                        if let Some(path) =
                            rfd::FileDialog::new().set_title("Taklif fayli").add_filter("AETHER-Q taklifi", &["aqinvite", "json"]).pick_file()
                        {
                            match std::fs::read_to_string(&path) {
                                Ok(t) => self.take_invite(&t),
                                Err(e) => self.cli_msg = Some(Err(e.to_string())),
                            }
                        }
                    }
                });
                ui.horizontal(|ui| {
                    ui.add(egui::TextEdit::multiline(&mut self.cli_text).desired_rows(3).desired_width(560.0).hint_text("{\"format\":\"aetherq-invite/1\", …}"));
                    if theme::small(ui, "Qo'llash", !self.cli_text.trim().is_empty()).clicked() {
                        let t = self.cli_text.clone();
                        self.take_invite(&t);
                    }
                });
                if let Some(m) = &self.cli_msg {
                    let (t, c) = match m {
                        Ok(t) => (t.as_str(), GREEN),
                        Err(t) => (t.as_str(), RED),
                    };
                    ui.add(egui::Label::new(RichText::new(t).size(12.5).color(c)).wrap());
                }
                if let Some(inv) = &self.cli_invite {
                    theme::card(ui, |ui| {
                        crate::ui::kv(ui, "Server:", &inv.name);
                        crate::ui::kv(ui, "Manzil:", &inv.address);
                        crate::ui::kv(ui, "Rejim:", inv.mode.label());
                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Barmoq izi:").size(12.5).color(MUTED));
                            ui.label(RichText::new(&inv.fingerprint).monospace().color(ACCENT));
                        });
                        ui.label(
                            RichText::new("Bu barmoq izini server administratori bilan telefonda solishtiring.").size(12.0).color(FAINT),
                        );
                    });
                }
                ui.add_space(6.0);
                field(ui, "2. Mahalliy port", "Ilovangiz shu portga ulanadi (127.0.0.1).");
                port_edit(ui, &mut self.cli_port);
                field(ui, "3. Profil nomi", "");
                ui.add(egui::TextEdit::singleline(&mut self.cli_name).desired_width(360.0).hint_text("masalan, Ofis serveri"));
                let _ = app;
            }
        }
    }

    fn take_invite(&mut self, text: &str) {
        match keys::parse_invite(text) {
            Ok(inv) => {
                if self.cli_name.trim().is_empty() {
                    self.cli_name = format!("{} ga ulanish", inv.name);
                }
                self.cli_msg = Some(Ok("Taklif to'g'ri: imzo kaliti va manzil o'qildi.".into()));
                self.cli_invite = Some(inv);
                self.cli_text.clear();
            }
            Err(e) => self.cli_msg = Some(Err(e)),
        }
    }

    #[cfg(test)]
    pub fn create_for_test(&mut self, app: &mut App) -> Result<(), String> {
        self.create(app)
    }

    fn create(&mut self, app: &mut App) -> Result<(), String> {
        match self.scenario {
            Scenario::Demo => self.create_demo(app),
            Scenario::Server => self.create_server(app),
            Scenario::Client => self.create_client(app),
        }
    }

    fn create_demo(&mut self, app: &mut App) -> Result<(), String> {
        let upstream = if self.demo_builtin {
            if app.diag.test_server.is_none() {
                let port = free_port("127.0.0.1", 18080, 18099).ok_or("18080–18099 oralig'ida bo'sh port yo'q")?;
                let srv = TestServer::start(&format!("127.0.0.1:{port}"))?;
                app.diag.test_addr = srv.addr.to_string();
                app.diag.test_server = Some(srv);
            }
            app.diag.test_server.as_ref().map(|s| s.addr.to_string()).unwrap_or_default()
        } else {
            model::split_host_port(&self.demo_app).ok_or("Ilova manzili host:port bo'lsin.")?;
            self.demo_app.trim().to_string()
        };
        let sp = free_port("127.0.0.1", 19443, 19499).ok_or("19443–19499 oralig'ida bo'sh port yo'q")?;
        let cp = free_port("127.0.0.1", 17000, 17099).ok_or("17000–17099 oralig'ida bo'sh port yo'q")?;
        let days = app.store.cfg.settings.key_days;
        let skey = app.create_key(&keys::suggest_name(&app.key_names(), "demo-server"), days)?;
        let ckey = app.create_key(&keys::suggest_name(&app.key_names(), "demo-klient"), days)?;
        let mut s = Profile::new(Role::Server);
        s.name = "Demo server".into();
        s.listen = format!("127.0.0.1:{sp}");
        s.target = upstream.clone();
        s.identity = skey.name.clone();
        s.allow.push(AllowEntry { label: "Demo klient".into(), pub_hex: ckey.pub_hex(), added: timefmt::rfc3339(timefmt::now_unix()) });
        let mut c = Profile::new(Role::Client);
        c.name = "Demo klient".into();
        c.listen = format!("127.0.0.1:{cp}");
        c.target = format!("127.0.0.1:{sp}");
        c.identity = ckey.name.clone();
        c.server_pub = skey.pub_hex();
        c.server_label = "Demo server".into();
        let (sid, cid) = (s.id.clone(), c.id.clone());
        app.save_profile(s)?;
        app.save_profile(c)?;
        app.start(&sid)?;
        app.start(&cid)?;
        self.created = vec![sid, cid];
        let addr = format!("127.0.0.1:{cp}");
        self.probe = Some(Task::spawn(move || diag::http_probe(&addr, "/")));
        Ok(())
    }

    fn create_server(&mut self, app: &mut App) -> Result<(), String> {
        let key = app.create_key(&keys::suggest_name(&app.key_names(), "server"), app.store.cfg.settings.key_days)?;
        let mut s = Profile::new(Role::Server);
        s.name = self.srv_name.trim().to_string();
        s.listen = format!("{}:{}", if self.srv_network { "0.0.0.0" } else { "127.0.0.1" }, self.srv_port);
        s.public_host = self.srv_public.trim().to_string();
        s.target = format!("{}:{}", self.srv_app_host.trim(), self.srv_app_port);
        s.identity = key.name.clone();
        s.mode = self.srv_mode;
        s.require_client_auth = self.srv_auth;
        s.autostart = true;
        let id = s.id.clone();
        app.save_profile(s)?;
        app.start(&id)?;
        self.created = vec![id];
        Ok(())
    }

    fn create_client(&mut self, app: &mut App) -> Result<(), String> {
        let inv = self.cli_invite.clone().ok_or("Avval taklif faylini import qiling.")?;
        let key = app.create_key(&keys::suggest_name(&app.key_names(), &default_client_key()), app.store.cfg.settings.key_days)?;
        let mut c = Profile::new(Role::Client);
        c.name = if self.cli_name.trim().is_empty() { format!("{} ga ulanish", inv.name) } else { self.cli_name.trim().to_string() };
        c.listen = format!("127.0.0.1:{}", self.cli_port);
        c.target = inv.address.clone();
        c.mode = inv.mode;
        c.server_pub = inv.server_pub.clone();
        c.server_label = inv.name.clone();
        c.identity = key.name.clone();
        c.autostart = true;
        let id = c.id.clone();
        app.save_profile(c)?;
        app.start(&id)?;
        self.created = vec![id];
        Ok(())
    }

    fn done(&mut self, ui: &mut Ui, app: &mut App) {
        match self.scenario {
            Scenario::Demo => {
                ui.label(RichText::new("✔ Demo zanjiri ishga tushdi").font(theme::heading(17.0)).color(GREEN));
                let client = self.created.get(1).and_then(|id| app.profile(id)).cloned();
                if let Some(c) = &client {
                    let url = format!("http://{}/", local_dial_addr(&c.listen));
                    ui.add_space(4.0);
                    ui.label(RichText::new(format!("Brauzerda oching: {url}")).color(TEXT));
                    ui.label(RichText::new("So'rov klient tuneli → AETHER-Q → server tuneli → sinov ilovasi yo'lidan o'tadi.").size(12.5).color(MUTED));
                    ui.horizontal(|ui| {
                        if theme::primary(ui, "🌐 Brauzerda ochish", true).clicked() {
                            crate::app::open_path(std::path::Path::new(&url));
                        }
                        if theme::secondary(ui, "↻ Qayta sinash", self.probe.is_none()).clicked() {
                            let addr = local_dial_addr(&c.listen);
                            self.probe_result = None;
                            self.probe = Some(Task::spawn(move || diag::http_probe(&addr, "/")));
                        }
                    });
                }
                self.probe_view(ui);
            }
            Scenario::Server => {
                let Some(id) = self.created.first().cloned() else { return };
                let Some(p) = app.profile(&id).cloned() else { return };
                ui.label(RichText::new(format!("✔ «{}» yaratildi va ishga tushdi", p.name)).font(theme::heading(17.0)).color(GREEN));
                ui.label(RichText::new(format!("Tunel: {} → ilova {}", p.listen, p.target)).color(MUTED));
                ui.add_space(8.0);
                theme::card(ui, |ui| {
                    ui.label(RichText::new("1. Taklif faylini klientga yuboring").font(theme::heading(14.5)).color(TEXT));
                    ui.label(RichText::new("Unda server manzili va ochiq kaliti bor (maxfiy emas).").size(12.5).color(MUTED));
                    if let Some(k) = app.key(&p.identity) {
                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Server barmoq izi:").size(12.5).color(MUTED));
                            ui.label(RichText::new(&k.fingerprint).monospace().color(ACCENT));
                        });
                    }
                    ui.horizontal(|ui| {
                        if theme::primary(ui, "💾 Taklifni saqlash…", true).clicked() {
                            app.acts.push(Action::SaveInvite(id.clone()));
                        }
                        if theme::secondary(ui, "📋 Nusxalash", true).clicked() {
                            app.acts.push(Action::CopyInvite(id.clone()));
                        }
                    });
                });
                ui.add_space(6.0);
                if p.require_client_auth {
                    theme::card(ui, |ui| {
                        ui.label(RichText::new("2. Klientning ruxsat so'rovini import qiling").font(theme::heading(14.5)).color(TEXT));
                        ui.label(RichText::new("Klient taklifni import qilgach, sizga .aqrequest fayli yuboradi.").size(12.5).color(MUTED));
                        ui.horizontal(|ui| {
                            if theme::primary(ui, "📂 Ruxsat so'rovini import qilish…", true).clicked() {
                                app.acts.push(Action::ImportAllowFile(id.clone()));
                            }
                        });
                        ui.horizontal(|ui| {
                            ui.add(egui::TextEdit::singleline(&mut self.allow_text).desired_width(460.0).hint_text("yoki so'rov matnini joylang"));
                            if theme::small(ui, "Qo'shish", !self.allow_text.trim().is_empty()).clicked() {
                                match app.add_allow(&id, &self.allow_text.clone(), "") {
                                    Ok(m) => {
                                        self.allow_text.clear();
                                        app.ok(m);
                                    }
                                    Err(e) => app.err(e),
                                }
                            }
                        });
                        for a in &p.allow {
                            ui.label(RichText::new(format!("✔ {} · {}", a.label, crate::ui::fp_of_hex(&a.pub_hex))).size(12.5).color(GREEN));
                        }
                        if p.allow.is_empty() {
                            ui.label(RichText::new("Hozircha hech kim qo'shilmagan.").size(12.5).color(FAINT));
                        }
                    });
                }
                ui.add_space(6.0);
                ui.label(
                    RichText::new("Windows Firewall ruxsat so'rasa — «Ruxsat berish» ni bosing, aks holda boshqa kompyuterlar ulana olmaydi.")
                        .size(12.5)
                        .color(theme::AMBER),
                );
            }
            Scenario::Client => {
                let Some(id) = self.created.first().cloned() else { return };
                let Some(p) = app.profile(&id).cloned() else { return };
                ui.label(RichText::new(format!("✔ «{}» yaratildi va ishga tushdi", p.name)).font(theme::heading(17.0)).color(GREEN));
                ui.label(RichText::new(format!("Ilovangiz endi {} ga ulanadi → tunel → {}", local_dial_addr(&p.listen), p.target)).color(MUTED));
                ui.add_space(8.0);
                theme::card(ui, |ui| {
                    ui.label(RichText::new("1. Ruxsat so'rovini serverga yuboring").font(theme::heading(14.5)).color(TEXT));
                    ui.label(RichText::new("Server administratori uni allowlist'ga qo'shgach, ulanish ishlaydi.").size(12.5).color(MUTED));
                    if let Some(k) = app.key(&p.identity) {
                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Sizning barmoq izingiz:").size(12.5).color(MUTED));
                            ui.label(RichText::new(&k.fingerprint).monospace().color(VIOLET));
                        });
                    }
                    ui.horizontal(|ui| {
                        if theme::primary(ui, "💾 So'rovni saqlash…", true).clicked() {
                            app.acts.push(Action::SaveRequest(id.clone()));
                        }
                        if theme::secondary(ui, "📋 Nusxalash", true).clicked() {
                            app.acts.push(Action::CopyRequest(id.clone()));
                        }
                    });
                });
                ui.add_space(6.0);
                theme::card(ui, |ui| {
                    ui.label(RichText::new("2. Server ruxsat bergach — sinab ko'ring").font(theme::heading(14.5)).color(TEXT));
                    if theme::secondary(ui, "🔎 Ulanishni sinash", self.probe.is_none()).clicked() {
                        let addr = local_dial_addr(&p.listen);
                        self.probe_result = None;
                        self.probe = Some(Task::spawn(move || diag::http_probe(&addr, "/")));
                    }
                    self.probe_view(ui);
                });
            }
        }
    }

    fn probe_view(&self, ui: &mut Ui) {
        match &self.probe_result {
            Some(Ok(p)) => {
                ui.label(RichText::new(format!("✔ Javob keldi: {} · {:.1} ms", p.status_line, p.ms)).color(GREEN));
                if !p.preview.is_empty() {
                    ui.add(egui::Label::new(RichText::new(p.preview.trim()).monospace().size(12.0).color(MUTED)).wrap());
                }
            }
            Some(Err(e)) => {
                ui.add(egui::Label::new(RichText::new(format!("✖ {e}")).color(RED)).wrap());
                ui.label(RichText::new("Sababini Jurnal sahifasida ko'ring (masalan, server hali ruxsat bermagan).").size(12.5).color(MUTED));
            }
            None if self.probe.is_some() => {
                ui.label(RichText::new("Sinalmoqda…").color(MUTED));
            }
            None => {}
        }
    }
}

/// Zanjir diagrammasi: bloklar va strelkalar.
fn chain(ui: &mut Ui, parts: &[&str]) {
    ui.horizontal_wrapped(|ui| {
        for (i, p) in parts.iter().enumerate() {
            let c = if p.contains("AETHER") { ACCENT } else { BLUE };
            theme::badge(ui, p, c);
            if i + 1 < parts.len() {
                ui.label(RichText::new("→").color(FAINT));
            }
        }
    });
}
