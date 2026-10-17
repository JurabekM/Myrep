//! Payload vault: har sessiyaga alohida kalit, XChaCha20-Poly1305 bilan shifrlangan payload'lar.
//!
//! Jurnalga faqat tuzlangan digest tushadi (spec §5). Vault'da `salt || payload` shifrlangan holda
//! turadi. `shred(session)` sessiya kalitini o'chiradi — payload'lar qaytarib bo'lmaydi, jurnal esa
//! tekshirilaveradi.

use std::fs::OpenOptions;
use std::io::Write as _;
use std::path::PathBuf;

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use serde_json::{Value, json};
use tamga_core::digest::{Digest, to_hex};
use tamga_core::{b64, payload};

use crate::{Result, StoreError, io_err, random};

pub struct Vault {
    dir: PathBuf,
    master: [u8; 32],
}

impl Vault {
    pub fn new(dir: PathBuf, master: [u8; 32]) -> Result<Self> {
        std::fs::create_dir_all(&dir).map_err(io_err(&dir))?;
        Ok(Self { dir, master })
    }

    /// Sessiya identifikatoridan xavfsiz fayl nomi.
    fn stem(session: &str) -> String {
        to_hex(&Digest::of(&[b"tamga-vault-session\0", session.as_bytes()]).0[..16])
    }

    fn key_path(&self, session: &str) -> PathBuf {
        self.dir.join(format!("{}.key", Self::stem(session)))
    }

    fn data_path(&self, session: &str) -> PathBuf {
        self.dir.join(format!("{}.bin", Self::stem(session)))
    }

    fn seal(key: &[u8; 32], aad: &[u8], plain: &[u8]) -> (Vec<u8>, Vec<u8>) {
        let nonce: [u8; 24] = random();
        let ct = XChaCha20Poly1305::new(key.into())
            .encrypt(&XNonce::from(nonce), Payload { msg: plain, aad })
            .expect("shifrlash");
        (nonce.to_vec(), ct)
    }

    fn open(key: &[u8; 32], aad: &[u8], nonce: &[u8], ct: &[u8]) -> Option<Vec<u8>> {
        let nonce = XNonce::try_from(nonce).ok()?;
        XChaCha20Poly1305::new(key.into())
            .decrypt(&nonce, Payload { msg: ct, aad })
            .ok()
    }

    /// Sessiya kaliti: yo'q bo'lsa yaratiladi. Shred qilingan sessiya uchun `None`.
    fn session_key(&self, session: &str, create: bool) -> Result<Option<[u8; 32]>> {
        let p = self.key_path(session);
        let aad = format!("tamga-vault-key:{session}");
        match std::fs::read_to_string(&p) {
            Ok(text) => {
                let v: Value =
                    serde_json::from_str(&text).map_err(|e| StoreError::Vault(e.to_string()))?;
                if v.get("shredded").and_then(Value::as_bool) == Some(true) {
                    return Ok(None);
                }
                let get = |k: &str| v.get(k).and_then(Value::as_str).and_then(b64::decode);
                let (Some(n), Some(c)) = (get("nonce"), get("ct")) else {
                    return Err(StoreError::Vault("kalit fayli buzilgan".into()));
                };
                let k = Self::open(&self.master, aad.as_bytes(), &n, &c)
                    .ok_or_else(|| StoreError::Vault("sessiya kaliti ochilmadi".into()))?;
                Ok(Some(
                    k.try_into()
                        .map_err(|_| StoreError::Vault("kalit uzunligi".into()))?,
                ))
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound && create => {
                let k: [u8; 32] = random();
                let (n, c) = Self::seal(&self.master, aad.as_bytes(), &k);
                let text = json!({"nonce": b64::encode(&n), "ct": b64::encode(&c)}).to_string();
                std::fs::write(&p, text).map_err(io_err(&p))?;
                Ok(Some(k))
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(io_err(&p)(e)),
        }
    }

    /// Payload'ni shifrlab saqlaydi va jurnal uchun payload-ref qaytaradi.
    pub fn put(&self, session: &str, data: &[u8]) -> Result<Value> {
        let key = self.session_key(session, true)?.ok_or_else(|| {
            StoreError::Vault("sessiya unutilgan (shred), yangi payload qabul qilinmaydi".into())
        })?;
        let salt: [u8; payload::SALT_LEN] = random();
        let reference = payload::reference(&salt, data, Some("v1"));
        let digest = reference["digest"].as_str().expect("digest").to_owned();
        let plain = [&salt[..], data].concat();
        let (n, c) = Self::seal(&key, digest.as_bytes(), &plain);
        let line = json!({"digest": digest, "nonce": b64::encode(&n), "ct": b64::encode(&c)})
            .to_string()
            + "\n";
        let p = self.data_path(session);
        let mut f = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&p)
            .map_err(io_err(&p))?;
        f.write_all(line.as_bytes()).map_err(io_err(&p))?;
        Ok(reference)
    }

    /// Payload'ni ochadi va jurnaldagi majburiyatga mosligini tekshiradi.
    /// `None` — topilmadi yoki sessiya unutilgan.
    pub fn get(&self, session: &str, reference: &Value) -> Result<Option<Vec<u8>>> {
        let Some(key) = self.session_key(session, false)? else {
            return Ok(None);
        };
        let Some(digest) = reference.get("digest").and_then(Value::as_str) else {
            return Ok(None);
        };
        let p = self.data_path(session);
        let text = match std::fs::read_to_string(&p) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(io_err(&p)(e)),
        };
        for line in text.lines() {
            let Ok(v) = serde_json::from_str::<Value>(line) else {
                continue;
            };
            if v.get("digest").and_then(Value::as_str) != Some(digest) {
                continue;
            }
            let get = |k: &str| v.get(k).and_then(Value::as_str).and_then(b64::decode);
            let plain = match (get("nonce"), get("ct")) {
                (Some(n), Some(c)) => Self::open(&key, digest.as_bytes(), &n, &c),
                _ => None,
            }
            .ok_or_else(|| StoreError::Vault("payload ochilmadi".into()))?;
            if plain.len() < payload::SALT_LEN {
                return Err(StoreError::Vault("payload qisqa".into()));
            }
            let salt: [u8; payload::SALT_LEN] = plain[..payload::SALT_LEN].try_into().expect("tuz");
            let data = plain[payload::SALT_LEN..].to_vec();
            if !payload::opens(reference, &salt, &data) {
                return Err(StoreError::Vault(
                    "payload jurnal majburiyatiga mos emas".into(),
                ));
            }
            return Ok(Some(data));
        }
        Ok(None)
    }

    /// Sessiyani unutish: kalit o'rniga `shredded` belgisi yoziladi, shifrlangan ma'lumot ochilmaydi.
    pub fn shred(&self, session: &str) -> Result<()> {
        let p = self.key_path(session);
        std::fs::write(&p, json!({"shredded": true}).to_string()).map_err(io_err(&p))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn put_get_shred() {
        let d = std::env::temp_dir().join(format!("tamga-vault-{}", std::process::id()));
        std::fs::remove_dir_all(&d).ok();
        let v = Vault::new(d.clone(), [9; 32]).unwrap();
        let r = v.put("s1", b"cat .env").unwrap();
        let r2 = v.put("s1", b"ls").unwrap();
        assert_eq!(v.get("s1", &r).unwrap().as_deref(), Some(&b"cat .env"[..]));
        assert_eq!(v.get("s1", &r2).unwrap().as_deref(), Some(&b"ls"[..]));
        assert_eq!(v.get("s2", &r).unwrap(), None, "boshqa sessiya");

        // Noto'g'ri master kalit bilan ochilmaydi.
        let wrong = Vault::new(d.clone(), [8; 32]).unwrap();
        assert!(wrong.get("s1", &r).is_err());

        v.shred("s1").unwrap();
        assert_eq!(v.get("s1", &r).unwrap(), None, "unutilgan");
        assert!(v.put("s1", b"x").is_err(), "unutilgan sessiyaga yozilmaydi");
        // Diskda ochiq matn yo'q.
        let raw = std::fs::read_dir(&d)
            .unwrap()
            .flat_map(|e| std::fs::read(e.unwrap().path()).unwrap())
            .collect::<Vec<u8>>();
        assert!(!raw.windows(8).any(|w| w == b"cat .env"));
        std::fs::remove_dir_all(d).ok();
    }
}
