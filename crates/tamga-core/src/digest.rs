//! `sha256:<64 kichik hex>` digest turi (spec §2.3).

use std::fmt;

use sha2::{Digest as _, Sha256};

const PREFIX: &str = "sha256:";

#[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Digest(pub [u8; 32]);

impl Digest {
    /// Genesis digest: `seq = 0` yozuvining `prev` qiymati.
    pub const GENESIS: Digest = Digest([0; 32]);

    /// Bir nechta bo'lakni ketma-ket xeshlaydi: `H(p0 || p1 || ...)`.
    pub fn of(parts: &[&[u8]]) -> Self {
        let mut h = Sha256::new();
        for p in parts {
            h.update(p);
        }
        Digest(h.finalize().into())
    }

    /// Qat'iy tahlil: aynan `sha256:` + 64 ta kichik hex belgi.
    pub fn parse(s: &str) -> Option<Self> {
        let hex = s.strip_prefix(PREFIX)?;
        if hex.len() != 64 {
            return None;
        }
        let mut out = [0u8; 32];
        for (i, pair) in hex.as_bytes().chunks_exact(2).enumerate() {
            out[i] = (nibble(pair[0])? << 4) | nibble(pair[1])?;
        }
        Some(Digest(out))
    }

    pub fn to_hex(&self) -> String {
        to_hex(&self.0)
    }
}

fn nibble(c: u8) -> Option<u8> {
    match c {
        b'0'..=b'9' => Some(c - b'0'),
        b'a'..=b'f' => Some(c - b'a' + 10),
        _ => None, // katta harf kanonik emas
    }
}

pub fn to_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push(HEX[(b >> 4) as usize] as char);
        s.push(HEX[(b & 0xf) as usize] as char);
    }
    s
}

impl fmt::Display for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{PREFIX}{}", self.to_hex())
    }
}

impl fmt::Debug for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Display::fmt(self, f)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_known_answer() {
        // FIPS 180-2 B.1: SHA-256("abc").
        assert_eq!(
            Digest::of(&[b"abc"]).to_hex(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        assert_eq!(
            Digest::of(&[b"a", b"bc"]),
            Digest::of(&[b"abc"]),
            "bo'laklar birlashadi"
        );
    }

    #[test]
    fn parse_is_strict() {
        let d = Digest::of(&[b"x"]);
        assert_eq!(Digest::parse(&d.to_string()), Some(d));
        assert!(Digest::parse(&d.to_string().to_uppercase()).is_none());
        assert!(Digest::parse(&format!("sha256:{}", "A".repeat(64))).is_none());
        assert!(Digest::parse(&format!("sha256:{}", "0".repeat(63))).is_none());
        assert!(Digest::parse(&format!("sha512:{}", "0".repeat(64))).is_none());
        assert_eq!(
            Digest::parse(&format!("sha256:{}", "0".repeat(64))),
            Some(Digest::GENESIS)
        );
    }
}
