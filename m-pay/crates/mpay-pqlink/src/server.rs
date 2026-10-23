//! PQ Link server tomoni: handshake, sessiyalar jadvali, yozuvlarni ochish/muhrlash.
//!
//! Sessiyalar xotirada (ADR-0006). Bir sessiya ichida so'rovlar ketma-ket bo'lishi shart:
//! qabul qilinadigan `seq` qat'iy `kutilgan` ga teng.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use mpay_common::clock::Clock;
use mpay_common::ports::SecurityLevel;
use mpay_common::DeviceId;
use mpay_crypto::{ct_eq, rng, SecretKey32};
use zeroize::Zeroizing;

use crate::attestation::{verify_chain, AttestationPolicy, TrustAnchors, VerifiedDevice};
use crate::crypto::{self, SessionKeys, DEVICE_SIG_LABEL, DIR_C2S, DIR_S2C};
use crate::identity::{ServerIdentity, ServerSigner};
use crate::wire::{
    ClientFinishedInner, ClientHello, MsgType, Sealed, ServerAcceptInner, ServerHello,
    SESSION_ID_LEN, SUITE_V1,
};
use crate::PqLinkError;

/// Sessiya identifikatori.
pub type SessionId = [u8; SESSION_ID_LEN];

/// Server sozlamalari.
#[derive(Debug, Clone)]
pub struct ServerConfig {
    /// O'rnatilgan sessiya umri (sekund).
    pub session_ttl_secs: i64,
    /// Yakunlanmagan handshake umri (sekund).
    pub handshake_ttl_secs: i64,
    /// Bir vaqtdagi sessiyalar (pending + established) chegarasi.
    pub max_sessions: usize,
    pub attestation: AttestationPolicy,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            session_ttl_secs: 15 * 60,
            handshake_ttl_secs: 60,
            max_sessions: 10_000,
            attestation: AttestationPolicy::default(),
        }
    }
}

struct Pending {
    keys: SessionKeys,
    th2: [u8; 32],
    expires: i64,
}

struct Established {
    c2s: SecretKey32,
    s2c: SecretKey32,
    device: VerifiedDevice,
    recv_seq: u64,
    send_seq: u64,
    expires: i64,
}

enum Slot {
    Pending(Pending),
    Established(Established),
}

impl Slot {
    fn expires(&self) -> i64 {
        match self {
            Slot::Pending(p) => p.expires,
            Slot::Established(e) => e.expires,
        }
    }
}

/// O'rnatilgan sessiya haqida ochiq ma'lumot (so'rov ishlovchilariga beriladi).
#[derive(Debug, Clone)]
pub struct SessionInfo {
    pub session_id: SessionId,
    pub device_id: DeviceId,
    pub security_level: SecurityLevel,
    pub expires_at: i64,
}

/// PQ Link server.
pub struct PqLinkServer {
    signer: Arc<dyn ServerSigner>,
    anchors: TrustAnchors,
    cfg: ServerConfig,
    clock: Arc<dyn Clock>,
    sessions: Mutex<HashMap<SessionId, Slot>>,
}

impl std::fmt::Debug for PqLinkServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PqLinkServer")
            .field("identity", self.signer.identity())
            .field("sessions", &self.session_count())
            .finish()
    }
}

impl PqLinkServer {
    pub fn new(
        signer: Arc<dyn ServerSigner>,
        anchors: TrustAnchors,
        cfg: ServerConfig,
        clock: Arc<dyn Clock>,
    ) -> Self {
        Self {
            signer,
            anchors,
            cfg,
            clock,
            sessions: Mutex::new(HashMap::new()),
        }
    }

    pub fn identity(&self) -> &ServerIdentity {
        self.signer.identity()
    }

    pub fn session_count(&self) -> usize {
        self.sessions.lock().map(|s| s.len()).unwrap_or(0)
    }

    fn lock(&self) -> Result<std::sync::MutexGuard<'_, HashMap<SessionId, Slot>>, PqLinkError> {
        self.sessions
            .lock()
            .map_err(|_| PqLinkError::Crypto("sessiya lock".into()))
    }

    /// ClientHello → ServerHello.
    pub fn handle_hello(&self, ch_bytes: &[u8]) -> Result<Vec<u8>, PqLinkError> {
        let ch = ClientHello::decode(ch_bytes)?;
        if !ch.suites.contains(&SUITE_V1) {
            return Err(PqLinkError::UnsupportedSuite);
        }
        let (x_pub, mlkem_ct, ss) = crypto::server_encapsulate(&ch.x25519, &ch.mlkem_ek)?;
        let session_id: SessionId = rng::array()?;
        let mut sh = ServerHello {
            server_random: rng::array()?,
            session_id,
            suite: SUITE_V1,
            x25519: x_pub,
            mlkem_ct,
            server_fp: self.identity().fingerprint(),
            sig_ed25519: [0; 64],
            sig_mldsa65: Vec::new(),
            server_finished: [0; 32],
        };
        let th1 = crypto::th1(ch_bytes, &sh.encode_unsigned()?);
        let keys = crypto::key_schedule(&ss, &th1)?;
        drop(ss);
        let (ed, ml) = self.signer.sign(&th1)?;
        sh.sig_ed25519 = ed;
        sh.sig_mldsa65 = ml;
        sh.server_finished = crypto::finished_mac(&keys.fin_s, &th1)?;
        let sh_bytes = sh.encode()?;
        let th2 = crypto::th2(ch_bytes, &sh_bytes);

        let now = self.clock.unix();
        let mut map = self.lock()?;
        map.retain(|_, s| s.expires() > now);
        if map.len() >= self.cfg.max_sessions {
            return Err(PqLinkError::TooManySessions);
        }
        map.insert(
            session_id,
            Slot::Pending(Pending {
                keys,
                th2,
                expires: now + self.cfg.handshake_ttl_secs,
            }),
        );
        Ok(sh_bytes)
    }

    /// ClientFinished → ServerAccept. Har qanday xatoda yakunlanmagan sessiya o'chiriladi.
    pub fn handle_finish(&self, cf_bytes: &[u8]) -> Result<(SessionInfo, Vec<u8>), PqLinkError> {
        let rec = Sealed::decode(cf_bytes, MsgType::ClientFinished)?;
        let now = self.clock.unix();
        let pending = {
            let mut map = self.lock()?;
            match map.remove(&rec.session_id) {
                Some(Slot::Pending(p)) if p.expires > now => p,
                Some(other @ Slot::Established(_)) => {
                    // Takroriy ClientFinished o'rnatilgan sessiyani buzmaydi.
                    map.insert(rec.session_id, other);
                    return Err(PqLinkError::UnexpectedMessage);
                }
                _ => return Err(PqLinkError::UnknownSession),
            }
        };
        if rec.seq != 0 {
            return Err(PqLinkError::Replay {
                expected: 0,
                got: rec.seq,
            });
        }
        let inner = crypto::open(&pending.keys.c2s, &rec, DIR_C2S)?;
        let cf = ClientFinishedInner::decode(&inner)?;
        if !crypto::verify_finished(&pending.keys.fin_c, &pending.th2, &cf.client_finished) {
            return Err(PqLinkError::BadFinished);
        }
        let device = verify_chain(&cf.cert_chain, &self.anchors, &self.cfg.attestation, now)?;
        let msg = [DEVICE_SIG_LABEL, &pending.th2[..]].concat();
        device.verify_signature(&msg, &cf.device_sig)?;

        let expires = now + self.cfg.session_ttl_secs;
        let accept = ServerAcceptInner {
            device_id: device.device_id.0,
            expires_at: expires,
        };
        let out = crypto::seal(
            &pending.keys.s2c,
            MsgType::ServerAccept,
            &rec.session_id,
            0,
            DIR_S2C,
            &accept.encode(),
        )?;
        let info = SessionInfo {
            session_id: rec.session_id,
            device_id: device.device_id,
            security_level: device.security_level,
            expires_at: expires,
        };
        let SessionKeys { c2s, s2c, .. } = pending.keys;
        self.lock()?.insert(
            rec.session_id,
            Slot::Established(Established {
                c2s,
                s2c,
                device,
                recv_seq: 1,
                send_seq: 1,
                expires,
            }),
        );
        tracing::info!(device = %info.device_id, level = ?info.security_level, "pqlink: sessiya o'rnatildi");
        Ok((info, out.encode()))
    }

    /// Qurilmadan kelgan yozuvni ochadi.
    pub fn open(&self, record: &[u8]) -> Result<(SessionInfo, Zeroizing<Vec<u8>>), PqLinkError> {
        let rec = Sealed::decode(record, MsgType::Record)?;
        let now = self.clock.unix();
        let mut map = self.lock()?;
        let Some(Slot::Established(s)) = map.get_mut(&rec.session_id) else {
            return Err(PqLinkError::UnknownSession);
        };
        if s.expires <= now {
            map.remove(&rec.session_id);
            return Err(PqLinkError::UnknownSession);
        }
        if rec.seq != s.recv_seq {
            // Takror yoki tartibsiz — rad, sessiya saqlanadi (holat o'zgarmaydi).
            return Err(PqLinkError::Replay {
                expected: s.recv_seq,
                got: rec.seq,
            });
        }
        match crypto::open(&s.c2s, &rec, DIR_C2S) {
            Ok(pt) => {
                s.recv_seq += 1;
                let info = SessionInfo {
                    session_id: rec.session_id,
                    device_id: s.device.device_id,
                    security_level: s.device.security_level,
                    expires_at: s.expires,
                };
                Ok((info, pt))
            }
            Err(e) => {
                map.remove(&rec.session_id);
                tracing::warn!("pqlink: buzilgan yozuv — sessiya yopildi");
                Err(e)
            }
        }
    }

    /// Qurilmaga javobni muhrlaydi.
    pub fn seal(&self, session_id: &SessionId, plaintext: &[u8]) -> Result<Vec<u8>, PqLinkError> {
        let mut map = self.lock()?;
        let Some(Slot::Established(s)) = map.get_mut(session_id) else {
            return Err(PqLinkError::UnknownSession);
        };
        let seq = s.send_seq;
        s.send_seq += 1;
        Ok(crypto::seal(&s.s2c, MsgType::Record, session_id, seq, DIR_S2C, plaintext)?.encode())
    }

    /// Sessiyani yopadi.
    pub fn close(&self, session_id: &SessionId) {
        if let Ok(mut m) = self.sessions.lock() {
            m.remove(session_id);
        }
    }
}

/// Sessiya ID'larini constant-time solishtirish (tashqi foydalanish uchun).
pub fn session_id_eq(a: &SessionId, b: &SessionId) -> bool {
    ct_eq(a, b)
}
