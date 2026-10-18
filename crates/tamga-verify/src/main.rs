//! tamga-verify — TAMGA Record 0.1 jurnalini mustaqil tekshiradi (spec §8).
//!
//! Foydalanish:
//!   tamga-verify <jurnal.jsonl> [--checkpoints <fayl>] [--key <ochiq-kalit.json>]
//!
//! Chiqish kodi: 0 — jurnal butun, 1 — buzilish topildi, 2 — foydalanish yoki o'qish xatosi.

use std::path::Path;
use std::process::ExitCode;

use tamga_core::chain::verify_log;
use tamga_core::checkpoint::verify_all;
use tamga_core::error::{ErrorCode, VerifyError};
use tamga_core::keys::PublicKeys;

const USAGE: &str =
    "foydalanish: tamga-verify <jurnal.jsonl> [--checkpoints <fayl>] [--key <ochiq-kalit.json>]";

struct Args {
    log: String,
    checkpoints: Option<String>,
    key: Option<String>,
}

fn parse_args() -> Result<Args, String> {
    let mut it = std::env::args().skip(1);
    let (mut log, mut checkpoints, mut key) = (None, None, None);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--checkpoints" => checkpoints = Some(it.next().ok_or("--checkpoints qiymatsiz")?),
            "--key" => key = Some(it.next().ok_or("--key qiymatsiz")?),
            "-h" | "--help" => return Err(String::new()),
            s if s.starts_with('-') => return Err(format!("noma'lum bayroq: {s}")),
            s if log.is_none() => log = Some(s.to_owned()),
            s => return Err(format!("ortiqcha argument: {s}")),
        }
    }
    let log = log.ok_or("jurnal fayli ko'rsatilmagan")?;
    if checkpoints.is_some() != key.is_some() {
        return Err(
            "--checkpoints va --key birga beriladi (kalit jurnal papkasidan olinmaydi, spec §10)"
                .into(),
        );
    }
    Ok(Args {
        log,
        checkpoints,
        key,
    })
}

/// Faylni UTF-8 sifatida o'qiydi; buzilgan bayt bo'lsa, u qaysi qatorda ekanini aytadi.
fn read_text(path: &str, code: ErrorCode) -> Result<Result<String, VerifyError>, String> {
    let bytes = std::fs::read(Path::new(path)).map_err(|e| format!("{path}: {e}"))?;
    Ok(String::from_utf8(bytes).map_err(|e| {
        let at = e.utf8_error().valid_up_to();
        let line = e.as_bytes()[..at].iter().filter(|b| **b == b'\n').count() as u64;
        VerifyError::new(code, line, "UTF-8 emas")
    }))
}

fn run(args: &Args) -> Result<Result<String, VerifyError>, String> {
    let log = match read_text(&args.log, ErrorCode::Parse)? {
        Ok(t) => t,
        Err(e) => return Ok(Err(e)),
    };
    let (Some(cp_path), Some(key_path)) = (&args.checkpoints, &args.key) else {
        return Ok(verify_log(&log).map(|s| {
            let mut out = format!(
                "OK: `{}` jurnali butun — {} yozuv, zanjir uzilmagan.\n",
                s.log.as_deref().unwrap_or("-"),
                s.len()
            );
            out += "Eslatma: checkpoint'siz faqat ichki izchillik tekshiriladi; oxirini kesish sezilmaydi.\n";
            for w in &s.warnings {
                out += &format!("ogohlantirish: {w}\n");
            }
            out
        }));
    };
    let key_text = std::fs::read_to_string(key_path).map_err(|e| format!("{key_path}: {e}"))?;
    let key_json = serde_json::from_str(&key_text).map_err(|e| format!("{key_path}: {e}"))?;
    let pk = PublicKeys::from_json(&key_json).map_err(|e| format!("{key_path}: {e}"))?;
    let cps = match read_text(cp_path, ErrorCode::CkptFormat)? {
        Ok(t) => t,
        Err(e) => return Ok(Err(e)),
    };
    // L-2: checkpoint fayli ataylab berilgan, lekin bo'sh (0 baytga qisqartirilgan), jurnal esa bo'sh
    // emas — bu imzo tekshiruvini chetlab o'tishga urinish, OK emas.
    if cps.trim().is_empty() && !log.trim().is_empty() {
        return Ok(Err(VerifyError::new(
            ErrorCode::CkptFormat,
            0,
            "checkpoint fayli bo'sh, jurnal esa bo'sh emas — imzo tekshirib bo'lmaydi (qisqartirilgan?)",
        )));
    }
    Ok(verify_all(&log, &cps, &pk).map(|r| {
        let mut out = format!(
            "OK: `{}` jurnali butun — {} yozuv, {} ta checkpoint (Ed25519 + ML-DSA-65) tasdiqlandi, kalit {}.\n",
            r.log.log.as_deref().unwrap_or("-"),
            r.log.len(),
            r.checkpoints.len(),
            pk.key_id()
        );
        if let Some(last) = r.checkpoints.iter().map(|c| c.size).max()
            && last < r.log.len()
        {
            out += &format!("Eslatma: oxirgi {} yozuv hali checkpoint bilan muhrlanmagan.\n", r.log.len() - last);
        }
        if r.keys.len() > 1 {
            out += &format!("Kalitlar zanjiri (spec §7.5): {}\n", r.keys.join(" → "));
        }
        for w in r.log.warnings.iter().chain(&r.key_warnings) {
            out += &format!("ogohlantirish: {w}\n");
        }
        out
    }))
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(a) => a,
        Err(msg) => {
            if !msg.is_empty() {
                eprintln!("xato: {msg}");
            }
            eprintln!("{USAGE}");
            return ExitCode::from(2);
        }
    };
    match run(&args) {
        Ok(Ok(report)) => {
            print!("{report}");
            ExitCode::SUCCESS
        }
        Ok(Err(e)) => {
            println!("BUZILISH: {} — indeks {}: {}", e.code, e.index, e.detail);
            ExitCode::from(1)
        }
        Err(msg) => {
            eprintln!("xato: {msg}");
            ExitCode::from(2)
        }
    }
}
