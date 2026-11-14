//! "Aytdi va qildi": OS kuzatuvini agent e'lon qilgan tool chaqiruvlari bilan solishtirish.
//!
//! "Aytdi" — `tool.pre` (tool nomi, faktlar). "Qildi" — sensor ko'rgan jarayon, TCP ulanish va fayl
//! o'zgarishi. Kuzatuv faol chaqiruv oynasiga (pre − 0,3 s … post + 1,5 s) tushsa, o'sha chaqiruvga
//! bog'lanadi (`ref`). Nomuvofiqlik:
//! - tarmoq ulanishi, lekin chaqiruv faktlarida `network_egress` yo'q;
//! - maxfiy papkadagi o'zgarish;
//! - hech qaysi chaqiruv faol bo'lmagan paytdagi jarayon/ulanish/fayl o'zgarishi.

use std::collections::HashMap;
use std::path::Path;
use std::time::{Duration, Instant};

use tamga_sensor::Observation;

const BEFORE: Duration = Duration::from_millis(300);
const AFTER: Duration = Duration::from_millis(1500);
const SHELL: [&str; 2] = ["Bash", "PowerShell"];
const WRITERS: [&str; 4] = ["Write", "Edit", "MultiEdit", "NotebookEdit"];

/// Kuzatuv maxfiy hisoblanadigan papkalar (foydalanuvchi profili ichida).
pub const SENSITIVE: [&str; 7] = [
    ".ssh",
    ".aws",
    ".azure",
    ".kube",
    ".gnupg",
    ".docker",
    ".config/gcloud",
];

#[derive(Debug, Clone)]
pub struct Call {
    pub seq: u64,
    pub tool: String,
    pub flags: Vec<String>,
    pub path: String,
    pub started: Instant,
    pub ended: Option<Instant>,
}

#[derive(Debug, Default)]
pub struct Ctx {
    pub root: Option<u32>,
    pub cwd: String,
    pub calls: Vec<Call>,
    pub last_seen: Option<Instant>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    pub session: String,
    pub ref_seq: Option<u64>,
    pub declared: bool,
    pub mismatch: Option<&'static str>,
    pub severity: &'static str,
}

/// Agent harness'ining "quvur" jarayonlari: konsol xosti hech qachon, shell'lar esa e'lon qilingan
/// chaqiruv ichida yozilmaydi (ular chaqiruvning o'zi). Shell ichidan tug'ilgan haqiqiy dasturlar
/// (python, curl, whoami...) va chaqiruvdan tashqaridagi shell'lar yoziladi.
pub fn is_plumbing(image: &str, declared: bool) -> bool {
    let i = image.to_ascii_lowercase();
    i == "conhost.exe"
        || (declared
            && matches!(
                i.as_str(),
                "bash.exe" | "sh.exe" | "cmd.exe" | "powershell.exe" | "pwsh.exe"
            ))
}

fn norm(p: &str) -> String {
    p.replace('\\', "/").trim_end_matches('/').to_lowercase()
}

fn under(path: &str, dir: &str) -> bool {
    let (p, d) = (norm(path), norm(dir));
    !d.is_empty() && (p == d || p.starts_with(&format!("{d}/")))
}

pub fn is_sensitive(path: &str, profile: &str) -> bool {
    SENSITIVE
        .iter()
        .any(|s| under(path, &format!("{profile}/{s}")))
}

#[derive(Debug, Default)]
pub struct Correlator {
    pub sessions: HashMap<String, Ctx>,
    pub profile: String,
}

impl Correlator {
    pub fn new(profile: String) -> Self {
        Self {
            sessions: HashMap::new(),
            profile,
        }
    }

    pub fn ctx(&mut self, session: &str) -> &mut Ctx {
        self.sessions.entry(session.to_owned()).or_default()
    }

    pub fn begin(&mut self, session: &str, call: Call) {
        let c = self.ctx(session);
        c.last_seen = Some(call.started);
        c.calls.push(call);
    }

    pub fn end(&mut self, session: &str, seq: u64, now: Instant) {
        if let Some(c) = self.sessions.get_mut(session) {
            c.last_seen = Some(now);
            if let Some(call) = c.calls.iter_mut().find(|c| c.seq == seq) {
                call.ended = Some(now);
            }
        }
    }

    /// Eski chaqiruvlarni tozalaydi (tugaganidan 5 s o'tgan yoki 30 daqiqadan beri ochiq).
    pub fn gc(&mut self, now: Instant) {
        for c in self.sessions.values_mut() {
            c.calls.retain(|call| match call.ended {
                Some(e) => now.saturating_duration_since(e) < Duration::from_secs(5),
                None => now.saturating_duration_since(call.started) < Duration::from_secs(1800),
            });
        }
    }

    fn active(c: &Ctx, now: Instant) -> impl Iterator<Item = &Call> {
        c.calls.iter().filter(move |call| {
            call.started.checked_sub(BEFORE).is_none_or(|s| s <= now)
                && call.ended.is_none_or(|e| now <= e + AFTER)
        })
    }

    /// Kuzatuvni sessiya va chaqiruvga bog'laydi. `None` — e'tiborga olinmaydi (sessiyasiz fayl).
    pub fn classify(&self, obs: &Observation, now: Instant, home: &Path) -> Option<Finding> {
        let by_root = |root: u32| {
            self.sessions
                .iter()
                .filter(|(_, c)| c.root == Some(root))
                .max_by_key(|(_, c)| c.last_seen)
                .map(|(s, _)| s.clone())
        };
        match obs {
            Observation::Process { root, .. } => {
                let session = by_root(*root)?;
                let ctx = &self.sessions[&session];
                let call = Self::active(ctx, now)
                    .max_by_key(|c| (SHELL.contains(&c.tool.as_str()), c.started));
                Some(match call {
                    Some(c) => Finding {
                        session,
                        ref_seq: Some(c.seq),
                        declared: true,
                        mismatch: None,
                        severity: "info",
                    },
                    None => Finding {
                        session,
                        ref_seq: None,
                        declared: false,
                        mismatch: Some("tool chaqiruvidan tashqarida jarayon"),
                        severity: "info",
                    },
                })
            }
            Observation::Connection { root, .. } => {
                let session = by_root(*root)?;
                let ctx = &self.sessions[&session];
                let calls: Vec<&Call> = Self::active(ctx, now).collect();
                if let Some(c) = calls
                    .iter()
                    .find(|c| c.flags.iter().any(|f| f == "network_egress"))
                {
                    return Some(Finding {
                        session,
                        ref_seq: Some(c.seq),
                        declared: true,
                        mismatch: None,
                        severity: "info",
                    });
                }
                Some(
                    match calls
                        .iter()
                        .max_by_key(|c| (SHELL.contains(&c.tool.as_str()), c.started))
                    {
                        Some(c) => Finding {
                            session,
                            ref_seq: Some(c.seq),
                            declared: false,
                            mismatch: Some("e'lon qilinmagan tarmoq ulanishi"),
                            severity: "warn",
                        },
                        None => Finding {
                            session,
                            ref_seq: None,
                            declared: false,
                            mismatch: Some("tool chaqiruvidan tashqarida tarmoq ulanishi"),
                            severity: "warn",
                        },
                    },
                )
            }
            Observation::File { path, .. } => {
                let path = path.display().to_string();
                if under(&path, &home.display().to_string()) {
                    return None; // TAMGA'ning o'z fayllari
                }
                let sensitive = is_sensitive(&path, &self.profile);
                // Sessiya: fayl uning ishchi papkasida bo'lsa — o'sha; maxfiy papka — oxirgi faol sessiya.
                let session = self
                    .sessions
                    .iter()
                    .filter(|(_, c)| under(&path, &c.cwd) || (sensitive && c.root.is_some()))
                    .max_by_key(|(_, c)| c.last_seen)
                    .map(|(s, _)| s.clone())?;
                let ctx = &self.sessions[&session];
                let calls: Vec<&Call> = Self::active(ctx, now).collect();
                if let Some(c) = calls
                    .iter()
                    .find(|c| WRITERS.contains(&c.tool.as_str()) && norm(&c.path) == norm(&path))
                {
                    return Some(Finding {
                        session,
                        ref_seq: Some(c.seq),
                        declared: true,
                        mismatch: None,
                        severity: "info",
                    });
                }
                let shell = calls
                    .iter()
                    .filter(|c| SHELL.contains(&c.tool.as_str()))
                    .max_by_key(|c| c.started);
                Some(match (shell, sensitive) {
                    (Some(c), false) => Finding {
                        session,
                        ref_seq: Some(c.seq),
                        declared: true,
                        mismatch: None,
                        severity: "info",
                    },
                    (Some(c), true) => Finding {
                        session,
                        ref_seq: Some(c.seq),
                        declared: false,
                        mismatch: Some("maxfiy papkadagi o'zgarish"),
                        severity: "warn",
                    },
                    (None, true) => Finding {
                        session,
                        ref_seq: None,
                        declared: false,
                        mismatch: Some("maxfiy papkadagi o'zgarish"),
                        severity: "warn",
                    },
                    (None, false) => Finding {
                        session,
                        ref_seq: None,
                        declared: false,
                        mismatch: Some("tool chaqiruvidan tashqarida fayl o'zgarishi"),
                        severity: "info",
                    },
                })
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn call(
        seq: u64,
        tool: &str,
        flags: &[&str],
        path: &str,
        started: Instant,
        ended: Option<Instant>,
    ) -> Call {
        Call {
            seq,
            tool: tool.into(),
            flags: flags.iter().map(|s| (*s).into()).collect(),
            path: path.into(),
            started,
            ended,
        }
    }

    fn setup() -> (Correlator, Instant) {
        let mut c = Correlator::new("C:/Users/me".into());
        let t0 = Instant::now();
        let ctx = c.ctx("s1");
        ctx.root = Some(10);
        ctx.cwd = "C:/work/proj".into();
        ctx.last_seen = Some(t0);
        (c, t0)
    }

    fn net(root: u32) -> Observation {
        Observation::Connection {
            pid: 12,
            image: "python.exe".into(),
            remote: "93.184.215.14:80".into(),
            root,
        }
    }

    #[test]
    fn network_said_vs_did() {
        let (mut c, t0) = setup();
        // `python check.py` — tahlilchi tarmoq ko'rmagan.
        c.begin("s1", call(5, "Bash", &[], "", t0, None));
        let f = c
            .classify(
                &net(10),
                t0 + Duration::from_millis(400),
                Path::new("C:/tamga"),
            )
            .unwrap();
        assert_eq!(
            (f.ref_seq, f.declared, f.mismatch, f.severity),
            (
                Some(5),
                false,
                Some("e'lon qilinmagan tarmoq ulanishi"),
                "warn"
            )
        );
        // `curl ...` — e'lon qilingan.
        c.begin(
            "s1",
            call(
                7,
                "Bash",
                &["network_egress"],
                "",
                t0 + Duration::from_secs(10),
                None,
            ),
        );
        let f = c
            .classify(
                &net(10),
                t0 + Duration::from_secs(10),
                Path::new("C:/tamga"),
            )
            .unwrap();
        assert!(f.declared && f.mismatch.is_none() && f.ref_seq == Some(7));
        assert!(
            c.classify(&net(99), t0, Path::new("C:/tamga")).is_none(),
            "kuzatilmayotgan ildiz"
        );
    }

    #[test]
    fn windows_and_outside_calls() {
        let (mut c, t0) = setup();
        c.begin(
            "s1",
            call(5, "Bash", &[], "", t0, Some(t0 + Duration::from_secs(1))),
        );
        let p = Observation::Process {
            pid: 12,
            ppid: 11,
            image: "cmd.exe".into(),
            cmd: "cmd /c whoami".into(),
            root: 10,
        };
        let inside = c
            .classify(&p, t0 + Duration::from_millis(2200), Path::new("C:/tamga"))
            .unwrap();
        assert_eq!(
            (inside.ref_seq, inside.declared),
            (Some(5), true),
            "post + 1,5 s ichida"
        );
        let outside = c
            .classify(&p, t0 + Duration::from_secs(4), Path::new("C:/tamga"))
            .unwrap();
        assert_eq!(
            (outside.ref_seq, outside.mismatch),
            (None, Some("tool chaqiruvidan tashqarida jarayon"))
        );
        c.gc(t0 + Duration::from_secs(10));
        assert!(c.sessions["s1"].calls.is_empty());
    }

    #[test]
    fn plumbing_filter() {
        assert!(
            is_plumbing("conhost.exe", false),
            "konsol xosti hech qachon"
        );
        assert!(
            is_plumbing("bash.exe", true),
            "e'lon qilingan chaqiruv ichidagi shell"
        );
        assert!(
            !is_plumbing("bash.exe", false),
            "chaqiruvdan tashqaridagi shell yoziladi"
        );
        assert!(!is_plumbing("python.exe", true));
        assert!(!is_plumbing("whoami.exe", true));
    }

    #[test]
    fn files_by_writer_shell_sensitive_and_own() {
        let (mut c, t0) = setup();
        let f = |p: &str| Observation::File {
            path: PathBuf::from(p),
            op: "modify",
        };
        let home = Path::new("C:/Users/me/AppData/Local/tamga");
        c.begin(
            "s1",
            call(3, "Write", &[], "C:\\work\\proj\\src\\a.rs", t0, None),
        );
        let w = c.classify(&f("C:/work/proj/src/a.rs"), t0, home).unwrap();
        assert_eq!((w.ref_seq, w.declared), (Some(3), true));
        let other = c.classify(&f("C:/work/proj/src/b.rs"), t0, home).unwrap();
        assert_eq!(
            other.mismatch,
            Some("tool chaqiruvidan tashqarida fayl o'zgarishi"),
            "Write boshqa faylga e'lon qilingan"
        );
        c.begin("s1", call(4, "Bash", &[], "", t0, None));
        assert!(
            c.classify(&f("C:/work/proj/build/out.o"), t0, home)
                .unwrap()
                .declared
        );
        let ssh = c
            .classify(&f("C:/Users/me/.ssh/authorized_keys"), t0, home)
            .unwrap();
        assert_eq!(
            (ssh.mismatch, ssh.severity),
            (Some("maxfiy papkadagi o'zgarish"), "warn")
        );
        assert!(
            c.classify(&f("C:/Users/me/AppData/Local/tamga/logs/x.jsonl"), t0, home)
                .is_none(),
            "o'z fayllarimiz"
        );
        assert!(
            c.classify(&f("D:/boshqa/x.txt"), t0, home).is_none(),
            "hech qaysi sessiyaga tegishli emas"
        );
    }
}
