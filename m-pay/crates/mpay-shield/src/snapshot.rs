//! Belgilar omborining snapshot'i (ADR-0026): Shield roli holatini davriy saqlaydi, zaxira instansiya
//! yetakchilikni olganda tiklaydi.
//!
//! Format (v1): `MPSHSNP1` ‖ versiya (u32) ‖ tana ‖ oldingi baytlarning SHA-256. Hamma sonlar
//! little-endian; xaritalar kalit bo'yicha saralangan — bir xil holat bir xil baytlarni beradi.
//! O'qish qat'iy: har uzunlik qolgan baytlar bilan cheklangan (katta ajratish yo'q), indekslar va
//! union-find daraxti tekshiriladi, oxirida ortiqcha bayt — xato.
//!
//! Tarkibida PAN yo'q: kartalar — `PanFingerprint` (kalitsiz qaytarib bo'lmaydigan HMAC), qurilmalar —
//! `DeviceId`, savdo nuqtalari — FNV xeshi.

use sha2::{Digest, Sha256};

const MAGIC: &[u8; 8] = b"MPSHSNP1";
const VERSION: u32 = 1;

/// Snapshot xatosi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SnapshotError {
    /// Tuzilma buzilgan.
    Format(&'static str),
    /// Xesh mos emas.
    Checksum,
    /// Noma'lum versiya.
    Version(u32),
}

impl std::fmt::Display for SnapshotError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Format(m) => write!(f, "snapshot formati: {m}"),
            Self::Checksum => f.write_str("snapshot xeshi mos emas"),
            Self::Version(v) => write!(f, "snapshot versiyasi {v} qo'llab-quvvatlanmaydi"),
        }
    }
}

impl std::error::Error for SnapshotError {}

pub(crate) type Result<T> = std::result::Result<T, SnapshotError>;

/// Yozuvchi.
#[derive(Default)]
pub(crate) struct W(Vec<u8>);

impl W {
    pub(crate) fn u8(&mut self, v: u8) {
        self.0.push(v);
    }
    pub(crate) fn u32(&mut self, v: u32) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    pub(crate) fn u64(&mut self, v: u64) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    pub(crate) fn i64(&mut self, v: i64) {
        self.0.extend_from_slice(&v.to_le_bytes());
    }
    pub(crate) fn f64(&mut self, v: f64) {
        self.u64(v.to_bits());
    }
    pub(crate) fn a32(&mut self, v: &[u8; 32]) {
        self.0.extend_from_slice(v);
    }
    pub(crate) fn len(&mut self, n: usize) {
        self.u64(n as u64);
    }
    pub(crate) fn opt_i64(&mut self, v: Option<i64>) {
        match v {
            Some(x) => {
                self.u8(1);
                self.i64(x);
            }
            None => self.u8(0),
        }
    }
}

/// O'quvchi.
pub(crate) struct R<'a> {
    b: &'a [u8],
    pos: usize,
}

impl<'a> R<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        let end = self
            .pos
            .checked_add(n)
            .filter(|e| *e <= self.b.len())
            .ok_or(SnapshotError::Format("kutilganidan oldin tugadi"))?;
        let s = &self.b[self.pos..end];
        self.pos = end;
        Ok(s)
    }
    pub(crate) fn u8(&mut self) -> Result<u8> {
        Ok(self.take(1)?[0])
    }
    pub(crate) fn u32(&mut self) -> Result<u32> {
        let mut a = [0; 4];
        a.copy_from_slice(self.take(4)?);
        Ok(u32::from_le_bytes(a))
    }
    pub(crate) fn u64(&mut self) -> Result<u64> {
        let mut a = [0; 8];
        a.copy_from_slice(self.take(8)?);
        Ok(u64::from_le_bytes(a))
    }
    pub(crate) fn i64(&mut self) -> Result<i64> {
        Ok(self.u64()? as i64)
    }
    pub(crate) fn f64(&mut self) -> Result<f64> {
        let v = f64::from_bits(self.u64()?);
        if v.is_finite() {
            Ok(v)
        } else {
            Err(SnapshotError::Format("son cheksiz yoki NaN"))
        }
    }
    pub(crate) fn a32(&mut self) -> Result<[u8; 32]> {
        let mut a = [0; 32];
        a.copy_from_slice(self.take(32)?);
        Ok(a)
    }
    /// Elementlar soni; har element kamida `min_size` bayt — qolgan baytlardan oshmasin.
    pub(crate) fn len(&mut self, min_size: usize) -> Result<usize> {
        let n = self.u64()?;
        let rest = (self.b.len() - self.pos) as u64;
        if n.saturating_mul(min_size.max(1) as u64) > rest {
            return Err(SnapshotError::Format("uzunlik qolgan baytlardan katta"));
        }
        Ok(n as usize)
    }
    pub(crate) fn opt_i64(&mut self) -> Result<Option<i64>> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.i64()?)),
            _ => Err(SnapshotError::Format("Option belgisi")),
        }
    }
}

/// Sarlavha va xesh bilan o'raydi.
pub(crate) fn seal(body: impl FnOnce(&mut W)) -> Vec<u8> {
    let mut w = W::default();
    w.0.extend_from_slice(MAGIC);
    w.u32(VERSION);
    body(&mut w);
    let h = Sha256::digest(&w.0);
    w.0.extend_from_slice(&h);
    w.0
}

/// Sarlavha va xeshni tekshiradi, tanani o'qiydi va oxirida ortiqcha bayt yo'qligini tasdiqlaydi.
pub(crate) fn open<T>(data: &[u8], body: impl FnOnce(&mut R<'_>) -> Result<T>) -> Result<T> {
    if data.len() < MAGIC.len() + 4 + 32 {
        return Err(SnapshotError::Format("juda qisqa"));
    }
    let (content, digest) = data.split_at(data.len() - 32);
    if Sha256::digest(content).as_slice() != digest {
        return Err(SnapshotError::Checksum);
    }
    if &content[..8] != MAGIC {
        return Err(SnapshotError::Format("belgi"));
    }
    let mut r = R { b: content, pos: 8 };
    let v = r.u32()?;
    if v != VERSION {
        return Err(SnapshotError::Version(v));
    }
    let out = body(&mut r)?;
    if r.pos != content.len() {
        return Err(SnapshotError::Format("ortiqcha baytlar"));
    }
    Ok(out)
}
