//! Ma'lumot papkasi va konfiguratsiya: `%APPDATA%\AETHER-Q\Studio` (yoki `AQ_STUDIO_HOME`).
//!
//! ```text
//!   config.json        profillar va sozlamalar
//!   keys\              identity'lar (aqctl bilan bir xil format)
//!   logs\              kunlik jurnal fayllari
//!   run\               standart rejim uchun vaqtinchalik allowlist fayllari
//! ```

use std::fs;
use std::path::{Path, PathBuf};

use crate::model::Config;

pub struct Store {
    pub root: PathBuf,
    pub cfg: Config,
    /// Konfiguratsiya o'qilmagan bo'lsa — sababi (foydalanuvchiga ko'rsatiladi, fayl ustidan yozilmaydi).
    pub load_error: Option<String>,
}

pub fn default_root() -> PathBuf {
    if let Some(p) = std::env::var_os("AQ_STUDIO_HOME") {
        return PathBuf::from(p);
    }
    if let Some(a) = std::env::var_os("APPDATA") {
        return PathBuf::from(a).join("AETHER-Q").join("Studio");
    }
    std::env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from(".")).join(".aq-studio")
}

impl Store {
    pub fn open(root: PathBuf) -> Store {
        for d in ["keys", "logs", "run"] {
            let _ = fs::create_dir_all(root.join(d));
        }
        let path = root.join("config.json");
        let (cfg, load_error) = match fs::read_to_string(&path) {
            Err(_) => (Config::default(), None),
            Ok(text) => match serde_json::from_str::<Config>(&text) {
                Ok(c) => (c, None),
                Err(e) => {
                    // Buzilgan faylni saqlab qo'yamiz — foydalanuvchi ma'lumoti yo'qolmasin.
                    let backup = root.join(format!("config.buzilgan-{}.json", crate::timefmt::now_unix()));
                    let _ = fs::copy(&path, &backup);
                    (Config::default(), Some(format!("config.json o'qilmadi ({e}); nusxasi: {}", backup.display())))
                }
            },
        };
        Store { root, cfg, load_error }
    }

    pub fn keys_dir(&self) -> PathBuf {
        self.root.join("keys")
    }

    pub fn logs_dir(&self) -> PathBuf {
        self.root.join("logs")
    }

    pub fn run_dir(&self) -> PathBuf {
        self.root.join("run")
    }

    /// Atomik saqlash: vaqtinchalik fayl + almashtirish.
    pub fn save(&self) -> Result<(), String> {
        let js = serde_json::to_string_pretty(&self.cfg).map_err(|e| e.to_string())?;
        let path = self.root.join("config.json");
        let tmp = self.root.join("config.json.tmp");
        fs::write(&tmp, js).map_err(|e| format!("sozlamalar yozilmadi: {e}"))?;
        fs::rename(&tmp, &path).map_err(|e| format!("sozlamalar saqlanmadi: {e}"))
    }

    /// aqctl.exe: sozlamadagi yo'l, so'ng dastur yonida, so'ng `dist\` (ishlab chiqish nusxasi uchun).
    pub fn aqctl(&self) -> Option<PathBuf> {
        let custom = self.cfg.settings.aqctl_path.trim();
        if !custom.is_empty() {
            let p = PathBuf::from(custom);
            return p.is_file().then_some(p);
        }
        find_beside_exe(exe_name("aqctl"))
    }
}

pub fn exe_name(base: &str) -> String {
    if cfg!(windows) {
        format!("{base}.exe")
    } else {
        base.to_string()
    }
}

/// Dastur papkasida yoki yuqoridagi `dist\` papkalarida faylni qidiradi.
pub fn find_beside_exe(name: String) -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let mut dir: Option<&Path> = exe.parent();
    for _ in 0..5 {
        let d = dir?;
        for cand in [d.join(&name), d.join("dist").join(&name)] {
            if cand.is_file() {
                return Some(cand);
            }
        }
        dir = d.parent();
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Profile, Role};

    #[test]
    fn save_and_reopen_and_corrupt_config_is_preserved() {
        let root = std::env::temp_dir().join(format!("aq-studio-store-{}", crate::model::new_id()));
        let mut s = Store::open(root.clone());
        assert!(s.cfg.profiles.is_empty() && s.load_error.is_none());
        let mut p = Profile::new(Role::Client);
        p.name = "Mijoz".into();
        s.cfg.profiles.push(p.clone());
        s.save().unwrap();
        let s2 = Store::open(root.clone());
        assert_eq!(s2.cfg.profiles, vec![p]);
        assert!(root.join("keys").is_dir() && root.join("logs").is_dir());

        fs::write(root.join("config.json"), "{ buzilgan").unwrap();
        let s3 = Store::open(root.clone());
        assert!(s3.load_error.is_some());
        let backups: Vec<_> = fs::read_dir(&root)
            .unwrap()
            .flatten()
            .filter(|e| e.file_name().to_string_lossy().starts_with("config.buzilgan-"))
            .collect();
        assert_eq!(backups.len(), 1, "buzilgan fayl nusxasi saqlanishi kerak");
        let _ = fs::remove_dir_all(&root);
    }
}
