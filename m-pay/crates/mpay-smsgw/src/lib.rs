//! `mpay-smsgw` — virtual SMS shlyuzi (2-faza P2.1, ADR-0016). Bankning haqiqiy SMS shlyuzi o'rnida
//! `mpay-server` ning `[otp] channel = "webhook"` kanalini telefonsiz sinash uchun:
//!
//! * `POST /send` `{"to","text","reference"}` + `Authorization: Bearer <token>` → `202 {"id"}`;
//! * `GET /messages[?to=+998…]` (shu token bilan) — "virtual telefonlar" qutisi, test va demo uchun;
//! * `DELETE /messages` — qutini tozalash.
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

#[derive(Default)]
struct Inner {
    messages: VecDeque<Sms>,
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
            .route("/healthz", axum::routing::get(|| async { "ok" }))
            .with_state(self.clone())
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

fn err(code: StatusCode, msg: &'static str) -> Response {
    (code, Json(serde_json::json!({ "error": msg }))).into_response()
}

async fn send(State(g): State<Gateway>, h: HeaderMap, Json(req): Json<SendReq>) -> Response {
    if !g.authorized(&h) {
        return err(StatusCode::UNAUTHORIZED, "token noto'g'ri");
    }
    let failing = g
        .fail_next
        .fetch_update(Ordering::SeqCst, Ordering::SeqCst, |n| n.checked_sub(1))
        .is_ok();
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

    #[test]
    fn fail_next_counts_down() {
        let g = Gateway::new(None);
        g.fail_next(2);
        let take = || {
            g.fail_next
                .fetch_update(Ordering::SeqCst, Ordering::SeqCst, |n| n.checked_sub(1))
                .is_ok()
        };
        assert!(take() && take() && !take());
    }
}
