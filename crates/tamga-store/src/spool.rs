//! Spool: daemon'ga ulanib bo'lmaganda hook hodisani shu yerga yozadi; daemon keyin jurnalga oladi.
//!
//! Fayl nomi `<unix_ms>-<pid>-<tasodifiy>.json` — leksik tartib vaqt tartibiga mos.

use std::path::{Path, PathBuf};

use serde_json::{Value, json};
use tamga_core::digest::to_hex;

use crate::{Result, io_err, now_ts, random};

/// Hodisani spool'ga yozadi. `decision` — hook o'zi qabul qilgan qaror (strict/dev rejimi).
pub fn write(dir: &Path, agent: &str, input: &Value, decision: &Value) -> Result<PathBuf> {
    std::fs::create_dir_all(dir).map_err(io_err(dir))?;
    let ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    let tag: [u8; 4] = random();
    let name = format!("{ms:015}-{}-{}.json", std::process::id(), to_hex(&tag));
    let tmp = dir.join(format!("{name}.tmp"));
    let path = dir.join(name);
    let body =
        json!({"ts": now_ts(), "agent": agent, "input": input, "decision": decision}).to_string();
    // Avval vaqtinchalik fayl, keyin rename — daemon yarim yozilgan faylni o'qimaydi.
    std::fs::write(&tmp, body).map_err(io_err(&tmp))?;
    std::fs::rename(&tmp, &path).map_err(io_err(&path))?;
    Ok(path)
}

/// Spool'dagi tayyor fayllar, vaqt tartibida.
pub fn pending(dir: &Path) -> Vec<PathBuf> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "json"))
        .collect();
    files.sort();
    files
}
