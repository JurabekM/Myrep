//! Claude Code `settings.json` ga TAMGA hook'larini qo'shish va olib tashlash.
//!
//! Mavjud sozlamalar saqlanadi: faqat `hooks.<Event>` massivlariga TAMGA yozuvi qo'shiladi.
//! O'zgartirishdan oldin `settings.json.tamga-backup` zaxirasi yoziladi.

use std::path::{Path, PathBuf};

use serde_json::{Map, Value, json};

/// Ro'yxatga olinadigan hook'lar va ularning matcher'i (`None` — matcher'siz hodisa).
const EVENTS: [(&str, Option<&str>); 5] = [
    ("SessionStart", None),
    ("UserPromptSubmit", None),
    ("PreToolUse", Some("*")),
    ("PostToolUse", Some("*")),
    ("SessionEnd", None),
];

const MARKER: &str = "tamga-hook";

pub fn target(rest: &[&str]) -> Result<PathBuf, String> {
    match rest {
        ["--project", dir] => Ok(Path::new(dir).join(".claude").join("settings.json")),
        ["--user"] => {
            let home = std::env::var_os("USERPROFILE")
                .or_else(|| std::env::var_os("HOME"))
                .ok_or("foydalanuvchi papkasi topilmadi")?;
            Ok(PathBuf::from(home).join(".claude").join("settings.json"))
        }
        _ => Err("--project <papka> yoki --user ko'rsating".into()),
    }
}

pub fn backup_path(settings: &Path) -> PathBuf {
    settings.with_extension("json.tamga-backup")
}

fn read(settings: &Path) -> Result<Map<String, Value>, String> {
    match std::fs::read_to_string(settings) {
        Ok(t) => match serde_json::from_str::<Value>(&t) {
            Ok(Value::Object(m)) => Ok(m),
            Ok(_) => Err(format!("{}: obyekt emas", settings.display())),
            Err(e) => Err(format!(
                "{}: JSON emas ({e}) — fayl o'zgartirilmadi",
                settings.display()
            )),
        },
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Map::new()),
        Err(e) => Err(format!("{}: {e}", settings.display())),
    }
}

fn write(settings: &Path, m: Map<String, Value>) -> Result<(), String> {
    if let Some(dir) = settings.parent() {
        std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    }
    if settings.exists() {
        std::fs::copy(settings, backup_path(settings)).map_err(|e| format!("zaxira: {e}"))?;
    }
    let text = serde_json::to_string_pretty(&Value::Object(m)).expect("json") + "\n";
    std::fs::write(settings, text).map_err(|e| format!("{}: {e}", settings.display()))
}

fn is_tamga(entry: &Value) -> bool {
    entry
        .get("hooks")
        .and_then(Value::as_array)
        .is_some_and(|hs| {
            hs.iter().any(|h| {
                h.get("command")
                    .and_then(Value::as_str)
                    .is_some_and(|c| c.contains(MARKER))
            })
        })
}

/// Hook buyrug'i: Claude Code buyruqni qobiq orqali ishga tushiradi, shuning uchun yo'l
/// oldinga qiyshiq chiziqli va qo'shtirnoqda.
fn command(hook: &Path) -> String {
    format!("\"{}\"", hook.display().to_string().replace('\\', "/"))
}

pub fn install(settings: &Path, hook: &Path) -> Result<(), String> {
    let mut m = read(settings)?;
    let hooks = m.entry("hooks").or_insert_with(|| json!({}));
    let hooks = hooks.as_object_mut().ok_or("`hooks` obyekt emas")?;
    for (event, matcher) in EVENTS {
        let list = hooks.entry(event).or_insert_with(|| json!([]));
        let list = list
            .as_array_mut()
            .ok_or(format!("`hooks.{event}` massiv emas"))?;
        list.retain(|e| !is_tamga(e)); // qayta o'rnatish — yo'l yangilanadi, takrorlanmaydi
        // PreToolUse Studio tasdiqlash navbatida inson qarorini kutishi mumkin (ask_timeout_secs ≤ 120 s standart).
        let timeout = if event == "PreToolUse" { 180 } else { 10 };
        let mut entry =
            json!({"hooks": [{"type": "command", "command": command(hook), "timeout": timeout}]});
        if let Some(mt) = matcher {
            entry["matcher"] = mt.into();
        }
        list.push(entry);
    }
    write(settings, m)
}

pub fn uninstall(settings: &Path) -> Result<usize, String> {
    let mut m = read(settings)?;
    let mut removed = 0;
    if let Some(hooks) = m.get_mut("hooks").and_then(Value::as_object_mut) {
        for (_, list) in hooks.iter_mut() {
            if let Some(arr) = list.as_array_mut() {
                let before = arr.len();
                arr.retain(|e| !is_tamga(e));
                removed += before - arr.len();
            }
        }
        hooks.retain(|_, v| v.as_array().is_none_or(|a| !a.is_empty()));
    }
    if m.get("hooks")
        .and_then(Value::as_object)
        .is_some_and(Map::is_empty)
    {
        m.remove("hooks");
    }
    write(settings, m)?;
    Ok(removed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn install_is_idempotent_and_preserves_user_settings() {
        let dir = std::env::temp_dir().join(format!("tamga-install-{}", std::process::id()));
        std::fs::remove_dir_all(&dir).ok();
        let s = dir.join(".claude/settings.json");
        std::fs::create_dir_all(s.parent().unwrap()).unwrap();
        let user = json!({
            "model": "opus",
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my-linter"}]}]}
        });
        std::fs::write(&s, user.to_string()).unwrap();

        let hook = Path::new(r"C:\Tools\tamga\tamga-hook.exe");
        install(&s, hook).unwrap();
        install(&s, hook).unwrap();
        let v: Value = serde_json::from_str(&std::fs::read_to_string(&s).unwrap()).unwrap();
        assert_eq!(v["model"], "opus");
        let pre = v["hooks"]["PreToolUse"].as_array().unwrap();
        assert_eq!(pre.len(), 2, "foydalanuvchi hook'i + bitta TAMGA");
        assert_eq!(
            pre[1]["hooks"][0]["command"],
            "\"C:/Tools/tamga/tamga-hook.exe\""
        );
        assert_eq!(pre[1]["matcher"], "*");
        assert!(v["hooks"]["SessionStart"][0].get("matcher").is_none());
        assert!(backup_path(&s).exists());

        assert_eq!(uninstall(&s).unwrap(), 5);
        let v: Value = serde_json::from_str(&std::fs::read_to_string(&s).unwrap()).unwrap();
        assert_eq!(v, user, "uninstall asl holatni tiklaydi");
        std::fs::remove_dir_all(dir).ok();
    }
}
