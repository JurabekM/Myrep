//! tamgad — TAMGA daemon.
//!
//! Joriy foydalanuvchiga xos named pipe'da (`\\.\pipe\tamga-<user>`) tinglaydi. Barcha yozuvlar
//! yagona yozuvchi vazifa orqali o'tadi: hodisa → normallashtirish (payload vault'ga) → qaror →
//! jurnal (`fsync`) → javob. Checkpoint'lar hajm, vaqt yoki sessiya oxiri bo'yicha imzolanadi.
//!
//! F2: qaror har doim `allow` / `default` (siyosat dvigateli F3 da). Hook `allow` ni agentga
//! qaytarmaydi — agentning o'z ruxsat so'rovlari ishlashda davom etadi.

mod normalize;

use std::collections::HashMap;
use std::io::Write as _;
use std::time::{Duration, Instant};

use serde_json::{Map, Value, json};
use tamga_core::keys::SigningKeys;
use tamga_store::home::{Config, default_log_id, pipe_name};
use tamga_store::logfile::LogFile;
use tamga_store::vault::Vault;
use tamga_store::{Home, keystore, now_ts, secrets, spool};
use tokio::sync::{mpsc, oneshot};

type Job = (Value, oneshot::Sender<Value>);

fn log_line(home: &Home, msg: &str) {
    let p = home.daemon_log();
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(p)
    {
        let _ = writeln!(f, "{} [{}] {msg}", now_ts(), std::process::id());
    }
}

struct State {
    home: Home,
    config: Config,
    log: LogFile,
    vault: Vault,
    keys: SigningKeys,
    key_id: String,
    pre_seqs: HashMap<String, u64>,
    last_checkpoint: Instant,
}

impl State {
    fn handle(&mut self, req: &Value) -> Value {
        match req.get("op").and_then(Value::as_str) {
            Some("hook") => self.hook(req, None),
            Some("status") => json!({
                "ok": true,
                "log": self.log.log_id(),
                "records": self.log.len(),
                "checkpointed": self.log.len() - self.log.uncheckpointed(),
                "key": self.key_id,
                "home": self.home.root().display().to_string(),
                "pid": std::process::id(),
                "mode": if self.config.mode == tamga_store::home::Mode::Strict { "strict" } else { "dev" },
            }),
            Some("checkpoint") => match self.checkpoint() {
                Ok(size) => json!({"ok": true, "size": size}),
                Err(e) => json!({"ok": false, "error": e}),
            },
            _ => json!({"ok": false, "error": "noma'lum op"}),
        }
    }

    /// Agent hodisasini yozadi. `spooled` — spool'dan kelgan hodisa: (asl vaqt, hook qarori).
    fn hook(&mut self, req: &Value, spooled: Option<(&str, &Value)>) -> Value {
        if req.get("agent").and_then(Value::as_str) != Some("claude-code") {
            return json!({"ok": false, "error": "faqat claude-code agenti qo'llab-quvvatlanadi (F2)"});
        }
        let input = req.get("input").cloned().unwrap_or(Value::Null);
        let ev = match normalize::claude_code(&input, &self.vault, &self.pre_seqs) {
            Ok(ev) => ev,
            Err(e) => return json!({"ok": false, "error": e}),
        };
        let mut body: Map<String, Value> = ev.body;
        let (verdict, reason) = ("allow", Value::Null);
        if ev.needs_decision {
            let decision = match spooled {
                Some((_, d)) if d.is_object() => d.clone(),
                _ => json!({"verdict": verdict, "by": "default"}),
            };
            body.insert("decision".into(), decision);
        }
        let ts = match spooled {
            Some((ts, _)) => {
                let ext = body.entry("ext").or_insert_with(|| json!({}));
                ext["dev.tamga.spooled"] = true.into();
                ts.to_owned()
            }
            None => now_ts(),
        };
        let is_end = ev.event == "session.end";
        match self.log.append(&ts, &ev.session, ev.event, body) {
            Ok(seq) => {
                if ev.event == "tool.pre"
                    && let Some(id) = ev.tool_use_id
                {
                    self.pre_seqs.insert(id, seq);
                }
                if is_end {
                    let _ = self.checkpoint();
                }
                json!({"ok": true, "seq": seq, "verdict": verdict, "reason": reason})
            }
            Err(e) => {
                log_line(&self.home, &format!("yozish xatosi: {e}"));
                json!({"ok": false, "error": e.to_string()})
            }
        }
    }

    fn checkpoint(&mut self) -> Result<Option<u64>, String> {
        let r = self.log.checkpoint(&self.keys).map_err(|e| e.to_string());
        self.last_checkpoint = Instant::now();
        if let Ok(Some(size)) = &r {
            log_line(&self.home, &format!("checkpoint: {size} yozuv"));
        }
        r
    }

    fn tick(&mut self) {
        let pending = self.log.uncheckpointed();
        let due = pending >= self.config.checkpoint_every
            || self.last_checkpoint.elapsed() >= Duration::from_secs(self.config.checkpoint_secs);
        if pending > 0
            && due
            && let Err(e) = self.checkpoint()
        {
            log_line(&self.home, &format!("checkpoint xatosi: {e}"));
        }
        self.drain_spool();
    }

    fn drain_spool(&mut self) {
        for path in spool::pending(&self.home.spool()) {
            let Ok(text) = std::fs::read_to_string(&path) else {
                continue;
            };
            let Ok(v) = serde_json::from_str::<Value>(&text) else {
                let _ = std::fs::rename(&path, path.with_extension("bad"));
                continue;
            };
            let ts = v
                .get("ts")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_owned();
            let decision = v.get("decision").cloned().unwrap_or(Value::Null);
            let req = json!({"op": "hook", "agent": v.get("agent").cloned().unwrap_or(Value::Null), "input": v.get("input").cloned().unwrap_or(Value::Null)});
            let resp = self.hook(&req, Some((&ts, &decision)));
            if resp.get("ok") == Some(&Value::Bool(true)) {
                let _ = std::fs::remove_file(&path);
            } else {
                log_line(&self.home, &format!("spool {}: {resp}", path.display()));
                let _ = std::fs::rename(&path, path.with_extension("bad"));
            }
        }
    }
}

fn open_state(home: Home) -> Result<State, String> {
    home.ensure().map_err(|e| e.to_string())?;
    let config = home.config();
    let store = secrets::default_store(&home).map_err(|e| e.to_string())?;
    let (keys, created) =
        keystore::load_or_create(store.as_ref(), &home).map_err(|e| e.to_string())?;
    let master = keystore::vault_master(store.as_ref()).map_err(|e| e.to_string())?;
    let log_id = default_log_id();
    let (log, report) = LogFile::open(
        &home.log_path(&log_id),
        &home.checkpoint_path(&log_id),
        &log_id,
        config.witness_dir.clone(),
    )
    .map_err(|e| e.to_string())?;
    let key_id = keys.public().key_id();
    log_line(
        &home,
        &format!(
            "ishga tushdi: jurnal {log_id}, {} yozuv, kalit {key_id}{}{}",
            report.records,
            if created { " (yangi yaratildi)" } else { "" },
            if report.recovered_partial_line {
                ", uzilgan oxirgi qator .partial ga ko'chirildi"
            } else {
                ""
            },
        ),
    );
    Ok(State {
        vault: Vault::new(home.vault(), master).map_err(|e| e.to_string())?,
        home,
        config,
        log,
        keys,
        key_id,
        pre_seqs: HashMap::new(),
        last_checkpoint: Instant::now(),
    })
}

/// Yagona yozuvchi: barcha so'rovlar ketma-ket bajariladi, zanjir tartibi kafolatlanadi.
async fn writer(mut state: State, mut rx: mpsc::Receiver<Job>) {
    let mut ticker = tokio::time::interval(Duration::from_secs(1));
    loop {
        tokio::select! {
            job = rx.recv() => match job {
                Some((req, reply)) => { let _ = reply.send(state.handle(&req)); }
                None => break,
            },
            _ = ticker.tick() => state.tick(),
        }
    }
    let _ = state.checkpoint();
    log_line(&state.home, "to'xtadi");
}

#[cfg(windows)]
async fn serve(pipe: String, tx: mpsc::Sender<Job>) -> std::io::Result<()> {
    use tokio::io::{AsyncBufReadExt as _, AsyncWriteExt as _, BufReader};
    use tokio::net::windows::named_pipe::ServerOptions;

    // Birinchi nusxa: boshqa daemon allaqachon ishlayotgan bo'lsa, xato qaytadi.
    let mut server = ServerOptions::new()
        .first_pipe_instance(true)
        .reject_remote_clients(true)
        .create(&pipe)?;
    loop {
        server.connect().await?;
        let conn = server;
        server = ServerOptions::new()
            .reject_remote_clients(true)
            .create(&pipe)?;
        let tx = tx.clone();
        tokio::spawn(async move {
            let (r, mut w) = tokio::io::split(conn);
            let mut lines = BufReader::new(r).lines();
            while let Ok(Some(line)) = lines.next_line().await {
                let resp = match serde_json::from_str::<Value>(&line) {
                    Ok(req) => {
                        let (reply_tx, reply_rx) = oneshot::channel();
                        if tx.send((req, reply_tx)).await.is_err() {
                            break;
                        }
                        reply_rx
                            .await
                            .unwrap_or_else(|_| json!({"ok": false, "error": "yozuvchi to'xtagan"}))
                    }
                    Err(e) => json!({"ok": false, "error": format!("JSON emas: {e}")}),
                };
                let mut out = resp.to_string();
                out.push('\n');
                if w.write_all(out.as_bytes()).await.is_err() {
                    break;
                }
            }
        });
    }
}

#[cfg(not(windows))]
async fn serve(_pipe: String, _tx: mpsc::Sender<Job>) -> std::io::Result<()> {
    Err(std::io::Error::other(
        "hozircha faqat Windows named pipe qo'llab-quvvatlanadi",
    ))
}

fn main() -> std::process::ExitCode {
    let home = Home::from_env();
    let state = match open_state(home.clone()) {
        Ok(s) => s,
        Err(e) => {
            log_line(&home, &format!("ishga tushmadi: {e}"));
            eprintln!("tamgad: {e}");
            return std::process::ExitCode::from(1);
        }
    };
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .expect("tokio");
    rt.block_on(async move {
        let (tx, rx) = mpsc::channel::<Job>(256);
        let writer = tokio::spawn(writer(state, rx));
        let pipe = pipe_name();
        let result = tokio::select! {
            r = serve(pipe.clone(), tx) => r,
            _ = tokio::signal::ctrl_c() => Ok(()),
        };
        // `tx` tushirildi — yozuvchi oxirgi checkpoint'ni yozib to'xtaydi.
        let _ = writer.await;
        match result {
            Ok(()) => std::process::ExitCode::SUCCESS,
            Err(e)
                if e.kind() == std::io::ErrorKind::PermissionDenied
                    || e.raw_os_error() == Some(231) =>
            {
                log_line(&home, &format!("{pipe} band — boshqa tamgad ishlayapti"));
                std::process::ExitCode::SUCCESS
            }
            Err(e) => {
                log_line(&home, &format!("pipe xatosi: {e}"));
                std::process::ExitCode::from(1)
            }
        }
    })
}
