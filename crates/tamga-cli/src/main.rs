//! tamga — TAMGA boshqaruv CLI.
//!
//! ```text
//! tamga init                                  kalitlar va papkalarni tayyorlash
//! tamga status                                daemon holati
//! tamga stop                                  daemon'ni to'xtatish (oxirgi checkpoint bilan)
//! tamga verify                                o'z jurnalini to'liq tekshirish (zanjir + checkpoint + imzo)
//! tamga checkpoint                            darhol checkpoint
//! tamga install claude-code --project <dir>   loyiha .claude/settings.json ga hook qo'shish
//! tamga install claude-code --user            ~/.claude/settings.json ga hook qo'shish
//! tamga uninstall claude-code (--project <dir> | --user)
//! tamga shred <session>                       sessiya payload'larini unutish (jurnal tekshirilaveradi)
//! ```

use std::process::ExitCode;
use std::time::Duration;

use serde_json::{Value, json};
use tamga_core::checkpoint::verify_all;
use tamga_core::keys::PublicKeys;
use tamga_store::home::default_log_id;
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
    daemon_req(&json!({"op": op}))
}

fn daemon_req(req: &Value) -> Result<Value, String> {
    let mut pipe = client::connect_auto(sibling("tamgad").as_deref(), Duration::from_secs(3))
        .map_err(|e| e.to_string())?;
    client::request(&mut pipe, req).map_err(|e| e.to_string())
}

/// Daemon'ni to'xtatadi (yangisini ishga tushirmaydi): kutilayotgan so'rovlar rad etiladi, oxirgi
/// checkpoint yoziladi. Jarayon haqiqatan chiqquncha kutadi — o'rnatuvchi fayllarni almashtira olsin.
fn stop() -> Result<ExitCode, String> {
    let Ok(mut pipe) = client::connect_auto(None, Duration::from_millis(500)) else {
        println!("daemon ishlamayapti");
        return Ok(ExitCode::SUCCESS);
    };
    let v = client::request(&mut pipe, &json!({"op": "shutdown"})).map_err(|e| e.to_string())?;
    drop(pipe);
    if v["ok"] != true {
        return Err(v["error"].as_str().unwrap_or("daemon rad etdi").to_owned());
    }
    let pid = v["pid"].as_u64();
    let deadline = std::time::Instant::now() + Duration::from_secs(10);
    while let Some(pid) = pid {
        if !process_alive(pid) {
            break;
        }
        if std::time::Instant::now() > deadline {
            return Err(format!("daemon (PID {pid}) 10 s ichida to'xtamadi"));
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    match v["checkpoint"].as_u64() {
        Some(n) => println!(
            "daemon to'xtadi (PID {}), yakuniy checkpoint: {n} yozuv",
            pid.unwrap_or(0)
        ),
        None => println!("daemon to'xtadi (PID {})", pid.unwrap_or(0)),
    }
    Ok(ExitCode::SUCCESS)
}

#[cfg(windows)]
fn process_alive(pid: u64) -> bool {
    use std::os::windows::process::CommandExt as _;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    std::process::Command::new("tasklist")
        .args(["/FI", &format!("PID eq {pid}"), "/FO", "CSV", "/NH"])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).contains(&format!("\"{pid}\"")))
        .unwrap_or(false)
}

#[cfg(not(windows))]
fn process_alive(pid: u64) -> bool {
    std::path::Path::new(&format!("/proc/{pid}")).exists()
}

/// Zaxira paroli: `TAMGA_BACKUP_PASSPHRASE` (avtomatlashtirish) yoki konsoldan, ekranda ko'rinmasdan.
fn passphrase(confirm: bool) -> Result<String, String> {
    if let Ok(p) = std::env::var("TAMGA_BACKUP_PASSPHRASE") {
        return Ok(p);
    }
    let p = rpassword::prompt_password("Zaxira paroli: ").map_err(|e| e.to_string())?;
    if confirm {
        let again =
            rpassword::prompt_password("Parolni takrorlang: ").map_err(|e| e.to_string())?;
        if again != p {
            return Err("parollar mos emas".into());
        }
    }
    Ok(p)
}

/// `tamga key show | rotate [--reason r] | backup --out f | restore <f> [--force]` — spec §7.5.
fn key(home: &Home, rest: &[&str]) -> Result<ExitCode, String> {
    let store = || secrets::default_store(home).map_err(|e| e.to_string());
    match rest {
        ["show"] => {
            let anchor = keystore::anchor(home).map_err(|e| e.to_string())?;
            println!("Langar kalit (auditorga beriladi): {}", anchor.key_id());
            println!("  fayl: {}", home.public_key().display());
            let log = std::fs::read_to_string(home.log_path(&default_log_id())).unwrap_or_default();
            match tamga_core::chain::verify_log(&log) {
                Ok(s) if s.rotations.is_empty() => println!("Almashtirishlar: yo'q"),
                Ok(s) => {
                    println!("Almashtirishlar ({}):", s.rotations.len());
                    for r in &s.rotations {
                        println!(
                            "  #{} {} -> {} ({})",
                            r.seq,
                            r.from,
                            r.to.key_id(),
                            r.reason
                        );
                    }
                }
                Err(e) => println!("jurnal o'qilmadi: {e}"),
            }
            if let Ok(v) = client::connect_auto(None, Duration::from_millis(500))
                .map_err(|e| e.to_string())
                .and_then(|mut p| {
                    client::request(&mut p, &json!({"op": "status"})).map_err(|e| e.to_string())
                })
            {
                println!("Faol kalit (daemon): {}", v["key"].as_str().unwrap_or("?"));
            }
            Ok(ExitCode::SUCCESS)
        }
        ["rotate", opts @ ..] => {
            let reason = match opts {
                [] => "scheduled",
                ["--reason", r] => r,
                _ => return Err("tamga key rotate [--reason scheduled|compromise|restore]".into()),
            };
            let v = daemon_req(&json!({"op": "rotate", "reason": reason}))?;
            if v["ok"] == true {
                println!(
                    "Kalit almashtirildi (yozuv #{}): {} -> {}",
                    v["seq"],
                    v["from"].as_str().unwrap_or(""),
                    v["to"].as_str().unwrap_or("")
                );
                println!(
                    "Eski kalit yo'q qilindi. Yangi zaxira oling: tamga key backup --out <fayl>"
                );
                Ok(ExitCode::SUCCESS)
            } else {
                Err(v["error"].as_str().unwrap_or("xato").to_owned())
            }
        }
        ["backup", "--out", out] => {
            let out = std::path::Path::new(out);
            if out.exists() {
                return Err(format!(
                    "{} allaqachon bor — boshqa nom bering",
                    out.display()
                ));
            }
            let text = keystore::backup(store()?.as_ref(), home, &passphrase(true)?)
                .map_err(|e| e.to_string())?;
            std::fs::write(out, text).map_err(|e| format!("{}: {e}", out.display()))?;
            println!("Zaxira yozildi: {}", out.display());
            println!(
                "Uni boshqa joyda saqlang (USB, parol menejeri). Parolsiz uni ochib bo'lmaydi."
            );
            Ok(ExitCode::SUCCESS)
        }
        ["restore", file, opts @ ..] => {
            let force = match opts {
                [] => false,
                ["--force"] => true,
                _ => return Err("tamga key restore <fayl> [--force]".into()),
            };
            if client::connect_auto(None, Duration::from_millis(300)).is_ok() {
                return Err("daemon ishlayapti — avval `tamga stop`".into());
            }
            let text = std::fs::read_to_string(file).map_err(|e| format!("{file}: {e}"))?;
            home.ensure().map_err(|e| e.to_string())?;
            let info =
                keystore::restore(store()?.as_ref(), home, &text, &passphrase(false)?, force)
                    .map_err(|e| e.to_string())?;
            println!(
                "Tiklandi: imzo kaliti {}, langar {} (zaxira {})",
                info.key, info.anchor, info.created
            );
            println!(
                "Zaxira begona qo'lga tushgan bo'lishi mumkin bo'lsa: tamga key rotate --reason restore"
            );
            Ok(ExitCode::SUCCESS)
        }
        _ => Err(
            "tamga key show | rotate [--reason r] | backup --out <fayl> | restore <fayl> [--force]"
                .into(),
        ),
    }
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
            if r.keys.len() > 1 {
                println!("Kalitlar zanjiri: {}", r.keys.join(" -> "));
            }
            for w in r.log.warnings.iter().chain(&r.key_warnings) {
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
        ["stop"] => stop(),
        ["key", rest @ ..] => key(&home, rest),
        ["pending"] => {
            let v = daemon("pending")?;
            let items = v["items"].as_array().cloned().unwrap_or_default();
            println!(
                "yo'nalish: {} — {} ta so'rov kutilmoqda",
                v["route"].as_str().unwrap_or("?"),
                items.len()
            );
            for i in items {
                println!(
                    "#{} [{}] {} — {} ({} s qoldi)
    {}",
                    i["seq"],
                    i["tool"].as_str().unwrap_or(""),
                    i["policy"].as_str().unwrap_or(""),
                    i["reason"].as_str().unwrap_or(""),
                    i["expires_in_secs"],
                    i["preview"].as_str().unwrap_or("")
                );
            }
            Ok(ExitCode::SUCCESS)
        }
        ["decide", seq, verdict, rest @ ..] => {
            let seq: u64 = seq.parse().map_err(|_| "seq butun son bo'lishi kerak")?;
            let scope = if rest == ["--session"] {
                "session"
            } else {
                "once"
            };
            let v = daemon_req(
                &json!({"op": "decide", "seq": seq, "verdict": verdict, "scope": scope}),
            )?;
            println!("{v}");
            Ok(if v["ok"] == true {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            })
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
            let target = tamga_store::integrate::target(rest)?;
            let hook = sibling("tamga-hook")
                .ok_or("tamga-hook topilmadi (tamga bilan bir papkada bo'lishi kerak)")?;
            if a[0] == "install" {
                let had_file = target.exists();
                tamga_store::integrate::install(&target, &hook)?;
                println!("Claude Code hook'lari o'rnatildi: {}", target.display());
                if had_file {
                    println!(
                        "Zaxira nusxa: {}",
                        tamga_store::integrate::backup_path(&target).display()
                    );
                }
            } else {
                let n = tamga_store::integrate::uninstall(&target)?;
                println!("{n} ta TAMGA hook'i olib tashlandi: {}", target.display());
            }
            Ok(ExitCode::SUCCESS)
        }
        ["show", seq] => show(&home, seq),
        ["export", rest @ ..] => export(&home, rest),
        ["shred", session] => {
            open_vault(&home)?
                .shred(session)
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

fn open_vault(home: &Home) -> Result<Vault, String> {
    let store = secrets::default_store(home).map_err(|e| e.to_string())?;
    let master = keystore::vault_master(store.as_ref()).map_err(|e| e.to_string())?;
    Vault::new(home.vault(), master).map_err(|e| e.to_string())
}

/// Yozuvni va uning payload'larini vault'dan ochib ko'rsatadi. Har bir payload jurnaldagi
/// tuzlangan digest bilan solishtiriladi (`Vault::get`).
fn show(home: &Home, seq: &str) -> Result<ExitCode, String> {
    let seq: u64 = seq.parse().map_err(|_| "seq butun son bo'lishi kerak")?;
    let path = home.log_path(&default_log_id());
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let line = text
        .lines()
        .nth(seq as usize)
        .ok_or(format!("#{seq} yozuv yo'q"))?;
    let record: Value = serde_json::from_str(line).map_err(|e| e.to_string())?;
    println!("{}", serde_json::to_string_pretty(&record).expect("json"));
    let session = record["session"].as_str().unwrap_or_default();
    let vault = open_vault(home)?;
    for (name, reference) in [
        ("tool.input", &record["tool"]["input"]),
        ("result", &record["result"]),
    ] {
        if reference.is_null() {
            continue;
        }
        match vault.get(session, reference).map_err(|e| e.to_string())? {
            Some(data) => println!(
                "--- {name} (vault, digest mos) ---\n{}",
                String::from_utf8_lossy(&data)
            ),
            None => println!("--- {name}: vault'da yo'q yoki sessiya unutilgan (shred) ---"),
        }
    }
    Ok(ExitCode::SUCCESS)
}

/// `tamga export [--out <fayl.zip>] [--session <id>]... [--payloads]`
fn export(home: &Home, rest: &[&str]) -> Result<ExitCode, String> {
    use tamga_store::export::{ExportOptions, default_path, export};
    let mut opts = ExportOptions {
        out: default_path(home),
        ..Default::default()
    };
    let mut it = rest.iter();
    while let Some(a) = it.next() {
        match *a {
            "--out" => opts.out = it.next().ok_or("--out qiymatsiz")?.into(),
            "--session" => opts
                .sessions
                .push((*it.next().ok_or("--session qiymatsiz")?).to_owned()),
            "--payloads" => opts.include_payloads = true,
            other => return Err(format!("noma'lum bayroq: {other}")),
        }
    }
    let vault = if opts.include_payloads {
        Some(open_vault(home)?)
    } else {
        None
    };
    let r = export(home, vault.as_ref(), &opts).map_err(|e| e.to_string())?;
    println!("Dalil to'plami: {}", r.path.display());
    println!(
        "{} yozuv, {} checkpoint, {} payload ({} unutilgan), jurnal {}",
        r.records,
        r.checkpoints,
        r.payloads,
        r.shredded,
        if r.verified {
            "butun"
        } else {
            "BUZILGAN — natija MANIFEST.json da"
        }
    );
    println!("SHA-256: {}", r.sha256);
    Ok(ExitCode::SUCCESS)
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
