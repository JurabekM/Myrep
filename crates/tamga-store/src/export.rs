//! Auditor uchun dalil to'plami (ZIP).
//!
//! ```text
//! MANIFEST.json            tarkib, tekshiruv natijasi va har bir faylning SHA-256 i
//! README-AUDITOR.md        qanday tekshirish (o'zbekcha + inglizcha)
//! report.html              inson o'qishi uchun xulosa (sessiyalar, bloklangan va inson qarorlari)
//! evidence/log.jsonl       jurnal (to'liq — zanjir genesis'dan tekshiriladi)
//! evidence/checkpoints.jsonl
//! evidence/public-key.json
//! payloads/manifest.json   (ixtiyoriy) payload + tuz: auditor majburiyatni o'zi tekshiradi
//! payloads/<seq>-<maydon>.bin
//! verify/tamga_verify/*.py mustaqil verifikator (faqat Python standart kutubxonasi)
//! ```

use std::collections::BTreeMap;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use serde_json::{Value, json};
use tamga_core::checkpoint::verify_all;
use tamga_core::digest::{Digest, to_hex};
use tamga_core::keys::PublicKeys;
use zip::write::SimpleFileOptions;

use crate::home::default_log_id;
use crate::vault::Vault;
use crate::{Home, Result, StoreError, io_err, now_ts};

macro_rules! py {
    ($name:literal) => {
        (
            concat!("verify/tamga_verify/", $name),
            include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../verify-py/tamga_verify/",
                $name
            )),
        )
    };
}

/// Dalil to'plamiga qo'shiladigan mustaqil verifikator.
const VERIFIER: [(&str, &str); 9] = [
    py!("__init__.py"),
    py!("__main__.py"),
    py!("cli.py"),
    py!("jcs.py"),
    py!("merkle.py"),
    py!("ed25519.py"),
    py!("mldsa65.py"),
    py!("verify.py"),
    (
        "verify/README.md",
        "Mustaqil verifikator: `python -m tamga_verify ...` (shu papkadan). Faqat standart kutubxona.\n",
    ),
];

#[derive(Debug, Clone, Default)]
pub struct ExportOptions {
    /// Payload'lari qo'shiladigan sessiyalar (bo'sh — hammasi). Jurnal har doim to'liq.
    pub sessions: Vec<String>,
    pub include_payloads: bool,
    pub out: PathBuf,
}

#[derive(Debug, Clone)]
pub struct ExportResult {
    pub path: PathBuf,
    pub records: usize,
    pub checkpoints: usize,
    pub payloads: usize,
    pub shredded: usize,
    pub verified: bool,
    pub sha256: String,
}

fn read_or_empty(p: &Path) -> Result<String> {
    match std::fs::read_to_string(p) {
        Ok(t) => Ok(t),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(e) => Err(io_err(p)(e)),
    }
}

/// Standart nom: `<TAMGA_HOME>/exports/tamga-evidence-<vaqt>.zip`.
pub fn default_path(home: &Home) -> PathBuf {
    let ts = now_ts().replace([':', '.'], "-");
    home.root()
        .join("exports")
        .join(format!("tamga-evidence-{ts}.zip"))
}

pub fn export(home: &Home, vault: Option<&Vault>, opts: &ExportOptions) -> Result<ExportResult> {
    let log_id = default_log_id();
    let log = read_or_empty(&home.log_path(&log_id))?;
    let cps = read_or_empty(&home.checkpoint_path(&log_id))?;
    let key_text = read_or_empty(&home.public_key())?;
    let pk = serde_json::from_str::<Value>(&key_text)
        .map_err(|e| StoreError::Vault(format!("public-key.json: {e}")))
        .and_then(|v| PublicKeys::from_json(&v).map_err(|e| StoreError::Vault(e.to_string())))?;

    // Buzilgan jurnal ham eksport qilinadi — auditorga aynan shu dalil kerak; natija manifestda.
    let verification = match verify_all(&log, &cps, &pk) {
        Ok(r) => json!({"ok": true, "records": r.log.len(), "checkpoints": r.checkpoints.len(),
                        "sealed": r.checkpoints.iter().map(|c| c.size).max().unwrap_or(0)}),
        Err(e) => {
            json!({"ok": false, "code": e.code.as_str(), "index": e.index, "detail": e.detail})
        }
    };
    let records: Vec<Value> = log
        .lines()
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect();
    let selected = |s: &str| opts.sessions.is_empty() || opts.sessions.iter().any(|x| x == s);

    let mut files: BTreeMap<String, Vec<u8>> = BTreeMap::new();
    files.insert("evidence/log.jsonl".into(), log.clone().into_bytes());
    files.insert(
        "evidence/checkpoints.jsonl".into(),
        cps.clone().into_bytes(),
    );
    files.insert(
        "evidence/public-key.json".into(),
        key_text.clone().into_bytes(),
    );
    for (name, text) in VERIFIER {
        files.insert(name.into(), text.as_bytes().to_vec());
    }

    let (mut payload_items, mut shredded) = (Vec::new(), Vec::new());
    if opts.include_payloads
        && let Some(v) = vault
    {
        for r in records
            .iter()
            .filter(|r| selected(r["session"].as_str().unwrap_or_default()))
        {
            let session = r["session"].as_str().unwrap_or_default();
            let seq = r["seq"].as_u64().unwrap_or(0);
            for (field, reference) in [("input", &r["tool"]["input"]), ("result", &r["result"])] {
                if reference.is_null() {
                    continue;
                }
                match v.get_with_salt(session, reference)? {
                    Some((salt, data)) => {
                        let file = format!("{seq}-{field}.bin");
                        payload_items.push(json!({"seq": seq, "field": field, "file": file, "salt": to_hex(&salt),
                                                  "digest": reference["digest"], "size": data.len(), "session": session}));
                        files.insert(format!("payloads/{file}"), data);
                    }
                    None => shredded.push(json!({"seq": seq, "field": field, "session": session})),
                }
            }
        }
        let manifest = json!({"description": "payload + tuz: H(\"TAMGA-PAYLOAD-v1\" 0x00 || tuz || payload) jurnaldagi digest bilan teng bo'lishi shart (spec §5)",
                              "payloads": payload_items, "shredded": shredded});
        files.insert(
            "payloads/manifest.json".into(),
            serde_json::to_vec_pretty(&manifest).expect("json"),
        );
    }

    files.insert(
        "report.html".into(),
        report_html(&log_id, pk.key_id().as_str(), &verification, &records, &cps).into_bytes(),
    );
    files.insert(
        "README-AUDITOR.md".into(),
        auditor_readme(opts.include_payloads).into_bytes(),
    );

    let manifest = json!({
        "format": "tamga-evidence/1",
        "created": now_ts(),
        "tool": format!("tamga {}", env!("CARGO_PKG_VERSION")),
        "log": log_id,
        "key": pk.key_id(),
        "verification": verification,
        "sessions_selected": opts.sessions,
        "payloads": payload_items.len(),
        "shredded": shredded.len(),
        "files": files.iter().map(|(n, b)| (n.clone(), json!(Digest::of(&[b]).to_string()))).collect::<serde_json::Map<_, _>>(),
    });
    files.insert(
        "MANIFEST.json".into(),
        serde_json::to_vec_pretty(&manifest).expect("json"),
    );

    if let Some(dir) = opts.out.parent() {
        std::fs::create_dir_all(dir).map_err(io_err(dir))?;
    }
    let f = std::fs::File::create(&opts.out).map_err(io_err(&opts.out))?;
    let mut zip = zip::ZipWriter::new(f);
    let options = SimpleFileOptions::default().compression_method(zip::CompressionMethod::Deflated);
    for (name, bytes) in &files {
        zip.start_file(name.as_str(), options)
            .map_err(|e| StoreError::Vault(format!("zip: {e}")))?;
        zip.write_all(bytes).map_err(io_err(&opts.out))?;
    }
    zip.finish()
        .map_err(|e| StoreError::Vault(format!("zip: {e}")))?;
    let zip_bytes = std::fs::read(&opts.out).map_err(io_err(&opts.out))?;

    Ok(ExportResult {
        path: opts.out.clone(),
        records: records.len(),
        checkpoints: cps.lines().count(),
        payloads: payload_items.len(),
        shredded: shredded.len(),
        verified: manifest["verification"]["ok"] == true,
        sha256: Digest::of(&[&zip_bytes]).to_string(),
    })
}

fn esc(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn report_html(
    log_id: &str,
    key: &str,
    verification: &Value,
    records: &[Value],
    cps: &str,
) -> String {
    let count = |f: &dyn Fn(&Value) -> bool| records.iter().filter(|r| f(r)).count();
    let tools = count(&|r| r["event"] == "tool.pre");
    let deny = count(&|r| r["event"] == "tool.pre" && r["decision"]["verdict"] == "deny");
    let ask = count(&|r| r["event"] == "tool.pre" && r["decision"]["verdict"] == "ask");
    let human = count(&|r| r["event"] == "decision.human");
    let mut sessions: BTreeMap<String, (String, usize, usize)> = BTreeMap::new();
    for r in records {
        let s = sessions
            .entry(r["session"].as_str().unwrap_or_default().into())
            .or_insert((r["ts"].as_str().unwrap_or_default().into(), 0, 0));
        if r["event"] == "tool.pre" {
            s.1 += 1;
            if r["decision"]["verdict"] == "deny" {
                s.2 += 1;
            }
        }
    }
    let status = if verification["ok"] == true {
        format!(
            "<p class=ok>✔ Jurnal butun: {} yozuv, {} checkpoint (Ed25519 + ML-DSA-65), muhrlangan: {}.</p>",
            verification["records"], verification["checkpoints"], verification["sealed"]
        )
    } else {
        format!(
            "<p class=bad>✘ Buzilish: {} — indeks {}: {}</p>",
            esc(verification["code"].as_str().unwrap_or("")),
            verification["index"],
            esc(verification["detail"].as_str().unwrap_or(""))
        )
    };
    let decisions: String = records
        .iter()
        .filter(|r| (r["event"] == "tool.pre" && r["decision"]["verdict"] != "allow") || r["event"] == "decision.human")
        .map(|r| {
            format!(
                "<tr><td>#{}</td><td>{}</td><td>{}</td><td>{}</td><td>{} / {}</td><td>{}</td><td>{}</td></tr>",
                r["seq"],
                esc(r["ts"].as_str().unwrap_or("")),
                esc(r["event"].as_str().unwrap_or("")),
                esc(r["tool"]["name"].as_str().unwrap_or(if r["event"] == "decision.human" { "↳ inson" } else { "" })),
                esc(r["decision"]["verdict"].as_str().unwrap_or("")),
                esc(r["decision"]["by"].as_str().unwrap_or("")),
                esc(r["decision"]["policy"].as_str().unwrap_or("")),
                esc(r["decision"]["reason"].as_str().unwrap_or("")),
            )
        })
        .collect();
    let session_rows: String = sessions
        .iter()
        .map(|(s, (ts, t, d))| {
            format!(
                "<tr><td><code>{}</code></td><td>{}</td><td>{t}</td><td>{d}</td></tr>",
                esc(s),
                esc(ts)
            )
        })
        .collect();
    let cp_rows: String = cps
        .lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .map(|c| {
            format!(
                "<tr><td>{}</td><td>{}</td><td><code>{}</code></td></tr>",
                c["size"],
                esc(c["ts"].as_str().unwrap_or("")),
                esc(c["root"].as_str().unwrap_or(""))
            )
        })
        .collect();
    format!(
        r#"<!doctype html><html lang="uz"><head><meta charset="utf-8"><title>TAMGA dalil to'plami — {log}</title>
<style>body{{font-family:Segoe UI,system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#1a1a1a}}
h1{{font-size:22px}}h2{{font-size:17px;margin-top:28px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
td,th{{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}}th{{color:#555}}code{{font-size:12px}}
.ok{{background:#e8f6ec;color:#1b6b33;padding:12px 16px;border-radius:8px}}.bad{{background:#fdecee;color:#a1182b;padding:12px 16px;border-radius:8px}}
.kpi{{display:flex;gap:24px}}.kpi div{{border:1px solid #ddd;border-radius:8px;padding:10px 16px}}.kpi b{{font-size:20px;display:block}}</style></head><body>
<h1>TAMGA dalil to'plami</h1>
<p>Jurnal <code>{log}</code> · kalit <code>{key}</code> · yaratilgan {created}</p>
{status}
<div class=kpi><div><b>{n}</b>yozuv</div><div><b>{tools}</b>tool so'rovi</div><div><b>{deny}</b>bloklangan</div><div><b>{ask}</b>ask</div><div><b>{human}</b>inson qarori</div></div>
<h2>Bloklangan, so'ralgan va inson qarorlari</h2><table><tr><th>#</th><th>Vaqt</th><th>Hodisa</th><th>Tool</th><th>Qaror</th><th>Siyosat</th><th>Sabab</th></tr>{decisions}</table>
<h2>Sessiyalar</h2><table><tr><th>Sessiya</th><th>Boshlangan</th><th>Tool</th><th>Bloklangan</th></tr>{session_rows}</table>
<h2>Checkpoint'lar</h2><table><tr><th>O'lcham</th><th>Vaqt</th><th>Merkle ildizi</th></tr>{cp_rows}</table>
<h2>Mustaqil tekshirish</h2><p>Bu xulosa faqat qulaylik uchun. Dalil — <code>evidence/</code> fayllari; ularni <code>README-AUDITOR.md</code> dagi buyruq bilan
TAMGA dasturiga ishonmasdan tekshiring.</p></body></html>"#,
        log = esc(log_id),
        key = esc(key),
        created = esc(&now_ts()),
        n = records.len(),
    )
}

fn auditor_readme(payloads: bool) -> String {
    let payload_cmd = if payloads {
        " --payloads ../payloads"
    } else {
        ""
    };
    format!(
        r#"# TAMGA dalil to'plami / TAMGA evidence bundle

## O'zbekcha

Bu to'plam AI agent harakatlari jurnalini (TAMGA Record 0.1) va uni **TAMGA dasturiga ishonmasdan**
tekshirish vositasini o'z ichiga oladi.

1. Ochiq kalitni operatordan alohida kanal orqali oling va `evidence/public-key.json` dagi `key` bilan
   solishtiring (kalit jurnal bilan birga kelgani uchun unga ko'r-ko'rona ishonmang — spec §10).
2. Python 3.10+ bilan (hech narsa o'rnatish shart emas):

   ```
   cd verify
   python -m tamga_verify ../evidence/log.jsonl --checkpoints ../evidence/checkpoints.jsonl --key ../evidence/public-key.json{payload_cmd}
   ```

3. `OK` — har bir yozuv o'zgartirilmagan, olib tashlanmagan va tartibi buzilmagan; checkpoint'lar Ed25519 va
   ML-DSA-65 bilan (ikkalasi ham) imzolangan. `BUZILISH: <kod> — indeks <n>` — birinchi buzilgan joy.
4. `MANIFEST.json` dagi `files` — to'plamdagi har bir faylning SHA-256 i.

Spetsifikatsiya: TAMGA Record 0.1 (`spec/TAMGA-RECORD-0.1.md`). Verifikator Ed25519 (RFC 8032) va ML-DSA-65
(FIPS 204) ni faqat Python standart kutubxonasi bilan noldan tekshiradi.

## English

This bundle contains an AI-agent action log (TAMGA Record 0.1) and an independent verifier that checks it
**without trusting TAMGA**. Obtain the public key out of band, compare its `key` id, then run the command above
(Python 3.10+, standard library only). `OK` means no record was altered, removed or reordered and every
checkpoint carries valid Ed25519 **and** ML-DSA-65 signatures.
"#
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::logfile::LogFile;
    use serde_json::Map;
    use tamga_core::keys::SigningKeys;

    #[test]
    fn bundle_contains_evidence_verifier_and_payloads() {
        let dir = std::env::temp_dir().join(format!("tamga-export-{}", std::process::id()));
        std::fs::remove_dir_all(&dir).ok();
        let home = Home::at(&dir);
        home.ensure().unwrap();
        let keys = SigningKeys::from_seeds(&[1; 32], &[2; 32]);
        crate::keystore::export_public(&keys.public(), &home).unwrap();
        let vault = Vault::new(home.vault(), [5; 32]).unwrap();
        let log_id = default_log_id();
        let (mut lf, _) = LogFile::open(
            &home.log_path(&log_id),
            &home.checkpoint_path(&log_id),
            &log_id,
            None,
        )
        .unwrap();
        let input = vault.put("s1", b"cat .env").unwrap();
        let mut body = Map::new();
        body.insert("tool".into(), json!({"name": "Bash", "input": input}));
        body.insert(
            "decision".into(),
            json!({"verdict": "deny", "by": "policy", "policy": "no-secret-exfil"}),
        );
        lf.append(&now_ts(), "s1", "tool.pre", body).unwrap();
        lf.checkpoint(&keys).unwrap();

        let out = dir.join("out/e.zip");
        let r = export(
            &home,
            Some(&vault),
            &ExportOptions {
                sessions: vec![],
                include_payloads: true,
                out: out.clone(),
            },
        )
        .unwrap();
        assert!(r.verified);
        assert_eq!(
            (r.records, r.checkpoints, r.payloads, r.shredded),
            (1, 1, 1, 0)
        );

        let mut z = zip::ZipArchive::new(std::fs::File::open(&out).unwrap()).unwrap();
        let names: Vec<String> = z.file_names().map(|n| n.unwrap().into_owned()).collect();
        for must in [
            "MANIFEST.json",
            "report.html",
            "evidence/log.jsonl",
            "verify/tamga_verify/mldsa65.py",
            "payloads/0-input.bin",
        ] {
            assert!(names.iter().any(|n| n == must), "{must} yo'q: {names:?}");
        }
        let mut payload = String::new();
        std::io::Read::read_to_string(
            &mut z.by_name("payloads/0-input.bin").unwrap(),
            &mut payload,
        )
        .unwrap();
        assert_eq!(payload, "cat .env");
        std::fs::remove_dir_all(dir).ok();
    }
}
