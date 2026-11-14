//! 0-RTT early data — Python `aether_q_v51/early.py` bilan bayt-mos.
//!
//! ⚠ REPLAY: early data ephemeral kalitdan OLDIN shifrlanadi (faqat RMS'ga tayanadi). Hujumchi
//!   ClientHello+early'ni qayta yuborishi mumkin. Shuning uchun: N17 — faqat IDEMPOTENT so'rovlar;
//!   N18 — forward secrecy yo'q; EarlyGuard — CH-hash bo'yicha takror rad etish (oyna ichida).
//! Mutual auth bilan birga ishlatilmaydi (S3.3c — handshake shuni rad etadi).

use std::collections::HashMap;

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{ChaCha20Poly1305, Key, Nonce};

use crate::kdf::{hkdf_expand32, hkdf_extract, sha3_256};

pub const EARLY_LABEL: &[u8] = b"AETHER-Q-v5.1 early";
pub const NONCE_LEN: usize = 12;

/// K_early = HKDF-Expand(HKDF-Extract(RMS, label), label ‖ H(CH), 32).
pub fn derive_early_key(rms: &[u8], ch: &[u8]) -> [u8; 32] {
    let prk = hkdf_extract(rms, EARLY_LABEL);
    let mut info = EARLY_LABEL.to_vec();
    info.extend_from_slice(&sha3_256(ch));
    hkdf_expand32(&prk, &info)
}

/// Klient: early data'ni shifrlaydi. Qaytaradi: nonce ‖ AEAD(data).
pub fn seal_early(rms: &[u8], ch: &[u8], data: &[u8], nonce: &[u8; NONCE_LEN]) -> Vec<u8> {
    let key = derive_early_key(rms, ch);
    let c = ChaCha20Poly1305::new(Key::from_slice(&key));
    let ct = c
        .encrypt(Nonce::from_slice(nonce), Payload { msg: data, aad: &sha3_256(ch) })
        .expect("early seal");
    let mut out = nonce.to_vec();
    out.extend_from_slice(&ct);
    out
}

/// Server: early data'ni ochadi. Yaroqsiz → None (handshake davom etadi).
pub fn open_early(rms: &[u8], ch: &[u8], blob: &[u8]) -> Option<Vec<u8>> {
    if blob.len() < NONCE_LEN + 16 {
        return None;
    }
    let key = derive_early_key(rms, ch);
    let c = ChaCha20Poly1305::new(Key::from_slice(&key));
    c.decrypt(
        Nonce::from_slice(&blob[..NONCE_LEN]),
        Payload { msg: &blob[NONCE_LEN..], aad: &sha3_256(ch) },
    )
    .ok()
}

/// Anti-replay qorovuli: har ClientHello-hash bir marta, `window` soniya ichida.
pub struct EarlyGuard {
    seen: HashMap<[u8; 32], u64>,
    pub window: u64,
    max_entries: usize,
}

impl EarlyGuard {
    pub fn new(window: u64, max_entries: usize) -> Self {
        Self { seen: HashMap::new(), window, max_entries }
    }

    /// Yangi bo'lsa true (qabul), takror bo'lsa false (REPLAY).
    pub fn check_and_insert(&mut self, ch: &[u8], now: u64) -> bool {
        let h = sha3_256(ch);
        if self.seen.len() > self.max_entries {
            let cutoff = now.saturating_sub(self.window);
            self.seen.retain(|_, t| *t > cutoff);
        }
        if let Some(prev) = self.seen.get(&h) {
            if now.saturating_sub(*prev) <= self.window {
                return false;
            }
        }
        self.seen.insert(h, now);
        true
    }

    pub fn len(&self) -> usize {
        self.seen.len()
    }

    pub fn is_empty(&self) -> bool {
        self.seen.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn early_roundtrip_and_replay_guard() {
        let rms = [4u8; 32];
        let ch = b"ch-bytes";
        let blob = seal_early(&rms, ch, b"GET /health", &[1u8; 12]);
        assert_eq!(open_early(&rms, ch, &blob).as_deref(), Some(&b"GET /health"[..]));
        assert!(open_early(&rms, b"other", &blob).is_none());
        let mut g = EarlyGuard::new(60, 1000);
        assert!(g.check_and_insert(ch, 100));
        assert!(!g.check_and_insert(ch, 110), "takror CH rad etilishi kerak");
        assert!(g.check_and_insert(ch, 200), "oynadan tashqarida qayta qabul");
    }
}
