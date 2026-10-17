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
