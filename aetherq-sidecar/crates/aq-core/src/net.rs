//! Tarmoq qatlami (sinxron, `std::net`): framing, handshake drayverlari, ticket keshi.
//! Python `aether_q_v51/net.py` bilan bir xil oqim, qo'shimcha: PoW retry, 0-RTT, NST.

use std::collections::HashMap;
use std::io::{Read, Write};
use std::sync::Mutex;

use crate::error::{AqError, Result};
use crate::handshake::{
    ch_flags, early_blob, error_alert, ClientConfig, ClientEstablished, ClientHs, HelloReply, Resume, ServerConfig,
    ServerEstablished, ServerHs, Ticket,
};
use crate::transport::REC_HDR;
use crate::wire::{FLAG_EARLY_DATA, HS_HDR, MAX_MSG};

/// Oqimdan AYNAN n bayt o'qiydi.
pub fn read_exact<R: Read>(r: &mut R, n: usize) -> Result<Vec<u8>> {
    let mut buf = vec![0u8; n];
    r.read_exact(&mut buf)?;
    Ok(buf)
}

/// Oqimdan bitta to'liq handshake frame'ini o'qiydi (sarlavha + tana).
pub fn read_frame<R: Read>(r: &mut R) -> Result<Vec<u8>> {
    let hdr = read_exact(r, HS_HDR)?;
    let len = u32::from_be_bytes([0, hdr[3], hdr[4], hdr[5]]) as usize;
    if len > MAX_MSG {
        return Err(AqError::Malformed("handshake xabari juda katta"));
    }
    let mut out = hdr;
    out.extend_from_slice(&read_exact(r, len)?);
    Ok(out)
}

/// Oqimdan bitta transport record'ini o'qiydi.
pub fn read_record<R: Read>(r: &mut R) -> Result<Vec<u8>> {
    let hdr = read_exact(r, REC_HDR)?;
    let len = u32::from_be_bytes([hdr[1], hdr[2], hdr[3], hdr[4]]) as usize;
    if len > MAX_MSG {
        return Err(AqError::Malformed("record juda katta"));
    }
    let mut out = hdr;
    out.extend_from_slice(&read_exact(r, len)?);
    Ok(out)
}

/// Xatoni (agar alert bo'lsa) qarshi tomonga yuboradi, so'ng qaytaradi.
fn fail<W: Write>(w: &mut W, e: AqError) -> AqError {
    if let Some(a) = error_alert(&e) {
        let _ = w.write_all(&a);
    }
    e
}

/// Klient ticket keshi (resumption). Kalit — manzil + server ochiq kaliti (hex).
#[derive(Default)]
pub struct SessionCache {
    inner: Mutex<HashMap<String, Ticket>>,
}

impl SessionCache {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get(&self, key: &str) -> Option<Resume> {
        self.inner.lock().ok()?.get(key).map(|t| t.as_resume())
    }

    pub fn put(&self, key: &str, t: Ticket) {
        if let Ok(mut m) = self.inner.lock() {
            m.insert(key.to_string(), t);
        }
    }

    pub fn remove(&self, key: &str) {
        if let Ok(mut m) = self.inner.lock() {
            m.remove(key);
        }
    }

    pub fn len(&self) -> usize {
        self.inner.lock().map(|m| m.len()).unwrap_or(0)
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Klient tomoni: handshake → sessiya (+ resumption/0-RTT, yangi ticket).
pub fn client_handshake<S: Read + Write>(stream: &mut S, cfg: ClientConfig) -> Result<ClientEstablished> {
    let want_ticket = cfg.want_ticket;
    let mut c = ClientHs::new(cfg);
    let first = c.start()?;
    stream.write_all(&first)?;
    while !c.is_connected() {
        let msg = read_frame(stream)?;
        match c.recv(&msg) {
            Ok(Some(out)) => stream.write_all(&out)?,
            Ok(None) => {}
            Err(e) => return Err(fail(stream, e)),
        }
    }
    if want_ticket {
        // Server SF bilan birga NST yuboradi (Python bilan bir xil).
        let msg = read_frame(stream)?;
        if let Err(e) = c.recv(&msg) {
            return Err(fail(stream, e));
        }
    }
    c.finish()
}

/// Server tomoni: handshake → sessiya (+ PoW, resumption, 0-RTT early data).
pub fn server_handshake<S: Read + Write>(stream: &mut S, cfg: ServerConfig) -> Result<ServerEstablished> {
    let require_ca = cfg.require_client_auth;
    let mut s = ServerHs::new(cfg);
    let first = read_frame(stream)?;
    // CH da FLAG_EARLY_DATA bo'lsa, keyingi frame — 0-RTT blob (PoW yo'lida ham o'qiladi).
    let early = match ch_flags(&first) {
        Some(f) if f & FLAG_EARLY_DATA != 0 => Some(early_blob(&read_frame(stream)?)?),
        _ => None,
    };
    let mut reply = match s.recv_hello(&first, early.as_deref()) {
        Ok(r) => r,
        Err(e) => return Err(fail(stream, e)),
    };
    loop {
        match reply {
            HelloReply::Retry(r) => {
                stream.write_all(&r)?;
                let f = read_frame(stream)?;
                reply = match s.recv_hello(&f, None) {
                    Ok(r) => r,
                    Err(e) => return Err(fail(stream, e)),
                };
            }
            HelloReply::Hello(sh) => {
                stream.write_all(&sh)?;
                break;
            }
        }
    }
    // Klient flight'i: CKX ‖ [CA] ‖ CF — xuddi Python net.server_handshake kabi.
    let mut flight = read_frame(stream)?;
    if require_ca {
        flight.extend_from_slice(&read_frame(stream)?);
    }
    flight.extend_from_slice(&read_frame(stream)?);
    let sf = match s.recv_flight(&flight) {
        Ok(sf) => sf,
        Err(e) => return Err(fail(stream, e)),
    };
    stream.write_all(&sf)?;
    s.finish()
}
