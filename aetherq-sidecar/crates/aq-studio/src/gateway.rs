//! Standart PQ-TLS rejimi: `aqctl gateway serve|connect` bola jarayoni.
//!
//! - Konsol oynasi ochilmaydi (`CREATE_NO_WINDOW`).
//! - Jarayon Windows Job Object'ga biriktiriladi: GUI qanday yopilmasin (hatto Task Manager bilan),
//!   bola jarayon ham o'chadi va portni band qilib qolmaydi.
//! - stderr qatorlari dvigatelga yuboriladi; server tomoni `/metrics` dan hisoblagichlarni o'qiydi.

use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::Sender;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use crate::engine::Msg;

/// Gateway `/metrics` hisoblagichlari.
#[derive(Default, Clone, Debug, PartialEq)]
pub struct GwMetrics {
    pub ok: bool,
    pub connections: u64,
    pub failures: u64,
    pub active: u64,
    pub up: u64,
    pub down: u64,
    pub hs_sum: f64,
    pub hs_count: u64,
}

pub struct GwProcess {
    child: Child,
    stop: Arc<AtomicBool>,
    pub metrics: Option<Arc<Mutex<GwMetrics>>>,
}

impl GwProcess {
    /// Jarayon tugaganmi (tugagan bo'lsa chiqish kodi).
    pub fn exited(&mut self) -> Option<Option<i32>> {
        match self.child.try_wait() {
            Ok(Some(st)) => Some(st.code()),
            Ok(None) => None,
            Err(_) => Some(None),
        }
    }

    pub fn kill(mut self) {
        self.stop.store(true, Ordering::SeqCst);
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// Bo'sh mahalliy port (metrika uchun).
pub fn free_local_port() -> Option<u16> {
    TcpListener::bind("127.0.0.1:0").ok().and_then(|l| l.local_addr().ok()).map(|a| a.port())
}

pub fn spawn(
    aqctl: &Path,
    args: &[String],
    profile_id: &str,
    tx: Sender<Msg>,
    metrics_addr: Option<String>,
) -> std::io::Result<GwProcess> {
    let mut cmd = Command::new(aqctl);
    cmd.args(args).stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let mut child = cmd.spawn()?;
    job::assign(&child);
    let stop = Arc::new(AtomicBool::new(false));
    for stream in [child.stderr.take().map(|s| Box::new(s) as Box<dyn Read + Send>), child.stdout.take().map(|s| Box::new(s) as Box<dyn Read + Send>)]
        .into_iter()
        .flatten()
    {
        let tx = tx.clone();
        let id = profile_id.to_string();
        thread::spawn(move || {
            for line in BufReader::new(stream).lines().map_while(Result::ok) {
                let line = line.trim_end().to_string();
                if !line.is_empty() && tx.send(Msg::GwLine(id.clone(), line)).is_err() {
                    break;
                }
            }
        });
    }
    let metrics = metrics_addr.map(|addr| {
        let m = Arc::new(Mutex::new(GwMetrics::default()));
        let (m2, stop2) = (m.clone(), stop.clone());
        thread::spawn(move || {
            while !stop2.load(Ordering::SeqCst) {
                if let Some(v) = fetch_metrics(&addr) {
                    *m2.lock().unwrap_or_else(|p| p.into_inner()) = v;
                }
                thread::sleep(Duration::from_millis(1000));
            }
        });
        m
    });
    Ok(GwProcess { child, stop, metrics })
}

/// `/metrics` ni oddiy HTTP/1.0 bilan o'qiydi.
fn fetch_metrics(addr: &str) -> Option<GwMetrics> {
    let mut s = TcpStream::connect_timeout(&addr.parse().ok()?, Duration::from_millis(500)).ok()?;
    s.set_read_timeout(Some(Duration::from_secs(2))).ok()?;
    s.write_all(b"GET /metrics HTTP/1.0\r\nHost: localhost\r\n\r\n").ok()?;
    let mut body = String::new();
    s.read_to_string(&mut body).ok()?;
    Some(parse_metrics(&body))
}

pub fn parse_metrics(text: &str) -> GwMetrics {
    let mut m = GwMetrics { ok: true, ..Default::default() };
    for line in text.lines() {
        if line.starts_with('#') {
            continue;
        }
        let Some((k, v)) = line.rsplit_once(' ') else {
            continue;
        };
        let f: f64 = v.trim().parse().unwrap_or(0.0);
        match k.trim() {
            "aqgw_connections_total" => m.connections = f as u64,
            "aqgw_handshake_failures_total" => m.failures = f as u64,
            "aqgw_active_connections" => m.active = f.max(0.0) as u64,
            "aqgw_bytes_total{direction=\"upstream\"}" => m.up = f as u64,
            "aqgw_bytes_total{direction=\"downstream\"}" => m.down = f as u64,
            "aqgw_handshake_seconds_sum" => m.hs_sum = f,
            "aqgw_handshake_seconds_count" => m.hs_count = f as u64,
            _ => {}
        }
    }
    m
}

#[cfg(windows)]
mod job {
    use std::os::windows::io::AsRawHandle;
    use std::sync::OnceLock;

    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation, SetInformationJobObject,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };

    /// Jarayon bo'yicha bitta job (handle usize sifatida — Send/Sync).
    fn handle() -> Option<usize> {
        static JOB: OnceLock<Option<usize>> = OnceLock::new();
        *JOB.get_or_init(|| {
            // SAFETY: Win32 API; null atributlar va nom — anonim job. Natija tekshiriladi.
            unsafe {
                let h = CreateJobObjectW(std::ptr::null(), std::ptr::null());
                if h.is_null() {
                    return None;
                }
                let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
                info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
                let ok = SetInformationJobObject(
                    h,
                    JobObjectExtendedLimitInformation,
                    &info as *const _ as *const core::ffi::c_void,
                    std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
                );
                (ok != 0).then_some(h as usize)
            }
        })
    }

    pub fn assign(child: &std::process::Child) {
        if let Some(h) = handle() {
            // SAFETY: ikkala handle ham tirik (job jarayon oxirigacha, child — chaqiruvchida).
            unsafe {
                AssignProcessToJobObject(h as *mut core::ffi::c_void, child.as_raw_handle() as *mut core::ffi::c_void);
            }
        }
    }
}

#[cfg(not(windows))]
mod job {
    pub fn assign(_child: &std::process::Child) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_gateway_metrics_text() {
        let t = "# HELP x\naqgw_connections_total 12\naqgw_handshake_failures_total 2\naqgw_active_connections 1\n\
                 aqgw_bytes_total{direction=\"upstream\"} 100\naqgw_bytes_total{direction=\"downstream\"} 250\n\
                 aqgw_handshake_seconds_sum 0.05\naqgw_handshake_seconds_count 10\n";
        let m = parse_metrics(t);
        assert_eq!((m.connections, m.failures, m.active, m.up, m.down, m.hs_count), (12, 2, 1, 100, 250, 10));
        assert!((m.hs_sum - 0.05).abs() < 1e-9 && m.ok);
    }
}
