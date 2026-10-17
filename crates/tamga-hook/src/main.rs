//! tamga-hook — Claude Code hook buyrug'i.
//!
//! stdin: Claude Code hook JSON'i. Hodisani `tamgad` ga yuboradi (daemon ishlamasa — uni ishga
//! tushiradi). Faqat `deny` yoki `ask` qarori agentga qaytariladi; `allow` uchun hech narsa
//! chiqarilmaydi, shunda Claude Code'ning o'z ruxsat tizimi o'zgarmay ishlaydi.
//!
//! Daemon'ga ulanib bo'lmasa hodisa spool'ga yoziladi va rejimga qarab: `strict` — `PreToolUse`
//! bloklanadi, `dev` — ruxsat beriladi. Chiqish kodi har doim 0 (2 — Claude Code'da blok degani).

use std::io::Read as _;
use std::time::Duration;

use serde_json::{Value, json};
use tamga_store::home::{Mode, pipe_name};
use tamga_store::{Home, client, spool};

const MAX_INPUT: u64 = 8 << 20;

fn decision_output(event: &str, verdict: &str, reason: &str) -> Option<String> {
    if event != "PreToolUse" || !matches!(verdict, "deny" | "ask") {
        return None;
    }
    Some(
        json!({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": verdict,
                "permissionDecisionReason": format!("TAMGA: {reason}"),
            }
        })
        .to_string(),
    )
}

fn main() {
    let mut raw = String::new();
    if std::io::stdin()
        .take(MAX_INPUT)
        .read_to_string(&mut raw)
        .is_err()
    {
        eprintln!("tamga-hook: stdin o'qilmadi");
        return;
    }
    // Ba'zi chaqiruvchilar (.NET) stdin boshiga UTF-8 BOM qo'shadi.
    let input = match serde_json::from_str::<Value>(raw.trim_start_matches('\u{feff}')) {
        Ok(v) => v,
        Err(e) => {
            // Hodisa yo'qolmasin: xom matn spool'ga tushadi (daemon uni `.bad` deb ajratadi).
            eprintln!("tamga-hook: stdin JSON emas: {e}");
            let home = Home::from_env();
            let _ = spool::write(
                &home.spool(),
                "claude-code",
                &Value::String(raw),
                &Value::Null,
            );
            return;
        }
    };
    let event = input
        .get("hook_event_name")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned();
    let req = json!({"op": "hook", "agent": "claude-code", "input": input});

    let daemon = std::env::current_exe()
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
    let reply = client::connect(&pipe_name(), daemon.as_deref(), Duration::from_millis(1500))
        .and_then(|mut pipe| client::request(&mut pipe, &req));

    match reply {
        Ok(resp) if resp.get("ok") == Some(&Value::Bool(true)) => {
            let verdict = resp
                .get("verdict")
                .and_then(Value::as_str)
                .unwrap_or("allow");
            let reason = resp
                .get("reason")
                .and_then(Value::as_str)
                .unwrap_or("siyosat qarori");
            if let Some(out) = decision_output(&event, verdict, reason) {
                println!("{out}");
            }
        }
        other => {
            let why = match other {
                Ok(resp) => resp
                    .get("error")
                    .and_then(Value::as_str)
                    .unwrap_or("noma'lum")
                    .to_owned(),
                Err(e) => e.to_string(),
            };
            let home = Home::from_env();
            let strict = home.config().mode == Mode::Strict;
            let decision = if strict {
                json!({"verdict": "deny", "by": "default", "reason": "daemon ishlamadi (strict)"})
            } else {
                json!({"verdict": "allow", "by": "default", "reason": "daemon ishlamadi (dev)"})
            };
            let input = req.get("input").cloned().unwrap_or(Value::Null);
            if let Err(e) = spool::write(&home.spool(), "claude-code", &input, &decision) {
                eprintln!("tamga-hook: spool'ga yozilmadi: {e}");
            }
            eprintln!("tamga-hook: {why}");
            if strict
                && let Some(out) = decision_output(
                    &event,
                    "deny",
                    "daemon ishlamayapti (strict rejim), harakat bloklandi",
                )
            {
                println!("{out}");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_pre_tool_deny_or_ask_is_returned() {
        assert!(
            decision_output("PreToolUse", "allow", "x").is_none(),
            "allow agentga qaytarilmaydi"
        );
        assert!(decision_output("PostToolUse", "deny", "x").is_none());
        let out: Value =
            serde_json::from_str(&decision_output("PreToolUse", "deny", "sir").unwrap()).unwrap();
        assert_eq!(out["hookSpecificOutput"]["permissionDecision"], "deny");
        assert_eq!(
            out["hookSpecificOutput"]["permissionDecisionReason"],
            "TAMGA: sir"
        );
    }
}
