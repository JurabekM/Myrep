//! tamgad — TAMGA daemon.
//!
//! Joriy foydalanuvchiga xos named pipe'da (`\\.\pipe\tamga-<user>`) tinglaydi. Barcha yozuvlar
//! yagona yozuvchi vazifa orqali o'tadi: hodisa → normallashtirish (payload vault'ga) → qaror →
//! jurnal (`fsync`) → javob. Checkpoint'lar hajm, vaqt yoki sessiya oxiri bo'yicha imzolanadi.
//!
//! Qaror: `tool.pre` uchun Cedar siyosatlari (`tamga-policy`) — standart to'plam va
//! `<TAMGA_HOME>/policies/*.cedar`. Sessiya taint'i (o'qilgan maxfiy qiymatlar) faqat xotirada.
//! Hook `allow` ni agentga qaytarmaydi — agentning o'z ruxsat so'rovlari ishlashda davom etadi.
//!
//! `ask` + `ask_route: "studio"`: hook javobi ushlab turiladi, Studio `decide` yuboradi, inson
//! qarori `decision.human` yozuvi bo'lib zanjirga tushadi. Javob kelmasa — timeout'da rad etiladi.

mod normalize;

use std::collections::{BTreeMap, HashMap, HashSet};
use std::io::Write as _;
use std::time::{Duration, Instant};

use serde_json::{Map, Value, json};
use tamga_core::keys::SigningKeys;
use tamga_policy::{Engine, Facts, Taint, Verdict};
use tamga_store::home::{AskRoute, Config, Mode, default_log_id, pipe_name};
use tamga_store::logfile::LogFile;
use tamga_store::vault::Vault;
use tamga_store::{Home, keystore, now_ts, secrets, spool};
use tokio::sync::{mpsc, oneshot};

type Reply = oneshot::Sender<Value>;

/// Yopilmay qolgan (masalan, agent yiqilgan) sessiya taint'i shuncha vaqt saqlanadi.
const TAINT_TTL: Duration = Duration::from_secs(7 * 24 * 3600);
type Job = (Value, Reply);

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

/// Studio'da inson qarorini kutayotgan `tool.pre`.
struct Pending {
    reply: Reply,
    created: Instant,
    ts: String,
    session: String,
    tool: String,
    policy: String,
    reason: String,
    facts: Vec<&'static str>,
    /// Ko'rsatish uchun qisqartirilgan va maxfiy qiymatlari yashirilgan kirish.
    preview: String,
}

/// `hook` natijasi: darhol javob yoki inson qaroriga qoldirish.
enum Outcome {
    Now(Value),
    Defer(u64, Box<Pending>),
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
    policy: Engine,
    /// Foydalanuvchi siyosatlari yuklanmagan bo'lsa — sabab (standart to'plam ishlatiladi).
    policy_error: Option<String>,
    taints: HashMap<String, Taint>,
    pending: BTreeMap<u64, Pending>,
    /// (sessiya, siyosat) — inson "shu sessiyada doim ruxsat" degan juftliklar.
    session_allow: HashSet<(String, String)>,
    /// Sessiyadagi faol ishtirokchilar soni: bir nechta MCP proxy bitta `--session` ni bo'lishadi.
    /// Taint faqat oxirgi ishtirokchi chiqqanda o'chiriladi.
    session_refs: HashMap<String, u32>,
}

fn preview(tool_input: &Value) -> String {
    let text = match tool_input.get("command").and_then(Value::as_str) {
        Some(cmd) => cmd.to_owned(),
        None => serde_json::to_string(tool_input).unwrap_or_default(),
    };
    let red = tamga_redact::redact(&text);
    if red.chars().count() > 400 {
        red.chars().take(400).collect::<String>() + "…"
    } else {
        red
    }
}

impl State {
    fn handle(&mut self, req: &Value, reply: Reply) {
        let resp = match req.get("op").and_then(Value::as_str) {
            Some("hook") => match self.hook(req, None) {
                Outcome::Now(v) => v,
                Outcome::Defer(seq, mut p) => {
                    p.reply = reply;
                    log_line(
                        &self.home,
                        &format!("ask #{seq}: {} — Studio qarori kutilmoqda", p.policy),
                    );
                    self.pending.insert(seq, *p);
                    return;
                }
            },
            Some("status") => self.status(),
            Some("checkpoint") => match self.checkpoint() {
                Ok(size) => json!({"ok": true, "size": size}),
                Err(e) => json!({"ok": false, "error": e}),
            },
            Some("pending") => self.pending_list(),
            Some("decide") => self.decide(req),
            Some("policies") => json!({
                "ok": true,
                "sources": self.policy.sources,
                "error": self.policy_error,
                "policies": self.policy.describe().iter().map(|p| json!({
                    "id": p.id, "source": p.source, "effect": p.effect,
                    "verdict": p.verdict, "reason": p.reason, "text": p.text,
                })).collect::<Vec<_>>(),
            }),
            _ => json!({"ok": false, "error": "noma'lum op"}),
        };
        let _ = reply.send(resp);
    }

    fn status(&self) -> Value {
        json!({
            "ok": true,
            "log": self.log.log_id(),
            "records": self.log.len(),
            "checkpointed": self.log.len() - self.log.uncheckpointed(),
            "key": self.key_id,
            "home": self.home.root().display().to_string(),
            "pid": std::process::id(),
            "mode": if self.config.mode == Mode::Strict { "strict" } else { "dev" },
            "config": self.config.to_json(),
            "policies": self.policy.sources,
            "policy_count": self.policy.policy_count(),
            "policy_error": self.policy_error,
            "tainted_sessions": self.taints.values().filter(|t| t.secret_read).count(),
            "pending": self.pending.len(),
        })
    }

    fn pending_list(&self) -> Value {
        let timeout = self.config.ask_timeout_secs;
        let items: Vec<Value> = self
            .pending
            .iter()
            .map(|(seq, p)| {
                let age = p.created.elapsed().as_secs();
                json!({
                    "seq": seq, "ts": p.ts, "session": p.session, "tool": p.tool,
                    "policy": p.policy, "reason": p.reason, "facts": p.facts, "preview": p.preview,
                    "age_secs": age, "expires_in_secs": timeout.saturating_sub(age),
                })
            })
            .collect();
        json!({"ok": true, "route": if self.config.ask_route == AskRoute::Studio { "studio" } else { "agent" }, "items": items})
    }

    /// Inson qarori: `{seq, verdict: allow|deny, scope: once|session}`.
    fn decide(&mut self, req: &Value) -> Value {
        let Some(seq) = req.get("seq").and_then(Value::as_u64) else {
            return json!({"ok": false, "error": "seq yo'q"});
        };
        let verdict = match req.get("verdict").and_then(Value::as_str) {
            Some("allow") => Verdict::Allow,
            Some("deny") => Verdict::Deny,
            _ => return json!({"ok": false, "error": "verdict allow yoki deny bo'lishi kerak"}),
        };
        let scope_session = req.get("scope").and_then(Value::as_str) == Some("session");
        let Some(p) = self.pending.remove(&seq) else {
            return json!({"ok": false, "error": "bu so'rov endi kutilmayapti (javob berilgan yoki muddati o'tgan)"});
        };
        let reason = match (verdict, scope_session) {
            (Verdict::Allow, true) => "inson ruxsat berdi (shu sessiyada shu qoida uchun doim)",
            (Verdict::Allow, false) => "inson ruxsat berdi",
            _ => "inson rad etdi",
        };
        if verdict == Verdict::Allow && scope_session {
            self.session_allow
                .insert((p.session.clone(), p.policy.clone()));
        }
        self.resolve(seq, p, verdict, "human", reason)
    }

    /// Kutilayotgan so'rovni yakunlaydi: `decision.human` yozuvi va hook'ka javob.
    fn resolve(&mut self, seq: u64, p: Pending, verdict: Verdict, by: &str, reason: &str) -> Value {
        let mut body = Map::new();
        body.insert("ref".into(), seq.into());
        body.insert(
            "decision".into(),
            json!({"verdict": verdict.as_str(), "by": by, "policy": p.policy, "reason": reason}),
        );
        let record = self
            .log
            .append(&now_ts(), &p.session, "decision.human", body);
        let hook_reason = format!("{reason} ({})", p.policy);
        let _ = p.reply.send(
            json!({"ok": true, "seq": seq, "verdict": verdict.as_str(), "reason": hook_reason}),
        );
        log_line(
            &self.home,
            &format!("ask #{seq}: {} — {reason}", verdict.as_str()),
        );
        match record {
            Ok(r) => json!({"ok": true, "record": r}),
            Err(e) => json!({"ok": false, "error": e.to_string()}),
        }
    }

    /// Agent hodisasini yozadi. `spooled` — spool'dan kelgan hodisa: (asl vaqt, hook qarori).
    fn hook(&mut self, req: &Value, spooled: Option<(&str, &Value)>) -> Outcome {
        // Agentlar: Claude Code hook'i va `tamga-mcp-proxy` (agent nomi `mcp-proxy:<server>`).
        let agent = req
            .get("agent")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned();
        if agent != "claude-code" && !agent.starts_with("mcp-proxy") {
            return Outcome::Now(json!({"ok": false, "error": format!("noma'lum agent: {agent}")}));
        }
        let input = req.get("input").cloned().unwrap_or(Value::Null);
        let ev = match normalize::hook_shaped(&input, &agent, &self.vault, &self.pre_seqs) {
            Ok(ev) => ev,
            Err(e) => return Outcome::Now(json!({"ok": false, "error": e})),
        };
        let mut body: Map<String, Value> = ev.body;
        let tool = input
            .get("tool_name")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned();
        let tool_input = input.get("tool_input").cloned().unwrap_or(Value::Null);
        let cwd = input.get("cwd").and_then(Value::as_str).unwrap_or_default();
        let (mut verdict, mut reason, mut policy) = (Verdict::Allow, String::new(), String::new());
        let mut flags = Vec::new();
        let mut defer = false;
        if ev.needs_decision {
            let decision = match spooled {
                Some((_, d)) if d.is_object() => d.clone(),
                _ => {
                    let facts =
                        Facts::from_tool(&tool, &tool_input, cwd, self.taints.get(&ev.session));
                    let d = self.policy.evaluate(&agent, &facts);
                    (verdict, reason, policy) = (d.verdict, d.reason.clone(), d.policy.clone());
                    flags = facts.true_flags();
                    if !flags.is_empty() {
                        let ext = body.entry("ext").or_insert_with(|| json!({}));
                        ext["dev.tamga.facts"] = json!(flags);
                    }
                    let mut v =
                        json!({"verdict": d.verdict.as_str(), "by": "policy", "policy": d.policy});
                    if !d.reason.is_empty() {
                        v["reason"] = d.reason.into();
                    }
                    if verdict == Verdict::Ask && self.config.ask_route == AskRoute::Studio {
                        if self
                            .session_allow
                            .contains(&(ev.session.clone(), policy.clone()))
                        {
                            verdict = Verdict::Allow;
                            v = json!({"verdict": "allow", "by": "human", "policy": policy,
                                       "reason": "shu sessiyada shu qoida uchun inson oldindan ruxsat bergan"});
                        } else {
                            defer = true;
                        }
                    }
                    v
                }
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
        let session = ev.session.clone();
        match self.log.append(&ts, &ev.session, ev.event, body) {
            Ok(seq) => {
                if ev.event == "tool.post" {
                    // Maxfiy faylni o'qigan tool natijasidagi qiymatlar sessiya taint'iga qo'shiladi.
                    let from_secret =
                        Facts::from_tool(&tool, &tool_input, cwd, None).reads_secret_file;
                    let response = input.get("tool_response").cloned().unwrap_or(Value::Null);
                    let t = self.taints.entry(session.clone()).or_default();
                    let before = (t.secret_read, t.len());
                    t.learn_from_response(&response, from_secret);
                    if (t.secret_read, t.len()) != before {
                        log_line(
                            &self.home,
                            &format!(
                                "taint: sessiya {session} — {} maxfiy qiymat kuzatilmoqda",
                                t.len()
                            ),
                        );
                        self.persist(&session);
                    }
                }
                if ev.event == "tool.pre"
                    && let Some(id) = ev.tool_use_id
                {
                    self.pre_seqs.insert(id, seq);
                }
                if ev.event == "session.start" {
                    *self.session_refs.entry(session.clone()).or_default() += 1;
                    self.persist(&session);
                }
                if is_end {
                    let left = match self.session_refs.get_mut(&session) {
                        Some(n) if *n > 1 => {
                            *n -= 1;
                            *n
                        }
                        _ => {
                            self.session_refs.remove(&session);
                            0
                        }
                    };
                    if left == 0 {
                        self.taints.remove(&session);
                        self.session_allow.retain(|(s, _)| *s != session);
                        if let Err(e) = self.vault.remove_state(&session) {
                            log_line(&self.home, &format!("holat o'chirilmadi: {e}"));
                        }
                    } else {
                        self.persist(&session);
                    }
                    let _ = self.checkpoint();
                }
                if defer {
                    let (tx, _) = oneshot::channel(); // `handle` haqiqiy javob kanali bilan almashtiradi
                    return Outcome::Defer(
                        seq,
                        Box::new(Pending {
                            reply: tx,
                            created: Instant::now(),
                            ts,
                            session,
                            tool,
                            policy,
                            reason,
                            facts: flags,
                            preview: preview(&tool_input),
                        }),
                    );
                }
                Outcome::Now(
                    json!({"ok": true, "seq": seq, "verdict": verdict.as_str(), "reason": reason}),
                )
            }
            Err(e) => {
                log_line(&self.home, &format!("yozish xatosi: {e}"));
                Outcome::Now(json!({"ok": false, "error": e.to_string()}))
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

    /// Sessiya holatini (taint + ishtirokchilar soni) diskka, sessiya vault kaliti bilan shifrlab yozadi.
    /// Faqat taint'li sessiyalar saqlanadi — qolganlari qayta ishga tushganda tiklanishi shart emas.
    fn persist(&mut self, session: &str) {
        let Some(t) = self.taints.get(session).filter(|t| t.secret_read) else {
            return;
        };
        let state = json!({"v": 1, "taint": t.to_json(), "refs": self.session_refs.get(session).copied().unwrap_or(1)});
        if let Err(e) = self.vault.put_state(session, state.to_string().as_bytes()) {
            log_line(
                &self.home,
                &format!("taint holati saqlanmadi ({session}): {e}"),
            );
        }
    }

    /// Daemon ishga tushganda saqlangan holatlarni tiklaydi; muddati o'tganlari o'chiriladi.
    fn restore(&mut self) {
        match self.vault.load_states(TAINT_TTL) {
            Ok(states) => {
                let n = states.len();
                for (session, bytes) in states {
                    let Ok(v) = serde_json::from_slice::<Value>(&bytes) else {
                        continue;
                    };
                    self.taints
                        .insert(session.clone(), Taint::from_json(&v["taint"]));
                    let refs = v["refs"]
                        .as_u64()
                        .unwrap_or(1)
                        .clamp(1, u64::from(u32::MAX)) as u32;
                    self.session_refs.insert(session, refs);
                }
                if n > 0 {
                    log_line(&self.home, &format!("taint holati tiklandi: {n} sessiya"));
                }
            }
            Err(e) => log_line(&self.home, &format!("taint holatlari o'qilmadi: {e}")),
        }
    }

    fn tick(&mut self) {
        // Config jonli: Studio yoki foydalanuvchi o'zgartirsa, qayta ishga tushirish shart emas.
        self.config = self.home.config();
        let timeout = Duration::from_secs(self.config.ask_timeout_secs);
        let expired: Vec<u64> = self
            .pending
            .iter()
            .filter(|(_, p)| p.created.elapsed() >= timeout)
            .map(|(s, _)| *s)
            .collect();
        for seq in expired {
            if let Some(p) = self.pending.remove(&seq) {
                self.resolve(
                    seq,
                    p,
                    Verdict::Deny,
                    "default",
                    "inson javobi kutilgan muddatda kelmadi",
                );
            }
        }
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
            let ok = match self.hook(&req, Some((&ts, &decision))) {
                Outcome::Now(resp) => {
                    let ok = resp.get("ok") == Some(&Value::Bool(true));
                    if !ok {
                        log_line(&self.home, &format!("spool {}: {resp}", path.display()));
                    }
                    ok
                }
                Outcome::Defer(..) => true, // spool'dagi qaror allaqachon qabul qilingan — bu holat bo'lmaydi
            };
            if ok {
                let _ = std::fs::remove_file(&path);
            } else {
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
    let (policy, policy_error) = match Engine::load(&home.root().join("policies")) {
        Ok(e) => (e, None),
        Err(e) => {
            log_line(
                &home,
                &format!(
                    "DIQQAT: foydalanuvchi siyosatlari yuklanmadi, faqat standart to'plam: {e}"
                ),
            );
            (
                Engine::with_defaults().map_err(|e| e.to_string())?,
                Some(e.to_string()),
            )
        }
    };
    log_line(
        &home,
        &format!(
            "siyosatlar: {} ta ({})",
            policy.policy_count(),
            policy.sources.join(", ")
        ),
    );
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
    let mut state = State {
        vault: Vault::new(home.vault(), master).map_err(|e| e.to_string())?,
        home,
        config,
        log,
        keys,
        key_id,
        pre_seqs: HashMap::new(),
        last_checkpoint: Instant::now(),
        policy,
        policy_error,
        taints: HashMap::new(),
        pending: BTreeMap::new(),
        session_allow: HashSet::new(),
        session_refs: HashMap::new(),
    };
    state.restore();
    Ok(state)
}

/// Yagona yozuvchi: barcha so'rovlar ketma-ket bajariladi, zanjir tartibi kafolatlanadi.
async fn writer(mut state: State, mut rx: mpsc::Receiver<Job>) {
    let mut ticker = tokio::time::interval(Duration::from_secs(1));
    loop {
        tokio::select! {
            job = rx.recv() => match job {
                Some((req, reply)) => state.handle(&req, reply),
                None => break,
            },
            _ = ticker.tick() => state.tick(),
        }
    }
    // To'xtashda kutilayotgan so'rovlar rad etiladi (fail-closed) va oxirgi checkpoint yoziladi.
    let waiting: Vec<u64> = state.pending.keys().copied().collect();
    for seq in waiting {
        if let Some(p) = state.pending.remove(&seq) {
            state.resolve(seq, p, Verdict::Deny, "default", "daemon to'xtadi");
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
        // `tx` tushirildi — yozuvchi kutilayotganlarni rad etib, oxirgi checkpoint'ni yozib to'xtaydi.
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
