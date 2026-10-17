//! JSON-RPC relay: mijoz ⇄ server, `tools/call` uchun TAMGA qarori.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ExitCode};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use serde_json::{Value, json};
use tamga_store::home::{Mode, pipe_name};
use tamga_store::{Home, client, spool};

pub struct Config {
    pub name: String,
    pub session: String,
    pub agent: String,
    pub cwd: String,
}

impl Config {
    pub fn new(name: String, session: String) -> Self {
        Self {
            agent: format!("mcp-proxy:{name}"),
            cwd: std::env::current_dir()
                .map(|p| p.display().to_string())
                .unwrap_or_default(),
            name,
            session,
        }
    }
}

/// Mijoz xabari bilan nima qilinadi.
#[derive(Debug, PartialEq)]
pub enum Intercept {
    /// `tools/call`: (JSON-RPC id, tool nomi, argumentlar).
    ToolCall(Value, String, Value),
    /// Boshqa har qanday xabar — o'zgarishsiz uzatiladi.
    Forward,
}

pub fn classify(line: &str) -> Intercept {
    let Ok(v) = serde_json::from_str::<Value>(line) else {
        return Intercept::Forward;
    };
    match (v.get("method").and_then(Value::as_str), v.get("id")) {
        (Some("tools/call"), Some(id)) if !id.is_null() => {
            let params = v.get("params").cloned().unwrap_or(Value::Null);
            let tool = params
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or("?")
                .to_owned();
            let args = params
                .get("arguments")
                .cloned()
                .unwrap_or_else(|| json!({}));
            Intercept::ToolCall(id.clone(), tool, args)
        }
        _ => Intercept::Forward,
    }
}

/// MCP spetsifikatsiyasi bo'yicha tool xatosi: model sababni ko'radi va o'zini to'g'rilay oladi.
pub fn blocked_response(id: &Value, text: &str) -> String {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": {"content": [{"type": "text", "text": text}], "isError": true}
    })
    .to_string()
}

/// Server xabari biror kutilayotgan `tools/call` ning javobimi: (id kaliti, natija).
pub fn response_of(line: &str) -> Option<(String, Value)> {
    let v: Value = serde_json::from_str(line).ok()?;
    if v.get("method").is_some() {
        return None; // server so'rovi yoki bildirishnomasi
    }
    let id = v.get("id")?.to_string();
    let payload = v
        .get("result")
        .cloned()
        .or_else(|| v.get("error").map(|e| json!({"error": e})))?;
    Some((id, payload))
}

struct Ctx {
    cfg: Config,
    out: Mutex<std::io::Stdout>,
    calls: Mutex<HashMap<String, (String, Value)>>,
    daemon_exe: Option<std::path::PathBuf>,
}

impl Ctx {
    fn write_client(&self, line: &str) {
        let mut out = self.out.lock().expect("stdout");
        let _ = out.write_all(line.as_bytes());
        let _ = out.write_all(b"\n");
        let _ = out.flush();
    }

    /// Hook shaklidagi hodisa daemon'ga. Javob: `Ok(response)` yoki daemon'ga ulanmadi.
    fn event(&self, hook: &str, extra: Value) -> Result<Value, String> {
        let mut input = json!({
            "session_id": self.cfg.session,
            "hook_event_name": hook,
            "cwd": self.cfg.cwd,
        });
        if let (Some(o), Value::Object(e)) = (input.as_object_mut(), extra) {
            o.extend(e);
        }
        let req = json!({"op": "hook", "agent": self.cfg.agent, "input": input});
        client::connect(
            &pipe_name(),
            self.daemon_exe.as_deref(),
            Duration::from_millis(1500),
        )
        .and_then(|mut p| client::request(&mut p, &req))
        .map_err(|e| e.to_string())
        .and_then(|r| {
            if r.get("ok") == Some(&Value::Bool(true)) {
                Ok(r)
            } else {
                Err(r
                    .get("error")
                    .and_then(Value::as_str)
                    .unwrap_or("daemon xatosi")
                    .to_owned())
            }
        })
        .inspect_err(|_| {
            // Hodisa yo'qolmasin: spool, daemon keyin oladi.
            let home = Home::from_env();
            let _ = spool::write(&home.spool(), &self.cfg.agent, &input, &Value::Null);
        })
    }

    /// `tools/call`: `Some(xabar)` — bloklandi (mijozga shu javob), `None` — serverga uzatish.
    fn decide(&self, id: &Value, tool: &str, args: &Value) -> Option<String> {
        let full = format!("mcp:{}/{tool}", self.cfg.name);
        let resp = self.event(
            "PreToolUse",
            json!({"tool_name": full, "tool_input": args, "tool_use_id": id.to_string()}),
        );
        match resp {
            Ok(r) => {
                let verdict = r.get("verdict").and_then(Value::as_str).unwrap_or("allow");
                let reason = r
                    .get("reason")
                    .and_then(Value::as_str)
                    .unwrap_or("siyosat qarori");
                match verdict {
                    "deny" => Some(format!("TAMGA bu chaqiruvni blokladi: {reason}")),
                    // MCP'da agent ruxsat oynasi yo'q: inson qarori uchun Studio yo'nalishi kerak.
                    "ask" => Some(format!(
                        "TAMGA: bu chaqiruv inson tasdig'ini talab qiladi ({reason}). TAMGA Studio'da «ask → Studio» yoqilsa, qaror u yerda so'raladi."
                    )),
                    _ => None,
                }
            }
            Err(e) => {
                eprintln!("tamga-mcp-proxy: daemon'ga ulanmadi: {e}");
                (Home::from_env().config().mode == Mode::Strict).then(|| {
                    "TAMGA: daemon ishlamayapti (strict rejim), chaqiruv bloklandi".to_owned()
                })
            }
        }
    }
}

pub fn run(cfg: Config, mut child: Child) -> ExitCode {
    let daemon_exe = std::env::current_exe()
        .ok()
        .and_then(|p| {
            p.parent().map(|d| {
                d.join(if cfg!(windows) {
                    "tamgad.exe"
                } else {
                    "tamgad"
                })
            })
        })
        .filter(|p| p.exists());
    let ctx = Arc::new(Ctx {
        cfg,
        out: Mutex::new(std::io::stdout()),
        calls: Mutex::new(HashMap::new()),
        daemon_exe,
    });
    let _ = ctx.event("SessionStart", json!({"source": "mcp-proxy"}));

    let mut server_in = child.stdin.take().expect("stdin piped");
    let server_out = child.stdout.take().expect("stdout piped");

    // Server → mijoz: javoblar o'zgarishsiz, kutilgan `tools/call` javoblari `tool.post` bo'lib yoziladi.
    // XAVFSIZLIK TARTIBI: `tool.post` (taint o'rganish) daemon'ga javob mijozga uzatilishidan OLDIN
    // yetkaziladi. Agent sirni faqat shu javobdan bilishi mumkin, demak u sirni keyingi so'rovga
    // qo'ygan paytda taint allaqachon daemon'da bo'ladi (sababiyat kafolati).
    let back = {
        let ctx = Arc::clone(&ctx);
        std::thread::spawn(move || {
            for line in BufReader::new(server_out).lines() {
                let Ok(line) = line else { break };
                if let Some((id, payload)) = response_of(&line) {
                    let call = ctx.calls.lock().expect("calls").remove(&id);
                    if let Some((tool, args)) = call {
                        let _ = ctx.event(
                            "PostToolUse",
                            json!({"tool_name": tool, "tool_input": args, "tool_response": payload, "tool_use_id": id}),
                        );
                    }
                }
                ctx.write_client(&line);
            }
        })
    };

    // Mijoz → server.
    for line in std::io::stdin().lock().lines() {
        let Ok(line) = line else { break };
        if let Intercept::ToolCall(id, tool, args) = classify(&line) {
            if let Some(text) = ctx.decide(&id, &tool, &args) {
                ctx.write_client(&blocked_response(&id, &text));
                continue;
            }
            let full = format!("mcp:{}/{tool}", ctx.cfg.name);
            ctx.calls
                .lock()
                .expect("calls")
                .insert(id.to_string(), (full, args));
        }
        if server_in
            .write_all(line.as_bytes())
            .and_then(|()| server_in.write_all(b"\n"))
            .and_then(|()| server_in.flush())
            .is_err()
        {
            break;
        }
    }
    drop(server_in); // mijoz yopildi — server ham yopilsin
    let status = child.wait();
    let _ = back.join();
    let _ = ctx.event("SessionEnd", json!({"reason": "mcp-proxy-exit"}));
    match status.ok().and_then(|s| s.code()) {
        Some(0) | None => ExitCode::SUCCESS,
        Some(c) => ExitCode::from(u8::try_from(c).unwrap_or(1)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_tool_calls_are_intercepted() {
        let call = r#"{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"read_text_file","arguments":{"path":".env"}}}"#;
        assert_eq!(
            classify(call),
            Intercept::ToolCall(json!(7), "read_text_file".into(), json!({"path": ".env"}))
        );
        let str_id = r#"{"jsonrpc":"2.0","id":"a-1","method":"tools/call","params":{"name":"x"}}"#;
        assert_eq!(
            classify(str_id),
            Intercept::ToolCall(json!("a-1"), "x".into(), json!({}))
        );
        for other in [
            r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#,
            r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/list"}"#,
            "buzilgan json",
        ] {
            assert_eq!(classify(other), Intercept::Forward, "{other}");
        }
    }

    #[test]
    fn blocked_response_is_mcp_tool_error_with_same_id() {
        let r: Value =
            serde_json::from_str(&blocked_response(&json!("a-1"), "TAMGA: yo'q")).unwrap();
        assert_eq!(r["id"], "a-1");
        assert_eq!(r["result"]["isError"], true);
        assert_eq!(r["result"]["content"][0]["text"], "TAMGA: yo'q");
    }

    #[test]
    fn server_responses_are_matched_by_id() {
        let ok =
            r#"{"jsonrpc":"2.0","id":7,"result":{"content":[{"type":"text","text":"API_KEY=x"}]}}"#;
        assert_eq!(response_of(ok).unwrap().0, "7");
        let err = r#"{"jsonrpc":"2.0","id":"a-1","error":{"code":-32000,"message":"no"}}"#;
        let (id, payload) = response_of(err).unwrap();
        assert_eq!(
            (id.as_str(), &payload["error"]["code"]),
            ("\"a-1\"", &json!(-32000))
        );
        assert!(
            response_of(r#"{"jsonrpc":"2.0","id":3,"method":"sampling/createMessage"}"#).is_none(),
            "server so'rovi javob emas"
        );
        assert!(response_of(r#"{"jsonrpc":"2.0","method":"notifications/progress"}"#).is_none());
    }
}
