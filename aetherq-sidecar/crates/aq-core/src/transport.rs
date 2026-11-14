//! Transport AEAD record layer (spec §8) — Python `aether_q_v51/transport.py` bilan bayt-mos.
//!
//! Record: type(1) ‖ length(4, BE) ‖ ciphertext (length = pt + 16).
//! AAD   = type(1) ‖ length(4) ‖ epoch(4) ‖ profile(1).
//! Nonce = IV(12) XOR seq (little-endian, past 8 bayt).

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{ChaCha20Poly1305, Key, Nonce};

use crate::error::{AqError, Result};
use crate::kdf::{hkdf_expand, hkdf_extract};

pub const TRANSPORT_LABEL: &[u8] = b"AETHER-Q-v5.1-TRANSPORT/L3/v1";
pub const TYPE_APP_DATA: u8 = 0x17;
pub const TYPE_ALERT: u8 = 0x15;
pub const TYPE_KEY_UPDATE: u8 = 0x18;
pub const REC_HDR: usize = 5;
pub const TAG_LEN: usize = 16;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Role {
    Client,
    Server,
}

/// Bitta yo'nalish: kalit, IV, monotonik hisoblagich.
struct Dir {
    key: [u8; 32],
    iv: [u8; 12],
    seq: u64,
}

impl Dir {
    fn new(key: [u8; 32], iv: [u8; 12]) -> Self {
        Self { key, iv, seq: 0 }
    }

    fn nonce(&self) -> [u8; 12] {
        let mut n = self.iv;
        for (i, b) in self.seq.to_le_bytes().iter().enumerate() {
            n[i] ^= b;
        }
        n
    }

    fn cipher(&self) -> ChaCha20Poly1305 {
        ChaCha20Poly1305::new(Key::from_slice(&self.key))
    }

    /// K_{n+1} = HKDF-Expand(K_n, TRANSPORT_LABEL ‖ "/rekey" ‖ n(8, BE), 32); seq = 0 (N14).
    fn rekey(&mut self, n: u64) {
        let mut info = TRANSPORT_LABEL.to_vec();
        info.extend_from_slice(b"/rekey");
        info.extend_from_slice(&n.to_be_bytes());
        let v = hkdf_expand(&self.key, &info, 32);
        self.key.copy_from_slice(&v);
        self.seq = 0;
    }
}

fn aad(rtype: u8, length: u32, epoch: u32, profile: u8) -> [u8; 10] {
    let mut a = [0u8; 10];
    a[0] = rtype;
    a[1..5].copy_from_slice(&length.to_be_bytes());
    a[5..9].copy_from_slice(&epoch.to_be_bytes());
    a[9] = profile;
    a
}

fn seal_dir(d: &mut Dir, profile: u8, plaintext: &[u8], rtype: u8) -> Result<Vec<u8>> {
    let length = (plaintext.len() + TAG_LEN) as u32;
    let a = aad(rtype, length, 0, profile);
    let nonce = d.nonce();
    let ct = d
        .cipher()
        .encrypt(Nonce::from_slice(&nonce), Payload { msg: plaintext, aad: &a })
        .map_err(|_| AqError::Crypto("AEAD seal"))?;
    d.seq += 1;
    let mut rec = Vec::with_capacity(REC_HDR + ct.len());
    rec.push(rtype);
    rec.extend_from_slice(&length.to_be_bytes());
    rec.extend_from_slice(&ct);
    Ok(rec)
}

fn open_dir(d: &mut Dir, profile: u8, record: &[u8]) -> Result<(u8, Vec<u8>)> {
    if record.len() < REC_HDR {
        return Err(AqError::Malformed("record sarlavhasi qisqa"));
    }
    let rtype = record[0];
    let length = u32::from_be_bytes([record[1], record[2], record[3], record[4]]);
    let end = REC_HDR + length as usize;
    if (length as usize) < TAG_LEN {
        return Err(AqError::Malformed("record uzunligi"));
    }
    // Record AYNAN bitta bo'lishi shart: ortiqcha bayt — rad (kanonik bo'lmagan record).
    if record.len() != end {
        return Err(AqError::Malformed("record uzunligi sarlavhaga mos emas"));
    }
    let a = aad(rtype, length, 0, profile);
    let nonce = d.nonce();
    let pt = d
        .cipher()
        .decrypt(Nonce::from_slice(&nonce), Payload { msg: &record[REC_HDR..end], aad: &a })
        .map_err(|_| AqError::Aead)?;
    d.seq += 1;
    Ok((rtype, pt))
}

/// Ikki tomonlama sessiya (handshake master'idan).
pub struct Session {
    pub profile: u8,
    pub role: Role,
    c2s: Dir,
    s2c: Dir,
    rekey_n: u64,
}

fn derive_dirs(master: &[u8], profile: u8) -> (Dir, Dir) {
    let prk = hkdf_extract(TRANSPORT_LABEL, master);
    let mut info = TRANSPORT_LABEL.to_vec();
    info.extend_from_slice(b"/ts");
    info.push(profile);
    let ts = hkdf_expand(&prk, &info, 32);
    let k_c2s = hkdf_expand(&ts, b"c2s-key", 32);
    let iv_c2s = hkdf_expand(&ts, b"c2s-iv", 12);
    let k_s2c = hkdf_expand(&ts, b"s2c-key", 32);
    let iv_s2c = hkdf_expand(&ts, b"s2c-iv", 12);
    let mut kc = [0u8; 32];
    kc.copy_from_slice(&k_c2s);
    let mut ks = [0u8; 32];
    ks.copy_from_slice(&k_s2c);
    let mut ic = [0u8; 12];
    ic.copy_from_slice(&iv_c2s);
    let mut is = [0u8; 12];
    is.copy_from_slice(&iv_s2c);
    (Dir::new(kc, ic), Dir::new(ks, is))
}

impl Session {
    /// Python `Session.from_shared_secret(master, profile, role)` bilan bir xil.
    pub fn from_master(master: &[u8], profile: u8, role: Role) -> Self {
        let (c2s, s2c) = derive_dirs(master, profile);
        Self { profile, role, c2s, s2c, rekey_n: 0 }
    }

    fn send_dir(&mut self) -> &mut Dir {
        match self.role {
            Role::Client => &mut self.c2s,
            Role::Server => &mut self.s2c,
        }
    }

    fn recv_dir(&mut self) -> &mut Dir {
        match self.role {
            Role::Client => &mut self.s2c,
            Role::Server => &mut self.c2s,
        }
    }

    pub fn seal(&mut self, plaintext: &[u8]) -> Result<Vec<u8>> {
        let p = self.profile;
        seal_dir(self.send_dir(), p, plaintext, TYPE_APP_DATA)
    }

    pub fn open(&mut self, record: &[u8]) -> Result<(u8, Vec<u8>)> {
        let p = self.profile;
        open_dir(self.recv_dir(), p, record)
    }

    /// Ikkala yo'nalishni rekey qiladi (ikkala tomon bir vaqtda chaqirishi shart — AQ-L16).
    pub fn rekey(&mut self) {
        self.rekey_n += 1;
        let n = self.rekey_n;
        self.c2s.rekey(n);
        self.s2c.rekey(n);
    }

    /// Yuborish va qabul qilish yarim-sessiyalariga ajratadi (sidecar pump'lari uchun).
    pub fn split(self) -> (Sender, Receiver) {
        let (send, recv) = match self.role {
            Role::Client => (self.c2s, self.s2c),
            Role::Server => (self.s2c, self.c2s),
        };
        (
            Sender { profile: self.profile, dir: send },
            Receiver { profile: self.profile, dir: recv },
        )
    }
}

/// Faqat yuborish tomoni.
pub struct Sender {
    profile: u8,
    dir: Dir,
}

impl Sender {
    pub fn seal(&mut self, plaintext: &[u8]) -> Result<Vec<u8>> {
        seal_dir(&mut self.dir, self.profile, plaintext, TYPE_APP_DATA)
    }
}

/// Faqat qabul qilish tomoni.
pub struct Receiver {
    profile: u8,
    dir: Dir,
}

impl Receiver {
    pub fn open(&mut self, record: &[u8]) -> Result<(u8, Vec<u8>)> {
        open_dir(&mut self.dir, self.profile, record)
    }
}

/// Record'ning to'liq uzunligini oqimdan o'qish uchun (sarlavhadan).
pub fn record_len(header: &[u8; REC_HDR]) -> usize {
    REC_HDR + u32::from_be_bytes([header[1], header[2], header[3], header[4]]) as usize
}
