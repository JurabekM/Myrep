//! DoS himoyasi: stateless PoW cookie (HelloRetry). Python `aether_q_v51/dos.py` bilan bayt-mos.
//!
//! Server yuk ostida holat ajratmasdan HELLO_RETRY{difficulty, cookie} yuboradi.
//! cookie = ts(8) ‖ KMAC256(secret, SHA3(CH) ‖ ts ‖ D(1), 16, "AETHER-Q-v5.1-COOKIE")
//! Klient PoW yechadi: SHA3("AETHER-Q-v5.1-POW" ‖ cookie ‖ nonce(8)) da ≥ D nol bit.
//! Asimmetriya: klient uchun qimmat, server uchun bitta hash.

use crate::error::{AqError, Result};
use crate::kdf::{ct_eq, kmac256, sha3_256};

pub const POW_LABEL: &[u8] = b"AETHER-Q-v5.1-POW";
pub const COOKIE_CUSTOM: &[u8] = b"AETHER-Q-v5.1-COOKIE";
pub const COOKIE_LEN: usize = 8 + 16;

pub fn leading_zero_bits(d: &[u8]) -> u32 {
    let mut n = 0;
    for &b in d {
        if b == 0 {
            n += 8;
            continue;
        }
        return n + b.leading_zeros();
    }
    n
}

pub struct PuzzleAuthority {
    secret: [u8; 32],
    pub difficulty: u8,
    pub ttl: u64,
}

impl PuzzleAuthority {
    pub fn new(secret: [u8; 32], difficulty: u8, ttl: u64) -> Self {
        Self { secret, difficulty, ttl }
    }

    pub fn random(difficulty: u8, ttl: u64) -> Result<Self> {
        let mut s = [0u8; 32];
        getrandom::getrandom(&mut s).map_err(|_| AqError::Crypto("getrandom"))?;
        Ok(Self::new(s, difficulty, ttl))
    }

    fn mac(&self, ch: &[u8], ts: &[u8; 8], difficulty: u8) -> Vec<u8> {
        let mut input = sha3_256(ch).to_vec();
        input.extend_from_slice(ts);
        input.push(difficulty);
        kmac256(&self.secret, &input, 16, COOKIE_CUSTOM)
    }

    /// Stateless cookie (CH ga bog'langan, `now` bilan vaqt oynasida).
    pub fn issue(&self, ch: &[u8], now: u64) -> Vec<u8> {
        let ts = now.to_be_bytes();
        let mut out = ts.to_vec();
        out.extend_from_slice(&self.mac(ch, &ts, self.difficulty));
        out
    }

    pub fn verify_cookie(&self, ch: &[u8], cookie: &[u8], now: u64) -> bool {
        if cookie.len() != COOKIE_LEN {
            return false;
        }
        let mut ts = [0u8; 8];
        ts.copy_from_slice(&cookie[..8]);
        let issued = u64::from_be_bytes(ts);
        if now < issued || now - issued > self.ttl {
            return false;
        }
        ct_eq(&self.mac(ch, &ts, self.difficulty), &cookie[8..])
    }

    /// Cookie va PoW'ni tekshiradi (CH_RETRY). true → qimmat yo'lni bajarish mumkin.
    pub fn verify(&self, ch: &[u8], cookie: &[u8], nonce: u64, now: u64) -> bool {
        self.verify_cookie(ch, cookie, now) && verify_pow(cookie, nonce, self.difficulty)
    }
}

fn pow_digest(cookie: &[u8], nonce: u64) -> [u8; 32] {
    let mut input = POW_LABEL.to_vec();
    input.extend_from_slice(cookie);
    input.extend_from_slice(&nonce.to_be_bytes());
    sha3_256(&input)
}

/// Server tomoni: bitta hash (arzon).
pub fn verify_pow(cookie: &[u8], nonce: u64, difficulty: u8) -> bool {
    leading_zero_bits(&pow_digest(cookie, nonce)) >= difficulty as u32
}

/// Klient tomoni: D nol bitli nonce. `max_iters` cheklovi (AQ-L05 byudjeti).
pub fn solve_pow(cookie: &[u8], difficulty: u8, max_iters: u64) -> Option<u64> {
    (0..max_iters).find(|&n| leading_zero_bits(&pow_digest(cookie, n)) >= difficulty as u32)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cookie_and_pow_roundtrip() {
        let a = PuzzleAuthority::new([7u8; 32], 8, 30);
        let ch = b"client hello bytes";
        let cookie = a.issue(ch, 1000);
        assert_eq!(cookie.len(), COOKIE_LEN);
        assert!(a.verify_cookie(ch, &cookie, 1005));
        assert!(!a.verify_cookie(b"other", &cookie, 1005), "boshqa CH ga yaroqsiz");
        assert!(!a.verify_cookie(ch, &cookie, 1100), "muddati o'tgan");
        let n = solve_pow(&cookie, 8, 1 << 24).expect("PoW");
        assert!(a.verify(ch, &cookie, n, 1005));
        let bad = (0u64..).find(|&m| !verify_pow(&cookie, m, 8)).unwrap();
        assert!(!a.verify(ch, &cookie, bad, 1005), "PoW yechimsiz nonce rad etilishi kerak");
    }

    #[test]
    fn leading_zero_bits_counts() {
        assert_eq!(leading_zero_bits(&[0x00, 0x80]), 8);
        assert_eq!(leading_zero_bits(&[0x01]), 7);
        assert_eq!(leading_zero_bits(&[0x00, 0x00]), 16);
    }
}
