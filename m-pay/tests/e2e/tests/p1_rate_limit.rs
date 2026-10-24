//! 1-faza, P1.1: so'rovlar chegarasi haqiqiy HTTP orqali (IP, API kaliti, qurilma).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_e2e::{test_fpan, Sandbox};
use mpay_terminal_sim::WalletError;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

/// Xom HTTP/1.1 so'rov: (status, Retry-After).
async fn raw_hello(sb: &Sandbox) -> (u16, Option<String>) {
    let mut s = tokio::net::TcpStream::connect(sb.addr()).await.unwrap();
    let req =
        "POST /v1/pqlink/hello HTTP/1.1\r\nHost: t\r\nContent-Type: application/x-mpay-pqlink\r\n\
               Content-Length: 3\r\nConnection: close\r\n\r\nabc";
    s.write_all(req.as_bytes()).await.unwrap();
    let mut buf = Vec::new();
    s.read_to_end(&mut buf).await.unwrap();
    let text = String::from_utf8_lossy(&buf);
    let status = text[9..12].parse().unwrap();
    let retry = text.lines().find_map(|l| {
        l.to_ascii_lowercase()
            .strip_prefix("retry-after: ")
            .map(str::to_owned)
    });
    (status, retry)
}

#[tokio::test]
async fn handshake_limited_per_ip_with_retry_after() {
    let sb = Sandbox::start_with(|c| {
        c.rate_limit.ip_handshake_burst = 3;
        c.rate_limit.ip_handshake_per_minute = 1;
    })
    .await;
    // Chegara tahlildan oldin: yaroqsiz tana ham hisoblanadi (400), keyin 429.
    for _ in 0..3 {
        assert_eq!(raw_hello(&sb).await.0, 400);
    }
    let (status, retry) = raw_hello(&sb).await;
    assert_eq!(status, 429);
    let secs: u64 = retry.expect("Retry-After").trim().parse().unwrap();
    assert!((1..=60).contains(&secs), "{secs}");
}

#[tokio::test]
async fn api_key_limited() {
    let sb = Sandbox::start_with(|c| {
        c.rate_limit.api_key_burst = 2;
        c.rate_limit.api_key_per_second = 1;
    })
    .await;
    let c = sb.client();
    for _ in 0..2 {
        let _: serde_json::Value = c
            .get_json("/v1/sandbox/accounts", Some(&sb.operator_key))
            .await
            .unwrap();
    }
    let e = c
        .get_json::<serde_json::Value>("/v1/sandbox/accounts", Some(&sb.operator_key))
        .await
        .unwrap_err();
    assert!(
        matches!(&e, WalletError::Api { status: 429, code, .. } if code == "RATE_LIMITED"),
        "{e:?}"
    );
    // Noto'g'ri kalit chegaraga yetmaydi — avval autentifikatsiya (401).
    let e = c
        .get_json::<serde_json::Value>("/v1/sandbox/accounts", Some("wrong"))
        .await
        .unwrap_err();
    assert!(matches!(e, WalletError::Api { status: 401, .. }), "{e:?}");
}

#[tokio::test]
async fn device_limited_and_session_stays_in_sync() {
    let sb = Sandbox::start_with(|c| {
        c.rate_limit.device_burst = 2;
        c.rate_limit.device_per_minute = 1;
    })
    .await;
    let mut w = sb.wallet().await;
    for i in 0..2 {
        w.provision(&test_fpan(10, 100 + i), "3112").await.unwrap();
    }
    for i in 2..4 {
        let e = w
            .provision(&test_fpan(10, 100 + i), "3112")
            .await
            .unwrap_err();
        // Javob muhrlangan — keyingi so'rov ham PQLINK_REPLAY/SESSION emas, aynan RATE_LIMITED.
        assert!(
            matches!(&e, WalletError::Api { status: 429, code, .. } if code == "RATE_LIMITED"),
            "{e:?}"
        );
    }
}
