//! Session resumption, PoW (HELLO_RETRY) va 0-RTT (early data) — in-memory va TCP sinovlari.

use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::thread;

use aq_core::dos::PuzzleAuthority;
use aq_core::early::{EarlyGuard};
use aq_core::error::alert;
use aq_core::handshake::{
    early_blob, ClientConfig, ClientEstablished, ClientHs, HelloReply, Resume, ServerConfig, ServerEstablished, ServerHs,
};
use aq_core::net::{client_handshake, server_handshake};
use aq_core::ticket::TicketAuthority;
use aq_core::wire::parse_frame;
use aq_core::{AqError, Identity};

/// Bir nechta frame'ni bitta buferdan ajratadi.
fn split(buf: &[u8]) -> Vec<Vec<u8>> {
    let mut out = Vec::new();
    let mut off = 0;
    while off < buf.len() {
        let (_, _, n) = parse_frame(&buf[off..]).expect("frame");
        out.push(buf[off..off + n].to_vec());
        off += n;
    }
    out
}

/// Klient va serverni xotirada to'liq handshake qilib o'tkazadi (PoW/resumption/0-RTT bilan).
fn drive(client_cfg: ClientConfig, server_cfg: ServerConfig) -> Result<(ClientEstablished, ServerEstablished), AqError> {
    let mut c = ClientHs::new(client_cfg);
    let mut s = ServerHs::new(server_cfg);
    let first = c.start()?;
    let frames = split(&first);
    let early = frames.get(1).map(|f| early_blob(f)).transpose()?;
    let mut reply = s.recv_hello(&frames[0], early.as_deref())?;
    loop {
        match reply {
            HelloReply::Retry(r) => {
                let out = c.recv(&r)?.expect("CH_RETRY");
                reply = s.recv_hello(&out, None)?;
            }
            HelloReply::Hello(sh) => {
                let flight = c.recv(&sh)?.expect("flight");
                let sf = s.recv_flight(&flight)?;
                for f in split(&sf) {
                    c.recv(&f)?;
                }
                break;
            }
        }
    }
    Ok((c.finish()?, s.finish()?))
}

fn srv_id(seed: u8) -> Identity {
    Identity::from_seed([seed; 32])
}

#[test]
fn resumption_inmemory_issues_and_accepts_ticket() {
    let srv = srv_id(21);
    let tickets = Arc::new(TicketAuthority::random(3600).unwrap());
    let scfg = || ServerConfig {
        identity: Some(srv.clone()),
        tickets: Some(tickets.clone()),
        ..Default::default()
    };
    let ccfg = ClientConfig { server_pub: Some(srv.pk.clone()), want_ticket: true, ..Default::default() };
    let (c1, s1) = drive(ccfg.clone(), scfg()).expect("birinchi ulanish");
    assert!(!c1.resumed && !s1.resumed, "birinchi ulanish to'liq bo'lishi kerak");
    let t = c1.new_ticket.expect("NST ticket olinishi kerak");

    let ccfg2 = ClientConfig {
        server_pub: Some(srv.pk.clone()),
        resume: Some(t.as_resume()),
        want_ticket: true,
        ..Default::default()
    };
    let (c2, s2) = drive(ccfg2, scfg()).expect("resumed ulanish");
    assert!(c2.resumed && s2.resumed, "ticket qabul qilinishi (resumption) kerak");
    assert!(c2.new_ticket.is_some(), "resumed ulanishda ham yangi ticket");
}

#[test]
fn resumption_rejected_for_other_context_falls_back_to_full() {
    let srv = srv_id(22);
    let tickets = Arc::new(TicketAuthority::random(3600).unwrap());
    let ccfg = ClientConfig { server_pub: Some(srv.pk.clone()), want_ticket: true, ..Default::default() };
    let s_a = ServerConfig {
        identity: Some(srv.clone()),
        tickets: Some(tickets.clone()),
        ticket_context: b"tenant-A".to_vec(),
        ..Default::default()
    };
    let (c1, _) = drive(ccfg, s_a).unwrap();
    let t = c1.new_ticket.unwrap();
    // Boshqa kontekst (tenant-B), xuddi shu ticket kaliti — ticket ochilmaydi (AQ-05).
    let s_b = ServerConfig {
        identity: Some(srv.clone()),
        tickets: Some(tickets.clone()),
        ticket_context: b"tenant-B".to_vec(),
        ..Default::default()
    };
    let ccfg2 = ClientConfig { server_pub: Some(srv.pk.clone()), resume: Some(t.as_resume()), ..Default::default() };
    let (c2, s2) = drive(ccfg2, s_b).expect("to'liq handshake'ga qaytish");
    assert!(!c2.resumed && !s2.resumed, "boshqa kontekstda resumption bo'lmasligi kerak");
}

#[test]
fn pow_puzzle_roundtrip_and_budget_rejection() {
    let srv = srv_id(23);
    // D=8: klient (max 20) yechadi.
    let puzzle = Arc::new(PuzzleAuthority::random(8, 30).unwrap());
    let scfg = ServerConfig { identity: Some(srv.clone()), puzzle: Some(puzzle.clone()), ..Default::default() };
    let ccfg = ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() };
    drive(ccfg, scfg).expect("PoW bilan ulanish");

    // D=25 > klient byudjeti (20): klient ishga kirmasdan rad etadi (AQ-L05).
    let hard = Arc::new(PuzzleAuthority::random(25, 30).unwrap());
    let scfg2 = ServerConfig { identity: Some(srv.clone()), puzzle: Some(hard), ..Default::default() };
    let ccfg2 = ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() };
    match drive(ccfg2, scfg2) {
        Err(AqError::Alert(c)) => assert_eq!(c, alert::DOS_REJECT),
        other => panic!("DOS_REJECT kutilgan edi: {:?}", other.is_ok()),
    }
}

#[test]
fn pow_wrong_solution_is_rejected_by_server() {
    let srv = srv_id(24);
    let puzzle = Arc::new(PuzzleAuthority::random(8, 30).unwrap());
    let mut s = ServerHs::new(ServerConfig { identity: Some(srv.clone()), puzzle: Some(puzzle.clone()), ..Default::default() });
    let mut c = ClientHs::new(ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() });
    let ch = c.start().unwrap();
    let retry = match s.recv_hello(&ch, None).unwrap() {
        HelloReply::Retry(r) => r,
        _ => panic!("HELLO_RETRY kutilgan edi"),
    };
    // Noto'g'ri nonce bilan CH_RETRY yasaymiz.
    let (_, body, _) = parse_frame(&retry).unwrap();
    let (difficulty, cookie) = aq_core::wire::dec_hello_retry(body).unwrap();
    let bad_nonce = (0u64..).find(|&n| !aq_core::dos::verify_pow(&cookie, n, difficulty)).unwrap();
    let bad = aq_core::wire::enc_client_hello_retry(&cookie, bad_nonce, &ch);
    match s.recv_hello(&bad, None) {
        Err(AqError::Alert(code)) => assert_eq!(code, alert::DOS_REJECT),
        _ => panic!("noto'g'ri PoW qabul qilindi"),
    }
}

#[test]
fn zero_rtt_early_data_accepted_on_resumption() {
    let srv = srv_id(25);
    let tickets = Arc::new(TicketAuthority::random(3600).unwrap());
    let guard = Arc::new(Mutex::new(EarlyGuard::new(60, 1000)));
    let scfg = ServerConfig {
        identity: Some(srv.clone()),
        tickets: Some(tickets.clone()),
        early_guard: Some(guard.clone()),
        ..Default::default()
    };
    let ccfg = ClientConfig { server_pub: Some(srv.pk.clone()), want_ticket: true, ..Default::default() };
    let (c1, _) = drive(ccfg, scfg.clone()).unwrap();
    let t = c1.new_ticket.unwrap();
    let ccfg2 = ClientConfig {
        server_pub: Some(srv.pk.clone()),
        resume: Some(t.as_resume()),
        early_data: Some(b"GET /health".to_vec()),
        ..Default::default()
    };
    let (_c2, s2) = drive(ccfg2, scfg.clone()).unwrap();
    assert_eq!(s2.early_data.as_deref(), Some(&b"GET /health"[..]), "0-RTT ma'lumot yetib borishi kerak");
}

#[test]
fn zero_rtt_replay_is_rejected() {
    let srv = srv_id(26);
    let tickets = Arc::new(TicketAuthority::random(3600).unwrap());
    let guard = Arc::new(Mutex::new(EarlyGuard::new(60, 1000)));
    let scfg = || ServerConfig {
        identity: Some(srv.clone()),
        tickets: Some(tickets.clone()),
        early_guard: Some(guard.clone()),
        ..Default::default()
    };
    // Ticket olish
    let ccfg = ClientConfig { server_pub: Some(srv.pk.clone()), want_ticket: true, ..Default::default() };
    let (c1, _) = drive(ccfg, scfg()).unwrap();
    let t = c1.new_ticket.unwrap();
    // Bitta CH+EARLY ni ikki marta yuboramiz (replay)
    let mut c = ClientHs::new(ClientConfig {
        server_pub: Some(srv.pk.clone()),
        resume: Some(t.as_resume()),
        early_data: Some(b"POST /order".to_vec()),
        ..Default::default()
    });
    let first = c.start().unwrap();
    let frames = split(&first);
    let blob = early_blob(&frames[1]).unwrap();
    let mut s_a = ServerHs::new(scfg());
    s_a.recv_hello(&frames[0], Some(&blob)).unwrap();
    assert!(s_a.early_data().is_some(), "birinchi qabul qilinishi kerak");
    let mut s_b = ServerHs::new(scfg());
    s_b.recv_hello(&frames[0], Some(&blob)).unwrap();
    assert!(s_b.early_data().is_none(), "takroriy CH+EARLY (replay) rad etilishi kerak");
}

#[test]
fn zero_rtt_rejected_with_mutual_auth() {
    let srv = srv_id(27);
    let cli = srv_id(28);
    let tickets = Arc::new(TicketAuthority::random(3600).unwrap());
    let guard = Arc::new(Mutex::new(EarlyGuard::new(60, 1000)));
    let scfg = ServerConfig {
        identity: Some(srv.clone()),
        tickets: Some(tickets.clone()),
        early_guard: Some(guard.clone()),
        require_client_auth: true,
        allowed_clients: Some(vec![cli.pk.clone()]),
        ..Default::default()
    };
    let (c1, _) = drive(
        ClientConfig { server_pub: Some(srv.pk.clone()), identity: Some(cli.clone()), want_ticket: true, ..Default::default() },
        scfg.clone(),
    )
    .unwrap();
    let t = c1.new_ticket.unwrap();
    let (_c2, s2) = drive(
        ClientConfig {
            server_pub: Some(srv.pk.clone()),
            identity: Some(cli.clone()),
            resume: Some(t.as_resume()),
            early_data: Some(b"GET /x".to_vec()),
            ..Default::default()
        },
        scfg,
    )
    .unwrap();
    assert!(s2.early_data.is_none(), "mutual auth bilan 0-RTT rad etilishi kerak (S3.3c)");
    assert_eq!(s2.client_pk.as_deref(), Some(cli.pk.as_slice()));
}

#[test]
fn tcp_resumption_roundtrip_with_session_flags() {
    let srv = srv_id(29);
    let tickets = Arc::new(TicketAuthority::random(3600).unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let scfg = ServerConfig { identity: Some(srv.clone()), tickets: Some(tickets.clone()), ..Default::default() };
    let h = thread::spawn(move || {
        let mut flags = Vec::new();
        for _ in 0..2 {
            let (mut st, _) = listener.accept().unwrap();
            let est = server_handshake(&mut st, scfg.clone()).unwrap();
            flags.push(est.resumed);
        }
        flags
    });
    let mut s1 = TcpStream::connect(("127.0.0.1", port)).unwrap();
    let e1 = client_handshake(
        &mut s1,
        ClientConfig { server_pub: Some(srv.pk.clone()), want_ticket: true, ..Default::default() },
    )
    .unwrap();
    assert!(!e1.resumed);
    let t = e1.new_ticket.clone().expect("ticket");
    drop(s1);
    let mut s2 = TcpStream::connect(("127.0.0.1", port)).unwrap();
    let e2 = client_handshake(
        &mut s2,
        ClientConfig {
            server_pub: Some(srv.pk.clone()),
            resume: Some(Resume { ticket: t.ticket.clone(), rms: t.rms }),
            want_ticket: true,
            ..Default::default()
        },
    )
    .unwrap();
    assert!(e2.resumed, "TCP orqali resumption ishlashi kerak");
    assert_eq!(h.join().unwrap(), vec![false, true]);
}
