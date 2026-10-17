//! Ilova holati va amallar. UI sahifalari faqat `Action` yuboradi; amallar shu yerda bajariladi —
//! shuning uchun har bir tugma oddiy funksiyaga ulangan va testlarda chaqirib tekshiriladi.

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use egui::{Color32, RichText};

use crate::diag::{HttpProbe, Task, TestServer};
use crate::engine::{Engine, Level};
use crate::icons::{self, Icon};
use crate::keys::{self, KeyInfo};
use crate::model::{self, AllowEntry, Profile, Role};
use crate::store::Store;
use crate::theme::{self, ACCENT, CARD_HI, FAINT, GREEN, MUTED, RED, SIDEBAR, TEXT};
use crate::timefmt;
use crate::ui::editor::Editor;
use crate::ui::wizard::{Scenario, Wizard};

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Page {
    Dashboard,
    Tunnels,
    Keys,
    Logs,
    Diagnostics,
    Settings,
    Help,
}

impl Page {
    pub const ALL: [Page; 7] =
        [Page::Dashboard, Page::Tunnels, Page::Keys, Page::Logs, Page::Diagnostics, Page::Settings, Page::Help];

    pub fn title(self) -> &'static str {
        match self {
            Page::Dashboard => "Boshqaruv paneli",
            Page::Tunnels => "Tunellar",
            Page::Keys => "Kalitlar",
            Page::Logs => "Jurnal",
            Page::Diagnostics => "Diagnostika",
            Page::Settings => "Sozlamalar",
            Page::Help => "Qo'llanma",
        }
    }

    pub fn subtitle(self) -> &'static str {
        match self {
            Page::Dashboard => "Tunellar holati, ulanishlar va trafik — jonli",
            Page::Tunnels => "Server va klient profillari: ishga tushirish, sozlash, kalit almashinuvi",
            Page::Keys => "ML-DSA-65 identity kalitlari: yaratish, eksport, muddat va rotatsiya",
            Page::Logs => "Barcha hodisalar: ulanishlar, rad etishlar va xatolar izohi bilan",
            Page::Diagnostics => "Port, manzil va tunelni tekshirish, sinov serveri, kripto o'z-o'zini tekshirish",
            Page::Settings => "Dastur sozlamalari va ma'lumot papkasi",
            Page::Help => "Sidecar nima, qanday ishga tushiriladi, xatolar va yechimlar",
        }
    }

    fn icon(self) -> Icon {
        match self {
            Page::Dashboard => Icon::Dashboard,
            Page::Tunnels => Icon::Tunnel,
            Page::Keys => Icon::Key,
            Page::Logs => Icon::Log,
            Page::Diagnostics => Icon::Pulse,
            Page::Settings => Icon::Settings,
            Page::Help => Icon::Help,
        }
    }
}

/// UI'dan keladigan amallar.
#[derive(Clone, Debug, PartialEq)]
pub enum Action {
    Goto(Page),
    Select(String),
    Start(String),
    Stop(String),
    StartAll,
    StopAll,
    NewProfile(Role),
    Edit(String),
    Duplicate(String),
    AskDelete(String),
    SaveInvite(String),
    CopyInvite(String),
    SaveRequest(String),
    CopyRequest(String),
    Test(String),
    ImportAllowFile(String),
    AddAllowText(String),
    AskRemoveAllow(String, usize),
    OpenWizard(Option<Scenario>),
    Copy(String, String),
    OpenFolder(PathBuf),
    CreateKey(String, u32),
    AskDeleteKey(String),
    AskRotateKey(String),
    ExportKeyPub(String),
}

pub enum Confirm {
    DeleteProfile(String),
    DeleteKey(String),
    RotateKey(String),
    RemoveAllow(String, usize),
    Exit,
}

pub struct Toast {
    pub text: String,
    pub color: Color32,
    pub until: Instant,
}

#[derive(Default)]
pub struct KeysUi {
    pub new_name: String,
    pub new_days: u32,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum LevelFilter {
    All,
    Problems,
    Errors,
}

pub struct LogsUi {
    pub profile: Option<String>,
    pub level: LevelFilter,
    pub search: String,
    pub autoscroll: bool,
    pub hide_closed: bool,
}

#[derive(Default)]
pub struct DiagUi {
    pub port_addr: String,
    pub port_result: Option<Result<String, String>>,
    pub reach_addr: String,
    pub reach_task: Option<Task<Result<f64, String>>>,
    pub reach_result: Option<Result<f64, String>>,
    pub probe_profile: Option<String>,
    pub probe_path: String,
    pub probe_task: Option<Task<Result<HttpProbe, String>>>,
    pub probe_result: Option<Result<HttpProbe, String>>,
    pub test_addr: String,
    pub test_server: Option<TestServer>,
    pub test_error: Option<String>,
    pub crypto_task: Option<Task<Result<f64, String>>>,
    pub crypto_result: Option<Result<f64, String>>,
    pub primary_ip: Option<String>,
}

pub struct App {
    pub store: Store,
    pub engine: Engine,
    pub keys: Vec<KeyInfo>,
    pub page: Page,
    pub toasts: Vec<Toast>,
    pub acts: Vec<Action>,
    pub selected: Option<String>,
    pub editor: Option<Editor>,
    pub confirm: Option<Confirm>,
    pub wizard: Option<Wizard>,
    pub keys_ui: KeysUi,
    pub logs_ui: LogsUi,
    pub diag: DiagUi,
    pub allow_text: String,
    pub allow_label: String,
    pub aqctl: Option<PathBuf>,
    pub now: i64,
    allow_exit: bool,
    autostarted: bool,
    /// Har bir profil bo'yicha oxirgi tunel sinovi (fon vazifa va natija).
    pub probes: Vec<(String, Task<Result<HttpProbe, String>>)>,
    pub probe_results: Vec<(String, Result<HttpProbe, String>)>,
    /// Keyingi kadrda buferga nusxalanadigan matn.
    pub pending_copy: Option<String>,
}

impl App {
    pub fn new(root: PathBuf) -> App {
        let store = Store::open(root);
        let s = store.cfg.settings.clone();
        let mut engine = Engine::new(store.logs_dir(), s.log_cap, s.log_to_file);
        if let Some(e) = &store.load_error {
            engine.note(Level::Error, "Studio", e.clone());
        }
        let aqctl = store.aqctl();
        let keys = keys::list(&store.keys_dir());
        let selected = store.cfg.profiles.first().map(|p| p.id.clone());
        let mut app = App {
            store,
            engine,
            keys,
            page: Page::Dashboard,
            toasts: Vec::new(),
            acts: Vec::new(),
            selected,
            editor: None,
            confirm: None,
            wizard: None,
            keys_ui: KeysUi { new_name: String::new(), new_days: s.key_days },
            logs_ui: LogsUi {
                profile: None,
                level: LevelFilter::All,
                search: String::new(),
                autoscroll: true,
                hide_closed: false,
            },
            diag: DiagUi {
                port_addr: "0.0.0.0:9443".into(),
                reach_addr: "127.0.0.1:8080".into(),
                probe_path: "/".into(),
                test_addr: "127.0.0.1:18080".into(),
                primary_ip: crate::diag::primary_ip(),
                ..Default::default()
            },
            allow_text: String::new(),
            allow_label: String::new(),
            aqctl,
            now: timefmt::now_unix(),
            allow_exit: false,
            autostarted: false,
            probes: Vec::new(),
            probe_results: Vec::new(),
            pending_copy: None,
        };
        app.engine.note(Level::Info, "Studio", format!("Dastur ochildi · ma'lumot papkasi: {}", app.store.root.display()));
        app
    }

    // ---------------------------------------------------------------- yordamchilar

    pub fn profile(&self, id: &str) -> Option<&Profile> {
        self.store.cfg.profiles.iter().find(|p| p.id == id)
    }

    fn profile_mut(&mut self, id: &str) -> Option<&mut Profile> {
        self.store.cfg.profiles.iter_mut().find(|p| p.id == id)
    }

    pub fn key_names(&self) -> Vec<String> {
        self.keys.iter().map(|k| k.name.clone()).collect()
    }

    pub fn key(&self, name: &str) -> Option<&KeyInfo> {
        self.keys.iter().find(|k| k.name == name)
    }

    pub fn refresh_keys(&mut self) {
        self.keys = keys::list(&self.store.keys_dir());
    }

    pub fn toast(&mut self, text: impl Into<String>, color: Color32) {
        self.toasts.push(Toast { text: text.into(), color, until: Instant::now() + Duration::from_secs(5) });
        if self.toasts.len() > 4 {
            self.toasts.remove(0);
        }
    }

    pub fn ok(&mut self, text: impl Into<String>) {
        self.toast(text, GREEN);
    }

    pub fn err(&mut self, text: impl Into<String>) {
        self.toast(text, RED);
    }

    fn save(&mut self) {
        if let Err(e) = self.store.save() {
            self.err(e);
        }
    }

    /// Profilni ishga tushirishdan oldin to'sqinlik qiluvchi muammolar.
    pub fn blocking_issues(&self, p: &Profile) -> Vec<String> {
        model::validate(p, &self.key_names(), &self.store.cfg.profiles, self.aqctl.is_some())
            .into_iter()
            .filter(|i| i.blocking)
            .map(|i| i.msg)
            .collect()
    }

    // ---------------------------------------------------------------- amallar

    pub fn start(&mut self, id: &str) -> Result<(), String> {
        let p = self.profile(id).cloned().ok_or("profil topilmadi")?;
        let issues = self.blocking_issues(&p);
        if let Some(first) = issues.first() {
            return Err(format!("«{}» ishga tushmadi: {first}", p.name));
        }
        let (kd, rd) = (self.store.keys_dir(), self.store.run_dir());
        self.engine.start(&p, &kd, &rd, self.aqctl.as_deref()).map_err(|e| format!("«{}»: {e}", p.name))
    }

    pub fn stop(&mut self, id: &str) {
        self.engine.stop(id);
    }

    /// Yangi yoki tahrirlangan profilni saqlaydi. Ishlab turgan bo'lsa — qayta ishga tushiradi.
    pub fn save_profile(&mut self, p: Profile) -> Result<(), String> {
        let was_running = self.engine.is_running(&p.id);
        match self.store.cfg.profiles.iter_mut().find(|x| x.id == p.id) {
            Some(x) => *x = p.clone(),
            None => self.store.cfg.profiles.push(p.clone()),
        }
        self.store.save()?;
        self.selected = Some(p.id.clone());
        if was_running {
            self.engine.stop(&p.id);
            self.start(&p.id)?;
        }
        Ok(())
    }

    pub fn delete_profile(&mut self, id: &str) {
        self.engine.stop(id);
        self.store.cfg.profiles.retain(|p| p.id != id);
        let _ = std::fs::remove_file(self.store.run_dir().join(format!("{id}.allow.txt")));
        if self.selected.as_deref() == Some(id) {
            self.selected = self.store.cfg.profiles.first().map(|p| p.id.clone());
        }
        self.save();
    }

    pub fn duplicate_profile(&mut self, id: &str) -> Option<String> {
        let mut p = self.profile(id)?.clone();
        p.id = model::new_id();
        p.name = format!("{} (nusxa)", p.name);
        p.autostart = false;
        // Nusxa boshqa portda bo'lsin: port +1.
        if let Some((h, port)) = model::split_host_port(&p.listen) {
            let h = if h.contains(':') { format!("[{h}]") } else { h };
            p.listen = format!("{h}:{}", port.saturating_add(1));
        }
        let new_id = p.id.clone();
        self.store.cfg.profiles.push(p);
        self.selected = Some(new_id.clone());
        self.save();
        Some(new_id)
    }

    /// Server profilining taklif fayli matni (JSON).
    pub fn invite_json(&self, id: &str) -> Result<String, String> {
        let p = self.profile(id).ok_or("profil topilmadi")?;
        if p.role != Role::Server {
            return Err("Taklif fayli faqat server profilidan olinadi.".into());
        }
        let key = self.key(&p.identity).ok_or("Server kaliti topilmadi.")?;
        let port = model::split_host_port(&p.listen).map(|x| x.1).unwrap_or(9443);
        let host = if !p.public_host.trim().is_empty() {
            p.public_host.trim().to_string()
        } else {
            match model::split_host_port(&p.listen).map(|x| x.0) {
                Some(h) if h != "0.0.0.0" && h != "::" => h,
                _ => self.diag.primary_ip.clone().unwrap_or_else(|| "127.0.0.1".into()),
            }
        };
        let host = if host.contains(':') && !host.starts_with('[') { format!("[{host}]") } else { host };
        let inv = keys::make_invite(&p.name, &format!("{host}:{port}"), p.mode, key, p.require_client_auth);
        serde_json::to_string_pretty(&inv).map_err(|e| e.to_string())
    }

    /// Klient profilining ruxsat so'rovi matni (JSON).
    pub fn request_json(&self, id: &str) -> Result<String, String> {
        let p = self.profile(id).ok_or("profil topilmadi")?;
        if p.identity.is_empty() {
            return Err("Klient profiliga kalit tanlanmagan — avval kalit tanlang.".into());
        }
        let key = self.key(&p.identity).ok_or("Klient kaliti topilmadi.")?;
        // Server allowlist'ida klient shu nom bilan ko'rinadi — profil nomi (ko'pincha server nomi) emas, kompyuter nomi.
        let name = format!("{} kompyuteri", crate::diag::hostname());
        serde_json::to_string_pretty(&keys::make_request(&name, key)).map_err(|e| e.to_string())
    }

    /// Server allowlist'iga klient kalitini qo'shadi (so'rov JSON, .pub yoki hex).
    pub fn add_allow(&mut self, id: &str, text: &str, label: &str) -> Result<String, String> {
        let fallback = if label.trim().is_empty() { "Klient".to_string() } else { label.trim().to_string() };
        let (name, pk) = keys::parse_client_key(text, &fallback)?;
        let name = if label.trim().is_empty() { name } else { label.trim().to_string() };
        let hex = aq_core::identity::to_hex(&pk);
        let p = self.profile_mut(id).ok_or("profil topilmadi")?;
        if p.role != Role::Server {
            return Err("Allowlist faqat server profilida bo'ladi.".into());
        }
        if p.allow.iter().any(|a| model::parse_pub_hex(&a.pub_hex).as_deref() == Some(pk.as_slice())) {
            return Err(format!("Bu kalit allowlist'da allaqachon bor ({}).", keys::fingerprint(&pk)));
        }
        p.allow.push(AllowEntry { label: name.clone(), pub_hex: hex, added: timefmt::rfc3339(timefmt::now_unix()) });
        let p = p.clone();
        self.save_profile(p)?;
        Ok(format!("«{name}» allowlist'ga qo'shildi ({})", keys::fingerprint(&pk)))
    }

    pub fn remove_allow(&mut self, id: &str, idx: usize) -> Result<String, String> {
        let p = self.profile_mut(id).ok_or("profil topilmadi")?;
        if idx >= p.allow.len() {
            return Err("yozuv topilmadi".into());
        }
        let e = p.allow.remove(idx);
        let p = p.clone();
        self.save_profile(p)?;
        Ok(format!("«{}» allowlist'dan olib tashlandi", e.label))
    }

    pub fn create_key(&mut self, name: &str, days: u32) -> Result<KeyInfo, String> {
        let k = keys::create(&self.store.keys_dir(), name.trim(), days)?;
        self.refresh_keys();
        self.engine.note(Level::Info, "Kalitlar", format!("Yangi kalit «{}» yaratildi ({}, {days} kun)", k.name, k.fingerprint));
        Ok(k)
    }

    pub fn profiles_using_key(&self, name: &str) -> Vec<String> {
        self.store.cfg.profiles.iter().filter(|p| p.identity == name).map(|p| p.name.clone()).collect()
    }

    pub fn delete_key(&mut self, name: &str) -> Result<(), String> {
        let users = self.profiles_using_key(name);
        if !users.is_empty() {
            return Err(format!("«{name}» kaliti ishlatilmoqda: {}. Avval profildan boshqa kalit tanlang.", users.join(", ")));
        }
        keys::delete(&self.store.keys_dir(), name)?;
        self.refresh_keys();
        self.engine.note(Level::Info, "Kalitlar", format!("«{name}» kaliti o'chirildi"));
        Ok(())
    }

    /// Rotatsiya: yangi kalit yaratiladi va uni ishlatgan profillar yangisiga o'tadi (ishlab turganlari qayta
    /// ishga tushadi). Eski kalit fayli saqlanadi — qarshi tomonlar yangilangandan keyin qo'lda o'chiriladi.
    pub fn rotate_key(&mut self, name: &str) -> Result<String, String> {
        let days = self.key(name).and_then(|k| k.created.zip(k.not_after)).map(|(c, n)| ((n - c) / 86_400) as u32);
        let new = keys::next_name(&self.key_names(), name);
        self.create_key(&new, days.unwrap_or(self.store.cfg.settings.key_days))?;
        let ids: Vec<String> = self.store.cfg.profiles.iter().filter(|p| p.identity == name).map(|p| p.id.clone()).collect();
        for id in &ids {
            if let Some(p) = self.profile(id).cloned() {
                let mut p = p;
                p.identity = new.clone();
                self.save_profile(p)?;
            }
        }
        Ok(format!(
            "«{new}» yaratildi; {} ta profil unga o'tdi. Qarshi tomonga yangi taklif/ruxsat so'rovini yuboring.",
            ids.len()
        ))
    }

    /// Tunel orqali HTTP sinovi (klient profili; fon vazifa).
    pub fn test_profile(&mut self, id: &str) -> Result<(), String> {
        let p = self.profile(id).cloned().ok_or("profil topilmadi")?;
        if p.role != Role::Client {
            return Err("Sinov klient profilida bajariladi (server tomonida — Diagnostika → manzilga ulanish).".into());
        }
        if !self.engine.is_running(id) {
            self.start(id)?;
        }
        let addr = local_dial_addr(&p.listen);
        self.probes.retain(|(pid, _)| pid != id);
        self.probe_results.retain(|(pid, _)| pid != id);
        self.probes.push((id.to_string(), Task::spawn(move || crate::diag::http_probe(&addr, "/"))));
        Ok(())
    }

    /// Dastur ochilganda avtomatik ishga tushirish.
    fn autostart(&mut self) {
        if self.autostarted {
            return;
        }
        self.autostarted = true;
        if !self.store.cfg.settings.autostart_enabled {
            return;
        }
        let ids: Vec<String> = self.store.cfg.profiles.iter().filter(|p| p.autostart).map(|p| p.id.clone()).collect();
        for id in ids {
            if let Err(e) = self.start(&id) {
                self.engine.note(Level::Error, "Avtomatik ishga tushirish", e);
            }
        }
    }

    pub fn apply(&mut self, a: Action) {
        match a {
            Action::Goto(p) => self.page = p,
            Action::Select(id) => self.selected = Some(id),
            Action::Start(id) => match self.start(&id) {
                Ok(()) => {
                    let n = self.profile(&id).map(|p| p.name.clone()).unwrap_or_default();
                    self.ok(format!("«{n}» ishga tushdi"));
                }
                Err(e) => self.err(e),
            },
            Action::Stop(id) => {
                self.stop(&id);
                let n = self.profile(&id).map(|p| p.name.clone()).unwrap_or_default();
                self.ok(format!("«{n}» to'xtatildi"));
            }
            Action::StartAll => {
                let ids: Vec<String> = self.store.cfg.profiles.iter().map(|p| p.id.clone()).collect();
                let (mut ok, mut bad) = (0, Vec::new());
                for id in ids {
                    if self.engine.is_running(&id) {
                        continue;
                    }
                    match self.start(&id) {
                        Ok(()) => ok += 1,
                        Err(e) => bad.push(e),
                    }
                }
                if bad.is_empty() {
                    self.ok(format!("{ok} ta tunel ishga tushdi"));
                } else {
                    self.err(format!("{ok} ta ishga tushdi, {} ta xato: {}", bad.len(), bad[0]));
                }
            }
            Action::StopAll => {
                let n = self.engine.running_count();
                self.engine.stop_all();
                self.ok(format!("{n} ta tunel to'xtatildi"));
            }
            Action::NewProfile(role) => self.editor = Some(Editor::new(Profile::new(role), true, self)),
            Action::Edit(id) => {
                if let Some(p) = self.profile(&id).cloned() {
                    self.editor = Some(Editor::new(p, false, self));
                }
            }
            Action::Duplicate(id) => {
                if self.duplicate_profile(&id).is_some() {
                    self.ok("Nusxa yaratildi (port +1). Tahrirlab, saqlang.");
                }
            }
            Action::AskDelete(id) => self.confirm = Some(Confirm::DeleteProfile(id)),
            Action::SaveInvite(id) => match self.invite_json(&id) {
                Ok(js) => {
                    let name = self.profile(&id).map(|p| p.name.clone()).unwrap_or_default();
                    if let Some(path) = rfd::FileDialog::new()
                        .set_title("Taklif faylini saqlash")
                        .add_filter("AETHER-Q taklifi", &["aqinvite"])
                        .set_file_name(format!("{}.aqinvite", safe_file_name(&name)))
                        .save_file()
                    {
                        match std::fs::write(&path, js) {
                            Ok(()) => self.ok(format!("Taklif saqlandi: {}", path.display())),
                            Err(e) => self.err(format!("Saqlanmadi: {e}")),
                        }
                    }
                }
                Err(e) => self.err(e),
            },
            Action::CopyInvite(id) => match self.invite_json(&id) {
                Ok(js) => {
                    self.pending_copy = Some(js);
                    self.ok("Taklif matni nusxalandi");
                }
                Err(e) => self.err(e),
            },
            Action::SaveRequest(id) => match self.request_json(&id) {
                Ok(js) => {
                    if let Some(path) = rfd::FileDialog::new()
                        .set_title("Ruxsat so'rovini saqlash")
                        .add_filter("AETHER-Q ruxsat so'rovi", &["aqrequest"])
                        .set_file_name(format!("{}.aqrequest", safe_file_name(&crate::diag::hostname())))
                        .save_file()
                    {
                        match std::fs::write(&path, js) {
                            Ok(()) => self.ok(format!("Ruxsat so'rovi saqlandi: {}", path.display())),
                            Err(e) => self.err(format!("Saqlanmadi: {e}")),
                        }
                    }
                }
                Err(e) => self.err(e),
            },
            Action::CopyRequest(id) => match self.request_json(&id) {
                Ok(js) => {
                    self.pending_copy = Some(js);
                    self.ok("Ruxsat so'rovi nusxalandi");
                }
                Err(e) => self.err(e),
            },
            Action::Test(id) => {
                if let Err(e) = self.test_profile(&id) {
                    self.err(e);
                }
            }
            Action::ImportAllowFile(id) => {
                if let Some(path) = rfd::FileDialog::new()
                    .set_title("Klient ruxsat so'rovi yoki .pub faylini tanlang")
                    .add_filter("Ruxsat so'rovi yoki ochiq kalit", &["aqrequest", "pub", "json", "txt"])
                    .pick_file()
                {
                    let label = path.file_stem().and_then(|s| s.to_str()).unwrap_or("Klient").to_string();
                    match std::fs::read_to_string(&path).map_err(|e| e.to_string()).and_then(|t| self.add_allow(&id, &t, if t.trim_start().starts_with('{') { "" } else { &label })) {
                        Ok(m) => self.ok(m),
                        Err(e) => self.err(e),
                    }
                }
            }
            Action::AddAllowText(id) => {
                let (text, label) = (self.allow_text.clone(), self.allow_label.clone());
                match self.add_allow(&id, &text, &label) {
                    Ok(m) => {
                        self.allow_text.clear();
                        self.allow_label.clear();
                        self.ok(m)
                    }
                    Err(e) => self.err(e),
                }
            }
            Action::AskRemoveAllow(id, i) => self.confirm = Some(Confirm::RemoveAllow(id, i)),
            Action::OpenWizard(s) => self.wizard = Some(Wizard::new(s, self)),
            Action::Copy(text, msg) => {
                self.pending_copy = Some(text);
                self.ok(msg);
            }
            Action::OpenFolder(p) => open_path(&p),
            Action::CreateKey(name, days) => match self.create_key(&name, days) {
                Ok(k) => {
                    self.keys_ui.new_name.clear();
                    self.ok(format!("«{}» kaliti yaratildi ({})", k.name, k.fingerprint));
                }
                Err(e) => self.err(e),
            },
            Action::AskDeleteKey(n) => self.confirm = Some(Confirm::DeleteKey(n)),
            Action::AskRotateKey(n) => self.confirm = Some(Confirm::RotateKey(n)),
            Action::ExportKeyPub(n) => {
                if let Some(k) = self.key(&n).cloned() {
                    if let Some(path) = rfd::FileDialog::new()
                        .set_title("Ochiq kalitni saqlash")
                        .add_filter("Ochiq kalit", &["pub"])
                        .set_file_name(format!("{}.pub", k.name))
                        .save_file()
                    {
                        match std::fs::write(&path, format!("{}\n", k.pub_hex())) {
                            Ok(()) => self.ok(format!("Ochiq kalit saqlandi: {}", path.display())),
                            Err(e) => self.err(format!("Saqlanmadi: {e}")),
                        }
                    }
                }
            }
        }
    }

    fn confirm_action(&mut self, c: Confirm) {
        match c {
            Confirm::DeleteProfile(id) => {
                let n = self.profile(&id).map(|p| p.name.clone()).unwrap_or_default();
                self.delete_profile(&id);
                self.ok(format!("«{n}» o'chirildi"));
            }
            Confirm::DeleteKey(n) => match self.delete_key(&n) {
                Ok(()) => self.ok(format!("«{n}» kaliti o'chirildi")),
                Err(e) => self.err(e),
            },
            Confirm::RotateKey(n) => match self.rotate_key(&n) {
                Ok(m) => self.ok(m),
                Err(e) => self.err(e),
            },
            Confirm::RemoveAllow(id, i) => match self.remove_allow(&id, i) {
                Ok(m) => self.ok(m),
                Err(e) => self.err(e),
            },
            Confirm::Exit => {}
        }
    }

    // ---------------------------------------------------------------- kadr

    /// Bir kadr: holatni yangilash, panellar, modal oynalar, amallarni bajarish.
    pub fn frame(&mut self, ui: &mut egui::Ui) {
        let ctx = ui.ctx().clone();
        self.now = timefmt::now_unix();
        self.autostart();
        self.engine.tick();
        self.poll_tasks();
        if let Some(t) = self.pending_copy.take() {
            ctx.copy_text(t);
        }
        self.handle_close(&ctx);

        self.sidebar(ui);
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(theme::BG).inner_margin(egui::Margin { left: 26, right: 26, top: 20, bottom: 12 }))
            .show(ui, |ui| {
                self.header(ui);
                ui.add_space(6.0);
                egui::ScrollArea::vertical().id_salt(("page", self.page as u8)).auto_shrink([false, false]).show(ui, |ui| {
                    match self.page {
                        Page::Dashboard => self.page_dashboard(ui),
                        Page::Tunnels => self.page_tunnels(ui),
                        Page::Keys => self.page_keys(ui),
                        Page::Logs => self.page_logs(ui),
                        Page::Diagnostics => self.page_diagnostics(ui),
                        Page::Settings => self.page_settings(ui),
                        Page::Help => self.page_help(ui),
                    }
                    ui.add_space(16.0);
                });
            });

        self.modals(&ctx);
        self.draw_toasts(&ctx);

        let acts = std::mem::take(&mut self.acts);
        for a in acts {
            self.apply(a);
        }
        let busy = self.engine.running_count() > 0 || !self.probes.is_empty() || self.diag_busy();
        ctx.request_repaint_after(Duration::from_millis(if busy { 250 } else { 1000 }));
    }

    fn diag_busy(&self) -> bool {
        self.diag.reach_task.is_some() || self.diag.probe_task.is_some() || self.diag.crypto_task.is_some()
    }

    /// Bo'sh javobli sinov natijasiga sabab qo'shadi: klientning o'z xatosi (kalit, allowlist, manzil) bo'lsa — o'sha,
    /// aks holda tunel ochilgan, lekin server tomonidagi ilova javob bermagan.
    pub fn explain_probe(&self, id: &str, r: Result<HttpProbe, String>) -> Result<HttpProbe, String> {
        match r {
            Err(e) if e == crate::diag::EMPTY_REPLY => Err(match self.engine.last_error.get(id) {
                Some((m, h)) if !h.is_empty() => format!("{m} — {h}"),
                Some((m, _)) => m.clone(),
                None => "Tunel ochildi (handshake muvaffaqiyatli), lekin javob kelmadi: server tomonidagi ilova ishlamayotgan \
                         bo'lishi mumkin — server jurnalini tekshiring."
                    .to_string(),
            }),
            other => other,
        }
    }

    #[cfg(test)]
    pub fn frame_tasks_for_test(&mut self) {
        self.poll_tasks();
    }

    fn poll_tasks(&mut self) {
        let mut done = Vec::new();
        self.probes.retain(|(id, t)| match t.poll() {
            Some(r) => {
                done.push((id.clone(), r));
                false
            }
            None => true,
        });
        for (id, r) in done {
            let name = self.profile(&id).map(|p| p.name.clone()).unwrap_or_default();
            // Bo'sh javob: sababni aniqlashtiramiz — klientning o'z xatosi bo'lsa (kalit, allowlist, manzil) o'shani,
            // aks holda tunel ochilgan, lekin server tomonidagi ilova javob bermagan.
            let r = self.explain_probe(&id, r);
            match &r {
                Ok(p) => {
                    let msg = format!("«{name}» sinovi: {} · {:.1} ms", p.status_line, p.ms);
                    self.engine.note(Level::Info, "Sinov", msg.clone());
                    self.ok(msg);
                }
                Err(e) => {
                    self.engine.note(Level::Error, "Sinov", format!("«{name}»: {e}"));
                    self.err(format!("«{name}» sinovi muvaffaqiyatsiz: {e}"));
                }
            }
            self.probe_results.retain(|(pid, _)| pid != &id);
            self.probe_results.push((id, r));
        }
        if let Some(r) = self.diag.reach_task.as_ref().and_then(|t| t.poll()) {
            self.diag.reach_result = Some(r);
            self.diag.reach_task = None;
        }
        if let Some(r) = self.diag.probe_task.as_ref().and_then(|t| t.poll()) {
            let id = self.diag.probe_profile.clone().unwrap_or_default();
            self.diag.probe_result = Some(self.explain_probe(&id, r));
            self.diag.probe_task = None;
        }
        if let Some(r) = self.diag.crypto_task.as_ref().and_then(|t| t.poll()) {
            match &r {
                Ok(ms) => self.engine.note(Level::Info, "Diagnostika", format!("Kripto o'z-o'zini tekshirish o'tdi: {ms:.2} ms/handshake")),
                Err(e) => self.engine.note(Level::Error, "Diagnostika", format!("Kripto o'z-o'zini tekshirish: {e}")),
            }
            self.diag.crypto_result = Some(r);
            self.diag.crypto_task = None;
        }
        if let Some(w) = self.wizard.as_mut() {
            w.poll();
        }
    }

    fn handle_close(&mut self, ctx: &egui::Context) {
        if ctx.input(|i| i.viewport().close_requested())
            && !self.allow_exit
            && self.engine.running_count() > 0
            && self.store.cfg.settings.confirm_exit
        {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.confirm = Some(Confirm::Exit);
        }
    }

    pub fn shutdown(&mut self) {
        self.engine.stop_all();
        if let Some(t) = self.diag.test_server.take() {
            t.stop();
        }
    }

    fn sidebar(&mut self, ui: &mut egui::Ui) {
        egui::Panel::left("nav")
            .resizable(false)
            .exact_size(232.0)
            .frame(egui::Frame::new().fill(SIDEBAR).inner_margin(egui::Margin::symmetric(14, 18)))
            .show(ui, |ui| {
                ui.horizontal(|ui| {
                    let (r, _) = ui.allocate_exact_size(egui::vec2(40.0, 40.0), egui::Sense::hover());
                    icons::logo(ui.painter(), r);
                    ui.vertical(|ui| {
                        ui.spacing_mut().item_spacing.y = 0.0;
                        ui.label(RichText::new("AETHER-Q").font(theme::heading(17.0)).color(TEXT));
                        ui.label(RichText::new("Sidecar Studio").size(12.5).color(ACCENT));
                    });
                });
                ui.add_space(18.0);
                let running = self.engine.running_count();
                let warn_keys = self.keys.iter().filter(|k| matches!(k.state(self.now), keys::KeyState::RotateSoon | keys::KeyState::Expired)).count();
                for page in Page::ALL {
                    let selected = self.page == page;
                    let badge = match page {
                        Page::Tunnels if running > 0 => Some((running.to_string(), GREEN)),
                        Page::Keys if warn_keys > 0 => Some((warn_keys.to_string(), theme::AMBER)),
                        _ => None,
                    };
                    let resp = nav_item(ui, page, selected, badge);
                    if resp.clicked() {
                        self.acts.push(Action::Goto(page));
                    }
                }
                ui.with_layout(egui::Layout::bottom_up(egui::Align::Min), |ui| {
                    ui.label(
                        RichText::new(format!("v{} · protokol {:#06x}", env!("CARGO_PKG_VERSION"), aq_core::PROTOCOL_VERSION))
                            .size(11.0)
                            .color(FAINT),
                    );
                    ui.add_space(4.0);
                    let (txt, col) = if running > 0 {
                        (format!("{running} ta tunel ishlayapti"), GREEN)
                    } else {
                        ("Hech narsa ishlamayapti".to_string(), FAINT)
                    };
                    theme::pill(ui, &txt, col);
                });
            });
    }

    fn header(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.vertical(|ui| {
                ui.spacing_mut().item_spacing.y = 2.0;
                ui.label(RichText::new(self.page.title()).font(theme::heading(24.0)).color(TEXT));
                ui.label(RichText::new(self.page.subtitle()).size(13.0).color(MUTED));
            });
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if matches!(self.page, Page::Dashboard | Page::Tunnels) {
                    if theme::primary(ui, "+ Yangi tunel", true).on_hover_text("Server yoki klient profilini qo'lda yaratish").clicked() {
                        self.acts.push(Action::NewProfile(Role::Client));
                    }
                    if theme::secondary(ui, "✨ Tez sozlash ustasi", true)
                        .on_hover_text("3 qadamda: demo, server yoki klient")
                        .clicked()
                    {
                        self.acts.push(Action::OpenWizard(None));
                    }
                    let n = self.engine.running_count();
                    let total = self.store.cfg.profiles.len();
                    if n > 0 {
                        if theme::secondary(ui, "■ Hammasini to'xtatish", true).clicked() {
                            self.acts.push(Action::StopAll);
                        }
                    } else if total > 0 && theme::secondary(ui, "▶ Hammasini ishga tushirish", true).clicked() {
                        self.acts.push(Action::StartAll);
                    }
                }
            });
        });
    }

    fn draw_toasts(&mut self, ctx: &egui::Context) {
        let now = Instant::now();
        self.toasts.retain(|t| t.until > now);
        if self.toasts.is_empty() {
            return;
        }
        egui::Area::new(egui::Id::new("toasts"))
            .anchor(egui::Align2::RIGHT_BOTTOM, egui::vec2(-20.0, -20.0))
            .order(egui::Order::Foreground)
            .show(ctx, |ui| {
                ui.set_max_width(460.0);
                for t in &self.toasts {
                    egui::Frame::new()
                        .fill(CARD_HI)
                        .stroke(egui::Stroke::new(1.0, t.color))
                        .corner_radius(egui::CornerRadius::same(10))
                        .inner_margin(egui::Margin::symmetric(14, 10))
                        .show(ui, |ui| {
                            ui.add(egui::Label::new(RichText::new(&t.text).color(TEXT)).wrap());
                        });
                    ui.add_space(6.0);
                }
            });
    }

    fn modals(&mut self, ctx: &egui::Context) {
        // Profil muharriri
        if let Some(mut ed) = self.editor.take() {
            match ed.show(ctx, self) {
                crate::ui::editor::Outcome::Open => self.editor = Some(ed),
                crate::ui::editor::Outcome::Cancel => {}
                crate::ui::editor::Outcome::Save(p) => {
                    let name = p.name.clone();
                    let is_new = ed.is_new;
                    match self.save_profile(p) {
                        Ok(()) => {
                            self.page = Page::Tunnels;
                            self.ok(if is_new { format!("«{name}» yaratildi") } else { format!("«{name}» saqlandi") });
                        }
                        Err(e) => {
                            self.err(e);
                            self.editor = Some(ed);
                        }
                    }
                }
            }
        }
        // Tez sozlash ustasi
        if let Some(mut w) = self.wizard.take() {
            if w.show(ctx, self) {
                self.wizard = Some(w);
            }
        }
        // Tasdiqlash
        if let Some(c) = self.confirm.take() {
            let (title, body, yes, danger) = match &c {
                Confirm::DeleteProfile(id) => (
                    "Profilni o'chirish",
                    format!("«{}» profili o'chiriladi (ishlab turgan bo'lsa to'xtatiladi). Kalitlar o'chirilmaydi.", self.profile(id).map(|p| p.name.as_str()).unwrap_or("?")),
                    "O'chirish",
                    true,
                ),
                Confirm::DeleteKey(n) => (
                    "Kalitni o'chirish",
                    format!("«{n}» kaliti butunlay o'chiriladi. Bu kalit bilan bog'langan qarshi tomonlar ulana olmay qoladi. Davom etasizmi?"),
                    "O'chirish",
                    true,
                ),
                Confirm::RotateKey(n) => (
                    "Kalitni yangilash (rotatsiya)",
                    format!("«{n}» o'rniga yangi kalit yaratiladi va uni ishlatayotgan profillar yangisiga o'tadi. Keyin qarshi tomonga yangi taklif yoki ruxsat so'rovini yuborish kerak. Eski kalit fayli saqlanib qoladi."),
                    "Yangilash",
                    false,
                ),
                Confirm::RemoveAllow(id, i) => (
                    "Klientni allowlist'dan olib tashlash",
                    format!(
                        "«{}» endi bu serverga ulana olmaydi (keyingi ulanishdan boshlab).",
                        self.profile(id).and_then(|p| p.allow.get(*i)).map(|a| a.label.as_str()).unwrap_or("?")
                    ),
                    "Olib tashlash",
                    true,
                ),
                Confirm::Exit => (
                    "Dasturdan chiqish",
                    format!("{} ta tunel ishlab turibdi. Chiqsangiz, ular to'xtaydi va ulanishlar uziladi.", self.engine.running_count()),
                    "To'xtatib chiqish",
                    true,
                ),
            };
            let mut keep = true;
            let mut accepted = false;
            let resp = egui::Modal::new(egui::Id::new("confirm")).show(ctx, |ui| {
                ui.set_width(460.0);
                ui.label(RichText::new(title).font(theme::heading(18.0)).color(TEXT));
                ui.add_space(6.0);
                ui.add(egui::Label::new(RichText::new(body).color(MUTED)).wrap());
                ui.add_space(14.0);
                ui.horizontal(|ui| {
                    let yes_resp = if danger { theme::danger(ui, yes, true) } else { theme::primary(ui, yes, true) };
                    if yes_resp.clicked() {
                        accepted = true;
                        keep = false;
                    }
                    if theme::secondary(ui, "Bekor qilish", true).clicked() {
                        keep = false;
                    }
                });
            });
            if resp.should_close() {
                keep = false;
            }
            if accepted {
                if matches!(c, Confirm::Exit) {
                    self.allow_exit = true;
                    self.shutdown();
                    ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                } else {
                    self.confirm_action(c);
                }
            } else if keep {
                self.confirm = Some(c);
            }
        }
    }
}

fn nav_item(ui: &mut egui::Ui, page: Page, selected: bool, badge: Option<(String, Color32)>) -> egui::Response {
    let h = 40.0;
    let (rect, resp) = ui.allocate_exact_size(egui::vec2(ui.available_width(), h), egui::Sense::click());
    let p = ui.painter_at(rect);
    let hovered = resp.hovered();
    if selected || hovered {
        p.rect_filled(rect, 10.0, if selected { CARD_HI } else { CARD_HI.gamma_multiply(0.5) });
    }
    if selected {
        p.rect_filled(egui::Rect::from_min_size(rect.min + egui::vec2(0.0, 9.0), egui::vec2(3.0, h - 18.0)), 2.0, ACCENT);
    }
    let col = if selected { ACCENT } else if hovered { TEXT } else { MUTED };
    icons::paint(&p, egui::Rect::from_center_size(egui::pos2(rect.left() + 24.0, rect.center().y), egui::vec2(18.0, 18.0)), page.icon(), col);
    p.text(
        egui::pos2(rect.left() + 46.0, rect.center().y),
        egui::Align2::LEFT_CENTER,
        page.title(),
        egui::FontId::new(14.5, if selected { theme::semibold() } else { egui::FontFamily::Proportional }),
        if selected { TEXT } else { MUTED },
    );
    if let Some((txt, c)) = badge {
        let r = egui::Rect::from_center_size(egui::pos2(rect.right() - 20.0, rect.center().y), egui::vec2(24.0, 18.0));
        p.rect_filled(r, 9.0, c.gamma_multiply(0.2));
        p.text(r.center(), egui::Align2::CENTER_CENTER, txt, egui::FontId::proportional(11.5), c);
    }
    ui.add_space(2.0);
    // Ekran o'quvchi va UI Automation uchun nom (qo'lda chizilgan element).
    resp.widget_info(|| egui::WidgetInfo::selected(egui::WidgetType::Button, true, selected, page.title()));
    resp.on_hover_text(page.subtitle()).on_hover_cursor(egui::CursorIcon::PointingHand)
}

/// 0.0.0.0 / [::] da tinglanayotgan port uchun mahalliy ulanish manzili.
pub fn local_dial_addr(listen: &str) -> String {
    match model::split_host_port(listen) {
        Some((h, p)) if h == "0.0.0.0" => format!("127.0.0.1:{p}"),
        Some((h, p)) if h == "::" => format!("[::1]:{p}"),
        _ => listen.trim().to_string(),
    }
}

pub fn safe_file_name(s: &str) -> String {
    let t: String = s.chars().map(|c| if c.is_alphanumeric() || c == '-' || c == '_' { c } else { '-' }).collect();
    let t = t.trim_matches('-').to_string();
    if t.is_empty() {
        "aetherq".into()
    } else {
        t
    }
}

pub fn open_path(p: &Path) {
    #[cfg(windows)]
    let _ = std::process::Command::new("explorer").arg(p).spawn();
    #[cfg(not(windows))]
    let _ = std::process::Command::new("xdg-open").arg(p).spawn();
}

impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        self.frame(ui);
    }

    fn on_exit(&mut self, _gl: Option<&eframe::glow::Context>) {
        self.shutdown();
    }

    fn clear_color(&self, _visuals: &egui::Visuals) -> [f32; 4] {
        theme::BG.to_normalized_gamma_f32()
    }
}
