//! `mpay-smsgw` — virtual SMS shlyuzi (2-faza P2.1, ADR-0016). Bankning haqiqiy SMS shlyuzi o'rnida
//! `mpay-server` ning `[otp] channel = "webhook"` kanalini telefonsiz sinash uchun:
//!
//! * `POST /send` `{"to","text","reference"}` + `Authorization: Bearer <token>` → `202 {"id"}`;
//! * `GET /messages[?to=+998…]` (shu token bilan) — "virtual telefonlar" qutisi, test va demo uchun;
//! * `DELETE /messages` — qutini tozalash;
//! * `POST /alerts` — Alertmanager webhook'i (virtual navbatchi kanali, 2026-10-26), `GET /alerts` —
//!   qabul qilingan ogohlantirishlar (nomi, holati, darajasi, instansiya).
//!
//! Faqat sinov vositasi: xabarlar xotirada, logga faqat maskalangan telefon va `reference` yoziladi
//! (SMS matni — ichida OTP — logga tushmaydi). Ishlab chiqarishda bu o'rinda bank shlyuzi turadi.
#![forbid(unsafe_code)]

use std::collections::VecDeque;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::{Arc, Mutex};

use axum::extract::{Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::post;
use axum::{Json, Router};
use mpay_common::phone::{is_e164, mask_phone};
use serde::{Deserialize, Serialize};
use subtle::ConstantTimeEq;
use zeroize::Zeroizing;

/// Qabul qilingan SMS.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Sms {
    pub id: u64,
    pub to: String,
    pub text: String,
    pub reference: String,
    pub received_at: i64,
}

#[derive(Deserialize)]
struct SendReq {
    to: String,
    text: String,
    #[serde(default)]
    reference: String,
}

#[derive(Deserialize)]
struct Filter {
    to: Option<String>,
}

/// Qabul qilingan ogohlantirish (Alertmanager webhook'idan, faqat yorliqlar).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    pub alertname: String,
    /// `firing` yoki `resolved`.
    pub status: String,
    pub severity: String,
    pub instance: String,
    pub received_at: i64,
}

/// Alertmanager webhook tanasi (`version: "4"`), bizga kerakli qismi.
#[derive(Deserialize)]
struct AlertmanagerPayload {
    #[serde(default)]
    alerts: Vec<AlertmanagerAlert>,
}

#[derive(Deserialize)]
struct AlertmanagerAlert {
    #[serde(default)]
    status: String,
    #[serde(default)]
    labels: std::collections::BTreeMap<String, String>,
}

#[derive(Default)]
struct Inner {
    messages: VecDeque<Sms>,
    alerts: VecDeque<Alert>,
    next_id: u64,
}

/// Shlyuz holati: xabarlar qutisi va nosozlik simulyatsiyasi.
#[derive(Clone)]
pub struct Gateway {
    token: Option<Arc<Zeroizing<String>>>,
    inner: Arc<Mutex<Inner>>,
    /// Keyingi shuncha `/send` so'roviga `503` (operator nosozligi simulyatsiyasi).
    fail_next: Arc<AtomicU32>,
}

/// Xotiradagi quti chegarasi (eski xabarlar tashlanadi).
const MAX_MESSAGES: usize = 10_000;

impl Gateway {
    /// `token` — `None` bo'lsa autentifikatsiyasiz (faqat lokal sinov).
    pub fn new(token: Option<String>) -> Self {
        Self {
            token: token.map(|t| Arc::new(Zeroizing::new(t))),
            inner: Arc::default(),
            fail_next: Arc::default(),
        }
    }

    /// Keyingi `n` ta `/send` ga `503` qaytaradi.
    pub fn fail_next(&self, n: u32) {
        self.fail_next.store(n, Ordering::SeqCst);
    }

    /// Qutidagi xabarlar (ixtiyoriy telefon bo'yicha).
    pub fn messages(&self, to: Option<&str>) -> Vec<Sms> {
        let g = self.inner.lock().unwrap_or_else(|e| e.into_inner());
        g.messages
            .iter()
            .filter(|m| to.is_none_or(|t| m.to == t))
            .cloned()
            .collect()
    }

    pub fn router(&self) -> Router {
        Router::new()
            .route("/send", post(send))
            .route("/messages", axum::routing::get(list).delete(clear))
            .route("/alerts", post(alert_webhook).get(list_alerts))
            .route("/healthz", axum::routing::get(|| async { "ok" }))
            .with_state(self.clone())
    }

    /// Qabul qilingan ogohlantirishlar.
    pub fn alerts(&self) -> Vec<Alert> {
        let g = self.inner.lock().unwrap_or_else(|e| e.into_inner());
        g.alerts.iter().cloned().collect()
    }

    fn authorized(&self, h: &HeaderMap) -> bool {
        let Some(want) = &self.token else {
            return true;
        };
        let got = h
            .get(axum::http::header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.strip_prefix("Bearer "))
            .unwrap_or("");
        got.len() == want.len() && bool::from(got.as_bytes().ct_eq(want.as_bytes()))
    }
}

fn now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// Hisoblagich > 0 bo'lsa bittaga kamaytiradi (`true`). `fetch_update` nightly'da eskirgan
/// (`try_update`), stable'da esa yangisi yo'q — ikkalasida bir xil ishlaydigan CAS tsikli.
fn take_one(a: &AtomicU32) -> bool {
    let mut cur = a.load(Ordering::SeqCst);
    while cur > 0 {
        match a.compare_exchange(cur, cur - 1, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => return true,
            Err(now) => cur = now,
        }
    }
    false
}

fn err(code: StatusCode, msg: &'static str) -> Response {
    (code, Json(serde_json::json!({ "error": msg }))).into_response()
}

async fn send(State(g): State<Gateway>, h: HeaderMap, Json(req): Json<SendReq>) -> Response {
    if !g.authorized(&h) {
        return err(StatusCode::UNAUTHORIZED, "token noto'g'ri");
    }
    let failing = take_one(&g.fail_next);
    if failing {
        tracing::warn!(to = %mask_phone(&req.to), "smsgw: nosozlik simulyatsiyasi (503)");
        return err(
            StatusCode::SERVICE_UNAVAILABLE,
            "operator vaqtincha ishlamayapti",
        );
    }
    if !is_e164(&req.to) {
        return err(StatusCode::UNPROCESSABLE_ENTITY, "to: E.164 kutilgan");
    }
    if req.text.is_empty() || req.text.chars().count() > 480 {
        return err(StatusCode::UNPROCESSABLE_ENTITY, "text: 1–480 belgi");
    }
    let id = {
        let mut i = g.inner.lock().unwrap_or_else(|e| e.into_inner());
        i.next_id += 1;
        let id = i.next_id;
        if i.messages.len() >= MAX_MESSAGES {
            i.messages.pop_front();
        }
        i.messages.push_back(Sms {
            id,
            to: req.to.clone(),
            text: req.text,
            reference: req.reference.clone(),
            received_at: now(),
        });
        id
    };
    tracing::info!(id, to = %mask_phone(&req.to), reference = %req.reference, "smsgw: SMS qabul qilindi");
    (StatusCode::ACCEPTED, Json(serde_json::json!({ "id": id }))).into_response()
}

async fn list(State(g): State<Gateway>, h: HeaderMap, Query(f): Query<Filter>) -> Response {
    if !g.authorized(&h) {
        return err(StatusCode::UNAUTHORIZED, "token noto'g'ri");
    }
    Json(g.messages(f.to.as_deref())).into_response()
}

async fn clear(State(g): State<Gateway>, h: HeaderMap) -> Response {
    if !g.authorized(&h) {
        return err(StatusCode::UNAUTHORIZED, "token noto'g'ri");
    }
    g.inner
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .messages
        .clear();
    StatusCode::NO_CONTENT.into_response()
}

async fn alert_webhook(
    State(g): State<Gateway>,
    h: HeaderMap,
    Json(p): Json<AlertmanagerPayload>,
) -> Response {
    if !g.authorized(&h) {
        return err(StatusCode::UNAUTHORIZED, "token noto'g'ri");
    }
    let label = |a: &AlertmanagerAlert, k: &str| a.labels.get(k).cloned().unwrap_or_default();
    let mut i = g.inner.lock().unwrap_or_else(|e| e.into_inner());
    for a in &p.alerts {
        let alert = Alert {
            alertname: label(a, "alertname"),
            status: a.status.clone(),
            severity: label(a, "severity"),
            instance: label(a, "instance"),
            received_at: now(),
        };
        tracing::warn!(alert = %alert.alertname, status = %alert.status, severity = %alert.severity, instance = %alert.instance, "navbatchi: ogohlantirish");
        if i.alerts.len() >= MAX_MESSAGES {
            i.alerts.pop_front();
        }
        i.alerts.push_back(alert);
    }
    StatusCode::OK.into_response()
}

async fn list_alerts(State(g): State<Gateway>, h: HeaderMap) -> Response {
    if !g.authorized(&h) {
        return err(StatusCode::UNAUTHORIZED, "token noto'g'ri");
    }
    Json(g.alerts()).into_response()
}

/// Fonda ishlayotgan shlyuz (testlar uchun).
pub struct RunningGateway {
    pub addr: SocketAddr,
    pub gateway: Gateway,
    stop: Option<tokio::sync::oneshot::Sender<()>>,
    task: tokio::task::JoinHandle<()>,
}

impl RunningGateway {
    pub fn url(&self) -> String {
        format!("http://{}/send", self.addr)
    }

    /// Shlyuzni to'xtatadi: ochiq ulanishlarga yopilish signali va tinglovchi darhol yopiladi —
    /// yangi ulanish rad etiladi ("shlyuz ishlamayapti" stsenariysi; graceful shutdown'ning o'zi
    /// tinglovchini ulanishlar tugaguncha ushlab turadi va mijoz javobsiz kutib qoladi).
    pub fn shutdown(&mut self) {
        if let Some(s) = self.stop.take() {
            let _ = s.send(());
        }
        self.task.abort();
    }
}

impl Drop for RunningGateway {
    fn drop(&mut self) {
        self.shutdown();
    }
}

/// `addr` da shlyuzni ishga tushiradi (port 0 — tasodifiy).
pub async fn spawn(addr: SocketAddr, gateway: Gateway) -> std::io::Result<RunningGateway> {
    let listener = tokio::net::TcpListener::bind(addr).await?;
    let addr = listener.local_addr()?;
    let (tx, rx) = tokio::sync::oneshot::channel::<()>();
    let app = gateway.router();
    let task = tokio::spawn(async move {
        let _ = axum::serve(listener, app)
            .with_graceful_shutdown(async {
                let _ = rx.await;
            })
            .await;
    });
    Ok(RunningGateway {
        addr,
        gateway,
        stop: Some(tx),
        task,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn token_check_is_exact() {
        let g = Gateway::new(Some("abc".into()));
        let mut h = HeaderMap::new();
        assert!(!g.authorized(&h));
        h.insert("authorization", "Bearer abd".parse().unwrap());
        assert!(!g.authorized(&h));
        h.insert("authorization", "Bearer abc".parse().unwrap());
        assert!(g.authorized(&h));
        assert!(Gateway::new(None).authorized(&HeaderMap::new()));
    }

    #[tokio::test]
    async fn alertmanager_webhook() {
        let mut gw = spawn(
            "127.0.0.1:0".parse().unwrap(),
            Gateway::new(Some("tk".into())),
        )
        .await
        .unwrap();
        let url = format!("http://{}/alerts", gw.addr);
        let body = r#"{"version":"4","status":"firing","receiver":"navbatchi","alerts":[
            {"status":"firing","labels":{"alertname":"MpayInstanceDown","severity":"critical","instance":"api-1:9464","job":"mpay-api"},
             "annotations":{"summary":"x"},"startsAt":"2026-10-26T10:00:00Z"}]}"#;
        let post = |auth: &'static str| {
            let url = url.clone();
            async move {
                let mut s = tokio::net::TcpStream::connect(gw_addr(&url)).await.unwrap();
                use tokio::io::{AsyncReadExt, AsyncWriteExt};
                let req = format!(
                    "POST /alerts HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer {auth}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                    body.len()
                );
                s.write_all(req.as_bytes()).await.unwrap();
                let mut out = String::new();
                s.read_to_string(&mut out).await.unwrap();
                out
            }
        };
        assert!(post("wrong").await.starts_with("HTTP/1.1 401"));
        assert!(post("tk").await.starts_with("HTTP/1.1 200"));
        let a = gw.gateway.alerts();
        assert_eq!(a.len(), 1);
        assert_eq!(
            (
                a[0].alertname.as_str(),
                a[0].status.as_str(),
                a[0].severity.as_str(),
                a[0].instance.as_str()
            ),
            ("MpayInstanceDown", "firing", "critical", "api-1:9464")
        );
        gw.shutdown();
    }

    fn gw_addr(url: &str) -> String {
        url.trim_start_matches("http://")
            .trim_end_matches("/alerts")
            .to_owned()
    }

    #[test]
    fn fail_next_counts_down() {
        let g = Gateway::new(None);
        g.fail_next(2);
        let take = || take_one(&g.fail_next);
        assert!(take() && take() && !take());
    }
}
