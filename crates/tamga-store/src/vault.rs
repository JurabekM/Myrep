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

    /// Kalit AAD'si. 0-avlod — avlodlardan oldingi format bilan mos.
    fn key_aad(session: &str, generation: u64) -> String {
        if generation == 0 {
            format!("tamga-vault-key:{session}")
        } else {
            format!("tamga-vault-key:{session}:{generation}")
        }
    }

    /// Joriy sessiya kaliti va uning avlodi. `create` bo'lsa, kalit yo'q yoki shred qilingan
    /// bo'lganda yangi avlod yaratiladi: shred faqat o'tgan payload'larni unutadi, sessiyaning
    /// keyingi yozuvlari yangi kalit bilan davom etadi.
    fn session_key(&self, session: &str, create: bool) -> Result<Option<(u64, [u8; 32])>> {
        let p = self.key_path(session);
        let next_generation = match std::fs::read_to_string(&p) {
            Ok(text) => {
                let v: Value =
                    serde_json::from_str(&text).map_err(|e| StoreError::Vault(e.to_string()))?;
                let generation = v.get("gen").and_then(Value::as_u64).unwrap_or(0);
                if v.get("shredded").and_then(Value::as_bool) != Some(true) {
                    let get = |k: &str| v.get(k).and_then(Value::as_str).and_then(b64::decode);
                    let (Some(n), Some(c)) = (get("nonce"), get("ct")) else {
                        return Err(StoreError::Vault("kalit fayli buzilgan".into()));
                    };
                    let k = Self::open(
                        &self.master,
                        Self::key_aad(session, generation).as_bytes(),
                        &n,
                        &c,
                    )
                    .ok_or_else(|| StoreError::Vault("sessiya kaliti ochilmadi".into()))?;
                    let k = k
                        .try_into()
                        .map_err(|_| StoreError::Vault("kalit uzunligi".into()))?;
                    return Ok(Some((generation, k)));
                }
                generation + 1
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => 0,
            Err(e) => return Err(io_err(&p)(e)),
        };
        if !create {
            return Ok(None);
        }
        let k: [u8; 32] = random();
        let (n, c) = Self::seal(
            &self.master,
            Self::key_aad(session, next_generation).as_bytes(),
            &k,
        );
        let text = json!({"gen": next_generation, "nonce": b64::encode(&n), "ct": b64::encode(&c)})
            .to_string();
        std::fs::write(&p, text).map_err(io_err(&p))?;
        Ok(Some((next_generation, k)))
    }

    /// Payload'ni shifrlab saqlaydi va jurnal uchun payload-ref qaytaradi.
    pub fn put(&self, session: &str, data: &[u8]) -> Result<Value> {
        let (generation, key) = self
            .session_key(session, true)?
            .ok_or_else(|| StoreError::Vault("sessiya kaliti yaratilmadi".into()))?;
        let salt: [u8; payload::SALT_LEN] = random();
        let reference = payload::reference(&salt, data, Some("v1"));
        let digest = reference["digest"].as_str().expect("digest").to_owned();
        let plain = [&salt[..], data].concat();
        let (n, c) = Self::seal(&key, digest.as_bytes(), &plain);
        let line = json!({"digest": digest, "gen": generation, "nonce": b64::encode(&n), "ct": b64::encode(&c)})
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
        Ok(self
            .get_with_salt(session, reference)?
            .map(|(_, data)| data))
    }

    /// [`Self::get`] + tuz: dalil to'plamida auditor majburiyatni o'zi tekshirishi uchun.
    pub fn get_with_salt(
        &self,
        session: &str,
        reference: &Value,
    ) -> Result<Option<([u8; payload::SALT_LEN], Vec<u8>)>> {
        let Some((generation, key)) = self.session_key(session, false)? else {
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
            if v.get("gen").and_then(Value::as_u64).unwrap_or(0) != generation {
                return Ok(None); // oldingi avlod kaliti shred qilingan — payload unutilgan
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
            return Ok(Some((salt, data)));
        }
        Ok(None)
    }

    /// Sessiyani unutish: kalit o'rniga `shredded` belgisi yoziladi, shifrlangan ma'lumot ochilmaydi.
    pub fn shred(&self, session: &str) -> Result<()> {
        let p = self.key_path(session);
        let generation = std::fs::read_to_string(&p)
            .ok()
            .and_then(|t| serde_json::from_str::<Value>(&t).ok())
            .and_then(|v| v.get("gen").and_then(Value::as_u64))
            .unwrap_or(0);
        std::fs::write(&p, json!({"shredded": true, "gen": generation}).to_string())
            .map_err(io_err(&p))?;
        // Sessiya holati (taint) ham shu kalit bilan shifrlangan — endi ochilmaydi, faylni ham o'chiramiz.
        self.remove_state(session)
    }

    fn state_path(&self, session: &str) -> PathBuf {
        self.dir.join(format!("{}.state", Self::stem(session)))
    }

    /// Sessiyaning daemon holati (masalan taint) — sessiya kaliti bilan shifrlanadi, shuning uchun
    /// `shred` uni ham unutadi. Fayl atomar almashtiriladi (vaqtinchalik fayl + rename).
    pub fn put_state(&self, session: &str, state: &[u8]) -> Result<()> {
        let (_, key) = self
            .session_key(session, true)?
            .ok_or_else(|| StoreError::Vault("sessiya kaliti yaratilmadi".into()))?;
        let aad = format!("tamga-state:{session}");
        let (n, c) = Self::seal(&key, aad.as_bytes(), state);
        let text = json!({"session": session, "nonce": b64::encode(&n), "ct": b64::encode(&c)})
            .to_string();
        let p = self.state_path(session);
        let tmp = p.with_extension("state.tmp");
        std::fs::write(&tmp, text).map_err(io_err(&tmp))?;
        std::fs::rename(&tmp, &p).map_err(io_err(&p))
    }

    pub fn remove_state(&self, session: &str) -> Result<()> {
        let p = self.state_path(session);
        match std::fs::remove_file(&p) {
            Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(io_err(&p)(e)),
            _ => Ok(()),
        }
    }

    /// Barcha saqlangan holatlar: `(sessiya, holat, oxirgi o'zgarish)`. `max_age` dan eski yoki
    /// ochilmaydigan (shred qilingan, buzilgan) holat fayllari o'chiriladi va qaytarilmaydi.
    pub fn load_states(&self, max_age: std::time::Duration) -> Result<Vec<(String, Vec<u8>)>> {
        let mut out = Vec::new();
        let entries = std::fs::read_dir(&self.dir).map_err(io_err(&self.dir))?;
        for e in entries.filter_map(|e| e.ok()) {
            let p = e.path();
            if p.extension().is_none_or(|x| x != "state") {
                continue;
            }
            let stale = e
                .metadata()
                .and_then(|m| m.modified())
                .ok()
                .and_then(|t| t.elapsed().ok())
                .is_some_and(|age| age > max_age);
            let opened = (!stale)
                .then(|| std::fs::read_to_string(&p).ok())
                .flatten()
                .and_then(|t| serde_json::from_str::<Value>(&t).ok())
                .and_then(|v| {
                    let session = v.get("session")?.as_str()?.to_owned();
                    // Fayl nomi sessiya bilan mos bo'lishi shart — boshqa sessiya holatini "ko'chirib" bo'lmaydi.
                    if self.state_path(&session) != p {
                        return None;
                    }
                    let (_, key) = self.session_key(&session, false).ok()??;
                    let get = |k: &str| v.get(k).and_then(Value::as_str).and_then(b64::decode);
                    let plain = Self::open(
                        &key,
                        format!("tamga-state:{session}").as_bytes(),
                        &get("nonce")?,
                        &get("ct")?,
                    )?;
                    Some((session, plain))
                });
            match opened {
                Some(item) => out.push(item),
                None => {
                    let _ = std::fs::remove_file(&p);
                }
            }
        }
        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn session_state_round_trip_expiry_and_shred() {
        let d = std::env::temp_dir().join(format!("tamga-vault-state-{}", std::process::id()));
        std::fs::remove_dir_all(&d).ok();
        let v = Vault::new(d.clone(), [9; 32]).unwrap();
        let day = std::time::Duration::from_secs(86_400);
        v.put_state("s1", br#"{"values":["sk-maxfiy-123456"]}"#)
            .unwrap();
        v.put_state("s2", b"ikkinchi").unwrap();
        let mut states = v.load_states(day).unwrap();
        states.sort();
        assert_eq!(states.len(), 2);
        assert_eq!(states[1], ("s2".to_owned(), b"ikkinchi".to_vec()));
        // Diskda ochiq matn yo'q.
        let raw: Vec<u8> = std::fs::read_dir(&d)
            .unwrap()
            .flat_map(|e| std::fs::read(e.unwrap().path()).unwrap())
            .collect();
        assert!(!raw.windows(9).any(|w| w == b"sk-maxfiy"));
        // Boshqa sessiya fayli ostiga ko'chirilgan holat qabul qilinmaydi va o'chiriladi.
        let s1 = v.state_path("s1");
        std::fs::copy(&s1, v.state_path("s3")).unwrap();
        assert_eq!(v.load_states(day).unwrap().len(), 2);
        assert!(!v.state_path("s3").exists());
        // Shred: holat ham yo'qoladi.
        v.shred("s1").unwrap();
        assert!(!s1.exists());
        assert_eq!(
            v.load_states(day)
                .unwrap()
                .iter()
                .map(|(s, _)| s.as_str())
                .collect::<Vec<_>>(),
            ["s2"]
        );
        // Muddati o'tgan holat o'chiriladi.
        assert!(v.load_states(std::time::Duration::ZERO).unwrap().is_empty());
        assert!(!v.state_path("s2").exists());
        std::fs::remove_dir_all(d).ok();
    }

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
        // Sessiya davom etadi: yangi payload yangi avlod kaliti bilan yoziladi va o'qiladi,
        // eski payload esa unutilganligicha qoladi.
        let after = v.put("s1", b"pwd").unwrap();
        assert_eq!(v.get("s1", &after).unwrap().as_deref(), Some(&b"pwd"[..]));
        assert_eq!(
            v.get("s1", &r).unwrap(),
            None,
            "eski avlod qaytib ochilmaydi"
        );
        v.shred("s1").unwrap();
        assert_eq!(v.get("s1", &after).unwrap(), None, "ikkinchi shred");
        // Diskda ochiq matn yo'q.
        let raw = std::fs::read_dir(&d)
            .unwrap()
            .flat_map(|e| std::fs::read(e.unwrap().path()).unwrap())
            .collect::<Vec<u8>>();
        assert!(!raw.windows(8).any(|w| w == b"cat .env"));
        std::fs::remove_dir_all(d).ok();
    }
}
