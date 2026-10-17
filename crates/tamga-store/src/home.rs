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

#[derive(Debug, Clone)]
pub struct Home {
    root: PathBuf,
}

impl Home {
    /// `TAMGA_HOME`, aks holda `%LOCALAPPDATA%\tamga` (yoki `~/.tamga`).
    pub fn from_env() -> Self {
        let root = std::env::var_os("TAMGA_HOME")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("LOCALAPPDATA").map(|p| PathBuf::from(p).join("tamga")))
            .or_else(|| std::env::var_os("HOME").map(|p| PathBuf::from(p).join(".tamga")))
            .unwrap_or_else(|| PathBuf::from(".tamga"));
        Self { root }
    }

    pub fn at(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
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
}

impl Default for Config {
    fn default() -> Self {
        Self {
            mode: Mode::Dev,
            checkpoint_every: 32,
            checkpoint_secs: 30,
            witness_dir: None,
        }
    }
}

impl Config {
    fn from_json(v: &Value) -> Self {
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
        }
    }

    fn to_json(&self) -> Value {
        json!({
            "mode": if self.mode == Mode::Strict { "strict" } else { "dev" },
            "checkpoint_every": self.checkpoint_every,
            "checkpoint_secs": self.checkpoint_secs,
            "witness_dir": self.witness_dir.as_ref().map(|p| p.display().to_string()),
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
