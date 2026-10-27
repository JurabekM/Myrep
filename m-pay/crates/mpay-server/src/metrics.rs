//! Prometheus metrikalari (2-faza P2.5, ADR-0020). Dashboard yo'q — faqat matn formatidagi
//! `/metrics` alohida ichki portda (`[metrics] listen`) va ogohlantirish qoidalari
//! (`deploy/prometheus/alerts.yml`).
//!
//! Yorliqlarda faqat cheklangan qiymatlar: marshrut **shabloni** (`/v1/tokens/{id}`), metod, HTTP
//! status, ISO 8583 javob kodi, chegara turi. PAN, token ID, qurilma ID, IP — hech qachon.
//!
//! Ro'yxat jarayon bo'yicha global (Prometheus odati): testlarda bir jarayondagi bir nechta server
//! hisoblagichlari qo'shilib ketadi — testlar faqat o'sishni tekshiradi.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::future::Future;
use std::net::SocketAddr;
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock, Mutex};
use std::time::Duration;

use axum::extract::{MatchedPath, Request};
use axum::middleware::Next;
use axum::response::Response;

/// Kechikish gistogrammasi chegaralari (soniya). 0,3 — SLA p99 (ADR-0017).
const BUCKETS: [f64; 13] = [
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0,
];

#[derive(Default)]
struct Hist {
    counts: [u64; BUCKETS.len()],
    sum: f64,
    count: u64,
}

/// Chegara turi (`mpay_rate_limited_total{kind}`).
#[derive(Debug, Clone, Copy)]
pub enum Limit {
    Ip,
    ApiKey,
    Device,
    Handshake,
}

impl Limit {
    fn as_str(self) -> &'static str {
        match self {
            Self::Ip => "ip",
            Self::ApiKey => "api_key",
            Self::Device => "device",
            Self::Handshake => "handshake_queue",
        }
    }
}

#[derive(Default)]
struct Registry {
    /// (marshrut, metod, status) → soni.
    http: Mutex<BTreeMap<(String, String, u16), u64>>,
    /// marshrut → kechikish.
    latency: Mutex<BTreeMap<String, Hist>>,
    /// ISO 8583 javob kodi → soni.
    authorizations: Mutex<BTreeMap<String, u64>>,
    rate_limited: Mutex<BTreeMap<&'static str, u64>>,
    /// Yaxlitlik tekshiruvi natijasi → soni.
    integrity: Mutex<BTreeMap<&'static str, u64>>,
    /// Reversal navbatga qo'yilishi sababi → soni (ADR-0024).
    reversals_enqueued: Mutex<BTreeMap<String, u64>>,
    /// Reversal yuborish natijasi (`done`, `failed`, `retry`) → soni.
    reversals: Mutex<BTreeMap<&'static str, u64>>,
    shield_degraded: AtomicU64,
    otp_failed: AtomicU64,
    proxy_rejected: AtomicU64,
    rate_limit_store_errors: AtomicU64,
}

static REG: LazyLock<Registry> = LazyLock::new(Registry::default);
static STARTED: LazyLock<f64> = LazyLock::new(|| {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
});

fn lock<T>(m: &Mutex<T>) -> std::sync::MutexGuard<'_, T> {
    m.lock().unwrap_or_else(|p| p.into_inner())
}

/// Yorliq qiymati: faqat `[A-Za-z0-9_]`, ≤ 16 belgi — aks holda `other` (kardinallik cheklangan).
fn label(v: &str) -> String {
    if !v.is_empty() && v.len() <= 16 && v.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_') {
        v.to_owned()
    } else {
        "other".into()
    }
}

/// HTTP so'rov natijasi (marshrut shabloni bo'yicha).
pub fn observe_http(route: &str, method: &str, status: u16, elapsed: Duration) {
    let route = if route.is_empty() { "unmatched" } else { route };
    // Metod mijozdan keladi: nostandart metodlar bilan series sonini cheksiz oshirib bo'lmasin.
    let method = match method {
        "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | "HEAD" | "OPTIONS" => method,
        _ => "other",
    };
    *lock(&REG.http)
        .entry((route.to_owned(), method.to_owned(), status))
        .or_default() += 1;
    let secs = elapsed.as_secs_f64();
    let mut l = lock(&REG.latency);
    let h = l.entry(route.to_owned()).or_default();
    for (i, b) in BUCKETS.iter().enumerate() {
        if secs <= *b {
            h.counts[i] += 1;
        }
    }
    h.sum += secs;
    h.count += 1;
}

/// Avtorizatsiya javob kodi (`00`, `51`, `59`, `96` …).
pub fn observe_authorization(code: &str) {
    *lock(&REG.authorizations).entry(label(code)).or_default() += 1;
}

pub fn rate_limited(kind: Limit) {
    *lock(&REG.rate_limited).entry(kind.as_str()).or_default() += 1;
}

/// Yaxlitlik tekshiruvi (P2.6): `ok`, `missing`, `invalid`, `unavailable`, `absent` (ixtiyoriy, berilmagan).
pub fn integrity_check(result: &'static str) {
    *lock(&REG.integrity).entry(result).or_default() += 1;
}

/// Natijasi noma'lum avtorizatsiya — reversal navbatga qo'yildi (`cause`: `ISSUER_TIMEOUT` …).
pub fn reversal_enqueued(cause: &str) {
    let cause = match cause {
        crate::reversal::CAUSE_TIMEOUT => "timeout",
        crate::reversal::CAUSE_UNREADABLE => "unreadable",
        crate::reversal::CAUSE_UNKNOWN => "unknown",
        _ => "other",
    };
    *lock(&REG.reversals_enqueued)
        .entry(cause.to_owned())
        .or_default() += 1;
}

/// Reversal yuborish natijasi: `done`, `failed`, `retry`.
pub fn reversal_result(result: &'static str) {
    *lock(&REG.reversals).entry(result).or_default() += 1;
}

/// Shield roli javob bermadi — mahalliy zaxira ishladi.
pub fn shield_degraded() {
    REG.shield_degraded.fetch_add(1, Ordering::Relaxed);
}

/// Umumiy chegara ombori xatosi (so'rov o'tkazildi — fail-open).
pub fn rate_limit_store_error() {
    REG.rate_limit_store_errors.fetch_add(1, Ordering::Relaxed);
}

/// OTP yetkazilmadi.
pub fn otp_failed() {
    REG.otp_failed.fetch_add(1, Ordering::Relaxed);
}

/// Ishonchli proksidan yaroqsiz PROXY sarlavhasi.
pub fn proxy_rejected() {
    REG.proxy_rejected.fetch_add(1, Ordering::Relaxed);
}

/// Har so'rov: metod, marshrut shabloni, status, davomiylik — log va metrika. Tanalar hech qachon
/// logga yozilmaydi.
pub async fn track(req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let route = req
        .extensions()
        .get::<MatchedPath>()
        .map(|p| p.as_str().to_owned())
        .unwrap_or_default();
    let start = std::time::Instant::now();
    let resp = next.run(req).await;
    let elapsed = start.elapsed();
    let status = resp.status().as_u16();
    tracing::info!(%method, route, status, ms = elapsed.as_millis() as u64, "http");
    observe_http(&route, method.as_str(), status, elapsed);
    resp
}

/// Matn formati yozuvchisi.
#[derive(Default)]
pub struct Text(String);

impl Text {
    fn head(&mut self, name: &str, kind: &str, help: &str) {
        let _ = writeln!(self.0, "# HELP {name} {help}\n# TYPE {name} {kind}");
    }

    /// Bitta qiymatli o'lchov (`gauge`). `labels` — tayyor `k="v",…` qatori yoki bo'sh.
    pub fn gauge(&mut self, name: &str, help: &str, labels: &str, v: f64) {
        self.head(name, "gauge", help);
        self.sample(name, labels, v);
    }

    /// Oldingi `gauge`/sarlavhaga yana bitta qator (boshqa yorliq bilan).
    pub fn sample(&mut self, name: &str, labels: &str, v: f64) {
        if labels.is_empty() {
            let _ = writeln!(self.0, "{name} {v}");
        } else {
            let _ = writeln!(self.0, "{name}{{{labels}}} {v}");
        }
    }

    pub fn finish(self) -> String {
        self.0
    }
}

/// Hisoblagich va gistogrammalar (jarayon bo'yicha umumiy) + `role` yorlig'i bilan build_info.
pub fn render_common(out: &mut Text, role: &str) {
    out.gauge(
        "mpay_build_info",
        "Versiya va rol",
        &format!("version=\"{}\",role=\"{role}\"", crate::VERSION),
        1.0,
    );
    out.gauge(
        "mpay_process_start_time_seconds",
        "Jarayon ishga tushgan vaqt (unix)",
        "",
        *STARTED,
    );

    out.head("mpay_http_requests_total", "counter", "HTTP so'rovlar");
    for ((route, method, status), n) in lock(&REG.http).iter() {
        out.sample(
            "mpay_http_requests_total",
            &format!("route=\"{route}\",method=\"{method}\",status=\"{status}\""),
            *n as f64,
        );
    }
    out.head(
        "mpay_http_request_duration_seconds",
        "histogram",
        "HTTP so'rov davomiyligi",
    );
    for (route, h) in lock(&REG.latency).iter() {
        let name = "mpay_http_request_duration_seconds";
        for (i, b) in BUCKETS.iter().enumerate() {
            out.sample(
                &format!("{name}_bucket"),
                &format!("route=\"{route}\",le=\"{b}\""),
                h.counts[i] as f64,
            );
        }
        out.sample(
            &format!("{name}_bucket"),
            &format!("route=\"{route}\",le=\"+Inf\""),
            h.count as f64,
        );
        out.sample(&format!("{name}_sum"), &format!("route=\"{route}\""), h.sum);
        out.sample(
            &format!("{name}_count"),
            &format!("route=\"{route}\""),
            h.count as f64,
        );
    }
    out.head(
        "mpay_authorizations_total",
        "counter",
        "Avtorizatsiyalar (ISO 8583 javob kodi)",
    );
    for (code, n) in lock(&REG.authorizations).iter() {
        out.sample(
            "mpay_authorizations_total",
            &format!("code=\"{code}\""),
            *n as f64,
        );
    }
    out.head(
        "mpay_rate_limited_total",
        "counter",
        "Chegara tufayli rad etilgan so'rovlar",
    );
    for (kind, n) in lock(&REG.rate_limited).iter() {
        out.sample(
            "mpay_rate_limited_total",
            &format!("kind=\"{kind}\""),
            *n as f64,
        );
    }
    out.head(
        "mpay_integrity_checks_total",
        "counter",
        "Provisioning yaxlitlik tekshiruvi natijalari",
    );
    for (r, n) in lock(&REG.integrity).iter() {
        out.sample(
            "mpay_integrity_checks_total",
            &format!("result=\"{r}\""),
            *n as f64,
        );
    }
    out.head(
        "mpay_reversals_enqueued_total",
        "counter",
        "Natijasi noma'lum avtorizatsiyalar — reversal navbatga (sabab)",
    );
    for (c, n) in lock(&REG.reversals_enqueued).iter() {
        out.sample(
            "mpay_reversals_enqueued_total",
            &format!("cause=\"{c}\""),
            *n as f64,
        );
    }
    out.head(
        "mpay_reversals_total",
        "counter",
        "Reversal yuborish natijalari (done, failed, retry)",
    );
    for (r, n) in lock(&REG.reversals).iter() {
        out.sample(
            "mpay_reversals_total",
            &format!("result=\"{r}\""),
            *n as f64,
        );
    }
    for (name, help, v) in [
        (
            "mpay_shield_degraded_total",
            "Shield roli javob bermadi (mahalliy zaxira)",
            &REG.shield_degraded,
        ),
        (
            "mpay_otp_delivery_failures_total",
            "OTP yetkazilmadi",
            &REG.otp_failed,
        ),
        (
            "mpay_proxy_protocol_rejected_total",
            "Yaroqsiz PROXY protocol sarlavhasi",
            &REG.proxy_rejected,
        ),
        (
            "mpay_rate_limit_store_errors_total",
            "Umumiy chegara ombori xatosi (so'rov o'tkazildi)",
            &REG.rate_limit_store_errors,
        ),
    ] {
        out.head(name, "counter", help);
        out.sample(name, "", v.load(Ordering::Relaxed) as f64);
    }
}

/// Ulanishlar hovuzi va bazaning sog'lig'i (`SELECT 1`, 1 s).
pub async fn render_db(out: &mut Text, pool: &sqlx::AnyPool) {
    let size = pool.size();
    let idle = pool.num_idle() as u32;
    out.gauge(
        "mpay_db_pool_connections",
        "Hovuzdagi ulanishlar",
        "state=\"idle\"",
        f64::from(idle),
    );
    out.sample(
        "mpay_db_pool_connections",
        "state=\"busy\"",
        f64::from(size.saturating_sub(idle)),
    );
    out.gauge(
        "mpay_db_pool_max_connections",
        "Hovuz chegarasi",
        "",
        f64::from(pool.options().get_max_connections()),
    );
    let ok = tokio::time::timeout(
        Duration::from_secs(1),
        sqlx::query_scalar::<_, i32>("SELECT 1").fetch_one(pool),
    )
    .await
    .is_ok_and(|r| r.is_ok());
    out.gauge(
        "mpay_db_up",
        "Baza javob beradi (1/0)",
        "",
        if ok { 1.0 } else { 0.0 },
    );
}

/// `/metrics` matnini yig'uvchi.
pub type Gather = Arc<dyn Fn() -> Pin<Box<dyn Future<Output = String> + Send>> + Send + Sync>;

/// Metrikalar porti (oddiy HTTP, faqat ichki tarmoq). Qaytadi: manzil va vazifa (to'xtatish — abort).
pub async fn start(
    listen: SocketAddr,
    gather: Gather,
) -> Result<(SocketAddr, tokio::task::JoinHandle<()>), String> {
    use axum::routing::get;
    let listener = tokio::net::TcpListener::bind(listen)
        .await
        .map_err(|e| format!("metrics.listen {listen}: {e}"))?;
    let addr = listener.local_addr().map_err(|e| e.to_string())?;
    let app = axum::Router::new().route(
        "/metrics",
        get(move || {
            let g = gather.clone();
            async move {
                (
                    [(
                        axum::http::header::CONTENT_TYPE,
                        "text/plain; version=0.0.4; charset=utf-8",
                    )],
                    g().await,
                )
            }
        }),
    );
    let handle = tokio::spawn(async move {
        if let Err(e) = axum::serve(listener, app).await {
            tracing::error!(error = %e, "metrics serveri to'xtadi");
        }
    });
    tracing::info!(%addr, "metrikalar tinglayapti (/metrics)");
    Ok((addr, handle))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn labels_are_bounded() {
        assert_eq!(label("00"), "00");
        assert_eq!(label("99001277123456781"), "other");
        assert_eq!(label("a\"}b"), "other");
        assert_eq!(label(""), "other");
        observe_http("/m", "XYZZY", 405, Duration::ZERO);
        assert!(lock(&REG.http).contains_key(&("/m".into(), "other".into(), 405)));
    }

    #[test]
    fn renders_text_format() {
        observe_http("/t/{id}", "GET", 200, Duration::from_millis(40));
        observe_authorization("00");
        rate_limited(Limit::Device);
        let mut t = Text::default();
        render_common(&mut t, "api");
        let s = t.finish();
        assert!(s.contains("# TYPE mpay_http_request_duration_seconds histogram"));
        assert!(
            s.contains("mpay_http_requests_total{route=\"/t/{id}\",method=\"GET\",status=\"200\"}")
        );
        assert!(
            s.contains("mpay_http_request_duration_seconds_bucket{route=\"/t/{id}\",le=\"0.05\"}")
        );
        assert!(s.contains("mpay_authorizations_total{code=\"00\"}"));
        assert!(s.contains("mpay_rate_limited_total{kind=\"device\"}"));
        // `le="0.025"` dan kichik bucket'larda 40 ms yo'q.
        let line = s
            .lines()
            .find(|l| {
                l.starts_with(
                    "mpay_http_request_duration_seconds_bucket{route=\"/t/{id}\",le=\"0.025\"}",
                )
            })
            .unwrap();
        assert!(line.ends_with(" 0"), "{line}");
    }
}
