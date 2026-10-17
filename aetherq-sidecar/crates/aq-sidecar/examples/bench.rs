//! O'lchov (MEASURED): handshake vaqti va tunel throughput'i.
//!
//! Ishga tushirish (release, repo ildizidan):
//!   powershell -File scripts\cargo-msvc.ps1 build --release --workspace
//!   powershell -File scripts\cargo-msvc.ps1 run --release -p aq-sidecar --example bench
//!
//! Stsenariylar:
//!   1. Handshake, faqat protokol (in-memory, I/O yo'q)
//!   2. Handshake, TCP loopback (sidecar `serve` ga), va klassik TCP connect bazasi
//!   3. Throughput: AETHER tunel (client → serve → echo) va bazaviy TCP (client → echo)
//!   4. AEAD record (seal+open) — faqat shifrlash, I/O yo'q

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use aq_core::handshake::{ClientConfig, ClientHs, ServerConfig, ServerHs};
use aq_core::net::{client_handshake, read_record};
use aq_core::{Identity, Role, Session};

const ECHO_PORT: u16 = 19100;
const SERVE_PORT: u16 = 19101;
const CHUNK: usize = 16 * 1024;
const TOTAL: usize = 64 * 1024 * 1024;

fn percentile(v: &mut [f64], p: f64) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let idx = ((v.len() as f64 - 1.0) * p).round() as usize;
    v[idx]
}

fn report(name: &str, v: &mut Vec<f64>) {
    let mean = v.iter().sum::<f64>() / v.len() as f64;
    let p50 = percentile(v, 0.50);
    let p99 = percentile(v, 0.99);
    println!("{name:<44} n={:<5} mean={mean:>8.3} ms  p50={p50:>8.3} ms  p99={p99:>8.3} ms", v.len());
}

fn sidecar_path() -> PathBuf {
    // target/release/examples/bench.exe → target/release/aq-sidecar.exe
    let mut p = std::env::current_exe().expect("exe path");
    p.pop();
    p.pop();
    p.push("aq-sidecar.exe");
    p
}

fn wait_port(port: u16) {
    for _ in 0..200 {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return;
        }
        thread::sleep(Duration::from_millis(25));
    }
    panic!("port {port} tayyor bo'lmadi");
}

fn start_echo(port: u16) {
    let l = TcpListener::bind(("127.0.0.1", port)).unwrap();
    thread::spawn(move || {
        for c in l.incoming().flatten() {
            thread::spawn(move || {
                let mut c = c;
                let mut buf = vec![0u8; 64 * 1024];
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
            });
        }
    });
}

fn spawn_sidecar(identity_path: &str, upstream: u16) -> Child {
    Command::new(sidecar_path())
        .args([
            "serve",
            "--listen",
            &format!("127.0.0.1:{SERVE_PORT}"),
            "--upstream",
            &format!("127.0.0.1:{upstream}"),
            "--identity",
            identity_path,
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("aq-sidecar ishga tushmadi (avval release build)")
}

/// 1) Faqat protokol: ikkala tomon bir jarayonda, I/O yo'q.
fn bench_inmemory_handshake(srv: &Identity, n: usize) -> Vec<f64> {
    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        let t = Instant::now();
        let mut c = ClientHs::new(ClientConfig { server_pub: Some(srv.pk.clone()), identity: None, ..Default::default() });
        let ch = c.start().unwrap();
        let mut s = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
        let sh = s.recv_hello(&ch, None).unwrap().into_bytes();
        let flight = c.recv(&sh).unwrap().unwrap();
        let sf = s.recv_flight(&flight).unwrap();
        c.recv(&sf).unwrap();
        out.push(t.elapsed().as_secs_f64() * 1e3);
    }
    out
}

/// 2) TCP: AETHER handshake (sidecar'ga) va klassik TCP connect (echo'ga).
fn bench_tcp_handshake(srv_pk: &[u8], n: usize) -> (Vec<f64>, Vec<f64>) {
    let mut hs = Vec::with_capacity(n);
    let mut plain = Vec::with_capacity(n);
    for _ in 0..n {
        let t = Instant::now();
        let mut s = TcpStream::connect(("127.0.0.1", SERVE_PORT)).unwrap();
        let _sess = client_handshake(&mut s, ClientConfig { server_pub: Some(srv_pk.to_vec()), identity: None, ..Default::default() })
            .unwrap();
        hs.push(t.elapsed().as_secs_f64() * 1e3);
        drop(s);
        let t = Instant::now();
        let _p = TcpStream::connect(("127.0.0.1", ECHO_PORT)).unwrap();
        plain.push(t.elapsed().as_secs_f64() * 1e3);
    }
    (hs, plain)
}

/// 3b) Bazaviy TCP throughput: 64 MiB → echo → 64 MiB (shifrsiz).
fn bench_plain_throughput() -> f64 {
    let mut sock = TcpStream::connect(("127.0.0.1", ECHO_PORT)).unwrap();
    let mut rd = sock.try_clone().unwrap();
    let t = Instant::now();
    let reader = thread::spawn(move || {
        let mut buf = vec![0u8; CHUNK];
        let mut got = 0usize;
        while got < TOTAL {
            let n = rd.read(&mut buf).unwrap();
            if n == 0 {
                break;
            }
            got += n;
        }
        got
    });
    let data = vec![0x5Au8; CHUNK];
    let mut sent = 0usize;
    while sent < TOTAL {
        sock.write_all(&data).unwrap();
        sent += CHUNK;
    }
    let got = reader.join().unwrap();
    assert_eq!(got, TOTAL);
    let secs = t.elapsed().as_secs_f64();
    TOTAL as f64 / secs / (1024.0 * 1024.0)
}

/// 4) AEAD record: seal + open, 16 KiB, I/O yo'q.
fn bench_aead(n_bytes: usize) -> f64 {
    let master = [3u8; 32];
    let mut cli = Session::from_master(&master, 1, Role::Client);
    let mut srv = Session::from_master(&master, 1, Role::Server);
    let data = vec![0xA5u8; CHUNK];
    let t = Instant::now();
    let mut done = 0usize;
    while done < n_bytes {
        let rec = cli.seal(&data).unwrap();
        let (_, pt) = srv.open(&rec).unwrap();
        assert_eq!(pt.len(), CHUNK);
        done += CHUNK;
    }
    let secs = t.elapsed().as_secs_f64();
    n_bytes as f64 / secs / (1024.0 * 1024.0)
}

fn main() {
    let srv = Identity::from_seed([0x5E; 32]);
    let key_path = std::env::temp_dir().join("aq-bench-server.key");
    srv.save(&key_path).unwrap();
    start_echo(ECHO_PORT);
    wait_port(ECHO_PORT);
    let mut child = spawn_sidecar(key_path.to_str().unwrap(), ECHO_PORT);
    wait_port(SERVE_PORT);

    println!("== Handshake (MEASURED, bu mashina, release) ==");
    let mut inmem = bench_inmemory_handshake(&srv, 300);
    report("handshake, faqat protokol (in-memory)", &mut inmem);
    let (mut tcp_hs, mut plain_conn) = bench_tcp_handshake(&srv.pk, 200);
    report("handshake, TCP loopback (sidecar serve)", &mut tcp_hs);
    report("bazaviy TCP connect (echo, handshake'siz)", &mut plain_conn);

    println!("\n== Throughput (MEASURED) ==");
    let tunnel = bench_tunnel_throughput_full(&srv.pk);
    let plain = bench_plain_throughput();
    println!("bazaviy TCP (client <-> echo)                {plain:>8.1} MiB/s");
    println!("AETHER tunel (client <-> sidecar <-> echo)   {tunnel:>8.1} MiB/s");

    println!("\n== AEAD record (MEASURED, I/O yo'q) ==");
    println!("ChaCha20-Poly1305 record seal+open, 16 KiB   {:>8.1} MiB/s", bench_aead(256 * 1024 * 1024));

    let _ = child.kill();
    let _ = child.wait();
}

/// Tunel throughput'i to'liq: yozish va o'qish alohida thread'larda.
fn bench_tunnel_throughput_full(srv_pk: &[u8]) -> f64 {
    let mut sock = TcpStream::connect(("127.0.0.1", SERVE_PORT)).unwrap();
    let sess = client_handshake(&mut sock, ClientConfig { server_pub: Some(srv_pk.to_vec()), ..Default::default() })
        .unwrap()
        .session;
    let (mut tx, mut rx) = sess.split();
    let mut rd = sock.try_clone().unwrap();
    let t = Instant::now();
    let reader = thread::spawn(move || {
        let mut got = 0usize;
        while got < TOTAL {
            let rec = read_record(&mut rd).unwrap();
            let (_, pt) = rx.open(&rec).unwrap();
            got += pt.len();
        }
        got
    });
    let data = vec![0x5Au8; CHUNK];
    let mut sent = 0usize;
    while sent < TOTAL {
        let rec = tx.seal(&data).unwrap();
        sock.write_all(&rec).unwrap();
        sent += CHUNK;
    }
    let got = reader.join().unwrap();
    assert_eq!(got, TOTAL);
    let secs = t.elapsed().as_secs_f64();
    TOTAL as f64 / secs / (1024.0 * 1024.0)
}
