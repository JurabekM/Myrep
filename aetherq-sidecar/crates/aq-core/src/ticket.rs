//! Session resumption ticket — stateless (TLS 1.3 uslubi). Python `TicketAuthority` bilan bayt-mos.
//!
//! Ticket = nonce(12) ‖ ChaCha20Poly1305(K_t, nonce, RMS(32) ‖ profile(1) ‖ issued(8, BE); AAD)
//! AAD    = "AQTKT" ‖ len(context)(2, BE) ‖ context   (AQ-05: ilova konteksti)
//! Server holat saqlamaydi: hamma ma'lumot ticket ichida shifrlangan.

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{ChaCha20Poly1305, Key, Nonce};

use crate::error::{AqError, Result};

pub const TICKET_AAD: &[u8] = b"AQTKT";

pub fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn aad(context: &[u8]) -> Vec<u8> {
    let mut a = TICKET_AAD.to_vec();
    a.extend_from_slice(&(context.len() as u16).to_be_bytes());
    a.extend_from_slice(context);
    a
}

pub struct TicketAuthority {
    key: [u8; 32],
    /// Ticket amal qilish muddati (soniya).
    pub ttl: u64,
}

impl TicketAuthority {
    pub fn new(key: [u8; 32], ttl: u64) -> Self {
        Self { key, ttl }
    }

    /// Tasodifiy kalit bilan (server ishga tushganda bir marta).
    pub fn random(ttl: u64) -> Result<Self> {
        let mut key = [0u8; 32];
        getrandom::getrandom(&mut key).map_err(|_| AqError::Crypto("getrandom"))?;
        Ok(Self::new(key, ttl))
    }

    /// Ticket chiqaradi. `now` — Unix soniyalari.
    pub fn issue(&self, rms: &[u8; 32], profile: u8, now: u64, context: &[u8]) -> Result<Vec<u8>> {
        let mut nonce = [0u8; 12];
        getrandom::getrandom(&mut nonce).map_err(|_| AqError::Crypto("getrandom"))?;
        let mut pt = rms.to_vec();
        pt.push(profile);
        pt.extend_from_slice(&now.to_be_bytes());
        let c = ChaCha20Poly1305::new(Key::from_slice(&self.key));
        let ct = c
            .encrypt(Nonce::from_slice(&nonce), Payload { msg: &pt, aad: &aad(context) })
            .map_err(|_| AqError::Crypto("ticket seal"))?;
        let mut out = nonce.to_vec();
        out.extend_from_slice(&ct);
        Ok(out)
    }

    /// Ticket'ni ochadi. Qaytaradi: (RMS, profile) yoki None (yaroqsiz / muddati o'tgan / boshqa kontekst).
    pub fn open(&self, ticket: &[u8], now: u64, context: &[u8]) -> Option<([u8; 32], u8)> {
        if ticket.len() < 13 {
            return None;
        }
        let c = ChaCha20Poly1305::new(Key::from_slice(&self.key));
        let pt = c
            .decrypt(
                Nonce::from_slice(&ticket[..12]),
                Payload { msg: &ticket[12..], aad: &aad(context) },
            )
            .ok()?;
        if pt.len() != 32 + 1 + 8 {
            return None;
        }
        let mut rms = [0u8; 32];
        rms.copy_from_slice(&pt[..32]);
        let profile = pt[32];
        let mut ib = [0u8; 8];
        ib.copy_from_slice(&pt[33..41]);
        let issued = u64::from_be_bytes(ib);
        if now < issued || now - issued > self.ttl {
            return None;
        }
        Some((rms, profile))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_and_context_binding() {
        let t = TicketAuthority::new([1u8; 32], 3600);
        let rms = [9u8; 32];
        let tk = t.issue(&rms, 1, 1000, b"tenant-A").unwrap();
        assert_eq!(t.open(&tk, 1100, b"tenant-A"), Some((rms, 1)));
        assert_eq!(t.open(&tk, 1100, b"tenant-B"), None, "boshqa kontekst rad etilishi kerak");
        assert_eq!(t.open(&tk, 1000 + 3601, b"tenant-A"), None, "muddati o'tgan");
    }
}
