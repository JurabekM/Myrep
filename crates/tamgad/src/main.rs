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

// L-3 (mustahkamlash): reliz'da konsol oynasiz. Daemon faqat log fayliga yozadi; hook uni
// CREATE_NO_WINDOW bilan ishga tushiradi, lekin to'g'ridan-to'g'ri ishga tushirilsa ham oyna chiqmaydi.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod control;
mod normalize;
mod observe;

use std::collections::{BTreeMap, HashMap, HashSet};
use std::io::Write as _;
use std::time::{Duration, Instant};

use serde_json::{Map, Value, json};
use tamga_core::keys::SigningKeys;
use tamga_core::rotation;
use tamga_policy::{Engine, Facts, Taint, Verdict};
use tamga_sensor::{Observation, Sensor};
use tamga_store::home::{AskRoute, Config, Mode, default_log_id, pipe_name};
use tamga_store::logfile::LogFile;
use tamga_store::secrets::SecretStore;
use tamga_store::vault::Vault;
use tamga_store::{Home, keystore, now_ts, random, secrets, spool};
use tokio::sync::{mpsc, oneshot};

type Reply = oneshot::Sender<Value>;

/// Yopilmay qolgan (masalan, agent yiqilgan) sessiya taint'i shuncha vaqt saqlanadi.
const TAINT_TTL: Duration = Duration::from_secs(7 * 24 * 3600);
/// Pipe'dagi bitta so'rov va spool faylining eng katta hajmi (hook `MAX_INPUT` bilan bir xil, M-4).
const MAX_MSG: u64 = 8 << 20;
/// So'rov, pipe mijozining PID'i (K1) va javob kanali.
/// Pipe mijozi haqida: PID (K1) va himoyalangan rejimda Windows identifikatori.
#[derive(Debug, Clone, Default)]
struct ClientInfo {
    pid: Option<u32>,
    /// Mijoz foydalanuvchisining SID'i (faqat xizmat rejimi).
    sid: Option<String>,
    /// Mijoz tokeni UAC bilan ko'tarilganmi (faqat xizmat rejimi).
    elevated: bool,
}

type Job = (Value, ClientInfo, Reply);

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
    /// OS sensori ("qildi") va "aytdi va qildi" korrelyatori.
    sensor: Option<std::sync::Arc<Sensor>>,
    corr: observe::Correlator,
    /// Fayl hodisalarini 2 s ichida takrorlamaslik: (yo'l, amal) -> oxirgi vaqt.
    file_dedupe: HashMap<(String, &'static str), Instant>,
    /// `shutdown` bajarilgan: yakuniy checkpoint ikki marta yozilmaydi.
    stopped: bool,
    /// Joriy hook so'rovini yuborgan mijozning SID'i (faqat xizmat rejimi, so'rov davomida).
    client_sid: Option<String>,
    /// Maxfiy kalitlar ombori (kalit almashtirish uchun).
    store: Box<dyn SecretStore>,
    /// Langar (birinchi) kalit identifikatori — `public-key.json`.
    anchor_id: String,
    /// Jurnalga yozilgan, lekin hali eski kalit checkpoint'i bilan tasdiqlanmagan almashtirish.
    pending_rotation: Option<(u64, SigningKeys)>,
    /// K1: ishonchli boshqaruv dasturlari (`tamga.exe`, `tamga-studio.exe`) shu papkada bo'lishi kerak.
    own_dir: Option<std::path::PathBuf>,
    deny_limit: control::DenyLimiter,
    /// K2: oxirgi ko'rilgan config va Claude Code hook'lari holati — o'zgarsa `control` yozuvi.
    last_config: Value,
    hooks_installed: Option<bool>,
    hooks_checked: Instant,
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
    fn handle(&mut self, req: &Value, client: ClientInfo, reply: Reply) {
        let op = req.get("op").and_then(Value::as_str).unwrap_or_default();
        if control::GATED.contains(&op)
            && let Err(why) = self.gate(op, req, &client)
        {
            let _ = reply.send(json!({"ok": false, "denied": true, "error": why}));
            return;
        }
        let resp = match req.get("op").and_then(Value::as_str) {
            Some("hook") => match self.hook_from(req, client.sid.as_deref()) {
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
            Some("rotate") => self.rotate(req),
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

    /// K1: boshqaruv buyrug'ini yuborgan jarayonni tekshiradi; urinish (qabul yoki rad) jurnalga yoziladi.
    fn gate(&mut self, op: &str, req: &Value, client: &ClientInfo) -> Result<(), String> {
        let caller = client.pid.and_then(tamga_sensor::identify);
        let mut verdict = control::authorize(caller.as_ref(), self.own_dir.as_deref());
        // Himoyalangan rejim: boshqaruv buyruqlari faqat administrator (UAC tasdiqlangan) tokenidan.
        // UAC so'rovi xavfsiz ish stolida — uni foydalanuvchining o'zi tasdiqlaydi.
        if verdict.is_ok() && self.home.is_service() && !client.elevated {
            verdict = Err(
                "himoyalangan rejimda boshqaruv buyruqlari faqat administrator (UAC) tasdig'i bilan".into(),
            );
        }
        if verdict.is_ok() || self.deny_limit.allow() {
            let mut info = control::client_json(caller.as_ref());
            if self.home.is_service() {
                info["sid"] = client.sid.clone().map_or(Value::Null, Value::from);
                info["elevated"] = client.elevated.into();
            }
            let mut c = json!({"op": op, "accepted": verdict.is_ok(), "client": info});
            if let Err(why) = &verdict {
                c["reason"] = why.clone().into();
            }
            self.control_record(c, req.get("seq").and_then(Value::as_u64));
        }
        if let Err(why) = &verdict {
            log_line(
                &self.home,
                &format!("boshqaruv buyrug'i rad etildi ({op}): {why}"),
            );
        }
        verdict
    }

    /// `control` yozuvi (spec §3.3): boshqaruv urinishlari va config / hook o'zgarishlari.
    fn control_record(&mut self, control: Value, reference: Option<u64>) {
        let mut body = Map::new();
        body.insert("control".into(), control);
        if let Some(r) = reference {
            body.insert("ref".into(), r.into());
        }
        if let Err(e) = self.log.append(&now_ts(), "tamga", "control", body) {
            log_line(&self.home, &format!("control yozuvi yozilmadi: {e}"));
        }
    }

    fn status(&self) -> Value {
        json!({
            "ok": true,
            "log": self.log.log_id(),
            "records": self.log.len(),
            "checkpointed": self.log.len() - self.log.uncheckpointed(),
            "key": self.key_id,
            "anchor": self.anchor_id,
            "home": self.home.root().display().to_string(),
            "pid": std::process::id(),
            "mode": if self.config.mode == Mode::Strict { "strict" } else { "dev" },
            "config": self.config.to_json(),
            "policies": self.policy.sources,
            "policy_count": self.policy.policy_count(),
            "policy_error": self.policy_error,
            "tainted_sessions": self.taints.values().filter(|t| t.secret_read).count(),
            "pending": self.pending.len(),
            "sensor": self.sensor.as_ref().map(|s| json!({
                "roots": s.roots(),
                "watched_dirs": s.watched_dirs().iter().map(|d| d.display().to_string()).collect::<Vec<_>>(),
                "poll_ms": tamga_sensor::POLL.as_millis() as u64,
                "blind_spots": tamga_sensor::BLIND_SPOTS,
            })),
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
    /// Pipe'dan kelgan hook: xizmat rejimida yozuvdagi `actor.user` — mijozning SID'i.
    fn hook_from(&mut self, req: &Value, sid: Option<&str>) -> Outcome {
        self.client_sid = if self.home.is_service() {
            sid.map(str::to_owned)
        } else {
            None
        };
        let out = self.hook(req, None);
        self.client_sid = None;
        out
    }

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
        if let Some(sid) = &self.client_sid
            && let Some(a) = body.get_mut("actor").and_then(Value::as_object_mut)
        {
            a.insert("user".into(), sid.clone().into());
        }
        let tool = input
            .get("tool_name")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned();
        let tool_input = input.get("tool_input").cloned().unwrap_or(Value::Null);
        let cwd = input.get("cwd").and_then(Value::as_str).unwrap_or_default();
        let (mut verdict, mut reason, mut policy) = (Verdict::Allow, String::new(), String::new());
        let mut flags = Vec::new();
        let mut call_path = String::new();
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
                    call_path = facts.path.clone();
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
        // "Qildi" uchun: agent ildizini (hook/proxy PID'idan) va ishchi papkani kuzatuvga olish.
        if spooled.is_none() {
            self.track_session(&session, req.get("pid").and_then(Value::as_u64), cwd);
        }
        let post_ref = (ev.event == "tool.post")
            .then(|| {
                ev.tool_use_id
                    .as_ref()
                    .and_then(|id| self.pre_seqs.get(id).copied())
            })
            .flatten();
        match self.log.append(&ts, &ev.session, ev.event, body) {
            Ok(seq) => {
                if ev.event == "tool.pre" && verdict != Verdict::Deny && spooled.is_none() {
                    self.corr.begin(
                        &session,
                        observe::Call {
                            seq,
                            tool: tool.clone(),
                            flags: flags.iter().map(|f| (*f).to_owned()).collect(),
                            path: call_path.clone(),
                            started: Instant::now(),
                            ended: None,
                        },
                    );
                }
                if let Some(pre) = post_ref {
                    self.corr.end(&session, pre, Instant::now());
                }
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
                    // H-2: sessiya tugaganda taint'ni O'CHIRMAYMIZ. Aks holda autentifikatsiyasiz
                    // `SessionEnd` (yoki `claude --resume` har qadamda yuboradigan) o'qilgan sir
                    // himoyasini tozalab, keyingi yuborishni ruxsat etardi. Taint diskda TTL (7 kun)
                    // yoki aniq `tamga shred <sessiya>` gacha qoladi. Faqat sensor va bir martalik
                    // "shu sessiyada doim ruxsat" grantlari tozalanadi.
                    if left == 0 {
                        self.untrack_session(&session);
                        self.session_allow.retain(|(s, _)| *s != session);
                    }
                    self.persist(&session);
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
            // Eski kalit almashtirish yozuvini qamradi — endi yangi kalit faol (spec §7.5).
            if self
                .pending_rotation
                .as_ref()
                .is_some_and(|(seq, _)| size > seq)
            {
                let (_, next) = self.pending_rotation.take().expect("tekshirildi");
                self.activate(next);
            }
        }
        r
    }

    /// Yangi kalitni xotirada darhol faollashtiradi; omborga ko'chirish xato bersa ham —
    /// keyingi checkpoint'lar baribir yangi kalit bilan bo'lishi shart. Ombor qayta ishga
    /// tushishda tiklanadi (`open_state`).
    fn activate(&mut self, next: SigningKeys) {
        let from = std::mem::replace(&mut self.key_id, next.public().key_id());
        self.keys = next;
        match keystore::promote_next(self.store.as_ref()) {
            Ok(()) => log_line(
                &self.home,
                &format!("kalit almashtirildi: {from} -> {}", self.key_id),
            ),
            Err(e) => log_line(
                &self.home,
                &format!(
                    "kalit {} faol, lekin omborga ko'chirilmadi: {e}",
                    self.key_id
                ),
            ),
        }
    }

    /// `tamga key rotate`: yozuv → eski kalit bilan checkpoint → yangi kalit (spec §7.5).
    fn rotate(&mut self, req: &Value) -> Value {
        let reason = req
            .get("reason")
            .and_then(Value::as_str)
            .unwrap_or("scheduled");
        if !rotation::REASONS.contains(&reason) {
            return json!({"ok": false, "error": format!("sabab {} dan biri bo'lsin", rotation::REASONS.join(", "))});
        }
        if self.pending_rotation.is_some() {
            return json!({"ok": false, "error": "oldingi almashtirish hali tasdiqlanmagan"});
        }
        let next = match keystore::stage_next(self.store.as_ref()) {
            Ok(k) => k,
            Err(e) => return json!({"ok": false, "error": e.to_string()}),
        };
        let (from, to, seq) = (self.key_id.clone(), next.public().key_id(), self.log.len());
        let rnd: [u8; 32] = random();
        let body = rotation::body(
            self.log.log_id(),
            seq,
            &self.keys.public(),
            &next,
            reason,
            Some(&rnd),
        );
        if let Err(e) = self.log.append(&now_ts(), "tamga", rotation::EVENT, body) {
            let _ = keystore::discard_next(self.store.as_ref());
            return json!({"ok": false, "error": e.to_string()});
        }
        log_line(
            &self.home,
            &format!("kalit almashtirish #{seq} ({reason}): {from} -> {to}"),
        );
        self.pending_rotation = Some((seq, next));
        match self.checkpoint() {
            Ok(_) if self.pending_rotation.is_none() => {
                json!({"ok": true, "seq": seq, "from": from, "to": to, "reason": reason})
            }
            Ok(_) => {
                json!({"ok": false, "error": "checkpoint yozilmadi — keyingisida yakunlanadi"})
            }
            Err(e) => {
                json!({"ok": false, "error": format!("yozuv #{seq} bor, checkpoint xatosi: {e} — keyingisida yakunlanadi")})
            }
        }
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

    /// Sessiyani OS kuzatuviga oladi: agent ildizi (bir marta) va ishchi papka.
    fn track_session(&mut self, session: &str, client_pid: Option<u64>, cwd: &str) {
        let Some(sensor) = self.sensor.clone() else {
            return;
        };
        let ctx = self.corr.ctx(session);
        ctx.last_seen = Some(Instant::now());
        if ctx.root.is_none()
            && let Some(pid) = client_pid.and_then(|p| u32::try_from(p).ok())
            && let Some(root) = sensor.watch_client(pid)
        {
            ctx.root = Some(root);
            log_line(
                &self.home,
                &format!("sensor: sessiya {session} - agent ildizi PID {root}"),
            );
        }
        if !cwd.is_empty() && ctx.cwd.is_empty() {
            ctx.cwd = cwd.to_owned();
            sensor.watch_dir(std::path::Path::new(cwd), true);
        }
    }

    fn untrack_session(&mut self, session: &str) {
        if let Some(ctx) = self.corr.sessions.remove(session)
            && let (Some(root), Some(sensor)) = (ctx.root, &self.sensor)
            && !self.corr.sessions.values().any(|c| c.root == Some(root))
        {
            sensor.unwatch_root(root);
        }
    }

    /// Sensor kuzatuvini sessiyaga bog'lab `os.observed` sifatida yozadi.
    fn observe(&mut self, obs: Observation) {
        let now = Instant::now();
        if let Observation::File { path, .. } = &obs {
            // Bitta yozish odatda create + modify beradi: yo'l bo'yicha 2 s ichida bitta yozuv.
            let key = (path.display().to_string(), "any");
            if self
                .file_dedupe
                .get(&key)
                .is_some_and(|t| now.duration_since(*t) < Duration::from_secs(2))
            {
                return;
            }
            self.file_dedupe.insert(key, now);
        }
        let Some(f) = self.corr.classify(&obs, now, self.home.root()) else {
            return;
        };
        if let Observation::Process { image, .. } = &obs
            && observe::is_plumbing(image, f.declared)
        {
            return;
        }
        let mut os = json!({"declared": f.declared, "severity": f.severity});
        let mut body = Map::new();
        match &obs {
            Observation::Process {
                pid,
                ppid,
                image,
                cmd,
                ..
            } => {
                os["kind"] = "process".into();
                os["pid"] = (*pid).into();
                os["ppid"] = (*ppid).into();
                os["image"] = image.clone().into();
                // Buyruq satrida sir bo'lishi mumkin - jurnalga faqat tuzlangan digest.
                if !cmd.is_empty()
                    && let Ok(r) = self.vault.put(&f.session, cmd.as_bytes())
                {
                    body.insert("result".into(), r);
                }
            }
            Observation::Connection {
                pid, image, remote, ..
            } => {
                os["kind"] = "network".into();
                os["pid"] = (*pid).into();
                os["image"] = image.clone().into();
                os["remote"] = remote.clone().into();
            }
            Observation::File { path, op } => {
                os["kind"] = "file".into();
                os["path"] = path.display().to_string().into();
                os["op"] = (*op).into();
            }
        }
        if let Some(m) = f.mismatch {
            os["mismatch"] = m.into();
        }
        if let Some(r) = f.ref_seq {
            body.insert("ref".into(), r.into());
        }
        body.insert("ext".into(), json!({"dev.tamga.os": os}));
        match self.log.append(&now_ts(), &f.session, "os.observed", body) {
            Ok(seq) if f.severity == "warn" => {
                log_line(
                    &self.home,
                    &format!("os.observed #{seq}: {}", f.mismatch.unwrap_or("")),
                );
            }
            Ok(_) => {}
            Err(e) => log_line(&self.home, &format!("os.observed yozilmadi: {e}")),
        }
    }

    fn tick(&mut self) {
        let now = Instant::now();
        self.corr.gc(now);
        self.file_dedupe
            .retain(|_, t| now.duration_since(*t) < Duration::from_secs(10));
        // Config jonli: Studio yoki foydalanuvchi o'zgartirsa, qayta ishga tushirish shart emas.
        // K2: har o'zgarish jurnalga yoziladi (kim o'zgartirganini fayl aytmaydi, lekin iz qoladi).
        self.config = self.home.config();
        let before = std::mem::replace(&mut self.last_config, self.config.to_json());
        let changes = control::config_diff(&before, &self.last_config);
        if !changes.is_empty() {
            log_line(
                &self.home,
                &format!("config o'zgardi: {}", Value::Object(changes.clone())),
            );
            self.control_record(
                json!({"op": "config", "accepted": true, "source": "config.json", "changes": changes}),
                None,
            );
        }
        if self.hooks_checked.elapsed() >= Duration::from_secs(15) {
            self.hooks_checked = now;
            let current = tamga_store::integrate::target(&["--user"])
                .ok()
                .and_then(|p| tamga_store::integrate::installed(&p).ok());
            if let (Some(prev), Some(cur)) = (self.hooks_installed, current)
                && prev != cur
            {
                log_line(
                    &self.home,
                    &format!("Claude Code hook'lari (foydalanuvchi): {prev} -> {cur}"),
                );
                self.control_record(
                    json!({"op": "integration", "accepted": true, "target": "claude-code-user", "installed": cur}),
                    None,
                );
            }
            if current.is_some() {
                self.hooks_installed = current;
            }
        }
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
            // M-4: spool papkasiga foydalanuvchi yoza oladi — haddan katta faylni o'qimaymiz.
            if std::fs::metadata(&path).is_ok_and(|m| m.len() > MAX_MSG) {
                let _ = std::fs::rename(&path, path.with_extension("bad"));
                continue;
            }
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

fn open_state(
    home: Home,
) -> Result<(State, Option<std::sync::mpsc::Receiver<Observation>>), String> {
    home.ensure().map_err(|e| e.to_string())?;
    let config = home.config();
    let store = secrets::default_store(&home).map_err(|e| e.to_string())?;
    let (mut keys, created) =
        keystore::load_or_create(store.as_ref(), &home).map_err(|e| e.to_string())?;
    let anchor_id = keystore::anchor(&home).map_err(|e| e.to_string())?.key_id();
    let master = keystore::vault_master(store.as_ref()).map_err(|e| e.to_string())?;
    let log_id = default_log_id();
    let (log, report) = LogFile::open(
        &home.log_path(&log_id),
        &home.checkpoint_path(&log_id),
        &log_id,
        config.witness_dir.clone(),
    )
    .map_err(|e| e.to_string())?;
    // M-3: ishga tushishda mavjud checkpoint'larni langar kalit bilan to'liq tekshiramiz. Jurnal
    // qisqartirilgan yoki checkpoint'dan keyin qayta yozilgan bo'lsa, buzilgan zanjirga yangi yozuv
    // qo'shishdan oldin aniq xato bilan to'xtaymiz (verify_log `open` da allaqachon bajarilgan).
    if log.checkpointed() > 0 {
        let anchor = keystore::anchor(&home).map_err(|e| e.to_string())?;
        let log_text =
            std::fs::read_to_string(home.log_path(&log_id)).map_err(|e| e.to_string())?;
        let ckpt_text = std::fs::read_to_string(home.checkpoint_path(&log_id)).unwrap_or_default();
        if let Err(e) = tamga_core::checkpoint::verify_all(&log_text, &ckpt_text, &anchor) {
            log_line(
                &home,
                &format!("DIQQAT: jurnal checkpoint tekshiruvidan o'tmadi: {e}"),
            );
            return Err(format!(
                "jurnal buzilgan ({e}) — yozishdan to'xtatildi; to'g'ri nusxani tiklang yoki guvoh bilan solishtiring"
            ));
        }
    }
    // Kalit almashtirish yiqilish bilan uzilgan bo'lsa — davom ettiriladi yoki bekor qilinadi.
    let checkpointed = log.checkpointed();
    let mut pending_rotation = None;
    if let Some(next) = keystore::staged_next(store.as_ref()).map_err(|e| e.to_string())? {
        let next_id = next.public().key_id();
        match report.rotations.iter().rev().find(|(_, to)| *to == next_id) {
            Some(&(seq, _)) if checkpointed > seq => {
                keystore::promote_next(store.as_ref()).map_err(|e| e.to_string())?;
                keys = next;
                log_line(
                    &home,
                    &format!("uzilgan almashtirish #{seq} yakunlandi: kalit {next_id}"),
                );
            }
            Some(&(seq, _)) => {
                log_line(
                    &home,
                    &format!("almashtirish #{seq} eski kalit checkpoint'ini kutmoqda"),
                );
                pending_rotation = Some((seq, next));
            }
            None => {
                keystore::discard_next(store.as_ref()).map_err(|e| e.to_string())?;
                log_line(&home, "jurnalga yozilmagan almashtirish bekor qilindi");
            }
        }
    }
    // Ombordagi kalit jurnal kutgan faol kalit bo'lishi shart, aks holda checkpoint'lar tekshiruvdan o'tmaydi.
    let expected = report
        .rotations
        .iter()
        .rfind(|(seq, _)| *seq < checkpointed)
        .map_or(anchor_id.clone(), |(_, k)| k.clone());
    let key_id = keys.public().key_id();
    if key_id != expected {
        return Err(format!(
            "ombordagi imzo kaliti {key_id} jurnaldagi faol kalit {expected} emas — to'g'ri zaxirani `tamga key restore` bilan tiklang"
        ));
    }
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
    // OS sensori (admin'siz). `TAMGA_SENSOR=0` - o'chirish.
    let (sensor, observations) = if std::env::var("TAMGA_SENSOR").as_deref() == Ok("0") {
        (None, None)
    } else {
        let (s, rx) = Sensor::start();
        (Some(s), Some(rx))
    };
    let profile = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_default()
        .replace('\\', "/");
    if let Some(s) = &sensor {
        for d in observe::SENSITIVE {
            s.watch_dir(&std::path::Path::new(&profile).join(d), true);
        }
    }
    let last_config = config.to_json();
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
        sensor,
        corr: observe::Correlator::new(profile),
        file_dedupe: HashMap::new(),
        stopped: false,
        client_sid: None,
        store,
        anchor_id,
        pending_rotation,
        own_dir: control::own_dir(),
        deny_limit: control::DenyLimiter::new(),
        last_config,
        hooks_installed: None,
        hooks_checked: Instant::now() - Duration::from_secs(60),
    };
    state.restore();
    if state.pending_rotation.is_some() {
        let _ = state.checkpoint();
    }
    Ok((state, observations))
}

/// Yagona yozuvchi: barcha so'rovlar ketma-ket bajariladi, zanjir tartibi kafolatlanadi.
async fn writer(
    mut state: State,
    mut rx: mpsc::Receiver<Job>,
    mut obs: mpsc::UnboundedReceiver<Observation>,
    stopped: oneshot::Sender<()>,
) {
    let mut ticker = tokio::time::interval(Duration::from_secs(1));
    loop {
        tokio::select! {
            job = rx.recv() => match job {
                // `tamga stop` (o'rnatuvchi/o'chiruvchi ham chaqiradi): javob yakuniy holat yozilgandan keyin.
                Some((req, client, reply)) if req.get("op").and_then(Value::as_str) == Some("shutdown") => {
                    match state.gate("shutdown", &req, &client) {
                        Ok(()) => {
                            let size = state.shutdown("tamga stop");
                            let _ = reply.send(json!({"ok": true, "pid": std::process::id(), "checkpoint": size}));
                            break;
                        }
                        Err(why) => {
                            let _ = reply.send(json!({"ok": false, "denied": true, "error": why}));
                        }
                    }
                }
                Some((req, client, reply)) => state.handle(&req, client, reply),
                None => break,
            },
            Some(o) = obs.recv() => state.observe(o),
            _ = ticker.tick() => state.tick(),
        }
    }
    state.shutdown("kanal yopildi");
    let _ = stopped.send(());
}

impl State {
    /// To'xtashda kutilayotgan so'rovlar rad etiladi (fail-closed) va oxirgi checkpoint yoziladi.
    /// Ikkinchi chaqiruv zararsiz: navbat bo'sh, yangi yozuv yo'q.
    fn shutdown(&mut self, why: &str) -> Option<u64> {
        if self.stopped {
            return None;
        }
        self.stopped = true;
        let waiting: Vec<u64> = self.pending.keys().copied().collect();
        for seq in waiting {
            if let Some(p) = self.pending.remove(&seq) {
                self.resolve(seq, p, Verdict::Deny, "default", "daemon to'xtadi");
            }
        }
        let size = self.checkpoint().ok().flatten();
        log_line(&self.home, &format!("to'xtadi ({why})"));
        size
    }
}

/// Himoyalangan rejimda pipe xavfsizlik deskriptori (oddiy rejimda — yo'q, standart DACL).
#[cfg(windows)]
type Secure = Option<std::sync::Arc<tamga_win::service::SecurityDescriptor>>;
#[cfg(not(windows))]
type Secure = Option<()>;

/// Windows xizmati nomi (o'rnatuvchi shu nom bilan yaratadi).
const SERVICE_NAME: &str = "tamgad";
/// Belgi faylida pipe ko'rsatilmagan bo'lsa.
const DEFAULT_SERVICE_PIPE: &str = r"\\.\pipe\tamga-service";

#[cfg(windows)]
async fn serve(pipe: String, tx: mpsc::Sender<Job>, secure: Secure) -> std::io::Result<()> {
    use tokio::io::{AsyncBufReadExt as _, AsyncReadExt as _, AsyncWriteExt as _, BufReader};
    use tokio::net::windows::named_pipe::{NamedPipeServer, ServerOptions};

    let create = |first: bool| -> std::io::Result<NamedPipeServer> {
        let mut o = ServerOptions::new();
        o.first_pipe_instance(first).reject_remote_clients(true);
        match &secure {
            Some(sd) => tamga_win::service::create_pipe_server(&o, &pipe, sd),
            None => o.create(&pipe),
        }
    };
    // Birinchi nusxa: boshqa daemon (yoki nomni egallab olgan jarayon) bo'lsa — xato.
    let mut server = create(true)?;
    let service = secure.is_some();
    loop {
        server.connect().await?;
        let conn = server;
        // K1: kim ulanganini bilish uchun (boshqaruv buyruqlari shu PID bo'yicha tekshiriladi).
        let pid = tamga_win::pipe_client_pid(&conn);
        server = create(false)?;
        let tx = tx.clone();
        tokio::spawn(async move {
            // M-4: ulanish 8 MiB bilan cheklanadi. Pipe ajratilmaydi (split) — himoyalangan rejimda
            // impersonatsiya uchun server handle'i kerak.
            let mut reader = BufReader::new(conn.take(MAX_MSG));
            let mut client = ClientInfo {
                pid,
                ..ClientInfo::default()
            };
            let mut identified = false;
            let mut line = String::new();
            loop {
                line.clear();
                match reader.read_line(&mut line).await {
                    Ok(0) | Err(_) => break,
                    Ok(_) => {}
                }
                // Himoyalangan rejim: mijoz identifikatori birinchi xabardan keyin (impersonatsiya talabi).
                if service && !identified {
                    identified = true;
                    if let Some(id) =
                        tamga_win::service::pipe_client_identity(reader.get_ref().get_ref())
                    {
                        client.sid = Some(id.sid);
                        client.elevated = id.elevated;
                    }
                }
                let resp = match serde_json::from_str::<Value>(line.trim_end()) {
                    Ok(req) => {
                        let (reply_tx, reply_rx) = oneshot::channel();
                        if tx.send((req, client.clone(), reply_tx)).await.is_err() {
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
                if reader
                    .get_mut()
                    .get_mut()
                    .write_all(out.as_bytes())
                    .await
                    .is_err()
                {
                    break;
                }
            }
        });
    }
}

#[cfg(not(windows))]
async fn serve(_pipe: String, _tx: mpsc::Sender<Job>, _secure: Secure) -> std::io::Result<()> {
    Err(std::io::Error::other(
        "hozircha faqat Windows named pipe qo'llab-quvvatlanadi",
    ))
}

/// Daemon tanasi (oddiy va xizmat rejimi uchun umumiy). `stop` — tashqi to'xtatish signali
/// (xizmat rejimida SCM). Qaytadi: chiqish kodi.
fn run(
    home: Home,
    pipe: String,
    secure: Secure,
    stop: impl std::future::Future<Output = ()>,
) -> u8 {
    let (state, observations) = match open_state(home.clone()) {
        Ok(s) => s,
        Err(e) => {
            log_line(&home, &format!("ishga tushmadi: {e}"));
            eprintln!("tamgad: {e}");
            return 1;
        }
    };
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .expect("tokio");
    rt.block_on(async move {
        let (tx, rx) = mpsc::channel::<Job>(256);
        // Sensor oqimi (std) -> yozuvchi (tokio): oddiy ko'prik oqimi.
        let (obs_tx, obs_rx) = mpsc::unbounded_channel();
        if let Some(observations) = observations {
            std::thread::spawn(move || {
                while let Ok(o) = observations.recv() {
                    if obs_tx.send(o).is_err() {
                        break;
                    }
                }
            });
        }
        let (stopped_tx, stopped_rx) = oneshot::channel();
        let writer = tokio::spawn(writer(state, rx, obs_rx, stopped_tx));
        let result = tokio::select! {
            r = serve(pipe.clone(), tx, secure) => r,
            _ = tokio::signal::ctrl_c() => Ok(()),
            () = stop => Ok(()),
            _ = stopped_rx => {
                // `shutdown` javobi ulanish vazifasi orqali pipe'ga yozib ulgursin.
                tokio::time::sleep(Duration::from_millis(200)).await;
                Ok(())
            }
        };
        // `tx` tushirildi — yozuvchi kutilayotganlarni rad etib, oxirgi checkpoint'ni yozib to'xtaydi.
        let _ = writer.await;
        match result {
            Ok(()) => 0,
            Err(e)
                if e.kind() == std::io::ErrorKind::PermissionDenied
                    || e.raw_os_error() == Some(231) =>
            {
                log_line(&home, &format!("{pipe} band — boshqa tamgad ishlayapti"));
                0
            }
            Err(e) => {
                log_line(&home, &format!("pipe xatosi: {e}"));
                1
            }
        }
    })
}

/// Himoyalangan rejim sozlamalari: `%ProgramData%\TAMGA`, belgidagi pipe, himoyalangan deskriptor.
#[cfg(windows)]
fn service_setup() -> Result<(Home, String, Secure), String> {
    use tamga_store::home::{Deployment, deployment_at, service_root};
    let root = service_root().ok_or("%ProgramData% aniqlanmadi")?;
    let pipe = match deployment_at(&root) {
        Deployment::Service(s) => s.pipe,
        Deployment::PerUser => DEFAULT_SERVICE_PIPE.to_owned(),
    };
    let sd =
        tamga_win::service::SecurityDescriptor::from_sddl(tamga_win::service::SERVICE_PIPE_SDDL)
            .map_err(|e| format!("pipe deskriptori: {e}"))?;
    Ok((Home::service(root), pipe, Some(std::sync::Arc::new(sd))))
}

/// SCM chaqiradigan xizmat tanasi.
#[cfg(windows)]
fn service_body(stop: std::sync::mpsc::Receiver<()>) -> u32 {
    let (home, pipe, secure) = match service_setup() {
        Ok(v) => v,
        Err(_) => return 2,
    };
    let (tx, rx) = oneshot::channel::<()>();
    std::thread::spawn(move || {
        let _ = stop.recv();
        let _ = tx.send(());
    });
    u32::from(run(home, pipe, secure, async move {
        let _ = rx.await;
    }))
}

fn main() -> std::process::ExitCode {
    let arg = std::env::args().nth(1);
    #[cfg(windows)]
    match arg.as_deref() {
        // SCM tomonidan: `sc create tamgad binPath= "...\tamgad.exe --service"`.
        Some("--service") => {
            return match tamga_win::service::run_as_service(SERVICE_NAME, service_body) {
                Ok(()) => std::process::ExitCode::SUCCESS,
                Err(e) => {
                    eprintln!("tamgad --service: SCM orqali ishga tushirilmagan ({e})");
                    std::process::ExitCode::from(2)
                }
            };
        }
        // Himoyalangan rejimni oldingi planda sinash (administrator konsoli, Ctrl+C bilan to'xtaydi).
        Some("--service-console") => {
            return match service_setup() {
                Ok((home, pipe, secure)) => {
                    std::process::ExitCode::from(run(home, pipe, secure, std::future::pending()))
                }
                Err(e) => {
                    eprintln!("tamgad: {e}");
                    std::process::ExitCode::from(2)
                }
            };
        }
        _ => {}
    }
    let _ = arg;
    std::process::ExitCode::from(run(
        Home::from_env(),
        pipe_name(),
        None,
        std::future::pending(),
    ))
}
