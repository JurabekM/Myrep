//! Identity — ML-DSA-65 imzolash kaliti (server va klient autentifikatsiyasi).
//!
//! Fayl formati (matn):
//!   aq-identity v1
//!   seed=<64 hex>        ← maxfiy (32 bayt ML-DSA seed)
//!   pk=<3904 hex>        ← ochiq (1952 bayt)
//!
//! Eslatma: KEM kalitlari identity'da emas — har handshake'da ephemeral (forward secrecy).

use std::fs;
use std::io;
use std::path::Path;

use ml_dsa::{MlDsa65, SigningKey};

use crate::error::{AqError, Result};
use crate::sig;

#[derive(Clone)]
pub struct Identity {
    pub seed: [u8; 32],
    pub pk: Vec<u8>,
}

impl Identity {
    pub fn generate() -> Result<Self> {
        let mut seed = [0u8; 32];
        getrandom::getrandom(&mut seed).map_err(|_| AqError::Crypto("getrandom"))?;
        Ok(Self::from_seed(seed))
    }

    pub fn from_seed(seed: [u8; 32]) -> Self {
        let (_, pk) = sig::keypair_from_seed(&seed);
        Self { seed, pk }
    }

    pub fn signing_key(&self) -> SigningKey<MlDsa65> {
        sig::keypair_from_seed(&self.seed).0
    }

    pub fn save(&self, path: &Path) -> io::Result<()> {
        let text = format!("aq-identity v1\nseed={}\npk={}\n", to_hex(&self.seed), to_hex(&self.pk));
        fs::write(path, text)
    }

    pub fn load(path: &Path) -> io::Result<Self> {
        let text = fs::read_to_string(path)?;
        let mut seed = None;
        for line in text.lines() {
            if let Some(v) = line.strip_prefix("seed=") {
                let b = from_hex(v.trim()).ok_or_else(bad)?;
                let arr: [u8; 32] = b.try_into().map_err(|_| bad())?;
                seed = Some(arr);
            }
        }
        let seed = seed.ok_or_else(bad)?;
        Ok(Self::from_seed(seed))
    }

    /// Ochiq kalitni faylga yozish (klientlar uchun `server_pub`/allowlist).
    pub fn save_public(&self, path: &Path) -> io::Result<()> {
        fs::write(path, format!("{}\n", to_hex(&self.pk)))
    }
}

fn bad() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, "identity fayli buzilgan")
}

/// Allowlist: har qatorda bitta ochiq kalit (hex). `#` bilan boshlangan qatorlar izoh.
pub fn load_allowlist(path: &Path) -> io::Result<Vec<Vec<u8>>> {
    let text = fs::read_to_string(path)?;
    let mut out = Vec::new();
    for line in text.lines() {
        let t = line.trim();
        if t.is_empty() || t.starts_with('#') {
            continue;
        }
        out.push(from_hex(t).ok_or_else(bad)?);
    }
    Ok(out)
}

/// Ochiq kalitni fayldan o'qish (hex, bitta qator).
pub fn load_public_key(path: &Path) -> io::Result<Vec<u8>> {
    let text = fs::read_to_string(path)?;
    from_hex(text.trim()).ok_or_else(bad)
}

pub fn to_hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

pub fn from_hex(s: &str) -> Option<Vec<u8>> {
    if s.len() % 2 != 0 {
        return None;
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(s.get(i..i + 2)?, 16).ok())
        .collect()
}
