//! tamga — TAMGA boshqaruv CLI.
//!
//! ```text
//! tamga init                                  kalitlar va papkalarni tayyorlash
//! tamga status                                daemon holati
//! tamga verify                                o'z jurnalini to'liq tekshirish (zanjir + checkpoint + imzo)
//! tamga checkpoint                            darhol checkpoint
//! tamga install claude-code --project <dir>   loyiha .claude/settings.json ga hook qo'shish
//! tamga install claude-code --user            ~/.claude/settings.json ga hook qo'shish
//! tamga uninstall claude-code (--project <dir> | --user)
//! tamga shred <session>                       sessiya payload'larini unutish (jurnal tekshirilaveradi)
//! ```

mod install;

use std::process::ExitCode;
use std::time::Duration;

use serde_json::{Value, json};
use tamga_core::checkpoint::verify_all;
use tamga_core::keys::PublicKeys;
use tamga_store::home::{default_log_id, pipe_name};
use tamga_store::vault::Vault;
use tamga_store::{Home, client, keystore, secrets};

fn sibling(name: &str) -> Option<std::path::PathBuf> {
    let exe = if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_owned()
    };
    std::env::current_exe()
        .ok()?
        .parent()
        .map(|d| d.join(exe))
        .filter(|p| p.exists())
}

fn daemon(op: &str) -> Result<Value, String> {
    let mut pipe = client::connect(
        &pipe_name(),
        sibling("tamgad").as_deref(),
        Duration::from_secs(3),
    )
    .map_err(|e| e.to_string())?;
    client::request(&mut pipe, &json!({"op": op})).map_err(|e| e.to_string())
}

fn init(home: &Home) -> Result<(), String> {
    home.ensure().map_err(|e| e.to_string())?;
    let store = secrets::default_store(home).map_err(|e| e.to_string())?;
    let (keys, created) =
        keystore::load_or_create(store.as_ref(), home).map_err(|e| e.to_string())?;
    keystore::vault_master(store.as_ref()).map_err(|e| e.to_string())?;
    if !home.config_path().exists() {
        home.write_config(&home.config())
            .map_err(|e| e.to_string())?;
    }
    println!("TAMGA papkasi: {}", home.root().display());
    println!(
        "Imzo kaliti: {} ({})",
        keys.public().key_id(),
        match (created, secrets::uses_file_store()) {
            (true, false) => "yangi yaratildi, Windows Credential Manager'da",
            (true, true) => "yangi yaratildi, FAYL omborida — faqat sinov uchun",
            (false, _) => "mavjud",
        }
    );
    println!(
        "Ochiq kalit (auditorga bering): {}",
        home.public_key().display()
    );
    println!("Jurnal: {}", home.log_path(&default_log_id()).display());
    Ok(())
}

fn verify(home: &Home) -> Result<bool, String> {
    let log_id = default_log_id();
    let read = |p: std::path::PathBuf| {
        std::fs::read_to_string(&p).or_else(|e| {
            if e.kind() == std::io::ErrorKind::NotFound {
                Ok(String::new())
            } else {
                Err(format!("{}: {e}", p.display()))
            }
        })
    };
    let log = read(home.log_path(&log_id))?;
    let cps = read(home.checkpoint_path(&log_id))?;
    let key: Value = serde_json::from_str(&read(home.public_key())?)
        .map_err(|e| format!("public-key.json: {e}"))?;
    let pk = PublicKeys::from_json(&key).map_err(|e| e.to_string())?;
    match verify_all(&log, &cps, &pk) {
        Ok(r) => {
            let sealed = r.checkpoints.iter().map(|c| c.size).max().unwrap_or(0);
            println!(
                "OK: {} — {} yozuv, {} checkpoint, oxirgi checkpoint {} yozuvni muhrlaydi.",
                log_id,
                r.log.len(),
                r.checkpoints.len(),
                sealed
            );
            for w in r.log.warnings {
                println!("ogohlantirish: {w}");
            }
            Ok(true)
        }
        Err(e) => {
            println!("BUZILISH: {e}");
            Ok(false)
        }
    }
}

fn run(args: &[String]) -> Result<ExitCode, String> {
    let home = Home::from_env();
    let a: Vec<&str> = args.iter().map(String::as_str).collect();
    match a.as_slice() {
        ["init"] => init(&home).map(|()| ExitCode::SUCCESS),
        ["status"] => {
            let v = daemon("status")?;
            println!("{}", serde_json::to_string_pretty(&v).expect("json"));
            Ok(ExitCode::SUCCESS)
        }
        ["checkpoint"] => {
            let v = daemon("checkpoint")?;
            println!("{v}");
            Ok(ExitCode::SUCCESS)
        }
        ["verify"] => verify(&home).map(|ok| {
            if ok {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }),
        ["install", "claude-code", rest @ ..] | ["uninstall", "claude-code", rest @ ..] => {
            let target = install::target(rest)?;
            let hook = sibling("tamga-hook")
                .ok_or("tamga-hook topilmadi (tamga bilan bir papkada bo'lishi kerak)")?;
            if a[0] == "install" {
                let had_file = target.exists();
                install::install(&target, &hook)?;
                println!("Claude Code hook'lari o'rnatildi: {}", target.display());
                if had_file {
                    println!("Zaxira nusxa: {}", install::backup_path(&target).display());
                }
            } else {
                let n = install::uninstall(&target)?;
                println!("{n} ta TAMGA hook'i olib tashlandi: {}", target.display());
            }
            Ok(ExitCode::SUCCESS)
        }
        ["shred", session] => {
            let store = secrets::default_store(&home).map_err(|e| e.to_string())?;
            let master = keystore::vault_master(store.as_ref()).map_err(|e| e.to_string())?;
            Vault::new(home.vault(), master)
                .and_then(|v| v.shred(session))
                .map_err(|e| e.to_string())?;
            println!(
                "`{session}` sessiyasi payload'lari unutildi. Jurnal va checkpoint'lar tekshirilaveradi."
            );
            Ok(ExitCode::SUCCESS)
        }
        _ => {
            eprintln!("{}", include_str!("usage.txt"));
            Ok(ExitCode::from(2))
        }
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("xato: {e}");
            ExitCode::from(2)
        }
    }
}
