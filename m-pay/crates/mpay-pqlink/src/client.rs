//! PQ Link qurilma (client) tomoni. Rust soft-wallet va testlar uchun; Android SDK (M6) shu
//! oqimni Kotlin'da takrorlaydi.

use mpay_common::DeviceId;
use mpay_crypto::{ct_eq, rng, SecretKey32};
use zeroize::Zeroizing;

use crate::crypto::{self, ClientKem, DEVICE_SIG_LABEL, DIR_C2S, DIR_S2C};
use crate::device::DeviceSigner;
use crate::identity::ServerIdentity;
use crate::server::SessionId;
use crate::wire::{
    ClientFinishedInner, ClientHello, MsgType, Sealed, ServerAcceptInner, ServerHello, SUITE_V1,
};
use crate::PqLinkError;

/// Boshlangan handshake (ClientHello yuborilgan).
pub struct ClientHandshake {
    kem: ClientKem,
    ch_bytes: Vec<u8>,
    pinned: ServerIdentity,
}

impl ClientHandshake {
    /// ClientHello yaratadi. `pinned` — server identifikatori (oldindan ma'lum).
    pub fn start(pinned: ServerIdentity) -> Result<(Self, Vec<u8>), PqLinkError> {
        let kem = ClientKem::generate()?;
        let ch = ClientHello {
            client_random: rng::array()?,
            suites: vec![SUITE_V1],
            x25519: kem.x25519_public(),
            mlkem_ek: kem.mlkem_ek(),
        };
        let ch_bytes = ch.encode()?;
        Ok((
            Self {
                kem,
                ch_bytes: ch_bytes.clone(),
                pinned,
            },
            ch_bytes,
        ))
    }

    /// ServerHello'ni tekshiradi va ClientFinished qaytaradi. Efemer KEM kalitlari shu yerda
    /// iste'mol qilinadi va tozalanadi.
    pub fn on_server_hello(
        self,
        sh_bytes: &[u8],
        device: &dyn DeviceSigner,
    ) -> Result<(PendingClient, Vec<u8>), PqLinkError> {
        let (sh, unsigned_len) = ServerHello::decode(sh_bytes)?;
        if sh.suite != SUITE_V1 {
            return Err(PqLinkError::UnsupportedSuite);
        }
        if !ct_eq(&sh.server_fp, &self.pinned.fingerprint()) {
            return Err(PqLinkError::ServerNotPinned);
        }
        let th1 = crypto::th1(&self.ch_bytes, &sh_bytes[..unsigned_len]);
        // Imzolar kalit almashuvidan oldin tekshiriladi: soxta server uchun dekapsulyatsiya qilinmaydi.
        self.pinned.verify(&th1, &sh.sig_ed25519, &sh.sig_mldsa65)?;
        let ss = self.kem.finish(&sh.x25519, &sh.mlkem_ct)?;
        let keys = crypto::key_schedule(&ss, &th1)?;
        drop(ss);
        if !crypto::verify_finished(&keys.fin_s, &th1, &sh.server_finished) {
            return Err(PqLinkError::BadFinished);
        }
        let th2 = crypto::th2(&self.ch_bytes, sh_bytes);
        let msg = [DEVICE_SIG_LABEL, &th2[..]].concat();
        let inner = ClientFinishedInner {
            cert_chain: device.cert_chain(),
            device_sig: device.sign(&msg)?,
            client_finished: crypto::finished_mac(&keys.fin_c, &th2)?,
        };
        let pt = Zeroizing::new(inner.encode()?);
        let rec = crypto::seal(
            &keys.c2s,
            MsgType::ClientFinished,
            &sh.session_id,
            0,
            DIR_C2S,
            &pt,
        )?;
        Ok((
            PendingClient {
                session_id: sh.session_id,
                c2s: keys.c2s,
                s2c: keys.s2c,
            },
            rec.encode(),
        ))
    }
}

/// ClientFinished yuborilgan, ServerAccept kutilmoqda.
pub struct PendingClient {
    session_id: SessionId,
    c2s: SecretKey32,
    s2c: SecretKey32,
}

impl PendingClient {
    pub fn on_accept(self, sa_bytes: &[u8]) -> Result<ClientSession, PqLinkError> {
        let rec = Sealed::decode(sa_bytes, MsgType::ServerAccept)?;
        if !ct_eq(&rec.session_id, &self.session_id) || rec.seq != 0 {
            return Err(PqLinkError::UnexpectedMessage);
        }
        let inner = ServerAcceptInner::decode(&crypto::open(&self.s2c, &rec, DIR_S2C)?)?;
        Ok(ClientSession {
            session_id: self.session_id,
            c2s: self.c2s,
            s2c: self.s2c,
            send_seq: 1,
            recv_seq: 1,
            device_id: DeviceId(inner.device_id),
            expires_at: inner.expires_at,
        })
    }
}

/// O'rnatilgan client sessiyasi.
pub struct ClientSession {
    session_id: SessionId,
    c2s: SecretKey32,
    s2c: SecretKey32,
    send_seq: u64,
    recv_seq: u64,
    device_id: DeviceId,
    expires_at: i64,
}

impl std::fmt::Debug for ClientSession {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ClientSession")
            .field("session_id", &hex::encode(self.session_id))
            .field("device_id", &self.device_id)
            .finish_non_exhaustive()
    }
}

impl ClientSession {
    pub fn session_id(&self) -> &SessionId {
        &self.session_id
    }

    /// Server tasdiqlagan qurilma identifikatori.
    pub fn device_id(&self) -> DeviceId {
        self.device_id
    }

    pub fn expires_at(&self) -> i64 {
        self.expires_at
    }

    /// So'rovni muhrlaydi.
    pub fn seal(&mut self, plaintext: &[u8]) -> Result<Vec<u8>, PqLinkError> {
        let seq = self.send_seq;
        self.send_seq += 1;
        Ok(crypto::seal(
            &self.c2s,
            MsgType::Record,
            &self.session_id,
            seq,
            DIR_C2S,
            plaintext,
        )?
        .encode())
    }

    /// Javobni ochadi.
    pub fn open(&mut self, record: &[u8]) -> Result<Zeroizing<Vec<u8>>, PqLinkError> {
        let rec = Sealed::decode(record, MsgType::Record)?;
        if !ct_eq(&rec.session_id, &self.session_id) {
            return Err(PqLinkError::UnknownSession);
        }
        if rec.seq != self.recv_seq {
            return Err(PqLinkError::Replay {
                expected: self.recv_seq,
                got: rec.seq,
            });
        }
        let pt = crypto::open(&self.s2c, &rec, DIR_S2C)?;
        self.recv_seq += 1;
        Ok(pt)
    }
}
