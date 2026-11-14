//! Kalitlar (identity) ombori: `aqctl identity new` bilan bir xil fayllar —
//! `NAME.key` (maxfiy), `NAME.key.pub` (ochiq), `NAME.meta.json` (muddat). Barmoq izi ham Go bilan bir xil.
//! Shuningdek kalit almashinuvi fayllari: taklif (server → klient) va ruxsat so'rovi (klient → server).

use std::fs;
use std::path::{Path, PathBuf};

use aq_core::identity::to_hex;
use aq_core::Identity;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::model::{parse_pub_hex, Mode};
use crate::timefmt;

/// Go `identity.Fingerprint` bilan bir xil: SHA-256 ning birinchi 8 bayti, 4 guruh hex.
pub fn fingerprint(pk: &[u8]) -> String {
    let h = to_hex(&Sha256::digest(pk)[..8]);
    format!("{}-{}-{}-{}", &h[0..4], &h[4..8], &h[8..12], &h[12..16])
}

/// Go `identity.Meta` bilan bir xil JSON.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct Meta {
    pub name: String,
    pub fingerprint: String,
    pub created: String,
    pub not_after: String,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum KeyState {
    Ok,
    RotateSoon,
    Expired,
    /// Muddat fayli yo'q (masalan, `aq-sidecar keygen` bilan yaratilgan).
    NoExpiry,
}

/// Rotatsiyadan necha kun oldin ogohlantirish (aqctl `--warn-days` standarti bilan bir xil).
pub const WARN_DAYS: i64 = 14;

#[derive(Clone, Debug)]
pub struct KeyInfo {
    pub name: String,
    pub pk: Vec<u8>,
    pub fingerprint: String,
    pub created: Option<i64>,
    pub not_after: Option<i64>,
}

impl KeyInfo {
    pub fn state(&self, now: i64) -> KeyState {
        match self.not_after {
            None => KeyState::NoExpiry,
            Some(na) if now >= na => KeyState::Expired,
            Some(na) if now >= na - WARN_DAYS * 86_400 => KeyState::RotateSoon,
            Some(_) => KeyState::Ok,
        }
    }

    pub fn days_left(&self, now: i64) -> Option<i64> {
        self.not_after.map(|na| (na - now).div_euclid(86_400))
    }

    pub fn pub_hex(&self) -> String {
        to_hex(&self.pk)
    }
}

/// Kalit nomi: harf, raqam, `-`, `_`, `.` (1..40 belgi).
pub fn valid_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 40
        && !name.starts_with('.')
        && name.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.'))
}

fn key_path(dir: &Path, name: &str) -> PathBuf {
    dir.join(format!("{name}.key"))
}

/// Papkadagi barcha kalitlar (nom bo'yicha tartiblangan). Buzilgan fayllar o'tkazib yuboriladi.
pub fn list(dir: &Path) -> Vec<KeyInfo> {
    let mut out = Vec::new();
    let Ok(rd) = fs::read_dir(dir) else {
        return out;
    };
    for e in rd.flatten() {
        let p = e.path();
        if p.extension().and_then(|x| x.to_str()) != Some("key") {
            continue;
        }
        let Some(name) = p.file_stem().and_then(|s| s.to_str()).map(str::to_owned) else {
            continue;
        };
        if let Ok(info) = load_info(dir, &name) {
            out.push(info);
        }
    }
    out.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    out
}

pub fn load_identity(dir: &Path, name: &str) -> Result<Identity, String> {
    Identity::load(&key_path(dir, name)).map_err(|e| format!("«{name}» kaliti o'qilmadi: {e}"))
}

pub fn load_info(dir: &Path, name: &str) -> Result<KeyInfo, String> {
    let id = load_identity(dir, name)?;
    let meta: Option<Meta> =
        fs::read_to_string(dir.join(format!("{name}.meta.json"))).ok().and_then(|t| serde_json::from_str(&t).ok());
    Ok(KeyInfo {
        name: name.to_string(),
        fingerprint: fingerprint(&id.pk),
        created: meta.as_ref().and_then(|m| timefmt::parse_rfc3339(&m.created)),
        not_after: meta.as_ref().and_then(|m| timefmt::parse_rfc3339(&m.not_after)),
        pk: id.pk,
    })
}

/// Yangi kalit: `.key`, `.key.pub`, `.meta.json` (muddat `days` kun).
pub fn create(dir: &Path, name: &str, days: u32) -> Result<KeyInfo, String> {
    create_at(dir, name, days, timefmt::now_unix())
}

pub fn create_at(dir: &Path, name: &str, days: u32, now: i64) -> Result<KeyInfo, String> {
    if !valid_name(name) {
        return Err("Kalit nomi: lotin harflari, raqamlar, «-», «_», «.» (1–40 belgi).".into());
    }
    if key_path(dir, name).exists() {
        return Err(format!("«{name}» nomli kalit allaqachon bor."));
    }
    fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    let id = Identity::generate().map_err(|e| e.to_string())?;
    id.save(&key_path(dir, name)).map_err(|e| format!("kalit yozilmadi: {e}"))?;
    id.save_public(&dir.join(format!("{name}.key.pub"))).map_err(|e| format!("ochiq kalit yozilmadi: {e}"))?;
    let meta = Meta {
        name: name.to_string(),
        fingerprint: fingerprint(&id.pk),
        created: timefmt::rfc3339(now),
        not_after: timefmt::rfc3339(now + days as i64 * 86_400),
    };
    let js = serde_json::to_string_pretty(&meta).map_err(|e| e.to_string())? + "\n";
    fs::write(dir.join(format!("{name}.meta.json")), js).map_err(|e| e.to_string())?;
    load_info(dir, name)
}

/// Kalitni o'chiradi (uchala fayl).
pub fn delete(dir: &Path, name: &str) -> Result<(), String> {
    fs::remove_file(key_path(dir, name)).map_err(|e| format!("o'chirilmadi: {e}"))?;
    let _ = fs::remove_file(dir.join(format!("{name}.key.pub")));
    let _ = fs::remove_file(dir.join(format!("{name}.meta.json")));
    Ok(())
}

/// Rotatsiya uchun yangi nom: `server` → `server-2`, `server-2` → `server-3`.
pub fn next_name(existing: &[String], base: &str) -> String {
    let stem = match base.rsplit_once('-') {
        Some((s, n)) if n.parse::<u32>().is_ok() => s,
        _ => base,
    };
    (2..)
        .map(|i| format!("{stem}-{i}"))
        .find(|n| !existing.iter().any(|e| e == n))
        .unwrap_or_else(|| format!("{stem}-new"))
}

/// Yangi kalit uchun nom: `base` band bo'lmasa o'zi, aks holda `base-2`, `base-3`, …
pub fn suggest_name(existing: &[String], base: &str) -> String {
    if existing.iter().any(|e| e == base) {
        next_name(existing, base)
    } else {
        base.to_string()
    }
}

pub const INVITE_FORMAT: &str = "aetherq-invite/1";
pub const REQUEST_FORMAT: &str = "aetherq-access-request/1";

/// Taklif: server → klient. Klient uni import qilib, server manzili va pinned kalitini oladi.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct Invite {
    pub format: String,
    pub name: String,
    pub address: String,
    pub mode: Mode,
    pub server_pub: String,
    pub fingerprint: String,
    pub require_client_auth: bool,
    pub created: String,
}

/// Ruxsat so'rovi: klient → server. Server uni allowlist'ga qo'shadi.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct AccessRequest {
    pub format: String,
    pub name: String,
    pub client_pub: String,
    pub fingerprint: String,
    pub created: String,
}

pub fn make_invite(name: &str, address: &str, mode: Mode, key: &KeyInfo, require_client_auth: bool) -> Invite {
    Invite {
        format: INVITE_FORMAT.into(),
        name: name.into(),
        address: address.into(),
        mode,
        server_pub: key.pub_hex(),
        fingerprint: key.fingerprint.clone(),
        require_client_auth,
        created: timefmt::rfc3339(timefmt::now_unix()),
    }
}

pub fn make_request(name: &str, key: &KeyInfo) -> AccessRequest {
    AccessRequest {
        format: REQUEST_FORMAT.into(),
        name: name.into(),
        client_pub: key.pub_hex(),
        fingerprint: key.fingerprint.clone(),
        created: timefmt::rfc3339(timefmt::now_unix()),
    }
}

/// Taklifni o'qiydi va tekshiradi (format, kalit uzunligi, barmoq izi mosligi).
pub fn parse_invite(text: &str) -> Result<Invite, String> {
    let inv: Invite = serde_json::from_str(text.trim()).map_err(|_| "Bu taklif fayli emas (JSON o'qilmadi).".to_string())?;
    if inv.format != INVITE_FORMAT {
        return Err(format!("Noma'lum format: {}", inv.format));
    }
    let pk = parse_pub_hex(&inv.server_pub).ok_or("Taklifdagi server kaliti noto'g'ri.")?;
    if fingerprint(&pk) != inv.fingerprint {
        return Err("Taklif buzilgan: barmoq izi kalitga mos emas.".into());
    }
    if crate::model::split_host_port(&inv.address).is_none() {
        return Err("Taklifdagi server manzili noto'g'ri.".into());
    }
    Ok(inv)
}

/// Allowlist uchun klient kaliti: ruxsat so'rovi (JSON), `.pub` fayli yoki hex matn.
/// Qaytaradi: (taklif qilingan nom, ochiq kalit).
pub fn parse_client_key(text: &str, fallback_label: &str) -> Result<(String, Vec<u8>), String> {
    let t = text.trim();
    if t.starts_with('{') {
        let v: serde_json::Value = serde_json::from_str(t).map_err(|_| "Ruxsat so'rovi JSON'i o'qilmadi.".to_string())?;
        match v.get("format").and_then(|f| f.as_str()) {
            Some(INVITE_FORMAT) => {
                return Err("Bu taklif fayli (server → klient) — uni klient tomonda import qiling. Allowlist'ga klientning ruxsat so'rovi (.aqrequest) kerak.".into())
            }
            Some(REQUEST_FORMAT) => {}
            other => return Err(format!("Noma'lum format: {}", other.unwrap_or("yo'q"))),
        }
        let r: AccessRequest = serde_json::from_value(v).map_err(|_| "Ruxsat so'rovi to'liq emas (maydonlar yetishmaydi).".to_string())?;
        let pk = parse_pub_hex(&r.client_pub).ok_or("So'rovdagi klient kaliti noto'g'ri.")?;
        if fingerprint(&pk) != r.fingerprint {
            return Err("Ruxsat so'rovi buzilgan: barmoq izi kalitga mos emas.".into());
        }
        return Ok((r.name, pk));
    }
    // .pub fayli yoki aqctl allowlist qatori: izoh qatorlarini tashlab, birinchi kalitni olamiz.
    let line = t.lines().map(str::trim).find(|l| !l.is_empty() && !l.starts_with('#')).unwrap_or("");
    let pk = parse_pub_hex(line).ok_or("Ochiq kalit topilmadi: ruxsat so'rovi (.aqrequest), .pub fayli yoki 3904 belgili hex kerak.")?;
    Ok((fallback_label.to_string(), pk))
}

/// aqctl `--allow` fayli (standart rejim uchun): har kalit oldidan barmoq izi izohi.
pub fn allowlist_text(keys: &[(String, Vec<u8>)]) -> String {
    let mut s = String::from("# AETHER-Q Studio tomonidan yaratilgan allowlist\n");
    for (label, pk) in keys {
        s.push_str(&format!("# {} {}\n{}\n", fingerprint(pk), label.replace('\n', " "), to_hex(pk)));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("aq-studio-keys-{tag}-{}", crate::model::new_id()));
        fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn fingerprint_matches_go_shape() {
        let fp = fingerprint(b"abc");
        // sha256("abc") = ba7816bf8f01cfea...
        assert_eq!(fp, "ba78-16bf-8f01-cfea");
    }

    #[test]
    fn create_list_load_delete_roundtrip() {
        let d = tmp("crud");
        let now = timefmt::parse_rfc3339("2026-10-17T00:00:00Z").unwrap();
        let k = create_at(&d, "server", 90, now).unwrap();
        assert_eq!(k.days_left(now), Some(90));
        assert_eq!(k.state(now), KeyState::Ok);
        assert_eq!(k.state(now + 80 * 86_400), KeyState::RotateSoon);
        assert_eq!(k.state(now + 90 * 86_400), KeyState::Expired);
        assert!(create_at(&d, "server", 90, now).is_err(), "takroriy nom");
        assert!(create_at(&d, "../x", 90, now).is_err(), "yaroqsiz nom");
        let all = list(&d);
        assert_eq!(all.len(), 1);
        assert_eq!(all[0].pk, k.pk);
        // aqctl bilan bir xil fayl: .pub hex va meta JSON maydonlari.
        let pubtxt = fs::read_to_string(d.join("server.key.pub")).unwrap();
        assert_eq!(pubtxt.trim(), k.pub_hex());
        let meta: Meta = serde_json::from_str(&fs::read_to_string(d.join("server.meta.json")).unwrap()).unwrap();
        assert_eq!(meta.fingerprint, k.fingerprint);
        assert_eq!(meta.not_after, "2027-01-15T00:00:00Z");
        delete(&d, "server").unwrap();
        assert!(list(&d).is_empty());
        let _ = fs::remove_dir_all(&d);
    }

    #[test]
    fn invite_and_request_roundtrip_and_tamper_detection() {
        let d = tmp("inv");
        let srv = create(&d, "srv", 30).unwrap();
        let cli = create(&d, "cli", 30).unwrap();
        let inv = make_invite("Ofis", "10.0.0.5:9443", Mode::AetherQ, &srv, true);
        let txt = serde_json::to_string_pretty(&inv).unwrap();
        assert_eq!(parse_invite(&txt).unwrap(), inv);
        let mut bad = inv.clone();
        bad.fingerprint = "0000-0000-0000-0000".into();
        assert!(parse_invite(&serde_json::to_string(&bad).unwrap()).is_err());

        let req = serde_json::to_string(&make_request("PC-1", &cli)).unwrap();
        let (label, pk) = parse_client_key(&req, "x").unwrap();
        assert_eq!((label.as_str(), pk.as_slice()), ("PC-1", cli.pk.as_slice()));
        // .pub fayli va allowlist qatori ham qabul qilinadi.
        let (l2, pk2) = parse_client_key(&format!("# izoh\n{}\n", cli.pub_hex()), "pc-2").unwrap();
        assert_eq!((l2.as_str(), pk2), ("pc-2", cli.pk.clone()));
        // Taklifni allowlist'ga import qilish — tushunarli xato.
        assert!(parse_client_key(&txt, "x").unwrap_err().contains("taklif"));
        let _ = fs::remove_dir_all(&d);
    }

    #[test]
    fn rotation_names_and_allowlist_file() {
        let ex = vec!["server".to_string(), "server-2".to_string()];
        assert_eq!(next_name(&ex, "server"), "server-3");
        assert_eq!(next_name(&ex, "server-2"), "server-3");
        assert_eq!(next_name(&[], "pc"), "pc-2");
        let txt = allowlist_text(&[("PC-1".into(), vec![1, 2, 3])]);
        assert!(txt.contains("\n010203\n"));
        // aq-core allowlist o'quvchisi uni o'qiy oladimi (izoh qatorlari tashlanadi)?
        let d = tmp("allow");
        let p = d.join("a.txt");
        fs::write(&p, &txt).unwrap();
        assert_eq!(aq_core::identity::load_allowlist(&p).unwrap(), vec![vec![1u8, 2, 3]]);
        let _ = fs::remove_dir_all(&d);
    }
}
