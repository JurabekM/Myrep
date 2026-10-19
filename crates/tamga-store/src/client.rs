//! Daemon bilan sinxron mijoz (hook va CLI uchun): named pipe orqali bitta JSON qator so'rov/javob.
//!
//! Protokol — har yo'nalishda `\n` bilan tugaydigan bitta JSON obyekt:
//!
//! | `op` | So'rov maydonlari | Javob |
//! |---|---|---|
//! | `hook` | `agent`, `input` (agentning xom hook JSON'i) | `{ok, seq, verdict, reason}` |
//! | `status` | — | `{ok, log, records, checkpointed, key, home, pid}` |
//! | `checkpoint` | — | `{ok, size}` |

use std::fs::OpenOptions;
use std::io::{BufRead as _, BufReader, Write as _};
use std::path::Path;
use std::time::{Duration, Instant};

use serde_json::Value;

/// `ERROR_PIPE_BUSY`: barcha pipe nusxalari band — qisqa kutib qayta urinamiz.
const ERROR_PIPE_BUSY: i32 = 231;

#[derive(Debug, thiserror::Error)]
pub enum ClientError {
    #[error("daemon'ga ulanib bo'lmadi: {0}")]
    Connect(std::io::Error),
    #[error("daemon bilan aloqa uzildi: {0}")]
    Io(std::io::Error),
    #[error("daemon javobi noto'g'ri: {0}")]
    Protocol(String),
    #[error("pipe serveri ishonchli emas: {0}")]
    Untrusted(String),
}

/// O'rnatish turiga qarab daemon'ga ulanadi:
/// - oddiy rejim — `pipe_name()`, kerak bo'lsa `spawn` (yonidagi `tamgad`) ishga tushiriladi;
/// - himoyalangan rejim — xizmat pipe'i, hech narsa ishga tushirilmaydi (xizmatni SCM boshqaradi) va
///   server jarayoni SCM bo'yicha ishlab turgan `tamgad` xizmatining o'zi va `install_dir\tamgad.exe`
///   ekani tekshiriladi: pipe nomini oldindan egallab olgan soxta server bilan gaplashilmaydi.
pub fn connect_auto(spawn: Option<&Path>, wait: Duration) -> Result<std::fs::File, ClientError> {
    use crate::home::{Deployment, deployment, pipe_name};
    match deployment() {
        Deployment::PerUser => connect(&pipe_name(), spawn, wait),
        Deployment::Service(s) => {
            let f = connect(&s.pipe, None, wait)?;
            verify_server(&f, &s.install_dir.join("tamgad.exe"))?;
            Ok(f)
        }
    }
}

#[cfg(windows)]
fn verify_server(f: &std::fs::File, expected: &Path) -> Result<(), ClientError> {
    let canon = |p: &Path| {
        std::fs::canonicalize(p)
            .unwrap_or_else(|_| p.to_path_buf())
            .to_string_lossy()
            .to_lowercase()
    };
    use tamga_win::service::{SERVICE_NAME, pipe_server_pid, process_image, service_pid};
    // Exe yo'li yetarli emas: oddiy foydalanuvchi o'rnatish papkasidagi `tamgad.exe` ni o'zi ham
    // ishga tushira oladi (xizmat to'xtagan paytda pipe nomini egallash uchun). Server — aynan SCM
    // ishga tushirgan xizmat jarayoni bo'lishi shart.
    let pid = pipe_server_pid(f)
        .ok_or_else(|| ClientError::Untrusted("server jarayoni aniqlanmadi".into()))?;
    match service_pid(SERVICE_NAME) {
        Some(svc) if svc == pid => {}
        Some(svc) => {
            return Err(ClientError::Untrusted(format!(
                "pipe serveri PID {pid}, xizmat PID {svc}"
            )));
        }
        None => {
            return Err(ClientError::Untrusted(format!(
                "`{SERVICE_NAME}` xizmati ishlamayapti, pipe serveri (PID {pid}) — begona jarayon"
            )));
        }
    }
    let got = process_image(pid)
        .ok_or_else(|| ClientError::Untrusted("server exe yo'li aniqlanmadi".into()))?;
    if canon(&got) == canon(expected) {
        Ok(())
    } else {
        Err(ClientError::Untrusted(format!(
            "{} (kutilgan {})",
            got.display(),
            expected.display()
        )))
    }
}

#[cfg(not(windows))]
fn verify_server(_f: &std::fs::File, _expected: &Path) -> Result<(), ClientError> {
    Ok(())
}

fn open(pipe: &str) -> std::io::Result<std::fs::File> {
    OpenOptions::new().read(true).write(true).open(pipe)
}

/// Pipe'ga ulanadi. Daemon ishlamayotgan bo'lsa va `spawn` berilgan bo'lsa — uni ishga tushirib,
/// `wait` muddatgacha qayta urinadi.
pub fn connect(
    pipe: &str,
    spawn: Option<&Path>,
    wait: Duration,
) -> Result<std::fs::File, ClientError> {
    let start = Instant::now();
    let mut spawned = false;
    loop {
        match open(pipe) {
            Ok(f) => return Ok(f),
            Err(e) => {
                let busy = e.raw_os_error() == Some(ERROR_PIPE_BUSY);
                if !busy && !spawned {
                    if let Some(exe) = spawn {
                        spawn_daemon(exe).map_err(ClientError::Connect)?;
                        spawned = true;
                    } else {
                        return Err(ClientError::Connect(e));
                    }
                }
                if start.elapsed() >= wait {
                    return Err(ClientError::Connect(e));
                }
                std::thread::sleep(Duration::from_millis(if busy { 5 } else { 40 }));
            }
        }
    }
}

/// Daemon'ni konsol oynasisiz va chaqiruvchining std handle'larini meros qilmasdan ishga tushiradi
/// (aks holda Claude Code hook chiqishining EOF'ini daemon to'xtaguncha kutadi — `tamga-win`).
fn spawn_daemon(exe: &Path) -> std::io::Result<()> {
    tamga_win::spawn_detached(exe)
}

/// Bitta so'rov yuboradi va javobni qaytaradi.
pub fn request(pipe: &mut std::fs::File, req: &Value) -> Result<Value, ClientError> {
    let mut line = serde_json::to_string(req).expect("json");
    line.push('\n');
    pipe.write_all(line.as_bytes()).map_err(ClientError::Io)?;
    pipe.flush().map_err(ClientError::Io)?;
    let mut reader = BufReader::new(pipe);
    let mut resp = String::new();
    reader.read_line(&mut resp).map_err(ClientError::Io)?;
    if resp.is_empty() {
        return Err(ClientError::Protocol("bo'sh javob".into()));
    }
    serde_json::from_str(&resp).map_err(|e| ClientError::Protocol(e.to_string()))
}
