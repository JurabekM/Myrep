//! AETHER-Q v5.1 handshake — Python `aether_q_v51/handshake.py` bilan bayt-mos.
//!
//! Oqim (2-RTT):
//!   Client → CH [+ EARLY_DATA]            (resumption: ticket; 0-RTT: early data)
//!   Server → HELLO_RETRY                  (PoW yoqilgan bo'lsa; klient CH_RETRY bilan javob beradi)
//!   Server → SH  (ephemeral ML-KEM ek; imzo H(CH ‖ SH-core) — resumption'da imzo yo'q)
//!   Client → CKX [+ CA] + CF
//!   Server → SF [+ NST]                   (NST: keyingi ulanish uchun ticket)
//! Transcript — xabarlarning xom frame baytlari ketma-ketligi.

use std::sync::{Arc, Mutex};

use crate::dos::{self, PuzzleAuthority};
use crate::early::{self, EarlyGuard};
use crate::error::{alert, AqError, Result};
use crate::identity::Identity;
use crate::kdf::{ct_eq, hkdf_expand32, hkdf_extract, kmac256, sha3_256};
use crate::kem::{self, KemPriv, PROFILE_HYBRID, PROFILE_MINIMAL};
use crate::sig;
use crate::ticket::{now_secs, TicketAuthority};
use crate::transport::{Role, Session};
use crate::wire::{
    alert_frame, dec_client_auth, dec_client_hello, dec_client_hello_retry, dec_client_kex, dec_finished,
    dec_hello_retry, dec_nst, dec_server_hello, enc_client_auth, enc_client_hello, enc_client_hello_retry,
    enc_client_kex, enc_early_data, enc_finished, enc_hello_retry, enc_nst, enc_server_hello, parse_exact,
    parse_frame, sh_core, ClientHello, FLAG_EARLY_DATA, FLAG_WANT_TICKET, MSG_ALERT, MSG_CH_RETRY,
    MSG_CLIENT_AUTH, MSG_CLIENT_HELLO, MSG_CLIENT_KEX, MSG_EARLY_DATA, MSG_FINISHED, MSG_NST,
    MSG_SERVER_HELLO, MSG_HELLO_RETRY, SH_FLAG_CLIENT_AUTH, SUPPORTED_VERSIONS,
};

/// Klient taklif qiladigan profillar (Python `PROFILE_PREFERENCE`).
pub const CLIENT_PROFILES: [u8; 2] = [PROFILE_HYBRID, PROFILE_MINIMAL];
/// Server preferens tartibi (kuchli → zaif).
pub const SERVER_PREFERENCE: [u8; 2] = [PROFILE_HYBRID, PROFILE_MINIMAL];

/// AQ-L05: klient PoW byudjeti (Python `MAX_POW_DIFFICULTY`, `MAX_POW_RETRIES`).
pub const DEFAULT_MAX_POW_DIFFICULTY: u8 = 20;
pub const DEFAULT_MAX_POW_RETRIES: u8 = 1;
/// PoW yechish uchun maksimal iteratsiya (`solve_pow` max_iters).
pub const MAX_POW_ITERS: u64 = 1 << 30;

/// `server_id_hash`: Python `sha3(b"AETHER-Q-v5.1-SRV-ID" ‖ pub)` (pub bo'sh bo'lsa bo'sh).
pub fn server_id_hash(server_pub: &[u8]) -> Vec<u8> {
    if server_pub.is_empty() {
        return Vec::new();
    }
    let mut v = b"AETHER-Q-v5.1-SRV-ID".to_vec();
    v.extend_from_slice(server_pub);
    sha3_256(&v).to_vec()
}

/// Python `_derive_hs(ss, rms, server_id)` = HKDF-Extract(salt = rms, ikm = ss ‖ server_id).
pub fn derive_hs(ss: &[u8], rms: &[u8], server_id: &[u8]) -> [u8; 32] {
    let mut ikm = ss.to_vec();
    ikm.extend_from_slice(server_id);
    hkdf_extract(rms, &ikm)
}

/// Python `_fin_keys(hs)`.
pub fn fin_keys(hs: &[u8; 32]) -> ([u8; 32], [u8; 32]) {
    (
        hkdf_expand32(hs, b"AETHER-Q-v5.1 c finished"),
        hkdf_expand32(hs, b"AETHER-Q-v5.1 s finished"),
    )
}

/// Python `_mac(key, transcript_digest, tag)` = KMAC256(key, digest, 32, "AETHER-Q-v5.1-" ‖ tag).
pub fn finished_mac(key: &[u8; 32], transcript_digest: &[u8; 32], tag: &[u8]) -> [u8; 32] {
    let mut custom = b"AETHER-Q-v5.1-".to_vec();
    custom.extend_from_slice(tag);
    let v = kmac256(key, transcript_digest, 32, &custom);
    let mut out = [0u8; 32];
    out.copy_from_slice(&v);
    out
}

/// Python `_master(hs, transcript)`.
pub fn derive_master(hs: &[u8; 32], transcript: &[u8]) -> [u8; 32] {
    let mut info = b"AETHER-Q-v5.1 master".to_vec();
    info.extend_from_slice(&sha3_256(transcript));
    hkdf_expand32(hs, &info)
}

/// Python `_derive_rms(hs, transcript)` — resumption master secret.
pub fn derive_rms(hs: &[u8; 32], transcript: &[u8]) -> [u8; 32] {
    let mut info = b"AETHER-Q-v5.1 resumption".to_vec();
    info.extend_from_slice(&sha3_256(transcript));
    hkdf_expand32(hs, &info)
}

fn rand_bytes<const N: usize>() -> Result<[u8; N]> {
    let mut b = [0u8; N];
    getrandom::getrandom(&mut b).map_err(|_| AqError::Crypto("getrandom"))?;
    Ok(b)
}

/// Peer ALERT xabarini tekshiradi.
fn peer_alert(mtype: u8, body: &[u8]) -> Option<AqError> {
    if mtype == MSG_ALERT {
        let code = body.get(1).copied().unwrap_or(alert::UNEXPECTED_MESSAGE);
        Some(AqError::Alert(code))
    } else {
        None
    }
}

/// Session resumption: oldingi ulanishdan (ticket, RMS).
#[derive(Clone)]
pub struct Resume {
    pub ticket: Vec<u8>,
    pub rms: [u8; 32],
}

/// Serverdan olingan yangi ticket (NST) va uning RMS'i.
#[derive(Clone)]
pub struct Ticket {
    pub ticket: Vec<u8>,
    pub rms: [u8; 32],
}

impl Ticket {
    pub fn as_resume(&self) -> Resume {
        Resume { ticket: self.ticket.clone(), rms: self.rms }
    }
}

#[derive(Clone)]
pub struct ClientConfig {
    /// Pinned server ML-DSA ochiq kaliti. `None` → server autentifikatsiyasi tekshirilmaydi.
    pub server_pub: Option<Vec<u8>>,
    /// Klient identity'si (mutual auth).
    pub identity: Option<Identity>,
    /// Oldingi sessiyadan resumption (ticket + RMS).
    pub resume: Option<Resume>,
    /// Server NST (yangi ticket) yuborishini so'raydi.
    pub want_ticket: bool,
    /// 0-RTT ma'lumot (faqat `resume` bilan; IDEMPOTENT so'rovlar uchun — N17).
    pub early_data: Option<Vec<u8>>,
    /// AQ-L05: qabul qilinadigan maksimal PoW qiyinligi.
    pub max_pow_difficulty: u8,
    /// AQ-L05: maksimal HELLO_RETRY soni.
    pub max_pow_retries: u8,
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            server_pub: None,
            identity: None,
            resume: None,
            want_ticket: false,
            early_data: None,
            max_pow_difficulty: DEFAULT_MAX_POW_DIFFICULTY,
            max_pow_retries: DEFAULT_MAX_POW_RETRIES,
        }
    }
}

#[derive(Clone, Default)]
pub struct ServerConfig {
    /// Server identity'si (ML-DSA imzo). `None` → autentifikatsiyasiz (sinov).
    pub identity: Option<Identity>,
    /// Klientdan ML-DSA imzo talab qilish (mutual auth).
    pub require_client_auth: bool,
    /// Ruxsat etilgan klient ochiq kalitlari. `None` → har qanday to'g'ri imzo.
    pub allowed_clients: Option<Vec<Vec<u8>>>,
    /// Session ticket kaliti (resumption). `None` → resumption o'chirilgan.
    pub tickets: Option<Arc<TicketAuthority>>,
    /// Ilova konteksti (AQ-05): ticket shu kontekstga qulflanadi.
    pub ticket_context: Vec<u8>,
    /// DoS PoW (HELLO_RETRY). `None` → PoW talab qilinmaydi.
    pub puzzle: Option<Arc<PuzzleAuthority>>,
    /// 0-RTT anti-replay qorovuli. `None` → 0-RTT qabul qilinmaydi.
    pub early_guard: Option<Arc<Mutex<EarlyGuard>>>,
}

#[derive(PartialEq, Eq, Clone, Copy, Debug)]
enum CState {
    Start,
    WaitServerHello,
    WaitServerFinished,
    Connected,
}

/// Klient handshake natijasi.
pub struct ClientEstablished {
    pub session: Session,
    pub resumed: bool,
    pub new_ticket: Option<Ticket>,
}

pub struct ClientHs {
    cfg: ClientConfig,
    state: CState,
    transcript: Vec<u8>,
    ch: Vec<u8>,
    retries: u8,
    profile: u8,
    hs: [u8; 32],
    s_fin: [u8; 32],
    rms: [u8; 32],
    resumed: bool,
    session: Option<Session>,
    new_ticket: Option<Ticket>,
}

impl ClientHs {
    pub fn new(cfg: ClientConfig) -> Self {
        Self {
            cfg,
            state: CState::Start,
            transcript: Vec::new(),
            ch: Vec::new(),
            retries: 0,
            profile: 0,
            hs: [0; 32],
            s_fin: [0; 32],
            rms: [0; 32],
            resumed: false,
            session: None,
            new_ticket: None,
        }
    }

    /// Birinchi flight: CH (+ 0-RTT EARLY_DATA, agar bor bo'lsa).
    pub fn start(&mut self) -> Result<Vec<u8>> {
        if self.state != CState::Start {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let ticket = self.cfg.resume.as_ref().map(|r| r.ticket.clone()).unwrap_or_default();
        let early = self.cfg.resume.is_some() && self.cfg.early_data.is_some();
        let mut flags = 0u8;
        if self.cfg.want_ticket {
            flags |= FLAG_WANT_TICKET;
        }
        if early {
            flags |= FLAG_EARLY_DATA;
        }
        let ch = enc_client_hello(&ClientHello {
            versions: SUPPORTED_VERSIONS.to_vec(),
            profiles: CLIENT_PROFILES.to_vec(),
            client_random: rand_bytes::<32>()?,
            flags,
            ticket,
        });
        self.transcript = ch.clone();
        self.ch = ch.clone();
        self.state = CState::WaitServerHello;
        if early {
            let r = self.cfg.resume.as_ref().expect("resume");
            let data = self.cfg.early_data.as_ref().expect("early");
            let nonce = rand_bytes::<{ early::NONCE_LEN }>()?;
            let blob = early::seal_early(&r.rms, &ch, data, &nonce);
            let mut out = ch;
            out.extend_from_slice(&enc_early_data(&blob));
            return Ok(out);
        }
        Ok(ch)
    }

    pub fn is_connected(&self) -> bool {
        self.state == CState::Connected
    }

    /// Klient NST so'raganmi (ulangandan keyin o'qish kerakmi).
    pub fn wants_ticket(&self) -> bool {
        self.cfg.want_ticket
    }

    /// Serverdan kelgan bitta frame. Qaytaradi: yuboriladigan javob (agar bor bo'lsa).
    pub fn recv(&mut self, data: &[u8]) -> Result<Option<Vec<u8>>> {
        match self.state {
            CState::WaitServerHello => self.on_server_hello(data),
            CState::WaitServerFinished => {
                self.on_server_finished(data)?;
                Ok(None)
            }
            CState::Connected => {
                self.on_ticket(data)?;
                Ok(None)
            }
            CState::Start => Err(AqError::Alert(alert::UNEXPECTED_MESSAGE)),
        }
    }

    fn on_server_hello(&mut self, data: &[u8]) -> Result<Option<Vec<u8>>> {
        let (mtype, body) = parse_exact(data)?;
        if let Some(e) = peer_alert(mtype, body) {
            return Err(e);
        }
        if mtype == MSG_HELLO_RETRY {
            // AQ-L05: PoW byudjeti — qiyinlik va urinishlar soni chegaralangan.
            self.retries += 1;
            if self.retries > self.cfg.max_pow_retries {
                return Err(AqError::Alert(alert::DOS_REJECT));
            }
            let (difficulty, cookie) = dec_hello_retry(body)?;
            if difficulty > self.cfg.max_pow_difficulty {
                return Err(AqError::Alert(alert::DOS_REJECT));
            }
            let nonce = dos::solve_pow(&cookie, difficulty, MAX_POW_ITERS)
                .ok_or(AqError::Alert(alert::DOS_REJECT))?;
            return Ok(Some(enc_client_hello_retry(&cookie, nonce, &self.ch)));
        }
        if mtype != MSG_SERVER_HELLO {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let sh = dec_server_hello(body)?;
        if !SUPPORTED_VERSIONS.contains(&sh.version) {
            return Err(AqError::Alert(alert::NO_COMMON_VERSION));
        }
        if !CLIENT_PROFILES.contains(&sh.profile) {
            return Err(AqError::Alert(alert::PROFILE_NOT_OFFERED));
        }
        // Resumption: resume taklif qildik va server imzosiz javob berdi → ticket qabul qilingan.
        let resuming = self.cfg.resume.is_some() && sh.sig.is_empty();
        if !resuming {
            if let Some(pk) = &self.cfg.server_pub {
                let mut m = self.transcript.clone();
                m.extend_from_slice(&sh.core);
                if sh.sig.is_empty() || !sig::verify(pk, &sha3_256(&m), &sh.sig) {
                    return Err(AqError::Alert(alert::BAD_SIGNATURE));
                }
            }
        }
        self.transcript.extend_from_slice(data);
        let (ct, ss) = kem::encaps(sh.profile, &sh.ek).map_err(|_| AqError::Alert(alert::DECAPS_FAILED))?;
        let (rms_in, sid) = if resuming {
            let r = self.cfg.resume.as_ref().expect("resume");
            (r.rms.to_vec(), server_id_hash(self.cfg.server_pub.as_deref().unwrap_or(&[])))
        } else {
            (Vec::new(), Vec::new())
        };
        let hs = derive_hs(&ss, &rms_in, &sid);
        let (c_fin, s_fin) = fin_keys(&hs);
        let ckx = enc_client_kex(&ct);
        self.transcript.extend_from_slice(&ckx);
        let mut auth = Vec::new();
        if sh.flags & SH_FLAG_CLIENT_AUTH != 0 {
            let id = self.cfg.identity.as_ref().ok_or(AqError::Alert(alert::CLIENT_AUTH_REQUIRED))?;
            let s = sig::sign(&id.signing_key(), &sha3_256(&self.transcript))?;
            auth = enc_client_auth(&id.pk, &s);
            self.transcript.extend_from_slice(&auth);
        }
        let cf = finished_mac(&c_fin, &sha3_256(&self.transcript), b"CF");
        let fin = enc_finished(&cf);
        self.transcript.extend_from_slice(&fin);
        self.profile = sh.profile;
        self.hs = hs;
        self.s_fin = s_fin;
        self.resumed = resuming;
        self.state = CState::WaitServerFinished;
        let mut out = ckx;
        out.extend_from_slice(&auth);
        out.extend_from_slice(&fin);
        Ok(Some(out))
    }

    fn on_server_finished(&mut self, data: &[u8]) -> Result<()> {
        let (mtype, body) = parse_exact(data)?;
        if let Some(e) = peer_alert(mtype, body) {
            return Err(e);
        }
        if mtype != MSG_FINISHED {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let got = dec_finished(body)?;
        let expected = finished_mac(&self.s_fin, &sha3_256(&self.transcript), b"SF");
        if !ct_eq(&expected, &got) {
            return Err(AqError::Alert(alert::BAD_FINISHED));
        }
        self.transcript.extend_from_slice(data);
        let master = derive_master(&self.hs, &self.transcript);
        self.rms = derive_rms(&self.hs, &self.transcript);
        self.session = Some(Session::from_master(&master, self.profile, Role::Client));
        self.state = CState::Connected;
        Ok(())
    }

    fn on_ticket(&mut self, data: &[u8]) -> Result<()> {
        let (mtype, body) = parse_exact(data)?;
        if let Some(e) = peer_alert(mtype, body) {
            return Err(e);
        }
        if mtype != MSG_NST {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let (ticket, _ttl) = dec_nst(body)?;
        // Bo'sh ticket — server resumption'ni qo'llamaydi (keshga yozilmaydi).
        self.new_ticket = if ticket.is_empty() {
            None
        } else {
            Some(Ticket { ticket, rms: self.rms })
        };
        Ok(())
    }

    /// Ulangan sessiya va (agar bo'lsa) yangi ticket.
    pub fn finish(self) -> Result<ClientEstablished> {
        let session = self.session.ok_or(AqError::Malformed("handshake tugamagan"))?;
        Ok(ClientEstablished { session, resumed: self.resumed, new_ticket: self.new_ticket })
    }
}

/// Server handshake natijasi.
pub struct ServerEstablished {
    pub session: Session,
    pub client_pk: Option<Vec<u8>>,
    pub resumed: bool,
    /// Qabul qilingan 0-RTT ma'lumot (faqat resumption + anti-replay o'tgan bo'lsa).
    pub early_data: Option<Vec<u8>>,
}

/// HelloRetry yoki ServerHello javobi.
pub enum HelloReply {
    Retry(Vec<u8>),
    Hello(Vec<u8>),
}

impl HelloReply {
    pub fn into_bytes(self) -> Vec<u8> {
        match self {
            HelloReply::Retry(b) | HelloReply::Hello(b) => b,
        }
    }
}

#[derive(PartialEq, Eq, Clone, Copy, Debug)]
enum SState {
    Start,
    WaitFlight,
    Connected,
}

pub struct ServerHs {
    cfg: ServerConfig,
    state: SState,
    transcript: Vec<u8>,
    profile: u8,
    kem: Option<KemPriv>,
    hs: [u8; 32],
    c_fin: [u8; 32],
    s_fin: [u8; 32],
    resumed: bool,
    rms_in: [u8; 32],
    want_ticket: bool,
    early_data: Option<Vec<u8>>,
    client_pk: Option<Vec<u8>>,
    session: Option<Session>,
}

impl ServerHs {
    pub fn new(cfg: ServerConfig) -> Self {
        Self {
            cfg,
            state: SState::Start,
            transcript: Vec::new(),
            profile: 0,
            kem: None,
            hs: [0; 32],
            c_fin: [0; 32],
            s_fin: [0; 32],
            resumed: false,
            rms_in: [0; 32],
            want_ticket: false,
            early_data: None,
            client_pk: None,
            session: None,
        }
    }

    fn own_pub(&self) -> Vec<u8> {
        self.cfg.identity.as_ref().map(|i| i.pk.clone()).unwrap_or_default()
    }

    /// ClientHello (yoki PoW yoqilgan bo'lsa CH_RETRY) ni qayta ishlaydi.
    /// `early` — CH dan keyingi EARLY_DATA frame'ining blobi (agar CH da FLAG_EARLY_DATA bo'lsa).
    pub fn recv_hello(&mut self, data: &[u8], early: Option<&[u8]>) -> Result<HelloReply> {
        if self.state != SState::Start {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let (mtype, body) = parse_exact(data)?;
        if let Some(p) = self.cfg.puzzle.clone() {
            let now = now_secs();
            if mtype == MSG_CLIENT_HELLO {
                let cookie = p.issue(data, now);
                return Ok(HelloReply::Retry(enc_hello_retry(&cookie, p.difficulty)));
            }
            if mtype == MSG_CH_RETRY {
                let (cookie, nonce, ch) = dec_client_hello_retry(body)?;
                if !p.verify(&ch, &cookie, nonce, now) {
                    return Err(AqError::Alert(alert::DOS_REJECT));
                }
                // PoW dan keyin 0-RTT qabul qilinmaydi (CH_RETRY da early blob yo'q).
                return self.process_hello(&ch, None);
            }
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        if mtype != MSG_CLIENT_HELLO {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        self.process_hello(data, early)
    }

    fn process_hello(&mut self, ch_frame: &[u8], early: Option<&[u8]>) -> Result<HelloReply> {
        let (mtype, body) = parse_exact(ch_frame)?;
        if mtype != MSG_CLIENT_HELLO {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let ch = dec_client_hello(body)?;
        let version = ch
            .versions
            .iter()
            .copied()
            .filter(|v| SUPPORTED_VERSIONS.contains(v))
            .max()
            .ok_or(AqError::Alert(alert::NO_COMMON_VERSION))?;
        let profile = SERVER_PREFERENCE
            .iter()
            .copied()
            .find(|p| ch.profiles.contains(p))
            .ok_or(AqError::Alert(alert::NO_COMMON_PROFILE))?;
        self.want_ticket = ch.flags & FLAG_WANT_TICKET != 0;
        let now = now_secs();
        // Resumption: ticket ochilsa va profil mos bo'lsa — RMS va imzo o'tkazib yuboriladi.
        if !ch.ticket.is_empty() {
            if let Some(t) = self.cfg.tickets.clone() {
                if let Some((rms, p)) = t.open(&ch.ticket, now, &self.cfg.ticket_context) {
                    if p == profile {
                        self.rms_in = rms;
                        self.resumed = true;
                    }
                }
            }
        }
        // 0-RTT: faqat resumption + anti-replay o'tgan + mutual auth bo'lmagan holda (S3.3c).
        if let Some(blob) = early {
            if !self.cfg.require_client_auth && self.resumed {
                if let Some(g) = self.cfg.early_guard.clone() {
                    let fresh = g.lock().map(|mut gg| gg.check_and_insert(ch_frame, now)).unwrap_or(false);
                    if fresh {
                        self.early_data = early::open_early(&self.rms_in, ch_frame, blob);
                    }
                }
            }
        }
        self.transcript = ch_frame.to_vec();
        let (ek, kem) = kem::keygen(profile).map_err(|_| AqError::Alert(alert::DECAPS_FAILED))?;
        let flags = if self.cfg.require_client_auth { SH_FLAG_CLIENT_AUTH } else { 0 };
        let srand = rand_bytes::<32>()?;
        let core = sh_core(version, profile, &srand, &ek, flags);
        let s = match &self.cfg.identity {
            Some(id) if !self.resumed => {
                let mut m = self.transcript.clone();
                m.extend_from_slice(&core);
                sig::sign(&id.signing_key(), &sha3_256(&m))?
            }
            _ => Vec::new(),
        };
        let sh = enc_server_hello(&core, &s);
        self.transcript.extend_from_slice(&sh);
        self.profile = profile;
        self.kem = Some(kem);
        self.state = SState::WaitFlight;
        Ok(HelloReply::Hello(sh))
    }

    /// Klient flight'i (CKX [+ CA] + CF). Qaytaradi: ServerFinished [+ NST].
    pub fn recv_flight(&mut self, flight: &[u8]) -> Result<Vec<u8>> {
        if self.state != SState::WaitFlight {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let (mtype, body, n) = parse_frame(flight)?;
        if mtype != MSG_CLIENT_KEX {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let ct = dec_client_kex(body)?;
        let kem = self.kem.as_ref().ok_or(AqError::Alert(alert::UNEXPECTED_MESSAGE))?;
        let ss = kem::decaps(kem, &ct).map_err(|_| AqError::Alert(alert::DECAPS_FAILED))?;
        let (rms_in, sid) = if self.resumed {
            (self.rms_in.to_vec(), server_id_hash(&self.own_pub()))
        } else {
            (Vec::new(), Vec::new())
        };
        let hs = derive_hs(&ss, &rms_in, &sid);
        let (c_fin, s_fin) = fin_keys(&hs);
        self.transcript.extend_from_slice(&flight[..n]);
        let mut rest = &flight[n..];
        if self.cfg.require_client_auth {
            if rest.is_empty() {
                return Err(AqError::Alert(alert::CLIENT_AUTH_REQUIRED));
            }
            let (t2, b2, n2) = parse_frame(rest)?;
            if t2 != MSG_CLIENT_AUTH {
                return Err(AqError::Alert(alert::CLIENT_AUTH_REQUIRED));
            }
            let (pk, csig) = dec_client_auth(b2)?;
            if !sig::verify(&pk, &sha3_256(&self.transcript), &csig) {
                return Err(AqError::Alert(alert::BAD_CLIENT_AUTH));
            }
            if let Some(list) = &self.cfg.allowed_clients {
                if !list.iter().any(|a| a == &pk) {
                    return Err(AqError::Alert(alert::BAD_CLIENT_AUTH));
                }
            }
            self.client_pk = Some(pk);
            self.transcript.extend_from_slice(&rest[..n2]);
            rest = &rest[n2..];
        }
        let (mt3, b3) = parse_exact(rest)?;
        if mt3 != MSG_FINISHED {
            return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
        }
        let got = dec_finished(b3)?;
        let expected = finished_mac(&c_fin, &sha3_256(&self.transcript), b"CF");
        if !ct_eq(&expected, &got) {
            return Err(AqError::Alert(alert::BAD_FINISHED));
        }
        self.transcript.extend_from_slice(rest);
        let sf = finished_mac(&s_fin, &sha3_256(&self.transcript), b"SF");
        let sfin = enc_finished(&sf);
        self.transcript.extend_from_slice(&sfin);
        let master = derive_master(&hs, &self.transcript);
        self.session = Some(Session::from_master(&master, self.profile, Role::Server));
        self.hs = hs;
        self.c_fin = c_fin;
        self.s_fin = s_fin;
        self.state = SState::Connected;
        let mut out = sfin;
        if self.want_ticket {
            // Klient NST kutadi: tickets yo'q bo'lsa ham BO'SH NST yuboramiz (klient qotib qolmasin).
            match self.cfg.tickets.clone() {
                Some(t) => {
                    let rms = derive_rms(&self.hs, &self.transcript);
                    let ticket = t.issue(&rms, self.profile, now_secs(), &self.cfg.ticket_context)?;
                    out.extend_from_slice(&enc_nst(&ticket, t.ttl as u32));
                }
                None => out.extend_from_slice(&enc_nst(&[], 0)),
            }
        }
        Ok(out)
    }

    pub fn is_connected(&self) -> bool {
        self.state == SState::Connected
    }

    pub fn client_pk(&self) -> Option<&[u8]> {
        self.client_pk.as_deref()
    }

    /// Qabul qilingan 0-RTT ma'lumot (handshake tugashidan oldin ham).
    pub fn early_data(&self) -> Option<&[u8]> {
        self.early_data.as_deref()
    }

    pub fn finish(self) -> Result<ServerEstablished> {
        let session = self.session.ok_or(AqError::Malformed("handshake tugamagan"))?;
        Ok(ServerEstablished {
            session,
            client_pk: self.client_pk,
            resumed: self.resumed,
            early_data: self.early_data,
        })
    }
}

/// Handshake xatosi uchun alert frame.
pub fn error_alert(e: &AqError) -> Option<Vec<u8>> {
    match e {
        AqError::Alert(c) => Some(alert_frame(*c)),
        _ => None,
    }
}

/// Early-data frame'idan blobni ajratadi (net qatlami uchun).
pub fn early_blob(frame: &[u8]) -> Result<Vec<u8>> {
    let (mt, body) = parse_exact(frame)?;
    if mt != MSG_EARLY_DATA {
        return Err(AqError::Alert(alert::UNEXPECTED_MESSAGE));
    }
    Ok(body.to_vec())
}

/// CH frame'idan flag'larni o'qiydi (net qatlami: early frame kutilsinmi).
pub fn ch_flags(frame: &[u8]) -> Option<u8> {
    let (mt, body) = parse_exact(frame).ok()?;
    if mt != MSG_CLIENT_HELLO {
        return None;
    }
    dec_client_hello(body).ok().map(|c| c.flags)
}
