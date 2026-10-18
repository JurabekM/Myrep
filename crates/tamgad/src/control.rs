//! K1/K2: boshqaruv buyruqlarini kim yuborganini tekshirish va jurnalga yozish.
//!
//! Agent daemon bilan bir Windows foydalanuvchisi huquqida ishlaydi, shuning uchun pipe'ning
//! o'zi uni ajrata olmaydi. Daemon pipe mijozining PID'ini oladi va jarayon daraxtiga qaraydi:
//! `decide`, `shutdown`, `rotate` faqat daemon bilan bir papkadagi `tamga.exe` yoki
//! `tamga-studio.exe` dan, va agent daraxtidan (`claude*`, hook, MCP proxy avlodlari) bo'lmagan
//! jarayondan qabul qilinadi. Har bir urinish (qabul yoki rad) `control` yozuvi bo'lib zanjirga tushadi.
//!
//! Halol chegara: bu to'siqni ko'taradi, lekin bir foydalanuvchi ichida mutlaq chegara emas —
//! shuning uchun siyosatdagi `tamper_with_tamga` fakti agentning TAMGA'ga qaratilgan buyruqlarini
//! bajarilishidan oldin bloklaydi va hamma urinishlar jurnalda qoladi.

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use serde_json::{Map, Value, json};
use tamga_sensor::Caller;

/// Chaqiruvchisi tekshiriladigan buyruqlar. `checkpoint` faqat imzo qo'shadi — cheklanmaydi.
pub const GATED: [&str; 3] = ["decide", "shutdown", "rotate"];
/// Boshqaruv dasturlari (fayl nomi, kengaytmasiz).
const TRUSTED: [&str; 2] = ["tamga", "tamga-studio"];

fn canon(p: &Path) -> String {
    std::fs::canonicalize(p)
        .unwrap_or_else(|_| p.to_path_buf())
        .display()
        .to_string()
        .to_lowercase()
}

/// Daemon exe joylashgan papka — ishonchli boshqaruv dasturlari shu yerda bo'lishi kerak.
pub fn own_dir() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()?
        .parent()
        .map(Path::to_path_buf)
}

/// Boshqaruv buyrug'ini qabul qilish mumkinmi. `Err` — inson o'qiydigan sabab.
pub fn authorize(caller: Option<&Caller>, own_dir: Option<&Path>) -> Result<(), String> {
    let c = caller.ok_or("chaqiruvchi jarayon aniqlanmadi")?;
    // H-3: bevosita ota-jarayon ko'rinmasa (etim yoki double-fork — oraliq jarayon o'lgan),
    // chaqiruvchining agentdan emasligini isbotlab bo'lmaydi — fail-closed.
    if !c.parent_known {
        return Err(format!(
            "{} ota-jarayoni ko'rinmaydi (etim yoki double-fork) — boshqaruv buyruqlari rad etiladi",
            c.name
        ));
    }
    if c.from_agent() {
        return Err(format!(
            "{} agent jarayon daraxtidan ({}) — boshqaruv buyruqlari faqat foydalanuvchidan (TAMGA Studio yoki alohida terminal)",
            c.name,
            c.ancestors
                .iter()
                .take(4)
                .cloned()
                .collect::<Vec<_>>()
                .join(" ← ")
        ));
    }
    let exe = c
        .exe
        .as_deref()
        .ok_or("chaqiruvchi exe yo'li aniqlanmadi")?;
    let stem = exe
        .file_stem()
        .map(|s| s.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    if !TRUSTED.contains(&stem.as_str()) {
        return Err(format!("{} TAMGA boshqaruv dasturi emas", c.name));
    }
    let same = matches!((exe.parent(), own_dir), (Some(a), Some(b)) if canon(a) == canon(b));
    if !same {
        return Err(format!("{} daemon bilan bir papkada emas", exe.display()));
    }
    Ok(())
}

/// Jurnal uchun chaqiruvchi (maxfiy ma'lumotsiz: to'liq yo'l emas, faqat fayl nomi).
pub fn client_json(c: Option<&Caller>) -> Value {
    match c {
        Some(c) => json!({"pid": c.pid, "image": c.name, "from_agent": c.from_agent()}),
        None => json!({"pid": null, "image": null, "from_agent": null}),
    }
}

/// Rad etilgan urinishlar jurnalni to'ldirib yubormasligi uchun: daqiqasiga 20 ta yozuv.
pub struct DenyLimiter {
    window: Instant,
    count: u32,
}

impl DenyLimiter {
    pub fn new() -> Self {
        Self {
            window: Instant::now(),
            count: 0,
        }
    }

    pub fn allow(&mut self) -> bool {
        if self.window.elapsed() >= Duration::from_secs(60) {
            self.window = Instant::now();
            self.count = 0;
        }
        self.count += 1;
        self.count <= 20
    }
}

/// Config o'zgarishi: `{maydon: [eski, yangi]}` (bir xil bo'lsa bo'sh).
pub fn config_diff(old: &Value, new: &Value) -> Map<String, Value> {
    let (Some(o), Some(n)) = (old.as_object(), new.as_object()) else {
        return Map::new();
    };
    o.keys()
        .chain(n.keys())
        .filter(|k| o.get(*k) != n.get(*k))
        .map(|k| {
            let v = json!([
                o.get(k).cloned().unwrap_or(Value::Null),
                n.get(k).cloned().unwrap_or(Value::Null)
            ]);
            (k.clone(), v)
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn caller(exe: &str, ancestors: &[&str]) -> Caller {
        let exe = PathBuf::from(exe);
        Caller {
            pid: 7,
            name: exe.file_name().unwrap().to_string_lossy().into_owned(),
            exe: Some(exe),
            ancestors: ancestors.iter().map(|s| (*s).to_owned()).collect(),
            parent_known: true,
        }
    }

    #[test]
    fn only_own_tools_outside_the_agent_tree() {
        let dir = std::env::temp_dir();
        let own = |n: &str| dir.join(n).display().to_string();
        let ok = caller(&own("tamga-studio.exe"), &["explorer.exe"]);
        assert!(authorize(Some(&ok), Some(&dir)).is_ok());
        assert!(
            authorize(
                Some(&caller(&own("tamga.exe"), &["WindowsTerminal.exe"])),
                Some(&dir)
            )
            .is_ok()
        );

        let agent = caller(&own("tamga.exe"), &["pwsh.exe", "claude.exe"]);
        assert!(
            authorize(Some(&agent), Some(&dir))
                .unwrap_err()
                .contains("agent")
        );
        let other = caller(&own("python.exe"), &["explorer.exe"]);
        assert!(
            authorize(Some(&other), Some(&dir))
                .unwrap_err()
                .contains("boshqaruv dasturi emas")
        );
        let copied = caller("C:/Elsewhere/tamga.exe", &["explorer.exe"]);
        assert!(
            authorize(Some(&copied), Some(&dir))
                .unwrap_err()
                .contains("bir papkada emas")
        );
        assert!(
            authorize(None, Some(&dir)).is_err(),
            "aniqlanmasa — rad (fail-closed)"
        );

        // H-3: node (npm Claude Code) va boshqa agent xostlari ham rad etiladi.
        let node = caller(&own("tamga.exe"), &["node.exe"]);
        assert!(
            authorize(Some(&node), Some(&dir))
                .unwrap_err()
                .contains("agent")
        );
        let cursor = caller(&own("tamga.exe"), &["pwsh.exe", "cursor.exe"]);
        assert!(
            authorize(Some(&cursor), Some(&dir))
                .unwrap_err()
                .contains("agent")
        );

        // H-3: bevosita ota ko'rinmasa (double-fork/etim) — rad etiladi.
        let mut orphan = caller(&own("tamga.exe"), &[]);
        orphan.parent_known = false;
        assert!(
            authorize(Some(&orphan), Some(&dir))
                .unwrap_err()
                .contains("ota-jarayoni"),
            "double-fork fail-closed"
        );
    }

    #[test]
    fn parent_known_detects_dangling_parent() {
        use std::collections::HashMap;
        use tamga_sensor::{ProcInfo, ProcTable};
        let mk = |ppid: Option<u32>| ProcInfo {
            ppid,
            name: "x".into(),
            cmd: String::new(),
        };
        // 10 (tamga) → 20 (tirik) → yo'q: 10 ning otasi ko'rinadi.
        let live = ProcTable(HashMap::from([(10, mk(Some(20))), (20, mk(None))]));
        assert!(live.parent_known(10));
        // 10 ning otasi 99 jadvalda yo'q (double-fork: oraliq o'lgan).
        let dead = ProcTable(HashMap::from([(10u32, mk(Some(99)))]));
        assert!(!dead.parent_known(10));
    }

    #[test]
    fn limiter_and_config_diff() {
        let mut l = DenyLimiter::new();
        assert_eq!((0..25).filter(|_| l.allow()).count(), 20);
        let d = config_diff(
            &json!({"mode": "strict", "a": 1}),
            &json!({"mode": "dev", "a": 1}),
        );
        assert_eq!(Value::Object(d), json!({"mode": ["strict", "dev"]}));
        assert!(config_diff(&json!({"a": 1}), &json!({"a": 1})).is_empty());
    }
}
