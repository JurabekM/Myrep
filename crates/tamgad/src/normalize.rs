//! Agent hook'larini TAMGA Record hodisalariga aylantirish.
//!
//! Buyruq matni, prompt va tool natijasi jurnalga yozilmaydi: ular vault'ga tushadi, jurnalda
//! faqat tuzlangan digest qoladi (spec §5).

use std::collections::HashMap;

use serde_json::{Map, Value, json};
use tamga_store::vault::Vault;

/// Jurnalga yoziladigan hodisa.
pub struct Event {
    pub session: String,
    pub event: &'static str,
    pub body: Map<String, Value>,
    /// Bu hodisa uchun TAMGA qarori kerakmi (faqat `tool.pre`).
    pub needs_decision: bool,
    pub tool_use_id: Option<String>,
}

fn s<'a>(v: &'a Value, k: &str) -> Option<&'a str> {
    v.get(k).and_then(Value::as_str)
}

fn actor() -> Value {
    let env = |k: &str| std::env::var(k).unwrap_or_else(|_| "unknown".into());
    json!({"user": env("USERNAME"), "host": env("COMPUTERNAME")})
}

/// JSON qiymatini vault'ga bayt sifatida saqlash (satr bo'lsa — matnning o'zi).
fn stash(vault: &Vault, session: &str, v: &Value) -> Result<Value, String> {
    let bytes = match v {
        Value::String(t) => t.as_bytes().to_vec(),
        other => serde_json::to_vec(other).expect("json"),
    };
    vault.put(session, &bytes).map_err(|e| e.to_string())
}

/// Claude Code hook kirishi (https://docs.claude.com/en/docs/claude-code/hooks).
/// `pre_seqs` — `tool_use_id` → `tool.pre` yozuvining `seq` (`tool.post.ref` uchun).
pub fn claude_code(
    input: &Value,
    vault: &Vault,
    pre_seqs: &HashMap<String, u64>,
) -> Result<Event, String> {
    let session = s(input, "session_id")
        .filter(|x| !x.is_empty())
        .ok_or("session_id yo'q")?
        .to_owned();
    let hook = s(input, "hook_event_name").ok_or("hook_event_name yo'q")?;
    let tool_use_id = s(input, "tool_use_id").map(str::to_owned);
    let mut body = Map::new();
    let mut needs_decision = false;

    let event = match hook {
        "SessionStart" => {
            let mut agent = json!({"kind": "claude-code"});
            if let Some(m) = s(input, "model") {
                agent["model"] = m.into();
            }
            body.insert("agent".into(), agent);
            body.insert("actor".into(), actor());
            if let Some(src) = s(input, "source") {
                body.insert(
                    "ext".into(),
                    json!({"dev.tamga.claude-code": {"source": src}}),
                );
            }
            "session.start"
        }
        "UserPromptSubmit" => {
            let prompt = input
                .get("prompt")
                .cloned()
                .unwrap_or(Value::String(String::new()));
            body.insert("result".into(), stash(vault, &session, &prompt)?);
            "prompt"
        }
        "PreToolUse" => {
            let name = s(input, "tool_name").ok_or("tool_name yo'q")?;
            let tool_input = input.get("tool_input").cloned().unwrap_or(Value::Null);
            body.insert(
                "tool".into(),
                json!({"name": name, "input": stash(vault, &session, &tool_input)?}),
            );
            needs_decision = true;
            "tool.pre"
        }
        "PostToolUse" => {
            let name = s(input, "tool_name").ok_or("tool_name yo'q")?;
            let response = input.get("tool_response").cloned().unwrap_or(Value::Null);
            body.insert("tool".into(), json!({"name": name}));
            body.insert("result".into(), stash(vault, &session, &response)?);
            if let Some(seq) = tool_use_id.as_ref().and_then(|id| pre_seqs.get(id)) {
                body.insert("ref".into(), (*seq).into());
            }
            "tool.post"
        }
        "SessionEnd" => {
            if let Some(r) = s(input, "reason") {
                body.insert(
                    "ext".into(),
                    json!({"dev.tamga.claude-code": {"reason": r}}),
                );
            }
            "session.end"
        }
        other => return Err(format!("qo'llab-quvvatlanmaydigan hook: {other}")),
    };
    Ok(Event {
        session,
        event,
        body,
        needs_decision,
        tool_use_id,
    })
}
