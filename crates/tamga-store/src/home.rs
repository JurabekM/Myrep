//! TAMGA ma'lumot papkasi va konfiguratsiya.

use std::path::{Path, PathBuf};

use serde_json::{Value, json};

use crate::{Result, io_err};

/// Daemon ulanmasa hook nima qiladi (PLAN §5, 6-band).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Harakat bloklanadi (fail-closed). Hodisa spool'ga yoziladi.
    Strict,
    /// Harakatga ruxsat beriladi, hodisa spool'ga yoziladi va keyin jurnalga `spooled` belgisi bilan tushadi.
    Dev,
}

/// O'rnatish turi (docs/SERVICE-DESIGN.md).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Deployment {
    /// Oddiy rejim: daemon joriy foydalanuvchi sifatida, ma'lumotlar `%LOCALAPPDATA%\tamga`.
    PerUser,
    /// Himoyalangan rejim: daemon Windows xizmati (`NT SERVICE\tamgad`), ma'lumotlar `%ProgramData%\TAMGA`.
    Service(ServiceInfo),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServiceInfo {
    /// Ma'lumotlar papkasi (`%ProgramData%\TAMGA`).
    pub root: PathBuf,
    /// Pipe'ning to'liq nomi (`\\.\pipe\…`).
    pub pipe: String,
    /// O'rnatish papkasi: mijozlar server exe'si `install_dir\tamgad.exe` ekanini tekshiradi.
    pub install_dir: PathBuf,
}

/// Belgi fayli: o'rnatuvchi (administrator) yozadi, ACL tufayli oddiy foydalanuvchi uni o'zgartira
/// olmaydi. Bor bo'lsa — mashina himoyalangan rejimda.
pub const SERVICE_MARKER: &str = "service.json";

/// `%ProgramData%\TAMGA`.
pub fn service_root() -> Option<PathBuf> {
    // Muhit o'zgaruvchisi emas: uni mijoz jarayoni o'zgartirib, belgini "ko'rmay" qolishi mumkin edi.
    #[cfg(windows)]
    let base = tamga_win::service::program_data();
    #[cfg(not(windows))]
    let base: Option<PathBuf> = None;
    base.map(|p| p.join("TAMGA"))
}

/// Mashinadagi o'rnatish turi (belgi faylidan).
pub fn deployment() -> Deployment {
    service_root().map_or(Deployment::PerUser, |r| deployment_at(&r))
}

/// Berilgan papkadagi belgi bo'yicha o'rnatish turi (sinovlar uchun alohida).
pub fn deployment_at(root: &Path) -> Deployment {
    let Some(v) = std::fs::read_to_string(root.join(SERVICE_MARKER))
        .ok()
        .and_then(|t| serde_json::from_str::<Value>(t.trim_start_matches('\u{feff}')).ok())
    else {
        return Deployment::PerUser;
    };
    let pipe = v["pipe"]
        .as_str()
        .filter(|p| !p.is_empty())
        .unwrap_or("tamga-service");
    let Some(install_dir) = v["install_dir"].as_str().filter(|p| !p.is_empty()) else {
        return Deployment::PerUser;
    };
    Deployment::Service(ServiceInfo {
        root: root.to_owned(),
        pipe: if pipe.starts_with(r"\\") {
            pipe.to_owned()
        } else {
            format!(r"\\.\pipe\{pipe}")
        },
        install_dir: PathBuf::from(install_dir),
    })
}

#[derive(Debug, Clone)]
pub struct Home {
    root: PathBuf,
    /// Xizmat konteksti (daemon `--service` rejimida): kalitlar DPAPI fayl omborida.
    service: bool,
}

impl Home {
    /// `TAMGA_HOME`; aks holda himoyalangan rejimda `%ProgramData%\TAMGA` (faqat o'qish uchun —
    /// yozish xizmat orqali); aks holda `%LOCALAPPDATA%\tamga` (yoki `~/.tamga`).
    pub fn from_env() -> Self {
        let root = std::env::var_os("TAMGA_HOME")
            .map(PathBuf::from)
            .or_else(|| match deployment() {
                Deployment::Service(s) => Some(s.root),
                Deployment::PerUser => None,
            })
            .or_else(|| std::env::var_os("LOCALAPPDATA").map(|p| PathBuf::from(p).join("tamga")))
            .or_else(|| std::env::var_os("HOME").map(|p| PathBuf::from(p).join(".tamga")))
            .unwrap_or_else(|| PathBuf::from(".tamga"));
        Self {
            root,
            service: false,
        }
    }

    pub fn at(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            service: false,
        }
    }

    /// Xizmat konteksti uchun (faqat `tamgad --service`).
    pub fn service(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            service: true,
        }
    }

    pub fn is_service(&self) -> bool {
        self.service
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn ensure(&self) -> Result<()> {
        for d in [self.logs(), self.vault(), self.spool()] {
            std::fs::create_dir_all(&d).map_err(io_err(&d))?;
        }
        Ok(())
    }

    pub fn logs(&self) -> PathBuf {
        self.root.join("logs")
    }
    pub fn vault(&self) -> PathBuf {
        self.root.join("vault")
    }
    pub fn spool(&self) -> PathBuf {
        self.root.join("spool")
    }
    pub fn public_key(&self) -> PathBuf {
        self.root.join("public-key.json")
    }
    pub fn config_path(&self) -> PathBuf {
        self.root.join("config.json")
    }
    pub fn daemon_log(&self) -> PathBuf {
        self.root.join("tamgad.log")
    }
    pub fn log_path(&self, log: &str) -> PathBuf {
        self.logs().join(format!("{log}.jsonl"))
    }
    pub fn checkpoint_path(&self, log: &str) -> PathBuf {
        self.logs().join(format!("{log}.checkpoints"))
    }

    /// `config.json` (yo'q bo'lsa — standart qiymatlar).
    pub fn config(&self) -> Config {
        let v: Value = std::fs::read_to_string(self.config_path())
            .ok()
            .and_then(|t| serde_json::from_str(&t).ok())
            .unwrap_or(Value::Null);
        Config::from_json(&v)
    }

    pub fn write_config(&self, c: &Config) -> Result<()> {
        let p = self.config_path();
        std::fs::write(
            &p,
            serde_json::to_string_pretty(&c.to_json()).expect("json") + "\n",
        )
        .map_err(io_err(&p))
    }
}

#[derive(Debug, Clone)]
pub struct Config {
    pub mode: Mode,
    /// Shuncha yangi yozuvdan keyin checkpoint yaratiladi.
    pub checkpoint_every: u64,
    /// Yangi yozuv bo'lsa, eng kamida shuncha soniyada bir checkpoint.
    pub checkpoint_secs: u64,
    /// Checkpoint nusxalari yoziladigan tashqi papka (boshqa disk, tarmoq papkasi, git repo).
    pub witness_dir: Option<PathBuf>,
    pub ask_route: AskRoute,
    /// Studio navbatida inson javobini kutish muddati; o'tsa — rad etiladi.
    pub ask_timeout_secs: u64,
}

/// `ask` qarori kimga yuboriladi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AskRoute {
    /// Agentning o'z ruxsat oynasiga (Claude Code foydalanuvchidan so'raydi).
    Agent,
    /// TAMGA Studio tasdiqlash navbatiga: daemon hook javobini inson qaror qilguncha ushlab turadi
    /// (headless agentlar uchun — `claude -p`, CI).
    Studio,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            mode: Mode::Dev,
            checkpoint_every: 32,
            checkpoint_secs: 30,
            witness_dir: None,
            ask_route: AskRoute::Agent,
            ask_timeout_secs: 120,
        }
    }
}

impl Config {
    pub fn from_json(v: &Value) -> Self {
        let d = Self::default();
        Self {
            mode: match v.get("mode").and_then(Value::as_str) {
                Some("strict") => Mode::Strict,
                _ => d.mode,
            },
            checkpoint_every: v
                .get("checkpoint_every")
                .and_then(Value::as_u64)
                .filter(|n| *n > 0)
                .unwrap_or(d.checkpoint_every),
            checkpoint_secs: v
                .get("checkpoint_secs")
                .and_then(Value::as_u64)
                .filter(|n| *n > 0)
                .unwrap_or(d.checkpoint_secs),
            witness_dir: v
                .get("witness_dir")
                .and_then(Value::as_str)
                .map(PathBuf::from),
            ask_route: match v.get("ask_route").and_then(Value::as_str) {
                Some("studio") => AskRoute::Studio,
                _ => d.ask_route,
            },
            ask_timeout_secs: v
                .get("ask_timeout_secs")
                .and_then(Value::as_u64)
                .filter(|n| (5..=3600).contains(n))
                .unwrap_or(d.ask_timeout_secs),
        }
    }

    pub fn to_json(&self) -> Value {
        json!({
            "mode": if self.mode == Mode::Strict { "strict" } else { "dev" },
            "checkpoint_every": self.checkpoint_every,
            "checkpoint_secs": self.checkpoint_secs,
            "witness_dir": self.witness_dir.as_ref().map(|p| p.display().to_string()),
            "ask_route": if self.ask_route == AskRoute::Studio { "studio" } else { "agent" },
            "ask_timeout_secs": self.ask_timeout_secs,
        })
    }
}

/// Mashina nomidan jurnal identifikatori: `host-<nom>` (spec §3.1 belgilar to'plamida).
pub fn default_log_id() -> String {
    let host = std::env::var("COMPUTERNAME")
        .or_else(|_| std::env::var("HOSTNAME"))
        .unwrap_or_else(|_| "local".into());
    let clean: String = host
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' {
                c.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .take(100)
        .collect();
    format!("host-{clean}")
}

/// Joriy foydalanuvchiga xos named pipe nomi (boshqa foydalanuvchilar bilan to'qnashmaydi).
pub fn pipe_name() -> String {
    // Himoyalangan rejimda pipe faqat belgi faylidan: `TAMGA_PIPE` e'tiborga olinmaydi, aks holda
    // muhit o'zgaruvchisi orqali mijozlarni soxta serverga yo'naltirish mumkin bo'lardi.
    if let Deployment::Service(s) = deployment() {
        return s.pipe;
    }
    // `TAMGA_PIPE` — sinov uchun alohida pipe. Qisqa nom ham qabul qilinadi: ba'zi qobiqlar
    // (Git Bash) muhit o'zgaruvchisidagi `\\.\pipe\` prefiksini buzadi.
    if let Ok(p) = std::env::var("TAMGA_PIPE")
        && !p.is_empty()
    {
        return if p.starts_with(r"\\") {
            p
        } else {
            format!(r"\\.\pipe\{p}")
        };
    }
    let user: String = std::env::var("USERNAME")
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_else(|_| "user".into())
        .chars()
        .filter(char::is_ascii_alphanumeric)
        .collect();
    format!(r"\\.\pipe\tamga-{user}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn deployment_from_marker() {
        let dir = std::env::temp_dir().join(format!("tamga-dep-{}", std::process::id()));
        std::fs::remove_dir_all(&dir).ok();
        std::fs::create_dir_all(&dir).unwrap();
        assert_eq!(deployment_at(&dir), Deployment::PerUser, "belgisiz");
        std::fs::write(dir.join(SERVICE_MARKER), "{bu json emas").unwrap();
        assert_eq!(deployment_at(&dir), Deployment::PerUser, "buzilgan belgi");
        std::fs::write(dir.join(SERVICE_MARKER), r#"{"pipe":"tamga-service"}"#).unwrap();
        assert_eq!(deployment_at(&dir), Deployment::PerUser, "install_dir yo'q");
        // BOM bilan (PowerShell/NSIS yozgan bo'lishi mumkin).
        std::fs::write(
            dir.join(SERVICE_MARKER),
            "\u{feff}{\"pipe\":\"tamga-service\",\"install_dir\":\"C:\\\\Program Files\\\\TAMGA Studio\"}",
        )
        .unwrap();
        let Deployment::Service(s) = deployment_at(&dir) else {
            panic!("xizmat rejimi kutilgan")
        };
        assert_eq!(s.pipe, r"\\.\pipe\tamga-service");
        assert_eq!(
            s.install_dir,
            PathBuf::from(r"C:\Program Files\TAMGA Studio")
        );
        assert_eq!(s.root, dir);
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn log_id_is_valid() {
        assert!(tamga_core::record::valid_log_id(&default_log_id()));
    }

    #[test]
    fn config_round_trip_and_defaults() {
        let dir = std::env::temp_dir().join(format!("tamga-home-test-{}", std::process::id()));
        let home = Home::at(&dir);
        home.ensure().unwrap();
        assert_eq!(home.config().mode, Mode::Dev);
        let c = Config {
            mode: Mode::Strict,
            checkpoint_every: 5,
            ..Config::default()
        };
        home.write_config(&c).unwrap();
        let back = home.config();
        assert_eq!(
            (back.mode, back.checkpoint_every, back.checkpoint_secs),
            (Mode::Strict, 5, 30)
        );
        std::fs::remove_dir_all(dir).ok();
    }
}
