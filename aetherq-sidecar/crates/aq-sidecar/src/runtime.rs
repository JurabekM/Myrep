//! Tunel runtime: `serve` / `connect` tinglovchisini ishga tushirish, to'xtatish, statistika va hodisalar.
//!
//! CLI (`aq-sidecar`) va GUI (`aq-studio`) shu bitta kodni ishlatadi. Har ulanish uchun:
//!
//! ```text
//!   serve:   peer (AETHER-Q) ──record'lar──> sidecar ──oddiy TCP──> upstream (ilova)
//!   connect: ilova ──oddiy TCP──> sidecar ──record'lar──> peer (serve)
//! ```
//!
//! Ulanish modeli: har ulanishga bitta thread (handshake) + ikkita thread (ikki yo'nalishli pump).
//! To'xtatish: bayroq qo'yiladi, `accept` o'z-o'ziga ulanish bilan uyg'otiladi, ochiq ulanishlar yopiladi.

use std::collections::{HashMap, VecDeque};
use std::io::{self, Read, Write};
use std::net::{Shutdown, SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use aq_core::dos::PuzzleAuthority;
use aq_core::error::AqError;
use aq_core::handshake::{ClientConfig, ServerConfig};
use aq_core::net::{client_handshake, read_record, server_handshake, SessionCache};
use aq_core::ticket::TicketAuthority;
use aq_core::transport::TYPE_APP_DATA;
use aq_core::{Identity, Session};

/// Bitta record'ga sig'adigan eng katta plaintext bo'lagi.
pub const CHUNK: usize = 16 * 1024;
/// Handshake vaqtidagi o'qish chegarasi (slow-loris himoyasi).
pub const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(20);
/// Statistikada saqlanadigan oxirgi handshake namunalari soni.
const HS_WINDOW: usize = 1024;
/// O'qishlar shu oraliqda uyg'onib, to'xtatish bayrog'ini tekshiradi. Windows'da `shutdown()` bloklangan
/// `recv`'ni uyg'otmaydi — busiz to'xtatilgan tunel ochiq ulanishda trafikni o'tkazishda davom etardi.
const POLL: Duration = Duration::from_millis(500);
/// Upstream/peer'ga TCP ulanish chegarasi.
const DIAL_TIMEOUT: Duration = Duration::from_secs(10);

fn is_timeout(e: &io::Error) -> bool {
    matches!(e.kind(), io::ErrorKind::WouldBlock | io::ErrorKind::TimedOut)
}

/// O'qish timeout'larini ichida qayta urinadigan oqim: ma'lumot yo'qolmaydi (timeout baytsiz qaytadi),
/// lekin har `POLL` da to'xtatish bayrog'i va (handshake uchun) umumiy muddat tekshiriladi.
struct StopIo<S> {
    s: S,
    stop: Arc<AtomicBool>,
    deadline: Option<Instant>,
}

impl<S: Read> Read for StopIo<S> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        loop {
            match self.s.read(buf) {
                Err(e) if is_timeout(&e) => {
                    if self.stop.load(Ordering::SeqCst) {
                        return Err(io::Error::new(io::ErrorKind::ConnectionAborted, "tunel to'xtatildi"));
                    }
                    if self.deadline.is_some_and(|d| Instant::now() >= d) {
                        return Err(io::Error::new(io::ErrorKind::TimedOut, "handshake vaqti tugadi"));
                    }
                }
                r => return r,
            }
        }
    }
}

impl<S: Write> Write for StopIo<S> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        self.s.write(buf)
    }
    fn flush(&mut self) -> io::Result<()> {
        self.s.flush()
    }
}

/// Manzilga chegaralangan vaqt ichida ulanadi (har bir resolve qilingan manzilni sinab).
fn dial(addr: &str) -> io::Result<TcpStream> {
    use std::net::ToSocketAddrs;
    let mut last = io::Error::new(io::ErrorKind::InvalidInput, "manzil topilmadi");
    for a in addr.to_socket_addrs()? {
        match TcpStream::connect_timeout(&a, DIAL_TIMEOUT) {
            Ok(s) => return Ok(s),
            Err(e) => last = e,
        }
    }
    Err(last)
}

/// Runtime hodisalari. CLI ularni log qatoriga, GUI esa jurnal va grafiklarga aylantiradi.
#[derive(Debug, Clone)]
pub enum Event {
    /// Server: klient handshake'dan o'tdi.
    Accepted { peer: String, client_pk: Option<Vec<u8>>, resumed: bool, handshake_ms: f64 },
    /// Klient: tunel ochildi.
    Opened { peer: String, resumed: bool, handshake_ms: f64 },
    /// Tunel yopildi (ikki yo'nalish ham tugadi).
    Closed { peer: String, to_net: u64, from_net: u64, secs: f64 },
    /// Handshake muvaffaqiyatsiz. `alert` — protokol alert kodi (bo'lsa), `hint` — o'zbekcha izoh.
    HandshakeFailed { peer: String, error: String, alert: Option<u8>, hint: &'static str },
    /// Server: upstream'ga, klient: peer'ga TCP ulanib bo'lmadi.
    DialFailed { target: String, error: String, hint: &'static str },
    /// Ochiq tunelda record'ni ochib bo'lmadi (buzilgan yoki soxta ma'lumot).
    RecordError { error: String },
    /// `accept` xatosi.
    AcceptError { error: String },
    /// Tinglovchi to'xtatildi.
    Stopped,
}

pub type Sink = Arc<dyn Fn(Event) + Send + Sync>;

/// Hech narsa qilmaydigan hodisa qabul qiluvchi.
pub fn null_sink() -> Sink {
    Arc::new(|_| {})
}

/// Tunel hisoblagichlari (lock'siz; handshake namunalari kichik mutex ostida).
#[derive(Default)]
pub struct Stats {
    pub active: AtomicU64,
    pub total: AtomicU64,
    pub resumed: AtomicU64,
    pub failed: AtomicU64,
    /// Mahalliy tomondan tarmoqqa (shifrlanib) ketgan baytlar.
    pub to_net: AtomicU64,
    /// Tarmoqdan kelib, mahalliy tomonga (ochilib) yozilgan baytlar.
    pub from_net: AtomicU64,
    hs: Mutex<VecDeque<f32>>,
}

/// Bir lahzalik holat (GUI va testlar uchun).
#[derive(Debug, Clone, Default, PartialEq)]
pub struct StatsSnapshot {
    pub active: u64,
    pub total: u64,
    pub resumed: u64,
    pub failed: u64,
    pub to_net: u64,
    pub from_net: u64,
    /// Oxirgi handshake'lar soni va persentillari (ms); namuna bo'lmasa 0.
    pub hs_n: usize,
    pub hs_p50: f64,
    pub hs_p99: f64,
}

impl Stats {
    fn record_handshake(&self, ms: f64) {
        let mut q = self.hs.lock().unwrap_or_else(|p| p.into_inner());
        if q.len() == HS_WINDOW {
            q.pop_front();
        }
        q.push_back(ms as f32);
    }

    pub fn snapshot(&self) -> StatsSnapshot {
        let mut v: Vec<f32> = self.hs.lock().unwrap_or_else(|p| p.into_inner()).iter().copied().collect();
        v.sort_by(|a, b| a.total_cmp(b));
        let pct = |p: f64| -> f64 {
            if v.is_empty() {
                return 0.0;
            }
            let rank = ((p / 100.0) * v.len() as f64).ceil().max(1.0) as usize;
            v[rank.min(v.len()) - 1] as f64
        };
        StatsSnapshot {
            active: self.active.load(Ordering::Relaxed),
            total: self.total.load(Ordering::Relaxed),
            resumed: self.resumed.load(Ordering::Relaxed),
            failed: self.failed.load(Ordering::Relaxed),
            to_net: self.to_net.load(Ordering::Relaxed),
            from_net: self.from_net.load(Ordering::Relaxed),
            hs_n: v.len(),
            hs_p50: pct(50.0),
            hs_p99: pct(99.0),
        }
    }
}

/// Ochiq ulanishlar ro'yxati — to'xtatishda hammasini yopish uchun.
#[derive(Default)]
struct Registry {
    next: AtomicU64,
    map: Mutex<HashMap<u64, Vec<TcpStream>>>,
}

impl Registry {
    fn add(&self, s: &TcpStream) -> u64 {
        let id = self.next.fetch_add(1, Ordering::Relaxed);
        self.attach(id, s);
        id
    }

    fn attach(&self, id: u64, s: &TcpStream) {
        if let Ok(c) = s.try_clone() {
            self.map.lock().unwrap_or_else(|p| p.into_inner()).entry(id).or_default().push(c);
        }
    }

    fn remove(&self, id: u64) {
        self.map.lock().unwrap_or_else(|p| p.into_inner()).remove(&id);
    }

    fn shutdown_all(&self) {
        let map = std::mem::take(&mut *self.map.lock().unwrap_or_else(|p| p.into_inner()));
        for (_, streams) in map {
            for s in streams {
                let _ = s.shutdown(Shutdown::Both);
            }
        }
    }
}

/// Har ulanish thread'iga beriladigan umumiy kontekst.
#[derive(Clone)]
struct Ctx {
    stats: Arc<Stats>,
    sink: Sink,
    stop: Arc<AtomicBool>,
    reg: Arc<Registry>,
}

impl Ctx {
    fn emit(&self, e: Event) {
        (self.sink)(e);
    }

    /// Xato hodisasi — to'xtatish paytida yopilgan ulanishlar xato deb ko'rsatilmaydi.
    fn fail(&self, e: Event) {
        if self.stop.load(Ordering::SeqCst) {
            return;
        }
        self.stats.failed.fetch_add(1, Ordering::Relaxed);
        self.emit(e);
    }
}

fn alert_of(e: &AqError) -> Option<u8> {
    match e {
        AqError::Alert(c) => Some(*c),
        _ => None,
    }
}

/// Handshake xatosining o'zbekcha izohi.
pub fn hint_for(e: &AqError) -> &'static str {
    match e {
        AqError::Alert(c) => explain_alert(*c),
        AqError::Io(io) => explain_io(io),
        AqError::Malformed(_) => "Qarshi tomon AETHER-Q emas yoki boshqa rejimda (noto'g'ri formatdagi xabar).",
        AqError::Aead => "Shifrlangan ma'lumot tekshiruvdan o'tmadi (buzilgan yoki soxta).",
        AqError::Crypto(_) => "Kriptografik xato (kalit fayli buzilgan bo'lishi mumkin).",
    }
}

/// Server tomoni sozlamalari.
#[derive(Clone)]
pub struct ServeOptions {
    pub listen: String,
    pub upstream: String,
    pub identity: Identity,
    pub require_client_auth: bool,
    /// Ruxsat etilgan klient ochiq kalitlari; `None` — har qanday to'g'ri imzo.
    pub allowed: Option<Vec<Vec<u8>>>,
    pub resumption: bool,
    pub ticket_ttl: u64,
    /// PoW qiyinligi (0 — o'chiq).
    pub pow: u8,
}

/// Klient tomoni sozlamalari.
#[derive(Clone)]
pub struct ConnectOptions {
    pub listen: String,
    pub peer: String,
    /// Pinned server ochiq kaliti.
    pub server_pub: Vec<u8>,
    pub identity: Option<Identity>,
    pub resume: bool,
}

/// Ishlayotgan tinglovchi. `stop()` (yoki drop) — port bo'shaydi, ochiq tunellar yopiladi.
pub struct Tunnel {
    local: SocketAddr,
    stop: Arc<AtomicBool>,
    stats: Arc<Stats>,
    reg: Arc<Registry>,
    sink: Sink,
    accept: Option<JoinHandle<()>>,
}

impl Tunnel {
    /// Server tomoni: `listen` da AETHER-Q ulanishlarini qabul qilib, `upstream` ga uzatadi.
    pub fn serve(o: ServeOptions, sink: Sink) -> Result<Tunnel, String> {
        let tickets = if o.resumption {
            Some(Arc::new(TicketAuthority::random(o.ticket_ttl).map_err(|e| format!("ticket kaliti: {e}"))?))
        } else {
            None
        };
        let puzzle = if o.pow == 0 {
            None
        } else {
            Some(Arc::new(PuzzleAuthority::random(o.pow, 30).map_err(|e| format!("puzzle: {e}"))?))
        };
        let listener = TcpListener::bind(&o.listen).map_err(|e| format!("{}: {e}", o.listen))?;
        let base = ServerConfig {
            identity: Some(o.identity.clone()),
            require_client_auth: o.require_client_auth,
            allowed_clients: o.allowed.clone(),
            tickets,
            puzzle,
            ..Default::default()
        };
        let upstream = o.upstream.clone();
        Self::start(listener, sink, move |stream, ctx| {
            let cfg = base.clone();
            let up = upstream.clone();
            thread::spawn(move || serve_connection(stream, cfg, &up, ctx));
        })
    }

    /// Klient tomoni: `listen` dagi oddiy ulanishlarni AETHER-Q tunel orqali `peer` ga uzatadi.
    pub fn connect(o: ConnectOptions, sink: Sink) -> Result<Tunnel, String> {
        let listener = TcpListener::bind(&o.listen).map_err(|e| format!("{}: {e}", o.listen))?;
        // Ticket keshi tinglovchi bo'yicha umumiy: ikkinchi ulanish resumption bilan ketadi.
        let cache = Arc::new(SessionCache::new());
        let key = cache_key(&o.peer, &o.server_pub);
        Self::start(listener, sink, move |stream, ctx| {
            let mut cfg = ClientConfig {
                server_pub: Some(o.server_pub.clone()),
                identity: o.identity.clone(),
                ..Default::default()
            };
            let cache_arg = if o.resume {
                cfg.resume = cache.get(&key);
                cfg.want_ticket = true;
                Some((cache.clone(), key.clone()))
            } else {
                None
            };
            let peer = o.peer.clone();
            thread::spawn(move || connect_connection(stream, cfg, &peer, cache_arg, ctx));
        })
    }

    fn start(
        listener: TcpListener,
        sink: Sink,
        mut on_conn: impl FnMut(TcpStream, Ctx) + Send + 'static,
    ) -> Result<Tunnel, String> {
        let local = listener.local_addr().map_err(|e| e.to_string())?;
        let ctx = Ctx {
            stats: Arc::new(Stats::default()),
            sink: sink.clone(),
            stop: Arc::new(AtomicBool::new(false)),
            reg: Arc::new(Registry::default()),
        };
        let (stats, stop, reg) = (ctx.stats.clone(), ctx.stop.clone(), ctx.reg.clone());
        let accept = thread::Builder::new()
            .name("aq-accept".into())
            .spawn(move || {
                for conn in listener.incoming() {
                    if ctx.stop.load(Ordering::SeqCst) {
                        break;
                    }
                    match conn {
                        Ok(s) => on_conn(s, ctx.clone()),
                        Err(e) => {
                            ctx.emit(Event::AcceptError { error: e.to_string() });
                            // Doimiy xatoda (masalan, deskriptorlar tugagan) protsessorni band qilmaslik.
                            thread::sleep(Duration::from_millis(50));
                        }
                    }
                }
                // listener shu yerda yopiladi — port bo'shaydi.
            })
            .map_err(|e| e.to_string())?;
        Ok(Tunnel { local, stop, stats, reg, sink, accept: Some(accept) })
    }

    /// Haqiqiy tinglash manzili (port 0 bilan ochilganda ham aniq port).
    pub fn local_addr(&self) -> SocketAddr {
        self.local
    }

    pub fn stats(&self) -> Arc<Stats> {
        self.stats.clone()
    }

    pub fn is_running(&self) -> bool {
        !self.stop.load(Ordering::SeqCst)
    }

    /// Tinglovchi to'xtaguncha kutadi (CLI uchun).
    pub fn wait(mut self) {
        if let Some(h) = self.accept.take() {
            let _ = h.join();
        }
    }

    /// To'xtatish: yangi ulanishlar qabul qilinmaydi, ochiq tunellar yopiladi, port bo'shaydi.
    pub fn stop(mut self) {
        self.shutdown();
    }

    fn shutdown(&mut self) {
        if self.stop.swap(true, Ordering::SeqCst) {
            return;
        }
        // Bloklangan accept'ni o'z-o'ziga ulanish bilan uyg'otamiz.
        let _ = TcpStream::connect_timeout(&wake_addr(self.local), Duration::from_millis(500));
        if let Some(h) = self.accept.take() {
            let _ = h.join();
        }
        self.reg.shutdown_all();
        (self.sink)(Event::Stopped);
    }
}

impl Drop for Tunnel {
    fn drop(&mut self) {
        if self.accept.is_some() {
            self.shutdown();
        }
    }
}

/// 0.0.0.0 / [::] da tinglanayotgan bo'lsa, uyg'otish loopback orqali.
fn wake_addr(a: SocketAddr) -> SocketAddr {
    match a {
        SocketAddr::V4(v) if v.ip().is_unspecified() => SocketAddr::from(([127, 0, 0, 1], v.port())),
        SocketAddr::V6(v) if v.ip().is_unspecified() => SocketAddr::from((std::net::Ipv6Addr::LOCALHOST, v.port())),
        other => other,
    }
}

/// Ticket kesh kaliti: manzil + server ochiq kaliti.
pub fn cache_key(peer: &str, server_pub: &[u8]) -> String {
    format!("{peer}|{}", aq_core::identity::to_hex(server_pub))
}

/// Qisqa barmoq izi (log uchun): ochiq kalitning birinchi 8 bayti hex.
pub fn short_fp(pk: &[u8]) -> String {
    pk.iter().take(8).map(|b| format!("{b:02x}")).collect()
}

fn peer_name(s: &TcpStream) -> String {
    s.peer_addr().map(|a| a.to_string()).unwrap_or_else(|_| "?".into())
}

/// Ikki oqimni AETHER-Q sessiyasi orqali bog'laydi. `plain` — mahalliy oddiy oqim, `wire` — record'lar oqimi.
/// Ikkala yo'nalish tugaguncha bloklaydi. Qaytaradi: (tarmoqqa, tarmoqdan) baytlar.
fn pump(session: Session, plain: TcpStream, wire: TcpStream, ctx: &Ctx) -> (u64, u64) {
    let (mut tx, mut rx) = session.split();
    let (plain_r, mut wire_w) = match (plain.try_clone(), wire.try_clone()) {
        (Ok(a), Ok(b)) => (a, b),
        _ => return (0, 0),
    };
    let _ = plain_r.set_read_timeout(Some(POLL));
    let _ = wire.set_read_timeout(Some(POLL));
    let mut plain_r = StopIo { s: plain_r, stop: ctx.stop.clone(), deadline: None };
    let mut wire_r = StopIo { s: wire, stop: ctx.stop.clone(), deadline: None };
    let mut plain_w = plain;

    let stats = ctx.stats.clone();
    // plain → wire: har o'qish bitta record bo'lib shifrlanadi.
    let up = thread::spawn(move || {
        let mut buf = vec![0u8; CHUNK];
        let mut n_total = 0u64;
        loop {
            let n = match plain_r.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => n,
            };
            let rec = match tx.seal(&buf[..n]) {
                Ok(r) => r,
                Err(_) => break,
            };
            if wire_w.write_all(&rec).is_err() {
                break;
            }
            n_total += n as u64;
            stats.to_net.fetch_add(n as u64, Ordering::Relaxed);
        }
        let _ = wire_w.shutdown(Shutdown::Write);
        n_total
    });

    // wire → plain: record'ni ochib, plaintext'ni yozadi.
    // (`wire_r` StopIo: timeout'da qayta urinadi, to'xtatilganda xato qaytaradi.)
    let ctx2 = ctx.clone();
    let down = thread::spawn(move || {
        let mut n_total = 0u64;
        loop {
            let rec = match read_record(&mut wire_r) {
                Ok(r) => r,
                Err(_) => break,
            };
            let (rtype, pt) = match rx.open(&rec) {
                Ok(v) => v,
                Err(e) => {
                    ctx2.fail(Event::RecordError { error: e.to_string() });
                    break;
                }
            };
            if rtype != TYPE_APP_DATA {
                continue;
            }
            if plain_w.write_all(&pt).is_err() {
                break;
            }
            n_total += pt.len() as u64;
            ctx2.stats.from_net.fetch_add(pt.len() as u64, Ordering::Relaxed);
        }
        let _ = plain_w.shutdown(Shutdown::Write);
        n_total
    });

    (up.join().unwrap_or(0), down.join().unwrap_or(0))
}

/// Server tomoni: peer ulanishini qabul qilib, upstream'ga tunnel qiladi.
fn serve_connection(mut peer: TcpStream, cfg: ServerConfig, upstream: &str, ctx: Ctx) {
    let id = ctx.reg.add(&peer);
    let name = peer_name(&peer);
    let t0 = Instant::now();
    let _ = peer.set_read_timeout(Some(POLL));
    let hs = server_handshake(
        &mut StopIo { s: &mut peer, stop: ctx.stop.clone(), deadline: Some(t0 + HANDSHAKE_TIMEOUT) },
        cfg,
    );
    let est = match hs {
        Ok(v) => v,
        Err(e) => {
            ctx.fail(Event::HandshakeFailed { peer: name, alert: alert_of(&e), hint: hint_for(&e), error: e.to_string() });
            ctx.reg.remove(id);
            return;
        }
    };
    let hs_ms = t0.elapsed().as_secs_f64() * 1e3;
    let plain = match dial(upstream) {
        Ok(s) => s,
        Err(e) => {
            ctx.fail(Event::DialFailed { target: upstream.to_string(), hint: explain_io(&e), error: e.to_string() });
            ctx.reg.remove(id);
            return;
        }
    };
    ctx.reg.attach(id, &plain);
    ctx.stats.total.fetch_add(1, Ordering::Relaxed);
    if est.resumed {
        ctx.stats.resumed.fetch_add(1, Ordering::Relaxed);
    }
    ctx.stats.record_handshake(hs_ms);
    ctx.stats.active.fetch_add(1, Ordering::Relaxed);
    ctx.emit(Event::Accepted { peer: name.clone(), client_pk: est.client_pk, resumed: est.resumed, handshake_ms: hs_ms });
    let t1 = Instant::now();
    let (to_net, from_net) = pump(est.session, plain, peer, &ctx);
    ctx.stats.active.fetch_sub(1, Ordering::Relaxed);
    ctx.reg.remove(id);
    ctx.emit(Event::Closed { peer: name, to_net, from_net, secs: t1.elapsed().as_secs_f64() });
}

/// Klient tomoni: mahalliy oddiy ulanishni qabul qilib, peer serverga tunnel qiladi.
fn connect_connection(
    local: TcpStream,
    cfg: ClientConfig,
    peer_addr: &str,
    cache: Option<(Arc<SessionCache>, String)>,
    ctx: Ctx,
) {
    let id = ctx.reg.add(&local);
    let t0 = Instant::now();
    let mut wire = match dial(peer_addr) {
        Ok(s) => s,
        Err(e) => {
            ctx.fail(Event::DialFailed { target: peer_addr.to_string(), hint: explain_io(&e), error: e.to_string() });
            ctx.reg.remove(id);
            return;
        }
    };
    ctx.reg.attach(id, &wire);
    let _ = wire.set_read_timeout(Some(POLL));
    let hs = client_handshake(
        &mut StopIo { s: &mut wire, stop: ctx.stop.clone(), deadline: Some(t0 + HANDSHAKE_TIMEOUT) },
        cfg,
    );
    let est = match hs {
        Ok(s) => s,
        Err(e) => {
            ctx.fail(Event::HandshakeFailed {
                peer: peer_addr.to_string(),
                alert: alert_of(&e),
                hint: hint_for(&e),
                error: e.to_string(),
            });
            ctx.reg.remove(id);
            return;
        }
    };
    let hs_ms = t0.elapsed().as_secs_f64() * 1e3;
    if let (Some((c, key)), Some(t)) = (&cache, est.new_ticket.clone()) {
        c.put(key, t);
    }
    ctx.stats.total.fetch_add(1, Ordering::Relaxed);
    if est.resumed {
        ctx.stats.resumed.fetch_add(1, Ordering::Relaxed);
    }
    ctx.stats.record_handshake(hs_ms);
    ctx.stats.active.fetch_add(1, Ordering::Relaxed);
    ctx.emit(Event::Opened { peer: peer_addr.to_string(), resumed: est.resumed, handshake_ms: hs_ms });
    let t1 = Instant::now();
    let (to_net, from_net) = pump(est.session, local, wire, &ctx);
    ctx.stats.active.fetch_sub(1, Ordering::Relaxed);
    ctx.reg.remove(id);
    ctx.emit(Event::Closed { peer: peer_addr.to_string(), to_net, from_net, secs: t1.elapsed().as_secs_f64() });
}

/// Alert kodining odamga tushunarli izohi (o'zbekcha) — GUI va diagnostika uchun.
pub fn explain_alert(code: u8) -> &'static str {
    use aq_core::error::alert::*;
    match code {
        BAD_SIGNATURE => "Server kaliti kutilgan (pinned) kalitga mos emas — klientdagi server kalitini yangilang.",
        CLIENT_AUTH_REQUIRED => "Server klient kalitini talab qiladi — klient profiliga identity tanlang.",
        BAD_CLIENT_AUTH => "Server bu klientni tanimaydi — klient kalitini server allowlist'iga qo'shing.",
        BAD_FINISHED => "Handshake yakuni mos kelmadi — kalitlar yoki ma'lumot buzilgan.",
        DECAPS_FAILED => "Kalit almashinuvi (ML-KEM/X25519) muvaffaqiyatsiz.",
        NO_COMMON_VERSION => "Protokol versiyasi mos emas.",
        NO_COMMON_PROFILE | PROFILE_NOT_OFFERED => "Kripto profili mos emas.",
        DOS_REJECT => "Server DoS himoyasi (PoW) ulanishni rad etdi.",
        BAD_TICKET => "Resumption ticket yaroqsiz — keyingi ulanish to'liq handshake bilan o'tadi.",
        UNEXPECTED_MESSAGE => "Kutilmagan xabar — qarshi tomon AETHER-Q emas yoki boshqa rejimda.",
        _ => "Noma'lum protokol xatosi.",
    }
}

/// io::Error uchun qisqa o'zbekcha izoh (dial xatolari uchun).
pub fn explain_io(e: &io::Error) -> &'static str {
    match e.kind() {
        io::ErrorKind::ConnectionRefused => "Manzilda hech narsa tinglamayapti (dastur ishlamayapti yoki port noto'g'ri).",
        io::ErrorKind::TimedOut => "Javob kelmadi (firewall yoki noto'g'ri manzil).",
        io::ErrorKind::AddrInUse => "Port band — boshqa dastur shu portni ishlatyapti.",
        io::ErrorKind::PermissionDenied => "Ruxsat yo'q (port yoki firewall cheklovi).",
        _ => "Tarmoq xatosi.",
    }
}
