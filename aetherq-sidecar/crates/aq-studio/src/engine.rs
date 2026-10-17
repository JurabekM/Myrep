//! Dvigatel: profillarni ishga tushirish/to'xtatish, hodisalarni jurnalga aylantirish, statistika va
//! grafiklar uchun vaqt qatorlari. AETHER-Q tunellari jarayon ichida (`aq_sidecar::runtime`),
//! standart rejim — `aqctl gateway` bola jarayoni.

use std::collections::{HashMap, VecDeque};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use aq_sidecar::runtime::{ConnectOptions, Event, ServeOptions, Tunnel};

use crate::gateway::{self, GwMetrics, GwProcess};
use crate::keys;
use crate::model::{parse_pub_hex, Mode, Profile, Role};
use crate::theme::fmt_bytes;
use crate::timefmt;

/// Grafik oynasi (soniya).
pub const SERIES_LEN: usize = 120;

pub enum Msg {
    Aq(String, Event),
    GwLine(String, String),
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Level {
    Info,
    Warn,
    Error,
}

impl Level {
    pub fn label(self) -> &'static str {
        match self {
            Level::Info => "Ma'lumot",
            Level::Warn => "Ogohlantirish",
            Level::Error => "Xato",
        }
    }
}

#[derive(Clone, Debug)]
pub struct LogEntry {
    pub t: i64,
    pub level: Level,
    /// Profil identifikatori ("" — dasturning o'zi).
    pub profile: String,
    pub source: String,
    pub msg: String,
    pub hint: String,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Status {
    Stopped,
    Starting,
    Running,
    Failed(String),
}

enum Backend {
    Aq(Tunnel),
    Gw(GwProcess),
}

struct Run {
    backend: Backend,
    started: Instant,
    name: String,
    role: Role,
    /// Allowlist yorliqlari: klient ochiq kaliti → nom.
    labels: Vec<(Vec<u8>, String)>,
    gw_total: u64,
    gw_failed: u64,
    last_lines: VecDeque<String>,
}

/// UI uchun profilning jonli holati. `None` — bu rejimda o'lchanmaydi.
#[derive(Clone, Debug, Default)]
pub struct Live {
    pub active: Option<u64>,
    pub total: u64,
    pub resumed: Option<u64>,
    pub failed: u64,
    pub to_net: Option<u64>,
    pub from_net: Option<u64>,
    pub hs_p50: Option<f64>,
    pub hs_p99: Option<f64>,
    pub uptime: Option<Duration>,
}

pub struct Engine {
    runs: HashMap<String, Run>,
    status: HashMap<String, Status>,
    tx: Sender<Msg>,
    rx: Receiver<Msg>,
    pub log: VecDeque<LogEntry>,
    log_cap: usize,
    log_to_file: bool,
    logs_dir: PathBuf,
    log_file: Option<(String, File)>,
    pub tz: i64,
    last_sample: Instant,
    prev_total: HashMap<String, u64>,
    pub rate: HashMap<String, VecDeque<f64>>,
    pub active: HashMap<String, VecDeque<f64>>,
    pub total_rate: VecDeque<f64>,
    pub total_active: VecDeque<f64>,
    /// Profilning oxirgi xatosi (matn, izoh) — kartochkada ko'rsatiladi.
    pub last_error: HashMap<String, (String, String)>,
    /// Jurnalga yangi yozuv tushgandan beri o'sib boradigan hisoblagich (UI auto-scroll uchun).
    pub log_seq: u64,
}

fn push_cap<T>(q: &mut VecDeque<T>, v: T, cap: usize) {
    if q.len() >= cap {
        q.pop_front();
    }
    q.push_back(v);
}

impl Engine {
    pub fn new(logs_dir: PathBuf, log_cap: usize, log_to_file: bool) -> Engine {
        let (tx, rx) = channel();
        Engine {
            runs: HashMap::new(),
            status: HashMap::new(),
            tx,
            rx,
            log: VecDeque::new(),
            log_cap: log_cap.max(100),
            log_to_file,
            logs_dir,
            log_file: None,
            tz: timefmt::local_offset(),
            last_sample: Instant::now(),
            prev_total: HashMap::new(),
            rate: HashMap::new(),
            active: HashMap::new(),
            total_rate: VecDeque::new(),
            total_active: VecDeque::new(),
            last_error: HashMap::new(),
            log_seq: 0,
        }
    }

    pub fn set_log_options(&mut self, cap: usize, to_file: bool) {
        self.log_cap = cap.max(100);
        self.log_to_file = to_file;
        while self.log.len() > self.log_cap {
            self.log.pop_front();
        }
    }

    pub fn status(&self, id: &str) -> Status {
        self.status.get(id).cloned().unwrap_or(Status::Stopped)
    }

    pub fn is_running(&self, id: &str) -> bool {
        self.runs.contains_key(id)
    }

    pub fn running_count(&self) -> usize {
        self.runs.len()
    }

    /// Dastur darajasidagi jurnal yozuvi.
    pub fn note(&mut self, level: Level, source: &str, msg: impl Into<String>) {
        self.push(LogEntry {
            t: timefmt::now_unix(),
            level,
            profile: String::new(),
            source: source.to_string(),
            msg: msg.into(),
            hint: String::new(),
        });
    }

    fn push(&mut self, e: LogEntry) {
        if self.log_to_file {
            self.write_file(&e);
        }
        push_cap(&mut self.log, e, self.log_cap);
        self.log_seq += 1;
    }

    fn write_file(&mut self, e: &LogEntry) {
        let date = timefmt::local_date(e.t, self.tz);
        if self.log_file.as_ref().map(|(d, _)| d != &date).unwrap_or(true) {
            let path = self.logs_dir.join(format!("studio-{}.log", date.replace('-', "")));
            self.log_file = OpenOptions::new().create(true).append(true).open(path).ok().map(|f| (date.clone(), f));
        }
        if let Some((_, f)) = self.log_file.as_mut() {
            let hint = if e.hint.is_empty() { String::new() } else { format!(" — {}", e.hint) };
            let _ = writeln!(
                f,
                "{} {} [{}] {}: {}{}",
                date,
                timefmt::local_hms(e.t, self.tz),
                e.level.label(),
                e.source,
                e.msg,
                hint
            );
        }
    }

    fn plog(&mut self, id: &str, name: &str, level: Level, msg: String, hint: &str) {
        if level != Level::Info {
            self.last_error.insert(id.to_string(), (msg.clone(), hint.to_string()));
        }
        self.push(LogEntry {
            t: timefmt::now_unix(),
            level,
            profile: id.to_string(),
            source: name.to_string(),
            msg,
            hint: hint.to_string(),
        });
    }

    /// Profilni ishga tushiradi. AETHER-Q darhol tinglay boshlaydi (yoki xato qaytaradi);
    /// standart rejim `Starting` holatida, aqctl tayyor deb yozguncha.
    pub fn start(&mut self, p: &Profile, keys_dir: &Path, run_dir: &Path, aqctl: Option<&Path>) -> Result<(), String> {
        if self.runs.contains_key(&p.id) {
            return Ok(());
        }
        let r = self.start_inner(p, keys_dir, run_dir, aqctl);
        match &r {
            Ok(backend) => {
                let st = if matches!(backend, Backend::Gw(_)) { Status::Starting } else { Status::Running };
                self.status.insert(p.id.clone(), st);
                self.last_error.remove(&p.id);
                self.prev_total.insert(p.id.clone(), 0);
            }
            Err(e) => {
                self.status.insert(p.id.clone(), Status::Failed(e.clone()));
                self.plog(&p.id, &p.name, Level::Error, format!("Ishga tushmadi: {e}"), start_hint(e));
            }
        }
        let backend = r?;
        let labels = p.allow.iter().filter_map(|a| parse_pub_hex(&a.pub_hex).map(|k| (k, a.label.clone()))).collect();
        let msg = match backend {
            Backend::Aq(_) => format!("Ishga tushdi: {} ({}, {})", p.route(), p.mode.label(), p.role.label().to_lowercase()),
            Backend::Gw(_) => format!("aqctl gateway ishga tushirilmoqda: {}", p.route()),
        };
        self.runs.insert(
            p.id.clone(),
            Run {
                backend,
                started: Instant::now(),
                name: p.name.clone(),
                role: p.role,
                labels,
                gw_total: 0,
                gw_failed: 0,
                last_lines: VecDeque::new(),
            },
        );
        self.plog(&p.id, &p.name, Level::Info, msg, "");
        Ok(())
    }

    fn start_inner(&mut self, p: &Profile, keys_dir: &Path, run_dir: &Path, aqctl: Option<&Path>) -> Result<Backend, String> {
        let identity = if p.identity.is_empty() { None } else { Some(keys::load_identity(keys_dir, &p.identity)?) };
        match p.mode {
            Mode::AetherQ => {
                let tx = Mutex::new(self.tx.clone());
                let id = p.id.clone();
                let sink: aq_sidecar::Sink = Arc::new(move |e| {
                    let _ = tx.lock().unwrap_or_else(|x| x.into_inner()).send(Msg::Aq(id.clone(), e));
                });
                let t = match p.role {
                    Role::Server => Tunnel::serve(
                        ServeOptions {
                            listen: p.listen.trim().to_string(),
                            upstream: p.target.trim().to_string(),
                            identity: identity.ok_or("server uchun kalit tanlanmagan")?,
                            require_client_auth: p.require_client_auth,
                            allowed: p.require_client_auth.then(|| p.allow_keys()),
                            resumption: p.resumption,
                            ticket_ttl: 3600,
                            pow: p.pow,
                        },
                        sink,
                    )?,
                    Role::Client => Tunnel::connect(
                        ConnectOptions {
                            listen: p.listen.trim().to_string(),
                            peer: p.target.trim().to_string(),
                            server_pub: parse_pub_hex(&p.server_pub).ok_or("server kaliti noto'g'ri")?,
                            identity,
                            resume: p.resumption,
                        },
                        sink,
                    )?,
                };
                Ok(Backend::Aq(t))
            }
            Mode::Standard => {
                let aqctl = aqctl.ok_or("aqctl.exe topilmadi (Sozlamalar → aqctl yo'li)")?;
                let key_file = |n: &str| keys_dir.join(format!("{n}.key")).display().to_string();
                let mut args: Vec<String>;
                let mut metrics = None;
                match p.role {
                    Role::Server => {
                        args = vec!["gateway", "serve", "--listen", p.listen.trim(), "--upstream", p.target.trim()]
                            .into_iter()
                            .map(String::from)
                            .collect();
                        args.extend(["--identity".into(), key_file(&p.identity)]);
                        if p.require_client_auth {
                            let allow: Vec<(String, Vec<u8>)> = p
                                .allow
                                .iter()
                                .filter_map(|a| parse_pub_hex(&a.pub_hex).map(|k| (a.label.clone(), k)))
                                .collect();
                            let f = run_dir.join(format!("{}.allow.txt", p.id));
                            std::fs::write(&f, keys::allowlist_text(&allow)).map_err(|e| format!("allowlist yozilmadi: {e}"))?;
                            args.extend(["--require-client-auth".into(), "--allow".into(), f.display().to_string()]);
                        }
                        if let Some(port) = gateway::free_local_port() {
                            let addr = format!("127.0.0.1:{port}");
                            args.extend(["--metrics".into(), addr.clone()]);
                            metrics = Some(addr);
                        }
                    }
                    Role::Client => {
                        args = vec!["gateway", "connect", "--listen", p.listen.trim(), "--peer", p.target.trim()]
                            .into_iter()
                            .map(String::from)
                            .collect();
                        args.extend(["--server-pub".into(), p.server_pub.trim().to_string()]);
                        if !p.identity.is_empty() {
                            args.extend(["--identity".into(), key_file(&p.identity)]);
                        }
                    }
                }
                let g = gateway::spawn(aqctl, &args, &p.id, self.tx.clone(), metrics)
                    .map_err(|e| format!("aqctl ishga tushmadi: {e}"))?;
                Ok(Backend::Gw(g))
            }
        }
    }

    pub fn stop(&mut self, id: &str) {
        if let Some(run) = self.runs.remove(id) {
            match run.backend {
                Backend::Aq(t) => t.stop(),
                Backend::Gw(g) => g.kill(),
            }
            self.status.insert(id.to_string(), Status::Stopped);
            let name = run.name.clone();
            self.plog(id, &name, Level::Info, "To'xtatildi".into(), "");
            // To'xtatilgan tunelning keyingi hodisalari (yopilish) jurnalni to'ldirmasin.
            self.drain_for(id);
        }
    }

    pub fn stop_all(&mut self) {
        let ids: Vec<String> = self.runs.keys().cloned().collect();
        for id in ids {
            self.stop(&id);
        }
    }

    fn drain_for(&mut self, id: &str) {
        let pending: Vec<Msg> = self.rx.try_iter().collect();
        for m in pending {
            let mine = match &m {
                Msg::Aq(pid, _) | Msg::GwLine(pid, _) => pid == id,
            };
            if !mine {
                self.handle(m);
            }
        }
    }

    /// Kadr boshida: hodisalarni qayta ishlash, gateway holati, soniyada bir marta namunalar.
    pub fn tick(&mut self) {
        let msgs: Vec<Msg> = self.rx.try_iter().take(5000).collect();
        for m in msgs {
            self.handle(m);
        }
        let mut exited = Vec::new();
        for (id, run) in self.runs.iter_mut() {
            if let Backend::Gw(g) = &mut run.backend {
                if let Some(code) = g.exited() {
                    exited.push((id.clone(), run.name.clone(), code, run.last_lines.back().cloned().unwrap_or_default()));
                }
            }
        }
        for (id, name, code, last) in exited {
            if let Some(run) = self.runs.remove(&id) {
                if let Backend::Gw(g) = run.backend {
                    g.kill();
                }
            }
            let why = if last.is_empty() { format!("kod {:?}", code) } else { last.clone() };
            self.status.insert(id.clone(), Status::Failed(why.clone()));
            self.plog(&id, &name, Level::Error, format!("aqctl gateway to'xtadi: {why}"), start_hint(&why));
        }
        let dt = self.last_sample.elapsed().as_secs_f64();
        if dt >= 1.0 {
            self.last_sample = Instant::now();
            let (mut sum_rate, mut sum_active) = (0.0, 0.0);
            let ids: Vec<String> = self.runs.keys().cloned().collect();
            for id in ids {
                let live = self.live(&id).unwrap_or_default();
                let prev = self.prev_total.insert(id.clone(), live.total).unwrap_or(live.total);
                let r = live.total.saturating_sub(prev) as f64 / dt;
                let a = live.active.unwrap_or(0) as f64;
                push_cap(self.rate.entry(id.clone()).or_default(), r, SERIES_LEN);
                push_cap(self.active.entry(id.clone()).or_default(), a, SERIES_LEN);
                sum_rate += r;
                sum_active += a;
            }
            push_cap(&mut self.total_rate, sum_rate, SERIES_LEN);
            push_cap(&mut self.total_active, sum_active, SERIES_LEN);
        }
    }

    fn label_for(run: &Run, pk: &[u8]) -> String {
        run.labels
            .iter()
            .find(|(k, _)| k.as_slice() == pk)
            .map(|(_, l)| format!("«{l}»"))
            .unwrap_or_else(|| format!("kalit {}", keys::fingerprint(pk)))
    }

    fn handle(&mut self, m: Msg) {
        match m {
            Msg::Aq(id, e) => self.handle_aq(&id, e),
            Msg::GwLine(id, line) => self.handle_gw(&id, line),
        }
    }

    fn handle_aq(&mut self, id: &str, e: Event) {
        let Some(run) = self.runs.get(id) else {
            return;
        };
        let name = run.name.clone();
        let server = run.role == Role::Server;
        let (level, msg, hint): (Level, String, &str) = match e {
            Event::Accepted { peer, client_pk, resumed, handshake_ms } => {
                let who = match &client_pk {
                    Some(pk) => Self::label_for(run, pk),
                    None => "kalitsiz klient".into(),
                };
                let r = if resumed { " · resumption" } else { "" };
                (Level::Info, format!("Klient ulandi: {peer} · {who} · handshake {handshake_ms:.1} ms{r}"), "")
            }
            Event::Opened { peer, resumed, handshake_ms } => {
                let r = if resumed { " · resumption" } else { "" };
                (Level::Info, format!("Tunel ochildi → {peer} · handshake {handshake_ms:.1} ms{r}"), "")
            }
            Event::Closed { peer, to_net, from_net, secs } => (
                Level::Info,
                format!("Tunel yopildi ({peer}) · ↑ {} ↓ {} · {:.1} s", fmt_bytes(to_net), fmt_bytes(from_net), secs),
                "",
            ),
            Event::HandshakeFailed { peer, error, hint, .. } => {
                if server {
                    (Level::Warn, format!("Ulanish rad etildi ({peer}): {error}"), hint)
                } else {
                    (Level::Error, format!("Handshake muvaffaqiyatsiz ({peer}): {error}"), hint)
                }
            }
            Event::DialFailed { target, error, hint } => {
                let what = if server { "Ilova" } else { "Server" };
                (Level::Error, format!("{what} manziliga ({target}) ulanib bo'lmadi: {error}"), hint)
            }
            Event::RecordError { error } => {
                (Level::Error, format!("Record xatosi: {error}"), "Tunelga soxta yoki buzilgan ma'lumot keldi; ulanish yopildi.")
            }
            Event::AcceptError { error } => (Level::Error, format!("Ulanishni qabul qilishda xato: {error}"), ""),
            Event::Stopped => return,
        };
        self.plog(id, &name, level, msg, hint);
    }

    fn handle_gw(&mut self, id: &str, line: String) {
        let Some(run) = self.runs.get_mut(id) else {
            return;
        };
        let text = line.strip_prefix("aqctl: ").unwrap_or(&line).to_string();
        push_cap(&mut run.last_lines, text.clone(), 20);
        let name = run.name.clone();
        if text.starts_with("gateway serve ") || text.starts_with("gateway connect ") {
            self.status.insert(id.to_string(), Status::Running);
            self.plog(id, &name, Level::Info, format!("Ishga tushdi: {text}"), "");
            return;
        }
        if text.starts_with("metrics:") {
            return;
        }
        let lower = text.to_lowercase();
        let bad = ["rad etildi", "ulanmadi", "allowlist'da yo'q", "sertifikati yo'q", "ml-dsa emas", "mos emas"]
            .iter()
            .any(|w| lower.contains(w));
        if text.contains("tunel ochildi") {
            run.gw_total += 1;
        }
        if bad && run.role == Role::Client {
            run.gw_failed += 1;
        }
        let hint = if lower.contains("pinned kalitga mos emas") {
            aq_sidecar::explain_alert(aq_core::error::alert::BAD_SIGNATURE)
        } else if lower.contains("allowlist'da yo'q") {
            aq_sidecar::explain_alert(aq_core::error::alert::BAD_CLIENT_AUTH)
        } else if lower.contains("ulanmadi") {
            "Manzilda dastur ishlamayapti, manzil noto'g'ri yoki firewall yopiq."
        } else {
            ""
        };
        let level = if bad { Level::Warn } else { Level::Info };
        self.plog(id, &name, level, text, hint);
    }

    /// Profilning jonli ko'rsatkichlari (ishlamayotgan bo'lsa None).
    pub fn live(&self, id: &str) -> Option<Live> {
        let run = self.runs.get(id)?;
        let uptime = Some(run.started.elapsed());
        Some(match &run.backend {
            Backend::Aq(t) => {
                let s = t.stats().snapshot();
                Live {
                    active: Some(s.active),
                    total: s.total,
                    resumed: Some(s.resumed),
                    failed: s.failed,
                    to_net: Some(s.to_net),
                    from_net: Some(s.from_net),
                    hs_p50: (s.hs_n > 0).then_some(s.hs_p50),
                    hs_p99: (s.hs_n > 0).then_some(s.hs_p99),
                    uptime,
                }
            }
            Backend::Gw(g) => match (&g.metrics, run.role) {
                (Some(m), Role::Server) => {
                    let m: GwMetrics = m.lock().unwrap_or_else(|p| p.into_inner()).clone();
                    let mean = (m.hs_count > 0).then(|| m.hs_sum * 1000.0 / m.hs_count as f64);
                    Live {
                        active: m.ok.then_some(m.active),
                        // Muvaffaqiyatli handshake'lar (allowlist tekshiruvidan keyin o'lchanadi).
                        total: m.hs_count,
                        resumed: None,
                        failed: m.failures,
                        to_net: m.ok.then_some(m.down),
                        from_net: m.ok.then_some(m.up),
                        hs_p50: mean,
                        hs_p99: None,
                        uptime,
                    }
                }
                _ => Live { total: run.gw_total, failed: run.gw_failed, uptime, ..Default::default() },
            },
        })
    }

    /// Barcha ishlayotgan profillar bo'yicha yig'indi.
    pub fn totals(&self) -> Live {
        let mut t = Live::default();
        let mut p50s = Vec::new();
        let mut p99s = Vec::new();
        for id in self.runs.keys() {
            if let Some(l) = self.live(id) {
                t.total += l.total;
                t.failed += l.failed;
                t.active = Some(t.active.unwrap_or(0) + l.active.unwrap_or(0));
                t.resumed = Some(t.resumed.unwrap_or(0) + l.resumed.unwrap_or(0));
                t.to_net = Some(t.to_net.unwrap_or(0) + l.to_net.unwrap_or(0));
                t.from_net = Some(t.from_net.unwrap_or(0) + l.from_net.unwrap_or(0));
                p50s.extend(l.hs_p50);
                p99s.extend(l.hs_p99);
            }
        }
        t.hs_p50 = (!p50s.is_empty()).then(|| p50s.iter().sum::<f64>() / p50s.len() as f64);
        t.hs_p99 = p99s.iter().copied().reduce(f64::max);
        t
    }

    pub fn clear_log(&mut self) {
        self.log.clear();
        self.log_seq += 1;
    }

    /// Jurnal yozuvini matn qatoriga (eksport va nusxalash uchun).
    pub fn format_entry(&self, e: &LogEntry) -> String {
        let hint = if e.hint.is_empty() { String::new() } else { format!(" — {}", e.hint) };
        format!(
            "{} {} [{}] {}: {}{}",
            timefmt::local_date(e.t, self.tz),
            timefmt::local_hms(e.t, self.tz),
            e.level.label(),
            e.source,
            e.msg,
            hint
        )
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        self.stop_all();
    }
}

/// Ishga tushish xatosiga izoh.
fn start_hint(e: &str) -> &'static str {
    let l = e.to_lowercase();
    if l.contains("10048") || l.contains("address already in use") || l.contains("addrinuse") || l.contains("bind") {
        "Port band: boshqa dastur yoki boshqa profil shu portni ishlatyapti. Portni o'zgartiring."
    } else if l.contains("10049") || l.contains("requested address") {
        "Bu IP manzil shu kompyuterga tegishli emas. 0.0.0.0 yoki 127.0.0.1 ishlating."
    } else if l.contains("kalit") || l.contains("identity") {
        "Kalitlar sahifasida kalit mavjudligini tekshiring."
    } else if l.contains("aqctl") {
        "Standart rejim uchun aqctl.exe dastur papkasida bo'lishi kerak."
    } else {
        ""
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{AllowEntry, Profile};
    use std::io::Read;
    use std::net::{TcpListener, TcpStream};

    fn tmpdir(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("aq-studio-engine-{tag}-{}", crate::model::new_id()));
        std::fs::create_dir_all(d.join("keys")).unwrap();
        std::fs::create_dir_all(d.join("logs")).unwrap();
        d
    }

    fn free_port() -> u16 {
        TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().port()
    }

    fn echo() -> String {
        let l = TcpListener::bind("127.0.0.1:0").unwrap();
        let a = l.local_addr().unwrap().to_string();
        std::thread::spawn(move || {
            for c in l.incoming().flatten() {
                std::thread::spawn(move || {
                    let mut c = c;
                    let mut b = [0u8; 4096];
                    while let Ok(n) = c.read(&mut b) {
                        if n == 0 || c.write_all(&b[..n]).is_err() {
                            break;
                        }
                    }
                });
            }
        });
        a
    }

    fn wait(mut f: impl FnMut() -> bool) -> bool {
        let t = Instant::now();
        while t.elapsed() < Duration::from_secs(10) {
            if f() {
                return true;
            }
            std::thread::sleep(Duration::from_millis(20));
        }
        false
    }

    #[test]
    fn start_tunnel_pair_in_process_logs_and_counts() {
        let d = tmpdir("pair");
        let kd = d.join("keys");
        let srv = keys::create(&kd, "srv", 30).unwrap();
        let cli = keys::create(&kd, "cli", 30).unwrap();
        let up = echo();
        let (sp, cp) = (free_port(), free_port());
        let mut s = Profile::new(Role::Server);
        s.name = "Server".into();
        s.listen = format!("127.0.0.1:{sp}");
        s.target = up;
        s.identity = "srv".into();
        s.allow.push(AllowEntry { label: "PC-1".into(), pub_hex: cli.pub_hex(), added: String::new() });
        let mut c = Profile::new(Role::Client);
        c.name = "Klient".into();
        c.listen = format!("127.0.0.1:{cp}");
        c.target = format!("127.0.0.1:{sp}");
        c.identity = "cli".into();
        c.server_pub = srv.pub_hex();

        let mut e = Engine::new(d.join("logs"), 1000, true);
        e.start(&s, &kd, &d, None).unwrap();
        e.start(&c, &kd, &d, None).unwrap();
        assert_eq!(e.status(&s.id), Status::Running);
        assert_eq!(e.running_count(), 2);

        let mut t = TcpStream::connect(("127.0.0.1", cp)).unwrap();
        t.write_all(b"salom").unwrap();
        let mut buf = [0u8; 5];
        t.read_exact(&mut buf).unwrap();
        assert_eq!(&buf, b"salom");
        drop(t);
        assert!(wait(|| {
            e.tick();
            e.live(&c.id).map(|l| l.total == 1 && l.active == Some(0)).unwrap_or(false)
        }));
        // Server jurnalida klient allowlist yorlig'i bilan ko'rinadi.
        assert!(e.log.iter().any(|l| l.msg.contains("Klient ulandi") && l.msg.contains("«PC-1»")), "{:?}", e.log);
        assert!(e.log.iter().any(|l| l.msg.contains("Tunel ochildi")));
        let tot = e.totals();
        assert_eq!(tot.total, 2);
        assert!(tot.to_net.unwrap() >= 10);

        // Port band: ikkinchi profil xuddi shu portda — tushunarli xato va Failed holati.
        let mut dup = c.clone();
        dup.id = "dup".into();
        assert!(e.start(&dup, &kd, &d, None).is_err());
        assert!(matches!(e.status("dup"), Status::Failed(_)));
        assert!(e.log.iter().any(|l| l.level == Level::Error && !l.hint.is_empty()));

        e.stop_all();
        assert_eq!(e.running_count(), 0);
        assert_eq!(e.status(&s.id), Status::Stopped);
        // Kunlik jurnal fayli yozildi.
        let files: Vec<_> = std::fs::read_dir(d.join("logs")).unwrap().flatten().collect();
        assert_eq!(files.len(), 1);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// Standart rejim: haqiqiy `aqctl gateway serve|connect` jarayonlari (dist\aqctl.exe bo'lsa).
    #[test]
    fn standard_mode_runs_aqctl_gateway_pair() {
        let aqctl = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..").join("dist").join("aqctl.exe");
        if !aqctl.is_file() {
            eprintln!("dist\\aqctl.exe yo'q — standart rejim sinovi o'tkazib yuborildi");
            return;
        }
        let d = tmpdir("std");
        let kd = d.join("keys");
        let srv = keys::create(&kd, "srv", 30).unwrap();
        let cli = keys::create(&kd, "cli", 30).unwrap();
        let (sp, cp) = (free_port(), free_port());
        let mut s = Profile::new(Role::Server);
        s.name = "Std server".into();
        s.mode = Mode::Standard;
        s.listen = format!("127.0.0.1:{sp}");
        s.target = echo();
        s.identity = "srv".into();
        s.allow.push(AllowEntry { label: "PC".into(), pub_hex: cli.pub_hex(), added: String::new() });
        let mut c = Profile::new(Role::Client);
        c.name = "Std klient".into();
        c.mode = Mode::Standard;
        c.listen = format!("127.0.0.1:{cp}");
        c.target = format!("127.0.0.1:{sp}");
        c.identity = "cli".into();
        c.server_pub = srv.pub_hex();
        let mut e = Engine::new(d.join("logs"), 1000, false);
        e.start(&s, &kd, &d, Some(&aqctl)).unwrap();
        e.start(&c, &kd, &d, Some(&aqctl)).unwrap();
        assert!(
            wait(|| {
                e.tick();
                e.status(&s.id) == Status::Running && e.status(&c.id) == Status::Running
            }),
            "aqctl tayyor bo'lmadi: {:?}",
            e.log
        );
        let mut t = TcpStream::connect(("127.0.0.1", cp)).unwrap();
        t.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
        t.write_all(b"salom").unwrap();
        let mut buf = [0u8; 5];
        t.read_exact(&mut buf).unwrap();
        assert_eq!(&buf, b"salom");
        drop(t);
        // Server statistikasi /metrics dan (soniyada bir so'raladi), klient — log qatoridan.
        assert!(
            wait(|| {
                e.tick();
                e.live(&s.id).map(|l| l.total >= 1).unwrap_or(false) && e.live(&c.id).map(|l| l.total >= 1).unwrap_or(false)
            }),
            "statistika kelmadi: {:?} / {:?}",
            e.live(&s.id),
            e.live(&c.id)
        );
        e.stop_all();
        // Bola jarayonlar o'ldirildi — portlar bo'shaydi.
        assert!(wait(|| std::net::TcpListener::bind(("127.0.0.1", sp)).is_ok()), "server porti bo'shamadi");
        assert!(wait(|| std::net::TcpListener::bind(("127.0.0.1", cp)).is_ok()), "klient porti bo'shamadi");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn wrong_server_key_is_reported_with_hint() {
        let d = tmpdir("pin");
        let kd = d.join("keys");
        let srv = keys::create(&kd, "srv", 30).unwrap();
        let cli = keys::create(&kd, "cli", 30).unwrap();
        let other = keys::create(&kd, "other", 30).unwrap();
        let (sp, cp) = (free_port(), free_port());
        let mut s = Profile::new(Role::Server);
        s.name = "S".into();
        s.listen = format!("127.0.0.1:{sp}");
        s.target = echo();
        s.identity = "srv".into();
        s.allow.push(AllowEntry { label: "c".into(), pub_hex: cli.pub_hex(), added: String::new() });
        let mut c = Profile::new(Role::Client);
        c.name = "K".into();
        c.listen = format!("127.0.0.1:{cp}");
        c.target = format!("127.0.0.1:{sp}");
        c.identity = "cli".into();
        c.server_pub = other.pub_hex();
        let _ = srv;
        let mut e = Engine::new(d.join("logs"), 1000, false);
        e.start(&s, &kd, &d, None).unwrap();
        e.start(&c, &kd, &d, None).unwrap();
        let _ = TcpStream::connect(("127.0.0.1", cp)).map(|mut t| {
            let _ = t.write_all(b"x");
            let mut v = Vec::new();
            let _ = t.read_to_end(&mut v);
        });
        assert!(wait(|| {
            e.tick();
            e.last_error.contains_key(&c.id)
        }));
        let (msg, hint) = &e.last_error[&c.id];
        assert!(msg.contains("Handshake muvaffaqiyatsiz"), "{msg}");
        assert!(hint.contains("pinned"), "{hint}");
        let _ = std::fs::remove_dir_all(&d);
    }
}
