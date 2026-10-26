//! PQ Link server tomoni: handshake, sessiyalar, yozuvlarni ochish/muhrlash.
//!
//! Sessiyalar [`SessionStore`] da (ADR-0006; 2-faza P2.4 — ko'p instansiyada umumiy ombor). Bir
//! sessiya ichida so'rovlar ketma-ket bo'lishi shart: qabul qilinadigan `seq` qat'iy `kutilgan` ga
//! teng.
//!
//! Handshake ikki bosqichli: og'ir kriptografiya ([`PqLinkServer::hello_crypto`],
//! [`PqLinkServer::finish_crypto`]) — sinxron (server uni `spawn_blocking` da chaqiradi), ombor
//! bosqichlari — async. [`PqLinkServer::handle_hello`] / [`PqLinkServer::handle_finish`] ularni
//! birlashtiradi (testlar va oddiy foydalanish).

use std::sync::Arc;

use mpay_common::clock::Clock;
use mpay_common::ports::SecurityLevel;
use mpay_common::DeviceId;
use mpay_crypto::{ct_eq, rng};
use zeroize::Zeroizing;

use crate::attestation::{verify_chain, AttestationPolicy, TrustAnchors, VerifiedDevice};
use crate::crypto::{self, SessionKeys, DEVICE_SIG_LABEL, DIR_C2S, DIR_S2C};
use crate::identity::{ServerIdentity, ServerSigner};
use crate::store::{
    EstablishedSession, MemorySessionStore, PendingSession, SessionStore, TakePending,
};
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
    /// Yakunlanmagan handshake'lar chegarasi (`hello` toshqini o'rnatilgan sessiyalar joyini egallamasin).
    pub max_pending: usize,
    pub attestation: AttestationPolicy,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            session_ttl_secs: 15 * 60,
            handshake_ttl_secs: 60,
            max_sessions: 10_000,
            max_pending: 2_500,
            attestation: AttestationPolicy::default(),
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
    /// Qurilma attestatsiyadan o'tgan vaqt (ro'yxatga olish darvozasi bo'lsa; ADR-0015).
    pub attested_at: Option<i64>,
}

/// `hello` kriptografiyasi natijasi (omborga hali yozilmagan).
pub struct HelloPrepared {
    session_id: SessionId,
    sh_bytes: Vec<u8>,
    pending: PendingSession,
}

/// `finish`: omordan olingan yakunlanmagan sessiya va yozuv.
pub struct FinishStart {
    rec: Sealed,
    pending: PendingSession,
}

/// `finish` kriptografiyasi natijasi (darvoza va omborga hali yozilmagan).
pub struct FinishVerified {
    session_id: SessionId,
    pending: PendingSession,
    device: VerifiedDevice,
}

/// PQ Link server.
pub struct PqLinkServer {
    signer: Arc<dyn ServerSigner>,
    anchors: TrustAnchors,
    cfg: ServerConfig,
    clock: Arc<dyn Clock>,
    store: Arc<dyn SessionStore>,
    enrollment: Option<Arc<dyn crate::EnrollmentGate>>,
}

impl std::fmt::Debug for PqLinkServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PqLinkServer")
            .field("identity", self.signer.identity())
            .field("store", &self.store)
            .finish()
    }
}

impl PqLinkServer {
    /// Xotiradagi ombor bilan (bitta instansiya).
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
            store: Arc::new(MemorySessionStore::new()),
            enrollment: None,
        }
    }

    /// Sessiyalar ombori (ko'p instansiyada — umumiy).
    pub fn with_store(mut self, store: Arc<dyn SessionStore>) -> Self {
        self.store = store;
        self
    }

    /// Attestatsiya zanjirini server ildizlari va siyosati bo'yicha tekshiradi (qurilma kalitini
    /// almashtirishda — handshake'dan tashqari, ADR-0015).
    pub fn verify_device_chain(
        &self,
        chain: &[Vec<u8>],
    ) -> Result<crate::attestation::VerifiedDevice, PqLinkError> {
        verify_chain(
            chain,
            &self.anchors,
            &self.cfg.attestation,
            self.clock.unix(),
        )
    }

    /// Qurilmani ro'yxatdan o'tkazish talabi (P1.7). Bo'lmasa — har qanday attestatsiyali qurilma.
    pub fn with_enrollment(mut self, gate: Arc<dyn crate::EnrollmentGate>) -> Self {
        self.enrollment = Some(gate);
        self
    }

    pub fn identity(&self) -> &ServerIdentity {
        self.signer.identity()
    }

    /// Muddati o'tmagan sessiyalar soni (diagnostika; ombor xatosida 0).
    pub async fn session_count(&self) -> usize {
        self.store.count(self.clock.unix()).await.unwrap_or(0)
    }

    /// Yangi handshake uchun joy bormi — qimmat ML-KEM/ML-DSA hisoblashdan **oldin** chaqiriladi
    /// (CPU kuchaytirish hujumi).
    pub async fn has_room(&self) -> Result<bool, PqLinkError> {
        self.store
            .has_room(
                self.clock.unix(),
                self.cfg.max_sessions,
                self.cfg.max_pending,
            )
            .await
    }

    /// ClientHello → ServerHello kriptografiyasi (sinxron, CPU).
    pub fn hello_crypto(&self, ch_bytes: &[u8]) -> Result<HelloPrepared, PqLinkError> {
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
        let SessionKeys {
            c2s, s2c, fin_c, ..
        } = keys;
        Ok(HelloPrepared {
            session_id,
            sh_bytes,
            pending: PendingSession {
                c2s,
                s2c,
                fin_c,
                th2,
                expires: self.clock.unix() + self.cfg.handshake_ttl_secs,
            },
        })
    }

    /// Yakunlanmagan sessiyani omborga yozadi va ServerHello'ni qaytaradi.
    pub async fn commit_hello(&self, p: HelloPrepared) -> Result<Vec<u8>, PqLinkError> {
        if !self.has_room().await? {
            return Err(PqLinkError::TooManySessions);
        }
        self.store.put_pending(p.session_id, p.pending).await?;
        Ok(p.sh_bytes)
    }

    /// ClientHello → ServerHello (joy tekshiruvi, kriptografiya, ombor).
    pub async fn handle_hello(&self, ch_bytes: &[u8]) -> Result<Vec<u8>, PqLinkError> {
        if !self.has_room().await? {
            return Err(PqLinkError::TooManySessions);
        }
        let p = self.hello_crypto(ch_bytes)?;
        self.commit_hello(p).await
    }

    /// ClientFinished: yozuvni o'qiydi va yakunlanmagan sessiyani ombordan oladi (o'chiradi —
    /// har qanday keyingi xatoda u qaytarilmaydi).
    pub async fn begin_finish(&self, cf_bytes: &[u8]) -> Result<FinishStart, PqLinkError> {
        let rec = Sealed::decode(cf_bytes, MsgType::ClientFinished)?;
        match self
            .store
            .take_pending(&rec.session_id, self.clock.unix())
            .await?
        {
            TakePending::Pending(pending) => Ok(FinishStart { rec, pending }),
            // Takroriy ClientFinished o'rnatilgan sessiyani buzmaydi.
            TakePending::Established => Err(PqLinkError::UnexpectedMessage),
            TakePending::Missing => Err(PqLinkError::UnknownSession),
        }
    }

    /// ClientFinished kriptografiyasi: finished MAC, attestatsiya zanjiri, qurilma imzosi (sinxron).
    pub fn finish_crypto(&self, s: FinishStart) -> Result<FinishVerified, PqLinkError> {
        let FinishStart { rec, pending } = s;
        if rec.seq != 0 {
            return Err(PqLinkError::Replay {
                expected: 0,
                got: rec.seq,
            });
        }
        let inner = crypto::open(&pending.c2s, &rec, DIR_C2S)?;
        let cf = ClientFinishedInner::decode(&inner)?;
        if !crypto::verify_finished(&pending.fin_c, &pending.th2, &cf.client_finished) {
            return Err(PqLinkError::BadFinished);
        }
        let device = verify_chain(
            &cf.cert_chain,
            &self.anchors,
            &self.cfg.attestation,
            self.clock.unix(),
        )?;
        let msg = [DEVICE_SIG_LABEL, &pending.th2[..]].concat();
        device.verify_signature(&msg, &cf.device_sig)?;
        Ok(FinishVerified {
            session_id: rec.session_id,
            pending,
            device,
        })
    }

    /// Ro'yxatga olish darvozasi, ServerAccept va sessiyani omborga yozish.
    pub async fn commit_finish(
        &self,
        v: FinishVerified,
    ) -> Result<(SessionInfo, Vec<u8>), PqLinkError> {
        let FinishVerified {
            session_id,
            pending,
            device,
        } = v;
        let attested_at = match &self.enrollment {
            Some(gate) => Some(gate.admit(&device).await?),
            None => None,
        };
        let expires = self.clock.unix() + self.cfg.session_ttl_secs;
        let accept = ServerAcceptInner {
            device_id: device.device_id.0,
            expires_at: expires,
        };
        let out = crypto::seal(
            &pending.s2c,
            MsgType::ServerAccept,
            &session_id,
            0,
            DIR_S2C,
            &accept.encode(),
        )?;
        let info = SessionInfo {
            session_id,
            device_id: device.device_id,
            security_level: device.security_level,
            expires_at: expires,
            attested_at,
        };
        let PendingSession { c2s, s2c, .. } = pending;
        self.store
            .put_established(
                session_id,
                EstablishedSession {
                    c2s,
                    s2c,
                    device_id: device.device_id,
                    security_level: device.security_level,
                    attested_at,
                    recv_seq: 1,
                    expires,
                },
            )
            .await?;
        tracing::info!(device = %info.device_id, level = ?info.security_level, "pqlink: sessiya o'rnatildi");
        Ok((info, out.encode()))
    }

    /// ClientFinished → ServerAccept. Har qanday xatoda yakunlanmagan sessiya o'chiriladi.
    pub async fn handle_finish(
        &self,
        cf_bytes: &[u8],
    ) -> Result<(SessionInfo, Vec<u8>), PqLinkError> {
        let s = self.begin_finish(cf_bytes).await?;
        let v = self.finish_crypto(s)?;
        self.commit_finish(v).await
    }

    /// Qurilmadan kelgan yozuvni ochadi.
    pub async fn open(
        &self,
        record: &[u8],
    ) -> Result<(SessionInfo, Zeroizing<Vec<u8>>), PqLinkError> {
        let rec = Sealed::decode(record, MsgType::Record)?;
        let Some(s) = self
            .store
            .get_established(&rec.session_id, self.clock.unix())
            .await?
        else {
            return Err(PqLinkError::UnknownSession);
        };
        if rec.seq != s.recv_seq {
            // Takror yoki tartibsiz — rad, sessiya saqlanadi (holat o'zgarmaydi).
            return Err(PqLinkError::Replay {
                expected: s.recv_seq,
                got: rec.seq,
            });
        }
        // Sessiya AEAD xatosida o'chirilmaydi: `session_id` va `seq` ochiq sarlavhada — kim ko'rsa,
        // soxta yozuv bilan begona sessiyani yopib qo'yardi (DoS). `recv_seq` oshmaydi.
        let pt = crypto::open(&s.c2s, &rec, DIR_C2S).inspect_err(|_| {
            tracing::warn!("pqlink: yozuvni ochib bo'lmadi — rad etildi");
        })?;
        // Hisoblagich atomar: parallel ikki so'rov (yoki ikki instansiya) bir xil `seq` ni o'tkazmaydi.
        if !self.store.advance_recv(&rec.session_id, rec.seq).await? {
            return Err(PqLinkError::Replay {
                expected: rec.seq + 1,
                got: rec.seq,
            });
        }
        let info = SessionInfo {
            session_id: rec.session_id,
            device_id: s.device_id,
            security_level: s.security_level,
            expires_at: s.expires,
            attested_at: s.attested_at,
        };
        Ok((info, pt))
    }

    /// Qurilmaga javobni muhrlaydi.
    pub async fn seal(
        &self,
        session_id: &SessionId,
        plaintext: &[u8],
    ) -> Result<Vec<u8>, PqLinkError> {
        let Some(s) = self
            .store
            .get_established(session_id, self.clock.unix())
            .await?
        else {
            return Err(PqLinkError::UnknownSession);
        };
        let Some(seq) = self.store.next_send(session_id).await? else {
            return Err(PqLinkError::UnknownSession);
        };
        Ok(crypto::seal(&s.s2c, MsgType::Record, session_id, seq, DIR_S2C, plaintext)?.encode())
    }

    /// Sessiyani yopadi.
    pub async fn close(&self, session_id: &SessionId) {
        if let Err(e) = self.store.remove(session_id).await {
            tracing::warn!(error = %e, "pqlink: sessiya yopilmadi");
        }
    }
}

/// Sessiya ID'larini constant-time solishtirish (tashqi foydalanish uchun).
pub fn session_id_eq(a: &SessionId, b: &SessionId) -> bool {
    ct_eq(a, b)
}
