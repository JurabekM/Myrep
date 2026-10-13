//! Rust ↔ Rust to'liq handshake (TCP loopback) va salbiy stsenariylar.

use std::net::{TcpListener, TcpStream};
use std::thread;

use aq_core::error::alert;
use aq_core::handshake::{ClientConfig, ClientHs, ServerConfig, ServerHs};
use aq_core::kem;
use aq_core::net::{client_handshake, read_frame, server_handshake};
use aq_core::wire;
use aq_core::{AqError, Identity, Role, Session};

fn server_identity(seed: u8) -> Identity {
    Identity::from_seed([seed; 32])
}

/// Server thread: bitta ulanish. `echo` bo'lsa handshake'dan keyin bitta xabarni qaytaradi.
/// Qaytaradi: (port, thread) — thread ichida klient ML-DSA kaliti (mutual auth bo'lsa).
fn spawn_server(
    cfg: ServerConfig,
    echo: bool,
) -> (u16, thread::JoinHandle<Result<Option<Vec<u8>>, AqError>>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let h = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        let est = server_handshake(&mut stream, cfg)?;
        let mut sess = est.session;
        if echo {
            let (_t, msg) = sess.open(&aq_core::net::read_record(&mut stream)?)?;
            let rec = sess.seal(&msg)?;
            std::io::Write::write_all(&mut stream, &rec)?;
        }
        Ok(est.client_pk)
    });
    (port, h)
}

#[test]
fn full_handshake_and_echo_over_tcp() {
    let srv = server_identity(1);
    let (port, h) = spawn_server(
        ServerConfig { identity: Some(srv.clone()), ..Default::default() },
        true,
    );
    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    let est = client_handshake(
        &mut stream,
        ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() },
    )
    .unwrap();
    let mut sess = est.session;
    assert_eq!(sess.role, Role::Client);
    assert!(!est.resumed);
    let rec = sess.seal(b"salom, AETHER-Q").unwrap();
    std::io::Write::write_all(&mut stream, &rec).unwrap();
    let back = aq_core::net::read_record(&mut stream).unwrap();
    let (_t, pt) = sess.open(&back).unwrap();
    assert_eq!(pt, b"salom, AETHER-Q");
    assert!(h.join().unwrap().unwrap().is_none());
}

#[test]
fn mutual_auth_allowed_client_is_identified() {
    let srv = server_identity(2);
    let cli = server_identity(3);
    let (port, h) = spawn_server(
        ServerConfig {
            identity: Some(srv.clone()),
            require_client_auth: true,
            allowed_clients: Some(vec![cli.pk.clone()]),
            ..Default::default()
        },
        false,
    );
    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    let _est = client_handshake(
        &mut stream,
        ClientConfig { server_pub: Some(srv.pk.clone()), identity: Some(cli.clone()), ..Default::default() },
    )
    .unwrap();
    let peer = h.join().unwrap().unwrap();
    assert_eq!(peer.as_deref(), Some(cli.pk.as_slice()));
}

#[test]
fn client_not_in_allowlist_is_rejected() {
    let srv = server_identity(4);
    let stranger = server_identity(5);
    let allowed_one = server_identity(6);
    let (port, h) = spawn_server(
        ServerConfig {
            identity: Some(srv.clone()),
            require_client_auth: true,
            allowed_clients: Some(vec![allowed_one.pk.clone()]),
            ..Default::default()
        },
        false,
    );
    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    let res = client_handshake(
        &mut stream,
        ClientConfig { server_pub: Some(srv.pk.clone()), identity: Some(stranger), ..Default::default() },
    );
    assert!(res.is_err(), "allowlist'da yo'q klient qabul qilindi!");
    match h.join().unwrap() {
        Err(AqError::Alert(c)) => assert_eq!(c, alert::BAD_CLIENT_AUTH),
        other => panic!("server BAD_CLIENT_AUTH kutilgan edi: {other:?}"),
    }
}

#[test]
fn wrong_pinned_server_key_is_rejected() {
    let srv = server_identity(7);
    let imposter_pin = server_identity(8);
    let (port, h) = spawn_server(
        ServerConfig { identity: Some(srv.clone()), ..Default::default() },
        false,
    );
    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    let res = client_handshake(
        &mut stream,
        ClientConfig { server_pub: Some(imposter_pin.pk.clone()), ..Default::default() },
    );
    match res {
        Err(AqError::Alert(c)) => assert_eq!(c, alert::BAD_SIGNATURE),
        Err(other) => panic!("BAD_SIGNATURE kutilgan edi: {other}"),
        Ok(_) => panic!("noto'g'ri pinned kalit qabul qilindi!"),
    }
    // Klient ulanishni yopadi: server o'qishdan chiqib, thread tugaydi.
    drop(stream);
    let _ = h.join();
}

/// S4/F1: nol (low-order) X25519 ct_x — exception emas, implicit rejection →
/// Finished tekshiruvida BAD_FINISHED bilan uzadi (panic/ValueError yo'q).
#[test]
fn low_order_x25519_is_implicit_rejection_not_exception() {
    let srv = server_identity(9);
    let mut client = ClientHs::new(ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() });
    let ch = client.start().unwrap();
    let mut server = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
    let sh = server.recv_hello(&ch, None).unwrap().into_bytes();
    let (_, sh_body, _) = wire::parse_frame(&sh).unwrap();
    let parsed = wire::dec_server_hello(sh_body).unwrap();
    // Honest ML-KEM ct_m, lekin ct_x = nol (low-order).
    let (bundle, _) = kem::encaps(parsed.profile, &parsed.ek).unwrap();
    let mut ct = bundle[..kem::MLKEM_CT_LEN].to_vec();
    ct.extend_from_slice(&[0u8; 32]);
    let mut flight = wire::enc_client_kex(&ct);
    flight.extend_from_slice(&wire::enc_finished(&[0u8; 32]));
    match server.recv_flight(&flight) {
        Err(AqError::Alert(c)) => assert_eq!(c, alert::BAD_FINISHED),
        other => panic!("BAD_FINISHED kutilgan edi (implicit rejection): {other:?}"),
    }
}

#[test]
fn tampered_record_fails_aead() {
    let mut master_cli = Session::from_master(&[9u8; 32], 1, Role::Client);
    let mut master_srv = Session::from_master(&[9u8; 32], 1, Role::Server);
    let mut rec = master_cli.seal(b"maxfiy").unwrap();
    let last = rec.len() - 1;
    rec[last] ^= 0x80;
    assert!(master_srv.open(&rec).is_err());
}

#[test]
fn trailing_bytes_after_server_hello_rejected() {
    let srv = server_identity(10);
    let mut client = ClientHs::new(ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() });
    let ch = client.start().unwrap();
    let mut server = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
    let mut sh = server.recv_hello(&ch, None).unwrap().into_bytes();
    sh.push(0x00);
    assert!(matches!(client.recv(&sh), Err(AqError::Malformed(_))));
}

/// Sanity: frame o'qish oqimdan to'g'ri ishlaydi (TCP).
#[test]
fn read_frame_reads_exact_frame_from_stream() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let f = wire::frame(wire::MSG_FINISHED, &[7u8; 32]);
    let f2 = f.clone();
    let h = thread::spawn(move || {
        let (mut s, _) = listener.accept().unwrap();
        std::io::Write::write_all(&mut s, &f2).unwrap();
    });
    let mut c = TcpStream::connect(("127.0.0.1", port)).unwrap();
    assert_eq!(read_frame(&mut c).unwrap(), f);
    h.join().unwrap();
}
