//! Runtime integratsiya testlari: haqiqiy TCP, jarayon ichida serve + connect.

use std::io::{Read, Write};
use std::net::{Shutdown, TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use aq_core::error::alert;
use aq_core::Identity;
use aq_sidecar::runtime::{ConnectOptions, Event, ServeOptions, Sink, Tunnel};

/// Hodisalarni yig'uvchi.
fn collector() -> (Sink, Arc<Mutex<Vec<Event>>>) {
    let store = Arc::new(Mutex::new(Vec::new()));
    let s = store.clone();
    (Arc::new(move |e| s.lock().unwrap().push(e)), store)
}

fn echo_server() -> String {
    let l = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = l.local_addr().unwrap().to_string();
    thread::spawn(move || {
        for c in l.incoming().flatten() {
            thread::spawn(move || {
                let mut c = c;
                let mut buf = [0u8; 8192];
                loop {
                    match c.read(&mut buf) {
                        Ok(0) | Err(_) => break,
                        Ok(n) => {
                            if c.write_all(&buf[..n]).is_err() {
                                break;
                            }
                        }
                    }
                }
                let _ = c.shutdown(Shutdown::Write);
            });
        }
    });
    addr
}

fn wait_until(mut f: impl FnMut() -> bool) -> bool {
    let t = Instant::now();
    while t.elapsed() < Duration::from_secs(10) {
        if f() {
            return true;
        }
        thread::sleep(Duration::from_millis(10));
    }
    false
}

struct Pair {
    server: Tunnel,
    client: Tunnel,
    sev: Arc<Mutex<Vec<Event>>>,
    cev: Arc<Mutex<Vec<Event>>>,
}

fn pair(srv: &Identity, cli: &Identity, upstream: &str, allowed: Vec<Vec<u8>>, pin: Vec<u8>) -> Pair {
    let (ss, sev) = collector();
    let (cs, cev) = collector();
    let server = Tunnel::serve(
        ServeOptions {
            listen: "127.0.0.1:0".into(),
            upstream: upstream.into(),
            identity: srv.clone(),
            require_client_auth: true,
            allowed: Some(allowed),
            resumption: true,
            ticket_ttl: 3600,
            pow: 0,
        },
        ss,
    )
    .unwrap();
    let client = Tunnel::connect(
        ConnectOptions {
            listen: "127.0.0.1:0".into(),
            peer: server.local_addr().to_string(),
            server_pub: pin,
            identity: Some(cli.clone()),
            resume: true,
        },
        cs,
    )
    .unwrap();
    Pair { server, client, sev, cev }
}

/// Yuborib, javobni EOF'gacha o'qiydi. Tunel rad etilsa sidecar ulanishni yopadi — Windows'da o'qilmagan
/// ma'lumot bo'lsa bu RST (10054) bo'lib keladi; u ham "ma'lumot o'tmadi" deb hisoblanadi.
fn roundtrip(addr: std::net::SocketAddr, payload: &[u8]) -> Vec<u8> {
    let mut s = TcpStream::connect(addr).unwrap();
    s.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
    let _ = s.write_all(payload);
    let _ = s.shutdown(Shutdown::Write);
    let mut out = Vec::new();
    match s.read_to_end(&mut out) {
        Ok(_) => out,
        Err(e) if e.kind() == std::io::ErrorKind::ConnectionReset => out,
        Err(e) => panic!("kutilmagan o'qish xatosi: {e}"),
    }
}

#[test]
fn roundtrip_counts_bytes_and_resumes_second_connection() {
    let up = echo_server();
    let (srv, cli) = (Identity::from_seed([1; 32]), Identity::from_seed([2; 32]));
    let p = pair(&srv, &cli, &up, vec![cli.pk.clone()], srv.pk.clone());
    let payload: Vec<u8> = (0..100_000u32).map(|i| (i * 7 % 251) as u8).collect();
    assert_eq!(roundtrip(p.client.local_addr(), &payload), payload);
    assert_eq!(roundtrip(p.client.local_addr(), b"ikkinchi"), b"ikkinchi");

    let (cs, ss) = (p.client.stats(), p.server.stats());
    assert!(wait_until(|| cs.snapshot().active == 0 && ss.snapshot().active == 0), "tunellar yopilmadi");
    let c = cs.snapshot();
    let s = ss.snapshot();
    assert_eq!((c.total, c.resumed, c.failed), (2, 1, 0), "klient: {c:?}");
    assert_eq!((s.total, s.resumed, s.failed), (2, 1, 0), "server: {s:?}");
    let n = (payload.len() + 8) as u64;
    assert_eq!((c.to_net, c.from_net), (n, n), "klient baytlari");
    assert_eq!((s.to_net, s.from_net), (n, n), "server baytlari");
    assert_eq!(c.hs_n, 2);
    assert!(c.hs_p50 > 0.0 && c.hs_p99 >= c.hs_p50);

    let sev = p.sev.lock().unwrap();
    let accepted: Vec<_> = sev
        .iter()
        .filter_map(|e| match e {
            Event::Accepted { client_pk, resumed, .. } => Some((client_pk.clone(), *resumed)),
            _ => None,
        })
        .collect();
    assert_eq!(accepted, vec![(Some(cli.pk.clone()), false), (Some(cli.pk.clone()), true)]);
    let cev = p.cev.lock().unwrap();
    assert_eq!(cev.iter().filter(|e| matches!(e, Event::Opened { .. })).count(), 2);
    assert_eq!(cev.iter().filter(|e| matches!(e, Event::Closed { .. })).count(), 2);
}

#[test]
fn wrong_pinned_key_reports_bad_signature_with_hint() {
    let up = echo_server();
    let (srv, cli) = (Identity::from_seed([3; 32]), Identity::from_seed([4; 32]));
    let other = Identity::from_seed([5; 32]);
    let p = pair(&srv, &cli, &up, vec![cli.pk.clone()], other.pk.clone());
    let got = roundtrip(p.client.local_addr(), b"salom");
    assert!(got.is_empty(), "noto'g'ri pin bilan ma'lumot o'tmasligi kerak");
    let cs = p.client.stats();
    assert!(wait_until(|| cs.snapshot().failed == 1));
    let cev = p.cev.lock().unwrap();
    let f = cev.iter().find_map(|e| match e {
        Event::HandshakeFailed { alert, hint, .. } => Some((*alert, *hint)),
        _ => None,
    });
    let (code, hint) = f.expect("HandshakeFailed hodisasi yo'q");
    assert_eq!(code, Some(alert::BAD_SIGNATURE));
    assert!(hint.contains("pinned"), "izoh: {hint}");
}

#[test]
fn client_not_in_allowlist_is_rejected_on_both_sides() {
    let up = echo_server();
    let (srv, cli) = (Identity::from_seed([6; 32]), Identity::from_seed([7; 32]));
    let stranger = Identity::from_seed([8; 32]);
    let p = pair(&srv, &cli, &up, vec![stranger.pk.clone()], srv.pk.clone());
    assert!(roundtrip(p.client.local_addr(), b"x").is_empty());
    let ss = p.server.stats();
    assert!(wait_until(|| ss.snapshot().failed == 1));
    let sev = p.sev.lock().unwrap();
    assert!(sev
        .iter()
        .any(|e| matches!(e, Event::HandshakeFailed { alert: Some(a), .. } if *a == alert::BAD_CLIENT_AUTH)));
    assert_eq!(ss.snapshot().total, 0);
}

#[test]
fn unreachable_upstream_reports_dial_failure() {
    // Bo'sh port: bind qilib, darhol yopamiz.
    let dead = TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().to_string();
    let (srv, cli) = (Identity::from_seed([9; 32]), Identity::from_seed([10; 32]));
    let p = pair(&srv, &cli, &dead, vec![cli.pk.clone()], srv.pk.clone());
    assert!(roundtrip(p.client.local_addr(), b"x").is_empty());
    let ss = p.server.stats();
    assert!(wait_until(|| ss.snapshot().failed == 1));
    let sev = p.sev.lock().unwrap();
    assert!(sev.iter().any(|e| matches!(e, Event::DialFailed { target, .. } if *target == dead)));
}

#[test]
fn busy_port_is_an_error_not_a_panic() {
    let taken = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = taken.local_addr().unwrap().to_string();
    let r = Tunnel::serve(
        ServeOptions {
            listen: addr.clone(),
            upstream: "127.0.0.1:1".into(),
            identity: Identity::from_seed([11; 32]),
            require_client_auth: false,
            allowed: None,
            resumption: false,
            ticket_ttl: 60,
            pow: 0,
        },
        aq_sidecar::null_sink(),
    );
    let e = r.err().expect("band port xato berishi kerak");
    assert!(e.starts_with(&addr), "xato matni manzil bilan boshlansin: {e}");
}

#[test]
fn stop_frees_port_and_closes_open_tunnels() {
    let up = echo_server();
    let (srv, cli) = (Identity::from_seed([12; 32]), Identity::from_seed([13; 32]));
    let p = pair(&srv, &cli, &up, vec![cli.pk.clone()], srv.pk.clone());
    let client_addr = p.client.local_addr();
    let server_addr = p.server.local_addr();

    // Ochiq (uzoq) tunel: yozamiz, echo qaytadi, lekin ulanishni yopmaymiz.
    let mut open = TcpStream::connect(client_addr).unwrap();
    open.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
    open.write_all(b"ping").unwrap();
    let mut buf = [0u8; 4];
    open.read_exact(&mut buf).unwrap();
    assert_eq!(&buf, b"ping");
    let cs = p.client.stats();
    assert_eq!(cs.snapshot().active, 1);

    let cev = p.cev.clone();
    p.client.stop();
    p.server.stop();
    // Ochiq tunel yopildi: o'qish EOF (yoki reset) bilan tugaydi, osilib qolmaydi.
    let mut rest = Vec::new();
    let r = open.read_to_end(&mut rest);
    assert!(r.is_ok() || r.is_err(), "o'qish qaytishi kerak");
    assert!(wait_until(|| cs.snapshot().active == 0), "faol tunel 0 ga tushmadi");
    assert!(cev.lock().unwrap().iter().any(|e| matches!(e, Event::Stopped)));
    // To'xtatish paytida yopilgan ulanish "xato" deb hisoblanmaydi.
    assert_eq!(cs.snapshot().failed, 0);
    // Portlar bo'shadi: xuddi shu manzillarni qayta bind qilish mumkin.
    assert!(wait_until(|| TcpListener::bind(client_addr).is_ok()), "klient porti bo'shamadi");
    assert!(wait_until(|| TcpListener::bind(server_addr).is_ok()), "server porti bo'shamadi");
}
