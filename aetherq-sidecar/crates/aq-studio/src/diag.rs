//! Diagnostika vositalari: port tekshiruvi, manzilga ulanish, tunel orqali HTTP sinovi, ichki sinov
//! serveri va kripto o'z-o'zini tekshirish. Uzoq amallar fon thread'ida (`Task`) bajariladi.

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream, ToSocketAddrs, UdpSocket};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc::{channel, Receiver};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

/// Fon vazifasi: natija tayyor bo'lgach `poll` uni bir marta qaytaradi.
pub struct Task<T> {
    rx: Receiver<T>,
}

impl<T: Send + 'static> Task<T> {
    pub fn spawn(f: impl FnOnce() -> T + Send + 'static) -> Task<T> {
        let (tx, rx) = channel();
        thread::spawn(move || {
            let _ = tx.send(f());
        });
        Task { rx }
    }

    pub fn poll(&self) -> Option<T> {
        self.rx.try_recv().ok()
    }
}

/// Manzil bo'shmi (bind qilib ko'radi).
pub fn port_free(addr: &str) -> Result<(), String> {
    let a: SocketAddr = addr.trim().parse().map_err(|_| "Manzil IP:port ko'rinishida bo'lsin.".to_string())?;
    TcpListener::bind(a).map(|_| ()).map_err(|e| format!("{e} — {}", aq_sidecar::explain_io(&e)))
}

/// TCP ulanish vaqti (ms).
pub fn tcp_reach(addr: &str, timeout: Duration) -> Result<f64, String> {
    let addrs: Vec<SocketAddr> =
        addr.trim().to_socket_addrs().map_err(|e| format!("Manzil topilmadi: {e}"))?.collect();
    let mut last = String::from("manzil topilmadi");
    for a in addrs {
        let t = Instant::now();
        match TcpStream::connect_timeout(&a, timeout) {
            Ok(_) => return Ok(t.elapsed().as_secs_f64() * 1e3),
            Err(e) => last = format!("{e} — {}", aq_sidecar::explain_io(&e)),
        }
    }
    Err(last)
}

/// Ulanish ochildi, lekin hech qanday javob kelmay yopildi.
pub const EMPTY_REPLY: &str = "Javob kelmadi: ulanish bo'sh holda yopildi.";

#[derive(Clone, Debug)]
pub struct HttpProbe {
    pub ms: f64,
    pub status_line: String,
    pub preview: String,
    pub bytes: usize,
}

/// Mahalliy port (klient tuneli) orqali `GET path` — javobni 8 s ichida o'qiydi.
pub fn http_probe(addr: &str, path: &str) -> Result<HttpProbe, String> {
    let a: SocketAddr = addr.trim().parse().map_err(|_| "Manzil IP:port bo'lsin.".to_string())?;
    let t = Instant::now();
    let mut s = TcpStream::connect_timeout(&a, Duration::from_secs(3))
        .map_err(|e| format!("Mahalliy portga ulanib bo'lmadi: {e} — tunel ishga tushirilganmi?"))?;
    s.set_read_timeout(Some(Duration::from_secs(8))).ok();
    let path = if path.starts_with('/') { path.to_string() } else { format!("/{path}") };
    let req = format!("GET {path} HTTP/1.1\r\nHost: {a}\r\nUser-Agent: aq-studio\r\nConnection: close\r\n\r\n");
    s.write_all(req.as_bytes()).map_err(|e| format!("Yuborib bo'lmadi: {e}"))?;
    let mut buf = Vec::new();
    let mut chunk = [0u8; 8192];
    loop {
        match s.read(&mut chunk) {
            Ok(0) => break,
            Ok(n) => {
                buf.extend_from_slice(&chunk[..n]);
                if buf.len() > 256 * 1024 {
                    break;
                }
            }
            Err(e) if buf.is_empty() => {
                return Err(match e.kind() {
                    std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut => {
                        "8 s ichida javob kelmadi: ilova javob bermayapti yoki tunel ochilmadi.".into()
                    }
                    _ => format!("Ulanish uzildi: {e}"),
                })
            }
            Err(_) => break,
        }
    }
    if buf.is_empty() {
        return Err(EMPTY_REPLY.into());
    }
    let text = String::from_utf8_lossy(&buf);
    let status_line = text.lines().next().unwrap_or("").to_string();
    let body = text.split_once("\r\n\r\n").map(|(_, b)| b).unwrap_or("");
    let preview: String = body.chars().take(300).collect();
    Ok(HttpProbe { ms: t.elapsed().as_secs_f64() * 1e3, status_line, preview, bytes: buf.len() })
}

/// Ichki sinov serveri: har so'rovga JSON javob. Namuna ilova o'rnida (demo va diagnostika).
pub struct TestServer {
    pub addr: SocketAddr,
    pub requests: Arc<AtomicU64>,
    stop: Arc<AtomicBool>,
    handle: Option<JoinHandle<()>>,
}

impl TestServer {
    pub fn start(addr: &str) -> Result<TestServer, String> {
        let l = TcpListener::bind(addr.trim()).map_err(|e| format!("{}: {e} — {}", addr.trim(), aq_sidecar::explain_io(&e)))?;
        let local = l.local_addr().map_err(|e| e.to_string())?;
        let stop = Arc::new(AtomicBool::new(false));
        let requests = Arc::new(AtomicU64::new(0));
        let (st, rq) = (stop.clone(), requests.clone());
        let handle = thread::spawn(move || {
            for c in l.incoming() {
                if st.load(Ordering::SeqCst) {
                    break;
                }
                if let Ok(c) = c {
                    let rq = rq.clone();
                    thread::spawn(move || serve_one(c, rq));
                }
            }
        });
        Ok(TestServer { addr: local, requests, stop, handle: Some(handle) })
    }

    pub fn stop(mut self) {
        self.shutdown();
    }

    fn shutdown(&mut self) {
        if self.stop.swap(true, Ordering::SeqCst) {
            return;
        }
        let wake = if self.addr.ip().is_unspecified() {
            SocketAddr::from(([127, 0, 0, 1], self.addr.port()))
        } else {
            self.addr
        };
        let _ = TcpStream::connect_timeout(&wake, Duration::from_millis(300));
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
    }
}

impl Drop for TestServer {
    fn drop(&mut self) {
        self.shutdown();
    }
}

fn serve_one(mut c: TcpStream, requests: Arc<AtomicU64>) {
    let _ = c.set_read_timeout(Some(Duration::from_secs(5)));
    let mut buf = Vec::new();
    let mut chunk = [0u8; 4096];
    while !buf.windows(4).any(|w| w == b"\r\n\r\n") && buf.len() < 64 * 1024 {
        match c.read(&mut chunk) {
            Ok(0) | Err(_) => return,
            Ok(n) => buf.extend_from_slice(&chunk[..n]),
        }
    }
    let n = requests.fetch_add(1, Ordering::Relaxed) + 1;
    let head = String::from_utf8_lossy(&buf);
    let first = head.lines().next().unwrap_or("");
    let path = first.split_whitespace().nth(1).unwrap_or("/");
    let path_json = path.replace('\\', "\\\\").replace('"', "\\\"");
    let body = format!(
        "{{\"status\":\"ok\",\"server\":\"AETHER-Q Studio sinov serveri\",\"path\":\"{path_json}\",\"request\":{n},\"time\":\"{}\"}}\n",
        crate::timefmt::rfc3339(crate::timefmt::now_unix())
    );
    let resp = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    let _ = c.write_all(resp.as_bytes());
}

/// Kripto o'z-o'zini tekshirish: jarayon ichida `n` ta to'liq handshake (mutual auth, ML-KEM-768 + X25519,
/// ML-DSA-65) va transport record aylanishi. Qaytaradi: o'rtacha ms.
pub fn crypto_selftest(n: usize) -> Result<f64, String> {
    use aq_core::handshake::{ClientConfig, ClientHs, ServerConfig, ServerHs};
    use aq_core::Identity;
    let srv = Identity::generate().map_err(|e| e.to_string())?;
    let cli = Identity::generate().map_err(|e| e.to_string())?;
    let t = Instant::now();
    for _ in 0..n.max(1) {
        let mut c = ClientHs::new(ClientConfig {
            server_pub: Some(srv.pk.clone()),
            identity: Some(cli.clone()),
            ..Default::default()
        });
        let mut s = ServerHs::new(ServerConfig {
            identity: Some(srv.clone()),
            require_client_auth: true,
            allowed_clients: Some(vec![cli.pk.clone()]),
            ..Default::default()
        });
        let ch = c.start().map_err(|e| e.to_string())?;
        let sh = s.recv_hello(&ch, None).map_err(|e| e.to_string())?.into_bytes();
        let flight = c.recv(&sh).map_err(|e| e.to_string())?.ok_or("klient flight yo'q")?;
        let sf = s.recv_flight(&flight).map_err(|e| e.to_string())?;
        c.recv(&sf).map_err(|e| e.to_string())?;
        if !c.is_connected() {
            return Err("handshake yakunlanmadi".into());
        }
        let mut cs = c.finish().map_err(|e| e.to_string())?.session;
        let mut ss = s.finish().map_err(|e| e.to_string())?.session;
        let rec = cs.seal(b"AETHER-Q").map_err(|e| e.to_string())?;
        let (_, pt) = ss.open(&rec).map_err(|e| e.to_string())?;
        if pt != b"AETHER-Q" {
            return Err("transport record mos emas".into());
        }
    }
    Ok(t.elapsed().as_secs_f64() * 1e3 / n.max(1) as f64)
}

/// Asosiy tarmoq IP manzili (paket yuborilmaydi — faqat marshrut tanlanadi).
pub fn primary_ip() -> Option<String> {
    let s = UdpSocket::bind("0.0.0.0:0").ok()?;
    s.connect("8.8.8.8:80").ok()?;
    let ip = s.local_addr().ok()?.ip();
    (!ip.is_unspecified() && !ip.is_loopback()).then(|| ip.to_string())
}

pub fn hostname() -> String {
    std::env::var("COMPUTERNAME").or_else(|_| std::env::var("HOSTNAME")).unwrap_or_else(|_| "bu-kompyuter".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_answers_http_probe_and_stops() {
        let srv = TestServer::start("127.0.0.1:0").unwrap();
        let addr = srv.addr.to_string();
        let r = http_probe(&addr, "/salom").unwrap();
        assert!(r.status_line.contains("200"), "{r:?}");
        assert!(r.preview.contains("\"path\":\"/salom\""), "{r:?}");
        assert_eq!(srv.requests.load(Ordering::Relaxed), 1);
        assert!(tcp_reach(&addr, Duration::from_secs(1)).is_ok());
        assert!(port_free(&addr).is_err(), "band port");
        srv.stop();
        assert!(port_free(&addr).is_ok(), "to'xtatilgandan keyin port bo'sh");
        assert!(http_probe(&addr, "/").is_err());
    }

    #[test]
    fn crypto_selftest_runs() {
        let ms = crypto_selftest(2).unwrap();
        assert!(ms > 0.0);
    }
}
