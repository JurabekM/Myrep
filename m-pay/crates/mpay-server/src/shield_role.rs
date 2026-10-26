//! Shield roli (2-faza P2.4, ADR-0019): `mpay-server shield --config …`. O'sha binar, faqat ichki
//! API — belgilar ombori (tezlik oynalari, qurilma–karta grafi) shu yagona instansiyada, API
//! instansiyalari [`crate::shield_client::RemoteShield`] orqali murojaat qiladi.
//!
//! * `POST /internal/shield/idv` — `IdvEventDto` → `IdvAssessment`
//! * `POST /internal/shield/txn` — `TxnEventDto` → `RiskAssessment`
//! * `GET /healthz`
//!
//! Kirish: `shield` rolidagi API kaliti (`[[auth.keys]] role = "shield"`); `require_mtls` bo'lsa
//! mijoz sertifikati CN = kalit ID. Ochiq PAN qabul qilinmaydi (DTO'larda yo'q).

use std::net::SocketAddr;
use std::sync::Arc;

use axum::body::Bytes;
use axum::extract::State;
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use mpay_common::ports::RiskAssessment;
use mpay_shield::remote::{IdvEventDto, TxnEventDto};
use mpay_shield::Shield;
use tokio::net::TcpListener;

use crate::auth::{Authenticator, Mtls};
use crate::config::{Config, Role};
use crate::error::ApiError;

struct RoleState {
    shield: Arc<Shield>,
    auth: Authenticator,
    require_mtls: bool,
}

impl RoleState {
    fn caller(&self, headers: &HeaderMap, mtls: &Mtls) -> Result<(), ApiError> {
        let c = self.auth.authorize(headers, Role::Shield)?;
        if self.require_mtls && mtls.0.as_deref() != Some(c.id.as_str()) {
            return Err(ApiError::new(
                StatusCode::FORBIDDEN,
                "MTLS_REQUIRED",
                "mijoz sertifikati kerak (CN = API kaliti ID)",
            ));
        }
        Ok(())
    }
}

type St = State<Arc<RoleState>>;

/// Tana autentifikatsiyadan **keyin** o'qiladi — kalitsiz mijoz tahlil xatolarini ko'rmaydi.
fn parse<T: serde::de::DeserializeOwned>(body: &[u8]) -> Result<T, ApiError> {
    serde_json::from_slice(body).map_err(|_| ApiError::bad_request("JSON formati noto'g'ri"))
}

async fn idv(
    State(s): St,
    headers: HeaderMap,
    mtls: Mtls,
    body: Bytes,
) -> Result<Response, ApiError> {
    s.caller(&headers, &mtls)?;
    let dto: IdvEventDto = parse(&body)?;
    let ev = dto.to_event().map_err(ApiError::bad_request)?;
    let d = s.shield.assess_provision(&ev);
    tracing::info!(score = d.assessment.score, decision = ?d.assessment.decision, "shield-role: ID&V");
    Ok(Json(d.assessment).into_response())
}

async fn txn(
    State(s): St,
    headers: HeaderMap,
    mtls: Mtls,
    body: Bytes,
) -> Result<Response, ApiError> {
    s.caller(&headers, &mtls)?;
    let dto: TxnEventDto = parse(&body)?;
    let ev = dto.to_event(&s.shield).map_err(ApiError::bad_request)?;
    let a = s.shield.assess_txn(&ev);
    tracing::debug!(score = a.score, decision = ?a.decision, "shield-role: tranzaksiya");
    Ok(Json(RiskAssessment {
        score: a.score,
        decision: a.decision,
        reasons: a.reasons,
    })
    .into_response())
}

async fn health(State(s): St) -> Json<serde_json::Value> {
    let (cards, devices, merchants, graph_nodes) = s.shield.stats();
    Json(serde_json::json!({
        "status": "ok",
        "role": "shield",
        "cards": cards,
        "devices": devices,
        "merchants": merchants,
        "graph_nodes": graph_nodes,
    }))
}

/// Ishlayotgan Shield roli.
pub struct RunningShield {
    pub addr: SocketAddr,
    pub metrics_addr: Option<SocketAddr>,
    shutdown: Option<tokio::sync::oneshot::Sender<()>>,
    metrics: Option<tokio::task::JoinHandle<()>>,
    pub handle: tokio::task::JoinHandle<std::io::Result<()>>,
}

impl RunningShield {
    pub fn shutdown(&mut self) {
        if let Some(tx) = self.shutdown.take() {
            let _ = tx.send(());
        }
        if let Some(m) = self.metrics.take() {
            m.abort();
        }
    }
}

impl Drop for RunningShield {
    fn drop(&mut self) {
        self.shutdown();
    }
}

/// Shield rolini ishga tushiradi (`[http]` — listen/TLS/client_ca, `[auth]`, `[shield]`).
pub async fn start(cfg: &Config) -> Result<RunningShield, String> {
    let shield = crate::state::build_engine(cfg).map_err(|e| e.to_string())?;
    let st = Arc::new(RoleState {
        shield,
        auth: Authenticator::new(&cfg.auth.keys),
        require_mtls: cfg.auth.require_mtls,
    });
    let app = Router::new()
        .route("/internal/shield/idv", post(idv))
        .route("/internal/shield/txn", post(txn))
        .route("/healthz", get(health))
        .route_layer(axum::middleware::from_fn(crate::metrics::track))
        .with_state(st.clone());
    let tls = match (&cfg.http.tls_cert, &cfg.http.tls_key) {
        (Some(c), Some(k)) => Some(crate::serve::load_tls(
            &cfg.resolve(c),
            &cfg.resolve(k),
            cfg.http
                .client_ca
                .as_ref()
                .map(|p| cfg.resolve(p))
                .as_deref(),
        )?),
        _ => {
            tracing::warn!("Shield roli: TLS o'chiq — faqat loopback sinov");
            None
        }
    };
    let listener = TcpListener::bind(cfg.http.listen)
        .await
        .map_err(|e| e.to_string())?;
    let addr = listener.local_addr().map_err(|e| e.to_string())?;
    let (tx, rx) = tokio::sync::oneshot::channel::<()>();
    let (metrics_addr, metrics) = match cfg.metrics.listen {
        Some(listen) => {
            let gather: crate::metrics::Gather = Arc::new(move || {
                let st = st.clone();
                Box::pin(async move {
                    let mut t = crate::metrics::Text::default();
                    crate::metrics::render_common(&mut t, "shield");
                    let (cards, devices, merchants, nodes) = st.shield.stats();
                    for (kind, v) in [
                        ("cards", cards),
                        ("devices", devices),
                        ("merchants", merchants),
                        ("graph_nodes", nodes),
                    ] {
                        t.gauge(
                            &format!("mpay_shield_{kind}"),
                            "Shield belgilar omboridagi yozuvlar",
                            "",
                            v as f64,
                        );
                    }
                    t.finish()
                })
            });
            let (a, h) = crate::metrics::start(listen, gather).await?;
            (Some(a), Some(h))
        }
        None => (None, None),
    };
    let opts = crate::accept_opts(cfg, tls, Arc::new(std::collections::HashSet::new()));
    let handle = tokio::spawn(crate::serve::serve(listener, app, opts, async move {
        let _ = rx.await;
    }));
    tracing::info!(%addr, "mpay-server: Shield roli tinglayapti");
    Ok(RunningShield {
        addr,
        metrics_addr,
        shutdown: Some(tx),
        metrics,
        handle,
    })
}
