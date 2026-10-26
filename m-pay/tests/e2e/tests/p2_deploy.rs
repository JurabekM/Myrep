//! 2-faza P2.5 (ADR-0020): L4 load balancer ortida — PROXY protocol v1 (mijozning haqiqiy IP'si
//! IP chegarasiga tushadi) va Prometheus `/metrics`.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_e2e::{test_fpan, Sandbox};
use mpay_terminal_sim::card::CardPolicy;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

/// PROXY sarlavhasi (`client` — mijoz IP'si yoki `None` — sarlavhasiz) + yaroqsiz hello: status.
async fn hello_via_proxy(sb: &Sandbox, client: Option<&str>) -> Option<u16> {
    let mut s = tokio::net::TcpStream::connect(sb.addr()).await.unwrap();
    if let Some(ip) = client {
        let hdr = format!("PROXY TCP4 {ip} 127.0.0.1 40000 {}\r\n", sb.addr().port());
        s.write_all(hdr.as_bytes()).await.unwrap();
    }
    let req =
        "POST /v1/pqlink/hello HTTP/1.1\r\nHost: t\r\nContent-Type: application/x-mpay-pqlink\r\n\
               Content-Length: 3\r\nConnection: close\r\n\r\nabc";
    let _ = s.write_all(req.as_bytes()).await;
    let mut buf = Vec::new();
    let _ = s.read_to_end(&mut buf).await;
    let text = String::from_utf8_lossy(&buf);
    text.get(9..12).and_then(|c| c.parse().ok())
}

async fn metrics(sb: &Sandbox) -> String {
    let addr = sb.server.metrics_addr.expect("metrics porti");
    let mut s = tokio::net::TcpStream::connect(addr).await.unwrap();
    s.write_all(b"GET /metrics HTTP/1.1\r\nHost: m\r\nConnection: close\r\n\r\n")
        .await
        .unwrap();
    let mut buf = Vec::new();
    s.read_to_end(&mut buf).await.unwrap();
    String::from_utf8(buf).unwrap()
}

#[tokio::test]
async fn proxy_protocol_client_ip_and_metrics() {
    let sb = Sandbox::start_with(|c| {
        c.http.proxy_protocol = true;
        c.http.trusted_proxies = vec!["127.0.0.0/8".parse().unwrap()];
        c.rate_limit.ip_handshake_burst = 2;
        c.rate_limit.ip_handshake_per_minute = 1;
        c.metrics.listen = Some("127.0.0.1:0".parse().unwrap());
    })
    .await;
    // Bir xil proksi (127.0.0.1) ortida ikki mijoz — chegara har biriga alohida.
    let a = "203.0.113.10";
    let b = "198.51.100.20";
    assert_eq!(hello_via_proxy(&sb, Some(a)).await, Some(400));
    assert_eq!(hello_via_proxy(&sb, Some(a)).await, Some(400));
    assert_eq!(
        hello_via_proxy(&sb, Some(a)).await,
        Some(429),
        "A chegarada"
    );
    assert_eq!(
        hello_via_proxy(&sb, Some(b)).await,
        Some(400),
        "B — boshqa mijoz, chegara alohida"
    );
    // Ishonchli proksidan sarlavhasiz ulanish yopiladi (soxta manzilni tekshirib bo'lmaydi).
    assert_eq!(hello_via_proxy(&sb, None).await, None);

    // Oddiy oqim ham ishlaydi va metrikaga tushadi (PROXY orqali `ServerClient` emas — xom).
    let m = metrics(&sb).await;
    assert!(m.starts_with("HTTP/1.1 200"), "{m}");
    assert!(m.contains("text/plain; version=0.0.4"));
    for want in [
        "mpay_build_info{version=",
        "mpay_http_requests_total{route=\"/v1/pqlink/hello\",method=\"POST\",status=\"429\"}",
        "mpay_http_request_duration_seconds_bucket{route=\"/v1/pqlink/hello\",le=\"0.3\"}",
        "mpay_rate_limited_total{kind=\"ip\"}",
        "mpay_proxy_protocol_rejected_total",
        "mpay_db_up 1",
        "mpay_db_pool_connections{state=\"idle\"}",
        "mpay_pqlink_sessions 0",
    ] {
        assert!(m.contains(want), "metrikada yo'q: {want}\n{m}");
    }
    let rejected: f64 = m
        .lines()
        .find_map(|l| l.strip_prefix("mpay_proxy_protocol_rejected_total "))
        .unwrap()
        .parse()
        .unwrap();
    assert!(rejected >= 1.0);
}

#[tokio::test]
async fn proxy_protocol_needs_trusted_proxies() {
    let sb = Sandbox::start().await;
    let mut cfg = sb.cfg.clone();
    cfg.http.proxy_protocol = true;
    cfg.http.trusted_proxies.clear();
    let e = cfg.validate().unwrap_err().to_string();
    assert!(e.contains("trusted_proxies"), "{e}");
}

#[tokio::test]
async fn metrics_count_authorizations_without_pan() {
    let sb = Sandbox::start_with(|c| c.metrics.listen = Some("127.0.0.1:0".parse().unwrap())).await;
    let fpan = test_fpan(10, 7001);
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let r = sb.pay(&mut card, 150_000, "SHOP0000000001", 1).await;
    let m = metrics(&sb).await;
    let want = format!("mpay_authorizations_total{{code=\"{}\"}}", r.response_code);
    assert!(m.contains(&want), "{m}");
    assert!(m.contains("route=\"/v1/tokens\""));
    assert!(m.contains("route=\"/v1/authorizations\""));
    let digits: String = fpan.chars().filter(char::is_ascii_digit).collect();
    assert!(!m.contains(&digits), "metrikada ochiq PAN");
    assert!(!m.contains(&r.dpan_masked), "metrikada token PAN");
}

/// `docker stop` (SIGTERM): yangi ulanish qabul qilinmaydi, bo'sh keep-alive ulanishlar yopiladi,
/// `serve` qaytadi — konteyner kutish vaqtini to'liq kutmasdan to'xtaydi.
#[tokio::test]
async fn shutdown_drains_keepalive_connections() {
    let mut sb = Sandbox::start_with(|c| {
        c.http.proxy_protocol = true;
        c.http.trusted_proxies = vec!["127.0.0.0/8".parse().unwrap()];
    })
    .await;
    let mut s = tokio::net::TcpStream::connect(sb.addr()).await.unwrap();
    let req = format!(
        "PROXY TCP4 203.0.113.30 127.0.0.1 40000 {}\r\nGET /healthz HTTP/1.1\r\nHost: t\r\n\r\n",
        sb.addr().port()
    );
    s.write_all(req.as_bytes()).await.unwrap();
    let mut buf = vec![0u8; 4096];
    let n = s.read(&mut buf).await.unwrap();
    assert!(String::from_utf8_lossy(&buf[..n]).starts_with("HTTP/1.1 200"));

    sb.server.shutdown();
    let t = std::time::Duration::from_secs(5);
    let eof = tokio::time::timeout(t, async {
        loop {
            if s.read(&mut buf).await.unwrap_or(0) == 0 {
                break;
            }
        }
    })
    .await;
    assert!(eof.is_ok(), "keep-alive ulanish yopilmadi");
    let done = tokio::time::timeout(t, &mut sb.server.handle).await;
    assert!(matches!(done, Ok(Ok(Ok(())))), "serve qaytmadi");
    assert!(
        tokio::net::TcpStream::connect(sb.addr()).await.is_err(),
        "to'xtatilgandan keyin ulanish qabul qilinmasligi kerak"
    );
}
