//! Proksi: mahalliy oddiy TCP ↔ AETHER-Q tunel. Ikki yo'nalish — ikki thread.
//!
//! Har bir ulanish uchun:
//!   serve:   peer (AETHER-Q) ──records──> sidecar ──plain──> monolit (upstream)
//!   connect: monolit ──plain──> sidecar ──records──> peer (serve)

use std::io::{Read, Write};
use std::net::{Shutdown, TcpStream};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

use aq_core::dos::PuzzleAuthority;
use aq_core::handshake::{ClientConfig, ServerConfig};
use aq_core::net::{client_handshake, read_record, server_handshake, SessionCache};
use aq_core::ticket::TicketAuthority;
use aq_core::transport::TYPE_APP_DATA;
use aq_core::{Identity, Session};

/// Maksimal bitta chunk (plaintext). Record ≤ 16 KiB + sarlavha.
pub const CHUNK: usize = 16 * 1024;
/// Handshake vaqtidagi o'qish kutish chegarasi (slow-loris himoyasi).
pub const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(20);

/// Ikki oqimni AETHER-Q sessiyasi orqali bog'laydi. `plain` — mahalliy oddiy oqim,
/// `wire` — AETHER-Q record'lari oqadigan oqim. Ikkalasi tugaguncha bloklaydi.
pub fn pump(session: Session, plain: TcpStream, wire: TcpStream) {
    let (mut tx, mut rx) = session.split();
    let mut plain_r = match plain.try_clone() {
        Ok(s) => s,
        Err(_) => return,
    };
    let mut wire_w = match wire.try_clone() {
        Ok(s) => s,
        Err(_) => return,
    };
    let mut wire_r = wire;
    let mut plain_w = plain;

    // plain → wire: har o'qishni bitta record qilib shifrlaydi.
    let up = thread::spawn(move || {
        let mut buf = vec![0u8; CHUNK];
        loop {
            let n = match plain_r.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => n,
            };
            let rec = match tx.seal(&buf[..n]) {
                Ok(r) => r,
                Err(_) => break,
            };
            if wire_w.write_all(&rec).is_err() {
                break;
            }
        }
        let _ = wire_w.shutdown(Shutdown::Write);
    });

    // wire → plain: record'ni ochadi va plaintext'ni yozadi.
    let down = thread::spawn(move || {
        loop {
            let rec = match read_record(&mut wire_r) {
                Ok(r) => r,
                Err(_) => break,
            };
            let (rtype, pt) = match rx.open(&rec) {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("aq-sidecar: record xatosi: {e}");
                    break;
                }
            };
            if rtype != TYPE_APP_DATA {
                continue;
            }
            if plain_w.write_all(&pt).is_err() {
                break;
            }
        }
        let _ = plain_w.shutdown(Shutdown::Write);
    });

    let _ = up.join();
    let _ = down.join();
}

fn short_fp(pk: &[u8]) -> String {
    pk.iter().take(8).map(|b| format!("{b:02x}")).collect()
}

/// Server tomoni: peer ulanishini qabul qilib, monolitga (upstream) tunnel qiladi.
pub fn serve_connection(mut peer: TcpStream, cfg: ServerConfig, upstream: &str) {
    let _ = peer.set_read_timeout(Some(HANDSHAKE_TIMEOUT));
    let est = match server_handshake(&mut peer, cfg) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("aq-sidecar: handshake rad etildi ({}): {e}", peer_name(&peer));
            return;
        }
    };
    let (session, client_pk) = (est.session, est.client_pk);
    match &client_pk {
        Some(pk) => eprintln!("aq-sidecar: ulandi {} klient={}", peer_name(&peer), short_fp(pk)),
        None => eprintln!("aq-sidecar: ulandi {} (klient autentifikatsiyasiz)", peer_name(&peer)),
    }
    let _ = peer.set_read_timeout(None);
    let plain = match TcpStream::connect(upstream) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("aq-sidecar: upstream {upstream} ga ulanmadi: {e}");
            return;
        }
    };
    pump(session, plain, peer);
}

/// Klient tomoni: mahalliy oddiy ulanishni qabul qilib, peer serverga tunnel qiladi.
/// `cache` — resumption (ticket) keshi; `None` bo'lsa resumption o'chirilgan.
pub fn connect_connection(
    local: TcpStream,
    mut cfg: ClientConfig,
    peer_addr: &str,
    cache: Option<(Arc<SessionCache>, String)>,
) {
    if let Some((c, key)) = &cache {
        cfg.resume = c.get(key);
        cfg.want_ticket = true;
    }
    let mut wire = match TcpStream::connect(peer_addr) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("aq-sidecar: peer {peer_addr} ga ulanmadi: {e}");
            return;
        }
    };
    let _ = wire.set_read_timeout(Some(HANDSHAKE_TIMEOUT));
    let est = match client_handshake(&mut wire, cfg) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("aq-sidecar: handshake muvaffaqiyatsiz ({peer_addr}): {e}");
            return;
        }
    };
    if let Some((c, key)) = &cache {
        if let Some(t) = est.new_ticket.clone() {
            c.put(key, t);
        }
    }
    let _ = wire.set_read_timeout(None);
    eprintln!(
        "aq-sidecar: tunel ochildi → {peer_addr}{}",
        if est.resumed { " (resumption)" } else { "" }
    );
    pump(est.session, local, wire);
}

fn peer_name(s: &TcpStream) -> String {
    s.peer_addr().map(|a| a.to_string()).unwrap_or_else(|_| "?".into())
}

/// Server konfiguratsiyasi. `tickets`/`puzzle` jarayon bo'yicha BIR MARTA yaratiladi va Arc orqali
/// barcha ulanishlar bilan ulashiladi (aks holda resumption va PoW ishlamaydi).
pub fn server_cfg(
    identity: Identity,
    require_client_auth: bool,
    allowed: Option<Vec<Vec<u8>>>,
    tickets: Option<Arc<TicketAuthority>>,
    puzzle: Option<Arc<PuzzleAuthority>>,
) -> ServerConfig {
    ServerConfig {
        identity: Some(identity),
        require_client_auth,
        allowed_clients: allowed,
        tickets,
        puzzle,
        ..Default::default()
    }
}

/// Klient konfiguratsiyasi (pinned server kaliti + ixtiyoriy o'z identity'si).
pub fn client_cfg(server_pub: Vec<u8>, identity: Option<Identity>) -> ClientConfig {
    ClientConfig { server_pub: Some(server_pub), identity, ..Default::default() }
}

/// Ticket kesh kaliti: manzil + server ochiq kaliti.
pub fn cache_key(peer: &str, server_pub: &[u8]) -> String {
    format!("{peer}|{}", aq_core::identity::to_hex(server_pub))
}

/// Qisqa fingerprint (log uchun).
pub fn fingerprint(pk: &[u8]) -> String {
    short_fp(pk)
}
