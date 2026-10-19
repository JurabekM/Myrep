//! Studio ma'lumot qatlami: jurnalni o'qish (inkremental), sessiyalar, yaxlitlik, vault.
//!
//! Studio jurnalga hech qachon yozmaydi: o'qish fayldan, boshqaruv (decide, checkpoint) faqat
//! `tamgad` orqali — zanjirda yagona yozuvchi bo'lib qoladi.

use std::collections::BTreeMap;
use std::path::PathBuf;

use serde_json::{Value, json};
use tamga_core::checkpoint::verify_all;
use tamga_core::keys::PublicKeys;
use tamga_store::Home;
use tamga_store::home::default_log_id;

/// Jurnaldan o'qilgan yozuvlar keshi: faqat yangi qo'shilgan qatorlar o'qiladi.
#[derive(Default)]
pub struct Cache {
    offset: u64,
    records: Vec<Value>,
}

impl Cache {
    fn log_path(home: &Home) -> PathBuf {
        home.log_path(&default_log_id())
    }

    /// Fayl oxiridan yangi to'liq qatorlarni o'qiydi. Fayl qisqargan bo'lsa (boshqa jurnal) — boshidan.
    pub fn refresh(&mut self, home: &Home) -> Result<(), String> {
        use std::io::{Read as _, Seek as _, SeekFrom};
        let path = Self::log_path(home);
        let mut f = match std::fs::File::open(&path) {
            Ok(f) => f,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                *self = Self::default();
                return Ok(());
            }
            Err(e) => return Err(format!("{}: {e}", path.display())),
        };
        let len = f.metadata().map_err(|e| e.to_string())?.len();
        if len < self.offset {
            *self = Self::default();
        }
        f.seek(SeekFrom::Start(self.offset))
            .map_err(|e| e.to_string())?;
        let mut buf = Vec::new();
        f.read_to_end(&mut buf).map_err(|e| e.to_string())?;
        let complete = buf.iter().rposition(|b| *b == b'\n').map_or(0, |i| i + 1);
        for line in String::from_utf8_lossy(&buf[..complete]).lines() {
            if let Ok(v) = serde_json::from_str::<Value>(line) {
                self.records.push(v);
            }
        }
        self.offset += complete as u64;
        Ok(())
    }

    pub fn records(&self) -> &[Value] {
        &self.records
    }
}

/// UI uchun ixcham yozuv (payload'lar va xeshlarsiz — faqat ko'rinadigan maydonlar).
pub fn compact(r: &Value) -> Value {
    let d = &r["decision"];
    json!({
        "seq": r["seq"], "ts": r["ts"], "session": r["session"], "event": r["event"],
        "tool": r["tool"]["name"], "verdict": d["verdict"], "by": d["by"], "policy": d["policy"],
        "reason": d["reason"], "ref": r["ref"], "hash": r["hash"],
        "facts": r["ext"]["dev.tamga.facts"], "spooled": r["ext"]["dev.tamga.spooled"],
        "model": r["agent"]["model"], "agent": r["agent"]["kind"], "os": r["ext"]["dev.tamga.os"],
    })
}

/// Sessiyalar bo'yicha yig'indi, eng yangisi birinchi.
pub fn sessions(records: &[Value]) -> Vec<Value> {
    #[derive(Default)]
    struct S {
        first: String,
        last: String,
        agent: String,
        events: u64,
        tools: u64,
        deny: u64,
        ask: u64,
        ended: bool,
        first_seq: u64,
    }
    let mut map: BTreeMap<String, S> = BTreeMap::new();
    for r in records {
        let id = r["session"].as_str().unwrap_or_default().to_owned();
        let s = map.entry(id).or_default();
        let ts = r["ts"].as_str().unwrap_or_default().to_owned();
        if s.events == 0 {
            s.first = ts.clone();
            s.first_seq = r["seq"].as_u64().unwrap_or(0);
        }
        s.last = ts;
        s.events += 1;
        if let Some(a) = r["agent"]["kind"].as_str() {
            s.agent = a.to_owned();
        }
        match r["event"].as_str() {
            Some("tool.pre") => {
                s.tools += 1;
                match r["decision"]["verdict"].as_str() {
                    Some("deny") => s.deny += 1,
                    Some("ask") => s.ask += 1,
                    _ => {}
                }
            }
            Some("session.end") => s.ended = true,
            _ => {}
        }
    }
    let mut out: Vec<(u64, Value)> = map
        .into_iter()
        .map(|(id, s)| {
            (
                s.first_seq,
                json!({"session": id, "first": s.first, "last": s.last, "agent": s.agent, "events": s.events,
                       "tools": s.tools, "deny": s.deny, "ask": s.ask, "ended": s.ended}),
            )
        })
        .collect();
    out.sort_by_key(|(seq, _)| std::cmp::Reverse(*seq));
    out.into_iter().map(|(_, v)| v).collect()
}

/// To'liq yaxlitlik tekshiruvi (spec §8): zanjir + checkpoint'lar + gibrid imzolar.
pub fn verify(home: &Home) -> Value {
    let log_id = default_log_id();
    let read = |p: PathBuf| std::fs::read_to_string(&p).unwrap_or_default();
    let log = read(home.log_path(&log_id));
    let cps = read(home.checkpoint_path(&log_id));
    let key_text = read(home.public_key());
    let pk = match serde_json::from_str::<Value>(&key_text)
        .map_err(|e| e.to_string())
        .and_then(|v| PublicKeys::from_json(&v).map_err(|e| e.to_string()))
    {
        Ok(pk) => pk,
        Err(e) => {
            return json!({"ok": false, "error": {"code": "E_KEY", "index": 0, "detail": format!("ochiq kalit: {e}")}});
        }
    };
    let checkpoint_list = |text: &str| -> Vec<Value> {
        text.lines()
            .filter_map(|l| serde_json::from_str::<Value>(l).ok())
            .map(|c| json!({"size": c["size"], "ts": c["ts"], "root": c["root"]}))
            .collect()
    };
    match verify_all(&log, &cps, &pk) {
        Ok(r) => json!({
            "ok": true, "log": log_id, "records": r.log.len(), "key": pk.key_id(),
            "keys": r.keys, "key_warnings": r.key_warnings,
            "checkpoints": checkpoint_list(&cps), "warnings": r.log.warnings,
            "sealed": r.checkpoints.iter().map(|c| c.size).max().unwrap_or(0),
        }),
        Err(e) => json!({
            "ok": false, "log": log_id, "key": pk.key_id(), "checkpoints": checkpoint_list(&cps),
            "records": log.lines().count(),
            "error": {"code": e.code.as_str(), "index": e.index, "detail": e.detail},
        }),
    }
}

/// Yozuv va uning payload'lari vault'dan — maxfiy qiymatlar yashirilgan holda.
pub fn record_detail(home: &Home, records: &[Value], seq: u64) -> Value {
    let Some(r) = records.iter().find(|r| r["seq"].as_u64() == Some(seq)) else {
        return json!({"ok": false, "error": "yozuv topilmadi"});
    };
    let session = r["session"].as_str().unwrap_or_default();
    // Himoyalangan rejimda payload'lar faqat xizmat ichida ochiladi (kalitlar xizmatga tegishli).
    let vault = if crate::protected() {
        Err(tamga_store::StoreError::Secret(
            "himoyalangan rejim: payload'lar faqat xizmatda".into(),
        ))
    } else {
        tamga_store::secrets::default_store(home)
            .and_then(|s| tamga_store::keystore::vault_master(s.as_ref()))
            .and_then(|m| tamga_store::vault::Vault::new(home.vault(), m))
    };
    let mut payloads = Vec::new();
    for (name, reference) in [("input", &r["tool"]["input"]), ("result", &r["result"])] {
        if reference.is_null() {
            continue;
        }
        let (status, text) = match &vault {
            Ok(v) => match v.get(session, reference) {
                Ok(Some(data)) => {
                    let raw = String::from_utf8_lossy(&data).into_owned();
                    let pretty = serde_json::from_str::<Value>(&raw)
                        .ok()
                        .and_then(|j| serde_json::to_string_pretty(&j).ok())
                        .unwrap_or(raw);
                    ("ok", tamga_redact::redact(&pretty))
                }
                Ok(None) => ("shredded", String::new()),
                Err(e) => ("error", e.to_string()),
            },
            Err(e) => ("error", e.to_string()),
        };
        payloads.push(json!({"name": name, "status": status, "text": text, "digest": reference["digest"], "size": reference["size"]}));
    }
    json!({"ok": true, "record": r, "payloads": payloads})
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sessions_are_aggregated_newest_first() {
        let recs: Vec<Value> = [
            json!({"seq": 0, "ts": "t0", "session": "a", "event": "session.start", "agent": {"kind": "claude-code"}}),
            json!({"seq": 1, "ts": "t1", "session": "a", "event": "tool.pre", "decision": {"verdict": "deny"}}),
            json!({"seq": 2, "ts": "t2", "session": "b", "event": "session.start"}),
            json!({"seq": 3, "ts": "t3", "session": "a", "event": "tool.pre", "decision": {"verdict": "ask"}}),
            json!({"seq": 4, "ts": "t4", "session": "a", "event": "session.end"}),
        ]
        .into();
        let s = sessions(&recs);
        assert_eq!(s[0]["session"], "b");
        assert_eq!(
            (
                s[1]["tools"].as_u64(),
                s[1]["deny"].as_u64(),
                s[1]["ask"].as_u64()
            ),
            (Some(2), Some(1), Some(1))
        );
        assert_eq!(
            (s[1]["ended"].as_bool(), s[1]["last"].as_str()),
            (Some(true), Some("t4"))
        );
    }

    #[test]
    fn cache_reads_only_complete_new_lines() {
        let dir = std::env::temp_dir().join(format!("tamga-studio-cache-{}", std::process::id()));
        std::fs::remove_dir_all(&dir).ok();
        let home = Home::at(&dir);
        home.ensure().unwrap();
        let p = Cache::log_path(&home);
        std::fs::write(&p, "{\"seq\":0}\n{\"seq\":1}\n{\"seq\"").unwrap();
        let mut c = Cache::default();
        c.refresh(&home).unwrap();
        assert_eq!(c.records().len(), 2, "yarim qator o'qilmaydi");
        let mut text = std::fs::read_to_string(&p).unwrap();
        text.push_str(":2}\n");
        std::fs::write(&p, text).unwrap();
        c.refresh(&home).unwrap();
        assert_eq!(c.records().len(), 3);
        std::fs::remove_dir_all(dir).ok();
    }
}
