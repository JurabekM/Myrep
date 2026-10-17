//! TAMGA OS sensori — **admin huquqisiz**: agent haqiqatda nima qilganini kuzatadi ("qildi").
//!
//! Manbalar (hammasi oddiy foydalanuvchi huquqi bilan):
//! - jarayonlar: `sysinfo` snapshot'i (ToolHelp + PEB'dan buyruq satri), har [`POLL`] da;
//! - TCP ulanishlari: `GetExtendedTcpTable` (`netstat2`) — PID bilan;
//! - fayl o'zgarishlari: `ReadDirectoryChangesW` (`notify`).
//!
//! **Ko'r nuqtalar** ([`BLIND_SPOTS`]) Studio'da doim ko'rsatiladi: fayl *o'qishlari* ko'rinmaydi
//! (admin'siz audit/ETW yo'q), polling oralig'idan qisqa jarayon va ulanishlar o'tkazib yuborilishi
//! mumkin, UDP/DNS kuzatilmaydi.
//!
//! Sensor faqat **kuzatilayotgan agent ildizlari**ning avlodlarini xabar qiladi; TAMGA'ning o'z
//! jarayonlari (hook, daemon, proxy) va ularning avlodlari chiqarib tashlanadi.

use std::collections::{HashMap, HashSet};
use std::net::IpAddr;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{Receiver, Sender, channel};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};

use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};

pub const POLL: Duration = Duration::from_millis(200);

pub const BLIND_SPOTS: [&str; 4] = [
    "fayl o'qishlari ko'rinmaydi (admin'siz audit yo'q) — faqat yaratish, o'zgartirish, o'chirish, qayta nomlash",
    "200 ms dan qisqa yashagan jarayon yoki TCP ulanishi o'tkazib yuborilishi mumkin",
    "UDP va DNS so'rovlari kuzatilmaydi",
    "fayl o'zgarishining qaysi jarayondan ekani noma'lum — vaqt bo'yicha bog'lanadi",
];

/// TAMGA'ning o'z jarayonlari: ular va ularning avlodlari kuzatuvdan chiqariladi.
const OWN: [&str; 5] = [
    "tamga-hook",
    "tamgad",
    "tamga-mcp-proxy",
    "tamga",
    "tamga-studio",
];

/// Kuzatuvga arzimaydigan papkalar (shovqin).
const IGNORED_DIRS: [&str; 6] = [
    ".git",
    "node_modules",
    "target",
    "__pycache__",
    ".venv",
    ".tamga",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcInfo {
    pub ppid: Option<u32>,
    pub name: String,
    pub cmd: String,
}

/// Jarayonlar jadvali (PID → ma'lumot).
#[derive(Debug, Clone, Default)]
pub struct ProcTable(pub HashMap<u32, ProcInfo>);

impl ProcTable {
    /// `pid` dan yuqoriga ajdodlar zanjiri (o'zi kirmaydi), sikl va 64 darajadan himoyalangan.
    pub fn ancestors(&self, pid: u32) -> Vec<u32> {
        let mut out = Vec::new();
        let mut cur = pid;
        while let Some(pp) = self.0.get(&cur).and_then(|p| p.ppid) {
            if pp == cur || pp == pid || out.contains(&pp) || out.len() >= 64 {
                break;
            }
            out.push(pp);
            cur = pp;
        }
        out
    }

    pub fn name(&self, pid: u32) -> String {
        self.0.get(&pid).map(|p| p.name.clone()).unwrap_or_default()
    }

    /// `pid` kuzatilayotgan ildizlardan biriga tegishlimi (ildizning o'zi emas) va TAMGA vositasi
    /// zanjirida emasmi. Qaytadi: mos ildiz.
    pub fn watched_root(&self, pid: u32, roots: &HashSet<u32>) -> Option<u32> {
        if roots.contains(&pid) || is_own(&self.name(pid)) {
            return None;
        }
        for a in self.ancestors(pid) {
            if roots.contains(&a) {
                return Some(a);
            }
            if is_own(&self.name(a)) {
                return None;
            }
        }
        None
    }

    /// Agent ildizi: `client` (hook yoki proxy jarayoni) dan yuqoriga birinchi `claude*` jarayoni,
    /// aks holda bevosita ota-jarayon.
    pub fn agent_root(&self, client: u32) -> Option<u32> {
        let chain = self.ancestors(client);
        chain
            .iter()
            .copied()
            .find(|p| self.name(*p).to_ascii_lowercase().starts_with("claude"))
            .or_else(|| chain.first().copied())
    }
}

fn stem(name: &str) -> String {
    let n = name.to_ascii_lowercase();
    n.strip_suffix(".exe").unwrap_or(&n).to_owned()
}

fn is_own(name: &str) -> bool {
    OWN.contains(&stem(name).as_str())
}

/// Tashqi manzilmi (loopback, ko'rsatilmagan va link-local emas).
pub fn is_remote(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v) => !(v.is_loopback() || v.is_unspecified() || v.is_link_local()),
        IpAddr::V6(v) => {
            !(v.is_loopback() || v.is_unspecified() || (v.segments()[0] & 0xffc0) == 0xfe80)
        }
    }
}

pub fn is_ignored(path: &Path) -> bool {
    path.components().any(|c| {
        IGNORED_DIRS
            .iter()
            .any(|d| c.as_os_str().eq_ignore_ascii_case(d))
    })
}

/// Sensor kuzatuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Observation {
    Process {
        pid: u32,
        ppid: u32,
        image: String,
        cmd: String,
        root: u32,
    },
    Connection {
        pid: u32,
        image: String,
        remote: String,
        root: u32,
    },
    File {
        path: PathBuf,
        op: &'static str,
    },
}

/// Sensor: fon oqimi `Observation` larni kanalga yuboradi.
pub struct Sensor {
    table: Arc<RwLock<ProcTable>>,
    roots: Arc<Mutex<HashSet<u32>>>,
    watcher: Mutex<Option<notify::RecommendedWatcher>>,
    watched_dirs: Mutex<HashSet<PathBuf>>,
    tx: Sender<Observation>,
}

impl Sensor {
    /// Sensorni ishga tushiradi va kuzatuvlar kanalini qaytaradi.
    pub fn start() -> (Arc<Self>, Receiver<Observation>) {
        let (tx, rx) = channel();
        let sensor = Arc::new(Self {
            table: Arc::new(RwLock::new(ProcTable::default())),
            roots: Arc::new(Mutex::new(HashSet::new())),
            watcher: Mutex::new(None),
            watched_dirs: Mutex::new(HashSet::new()),
            tx: tx.clone(),
        });
        let file_tx = tx.clone();
        let watcher = notify::recommended_watcher(move |res: notify::Result<notify::Event>| {
            let Ok(ev) = res else { return };
            use notify::EventKind as K;
            let op = match ev.kind {
                K::Create(_) => "create",
                K::Modify(notify::event::ModifyKind::Name(_)) => "rename",
                K::Modify(_) => "modify",
                K::Remove(_) => "remove",
                _ => return,
            };
            for path in ev.paths {
                if !is_ignored(&path) {
                    let _ = file_tx.send(Observation::File { path, op });
                }
            }
        })
        .ok();
        *sensor.watcher.lock().expect("watcher") = watcher;

        let (table, roots) = (Arc::clone(&sensor.table), Arc::clone(&sensor.roots));
        std::thread::Builder::new()
            .name("tamga-sensor".into())
            .spawn(move || poll_loop(&table, &roots, &tx))
            .expect("sensor oqimi");
        (sensor, rx)
    }

    /// Agent ildizini kuzatuvga qo'shadi (hook/proxy PID'idan aniqlanadi).
    pub fn watch_client(&self, client_pid: u32) -> Option<u32> {
        // Hook qisqa yashaydi va oxirgi snapshot'dan keyin tug'ilgan bo'lishi mumkin — u holda
        // shu yerning o'zida yangi snapshot olinadi (sessiyaga bir marta).
        if !self
            .table
            .read()
            .expect("jadval")
            .0
            .contains_key(&client_pid)
        {
            let fresh = snapshot(&mut System::new());
            *self.table.write().expect("jadval") = fresh;
        }
        let root = self.table.read().expect("jadval").agent_root(client_pid)?;
        self.roots.lock().expect("roots").insert(root);
        Some(root)
    }

    pub fn unwatch_root(&self, root: u32) {
        self.roots.lock().expect("roots").remove(&root);
    }

    /// Papkani rekursiv fayl kuzatuviga qo'shadi (bir marta).
    pub fn watch_dir(&self, dir: &Path, recursive: bool) -> bool {
        if !dir.is_dir()
            || !self
                .watched_dirs
                .lock()
                .expect("dirs")
                .insert(dir.to_owned())
        {
            return false;
        }
        use notify::Watcher as _;
        let mode = if recursive {
            notify::RecursiveMode::Recursive
        } else {
            notify::RecursiveMode::NonRecursive
        };
        self.watcher
            .lock()
            .expect("watcher")
            .as_mut()
            .is_some_and(|w| w.watch(dir, mode).is_ok())
    }

    pub fn watched_dirs(&self) -> Vec<PathBuf> {
        self.watched_dirs
            .lock()
            .expect("dirs")
            .iter()
            .cloned()
            .collect()
    }

    pub fn roots(&self) -> Vec<u32> {
        self.roots.lock().expect("roots").iter().copied().collect()
    }

    /// Sinov va yordamchilar uchun: tashqi kuzatuvni kanalga qo'shish.
    pub fn inject(&self, o: Observation) {
        let _ = self.tx.send(o);
    }
}

fn snapshot(sys: &mut System) -> ProcTable {
    sys.refresh_processes_specifics(
        ProcessesToUpdate::All,
        true,
        ProcessRefreshKind::nothing()
            .with_cmd(UpdateKind::OnlyIfNotSet)
            .with_exe(UpdateKind::OnlyIfNotSet),
    );
    ProcTable(
        sys.processes()
            .iter()
            .map(|(pid, p)| {
                let cmd = p
                    .cmd()
                    .iter()
                    .map(|a| a.to_string_lossy())
                    .collect::<Vec<_>>()
                    .join(" ");
                (
                    pid.as_u32(),
                    ProcInfo {
                        ppid: p.parent().map(Pid::as_u32),
                        name: p.name().to_string_lossy().into_owned(),
                        cmd,
                    },
                )
            })
            .collect(),
    )
}

fn poll_loop(table: &RwLock<ProcTable>, roots: &Mutex<HashSet<u32>>, tx: &Sender<Observation>) {
    let mut sys = System::new();
    let mut seen_pids: HashSet<u32> = HashSet::new();
    let mut seen_conns: HashMap<(u32, String), Instant> = HashMap::new();
    let mut first = true;
    loop {
        let snap = snapshot(&mut sys);
        let current: HashSet<u32> = snap.0.keys().copied().collect();
        let watched = roots.lock().expect("roots").clone();
        if !first && !watched.is_empty() {
            for pid in current.difference(&seen_pids) {
                if let Some(root) = snap.watched_root(*pid, &watched) {
                    let p = &snap.0[pid];
                    let _ = tx.send(Observation::Process {
                        pid: *pid,
                        ppid: p.ppid.unwrap_or(0),
                        image: p.name.clone(),
                        cmd: p.cmd.clone(),
                        root,
                    });
                }
            }
        }
        if !watched.is_empty() {
            let flags = netstat2::AddressFamilyFlags::IPV4 | netstat2::AddressFamilyFlags::IPV6;
            if let Ok(sockets) = netstat2::get_sockets_info(flags, netstat2::ProtocolFlags::TCP) {
                for s in sockets {
                    let netstat2::ProtocolSocketInfo::Tcp(t) = &s.protocol_socket_info else {
                        continue;
                    };
                    if matches!(
                        t.state,
                        netstat2::TcpState::Listen
                            | netstat2::TcpState::TimeWait
                            | netstat2::TcpState::Closed
                    ) || !is_remote(&t.remote_addr)
                    {
                        continue;
                    }
                    let remote = match t.remote_addr {
                        IpAddr::V6(v) => format!("[{v}]:{}", t.remote_port),
                        IpAddr::V4(v) => format!("{v}:{}", t.remote_port),
                    };
                    for pid in &s.associated_pids {
                        // Yangi (PID, manzil) juftligi bo'lsagina xabar qilinadi; borlari yangilanadi.
                        let is_new = seen_conns
                            .insert((*pid, remote.clone()), Instant::now())
                            .is_none();
                        if !is_new {
                            continue;
                        }
                        if let Some(root) = snap.watched_root(*pid, &watched) {
                            let _ = tx.send(Observation::Connection {
                                pid: *pid,
                                image: snap.name(*pid),
                                remote: remote.clone(),
                                root,
                            });
                        }
                    }
                }
            }
            seen_conns.retain(|_, t| t.elapsed() < Duration::from_secs(120));
        }
        seen_pids = current;
        *table.write().expect("jadval") = snap;
        first = false;
        std::thread::sleep(POLL);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn table(rows: &[(u32, u32, &str)]) -> ProcTable {
        ProcTable(
            rows.iter()
                .map(|(pid, pp, n)| {
                    (
                        *pid,
                        ProcInfo {
                            ppid: Some(*pp),
                            name: (*n).to_owned(),
                            cmd: String::new(),
                        },
                    )
                })
                .collect(),
        )
    }

    #[test]
    fn ancestors_roots_and_own_tools() {
        // 1 explorer → 10 claude.exe → 11 bash.exe → 12 python.exe → 13 cmd.exe
        //                              → 20 tamga-hook.exe → 21 tamgad.exe
        //                              → 30 tamga-mcp-proxy.exe → 31 node.exe
        let t = table(&[
            (10, 1, "claude.exe"),
            (11, 10, "bash.exe"),
            (12, 11, "python.exe"),
            (13, 12, "cmd.exe"),
            (20, 10, "tamga-hook.exe"),
            (21, 20, "tamgad.exe"),
            (30, 10, "tamga-mcp-proxy.exe"),
            (31, 30, "node.exe"),
        ]);
        assert_eq!(t.ancestors(13), [12, 11, 10, 1]);
        assert_eq!(t.agent_root(20), Some(10), "hook'dan yuqorida claude");
        let roots: HashSet<u32> = [10].into();
        assert_eq!(t.watched_root(13, &roots), Some(10));
        assert_eq!(
            t.watched_root(10, &roots),
            None,
            "ildizning o'zi (API trafigi) emas"
        );
        assert_eq!(
            t.watched_root(21, &roots),
            None,
            "TAMGA vositalari chiqariladi"
        );
        assert_eq!(
            t.watched_root(31, &roots),
            None,
            "proxy ostidagi MCP server — proxy qatlami yozadi"
        );
        assert_eq!(t.watched_root(1, &roots), None);
    }

    #[test]
    fn cycle_guard_and_fallback_root() {
        let t = table(&[(5, 6, "a.exe"), (6, 5, "b.exe")]);
        assert_eq!(t.ancestors(5), [6], "sikl to'xtatiladi");
        let t = table(&[(40, 41, "tamga-hook.exe"), (41, 2, "cursor.exe")]);
        assert_eq!(t.agent_root(40), Some(41), "claude topilmasa — ota-jarayon");
    }

    #[test]
    fn remote_and_ignored() {
        assert!(is_remote(&"93.184.215.14".parse().unwrap()));
        assert!(!is_remote(&"127.0.0.1".parse().unwrap()));
        assert!(!is_remote(&"::1".parse().unwrap()));
        assert!(!is_remote(&"169.254.1.1".parse().unwrap()));
        assert!(is_ignored(Path::new("C:/p/.git/index")));
        assert!(is_ignored(Path::new("C:/p/node_modules/x/y.js")));
        assert!(!is_ignored(Path::new("C:/p/src/main.rs")));
    }

    #[test]
    fn live_snapshot_sees_this_process() {
        let mut sys = System::new();
        let t = snapshot(&mut sys);
        let me = std::process::id();
        assert!(t.0.contains_key(&me));
        assert!(
            !t.ancestors(me).is_empty(),
            "test jarayonining ota-jarayoni ko'rinadi"
        );
    }
}
