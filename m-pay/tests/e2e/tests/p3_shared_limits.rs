//! 3-faza tayyorgarligi: ko'p instansiyada umumiy so'rovlar chegarasi. IP (handshake) va qurilma
//! (muhrlangan so'rovlar) chelaklari umumiy omborda — balanser so'rovlarni instansiyalar orasida
//! taqsimlasa ham chegara `N ×` ga ko'paymaydi. `MPAY_TEST_PG_URL` bo'lsa — PostgreSQL, aks holda
//! bitta SQLite fayl.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_e2e::{test_fpan, Sandbox};
use mpay_server::config::{Config, SessionStoreKind};
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::WalletError;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

/// Sandbox (A) va o'sha konfiguratsiya/ombor bilan ikkinchi instansiya (B).
async fn two_instances(tweak: impl FnOnce(&mut Config)) -> (Sandbox, mpay_server::RunningServer) {
    let sb = Sandbox::start_with(|c| {
        c.pqlink.session_store = SessionStoreKind::Database;
        tweak(c);
    })
    .await;
    let mut cfg = sb.cfg.clone();
    cfg.http.listen = "127.0.0.1:0".parse().unwrap();
    let b = mpay_server::start(&cfg).await.unwrap();
    (sb, b)
}

/// Yaroqsiz tanali `hello` — status kodi (chegara tahlildan oldin: 400 yoki 429).
async fn raw_hello(addr: std::net::SocketAddr) -> u16 {
    let mut s = tokio::net::TcpStream::connect(addr).await.unwrap();
    s.write_all(
        b"POST /v1/pqlink/hello HTTP/1.1\r\nHost: t\r\nContent-Type: application/x-mpay-pqlink\r\n\
          Content-Length: 3\r\nConnection: close\r\n\r\nabc",
    )
    .await
    .unwrap();
    let mut buf = Vec::new();
    s.read_to_end(&mut buf).await.unwrap();
    String::from_utf8_lossy(&buf)[9..12].parse().unwrap()
}

fn ip_limit(c: &mut Config) {
    c.rate_limit.ip_handshake_burst = 3;
    c.rate_limit.ip_handshake_per_minute = 1;
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn ip_limit_is_global_across_instances() {
    let (sb, mut b) = two_instances(ip_limit).await;
    assert!(sb.server.state.limits.is_shared() && b.state.limits.is_shared());
    let (a, bb) = (sb.addr(), b.addr);
    // Burst 3 ikki instansiyaga bo'lingan: A, B, A — o'tadi (400 — tana yaroqsiz).
    for addr in [a, bb, a] {
        assert_eq!(raw_hello(addr).await, 400);
    }
    // Mahalliy chelaklarda token bor, umumiysida yo'q — ikkalasida ham 429.
    assert_eq!(raw_hello(bb).await, 429);
    assert_eq!(raw_hello(a).await, 429);
    b.shutdown();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn local_limits_when_shared_disabled() {
    let (sb, mut b) = two_instances(|c| {
        ip_limit(c);
        c.rate_limit.shared = Some(false);
    })
    .await;
    assert!(!sb.server.state.limits.is_shared());
    // Har instansiya o'z burst'i — jami 6 (umumiy chegara yo'qligi shu).
    for addr in [sb.addr(), b.addr] {
        for _ in 0..3 {
            assert_eq!(raw_hello(addr).await, 400);
        }
    }
    assert_eq!(raw_hello(sb.addr()).await, 429);
    b.shutdown();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn device_limit_is_global_across_instances() {
    let (sb, mut b) = two_instances(|c| {
        c.rate_limit.device_burst = 2;
        c.rate_limit.device_per_minute = 1;
    })
    .await;
    let ca = sb.client();
    let cb = ServerClient::new(&format!("http://{}", b.addr), None).unwrap();
    let mut w = sb.wallet().await;
    // Burst 2: A va B da bittadan — o'tadi.
    w.provision(&test_fpan(10, 5201), "3112").await.unwrap();
    w.set_client(cb.clone());
    w.provision(&test_fpan(10, 5202), "3112").await.unwrap();
    // Keyingisi qaysi instansiyada bo'lmasin — RATE_LIMITED (javob muhrlangan, sessiya buzilmaydi).
    for (i, c) in [ca, cb].into_iter().enumerate() {
        w.set_client(c);
        let e = w
            .provision(&test_fpan(10, 5203 + i as u32), "3112")
            .await
            .unwrap_err();
        assert!(
            matches!(&e, WalletError::Api { status: 429, code, .. } if code == "RATE_LIMITED"),
            "{e:?}"
        );
    }
    b.shutdown();
}
