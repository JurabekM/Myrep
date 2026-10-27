//! Shield roli (2-faza P2.4, ADR-0019): `mpay-server shield --config …`. O'sha binar, faqat ichki
//! API — belgilar ombori (tezlik oynalari, qurilma–karta grafi) shu yagona instansiyada, API
//! instansiyalari [`crate::shield_client::RemoteShield`] orqali murojaat qiladi.
//!
//! * `POST /internal/shield/idv` — `IdvEventDto` → `IdvAssessment`
//! * `POST /internal/shield/txn` — `TxnEventDto` → `RiskAssessment`
//! * `POST /internal/shield/rekey` — `RekeyEventDto` → `RekeyResult` (ADR-0015)
//! * `GET /healthz`
//!
//! Yuqori mavjudlik (`[shield_ha] enabled`, ADR-0026): bir nechta instansiya, bittasi yetakchi;
//! zaxira ichki API'ga `503 SHIELD_STANDBY` qaytaradi (`crate::shield_ha`).
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
use mpay_shield::remote::{IdvEventDto, RekeyEventDto, RekeyResult, TxnEventDto};
use mpay_shield::Shield;
use tokio::net::TcpListener;

use mpay_common::clock::{Clock, SystemClock};

use crate::auth::{Authenticator, Mtls};
use crate::config::{Config, Role};
use crate::error::ApiError;
use crate::shield_ha::ShieldHa;

struct RoleState {
    shield: Arc<Shield>,
    auth: Authenticator,
    require_mtls: bool,
    ha: Option<Arc<ShieldHa>>,
    clock: Arc<dyn Clock>,
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
        // Zaxira instansiya xizmat qilmaydi — mijoz keyingi URL'ga o'tadi (ADR-0026).
        if let Some(ha) = &self.ha {
            if !ha.is_active(crate::shield_ha::now_ms(self.clock.as_ref())) {
                let mut e = ApiError::new(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "SHIELD_STANDBY",
                    "zaxira Shield instansiyasi",
                );
                e.retry_after = Some(1);
                return Err(e);
            }
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

async fn rekey(
    State(s): St,
    headers: HeaderMap,
    mtls: Mtls,
    body: Bytes,
) -> Result<Response, ApiError> {
    s.caller(&headers, &mtls)?;
    let dto: RekeyEventDto = parse(&body)?;
    let (old, new) = dto.ids().map_err(ApiError::bad_request)?;
    let linked = s.shield.link_rekeyed_device(old, new);
    tracing::info!(old = %dto.old, new = %dto.new, linked, "shield-role: qurilma kaliti almashtirildi");
    Ok(Json(RekeyResult { linked }).into_response())
}

async fn health(State(s): St) -> Json<serde_json::Value> {
    let (cards, devices, merchants, graph_nodes) = s.shield.stats();
    let ha = match &s.ha {
        Some(ha) => Some(ha.status(crate::shield_ha::now_ms(s.clock.as_ref())).await),
        None => None,
    };
    Json(serde_json::json!({
        "status": "ok",
        "role": "shield",
        // HA o'chiq — yagona instansiya doim yetakchi.
        "leader": ha.as_ref().is_none_or(|h| h.leader),
        "ha": ha,
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
    /// Yetakchilik (`[shield_ha] enabled`).
    pub ha: Option<Arc<ShieldHa>>,
    ha_task: Option<tokio::task::AbortHandle>,
    clock: Arc<dyn Clock>,
    pub handle: tokio::task::JoinHandle<std::io::Result<()>>,
}

impl RunningShield {
    /// To'g'ri to'xtatishdan oldin: yakuniy snapshot va ijarani bo'shatish (zaxira darhol oladi).
    pub async fn step_down(&mut self) {
        if let Some(t) = self.ha_task.take() {
            t.abort();
        }
        if let Some(ha) = &self.ha {
            ha.step_down(crate::shield_ha::now_ms(self.clock.as_ref()))
                .await;
        }
    }

    /// Yangi ulanishlarni to'xtatadi. `step_down` siz — yiqilish kabi: ijara muddatida tugaydi.
    pub fn shutdown(&mut self) {
        if let Some(t) = self.ha_task.take() {
            t.abort();
        }
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
    let clock: Arc<dyn Clock> = Arc::new(SystemClock);
    let ha = if cfg.shield_ha.enabled {
        let url = cfg
            .database
            .connect_url(|p| cfg.resolve(p))
            .map_err(|e| e.to_string())?;
        let db =
            mpay_vault::db::Db::open(&url, cfg.database.synchronous, cfg.database.max_connections)
                .await
                .map_err(|e| format!("ma'lumotlar bazasi: {e}"))?;
        crate::dedup::migrate(&db)
            .await
            .map_err(|e| e.to_string())?;
        let ha = Arc::new(ShieldHa::new(db, shield.clone(), cfg.shield_ha.clone()));
        // Birinchi qadam xizmatdan oldin: yetakchi bo'lsa — snapshot tiklangan holda boshlaydi.
        if let Err(e) = ha.tick(crate::shield_ha::now_ms(clock.as_ref())).await {
            tracing::warn!(error = %e, "shield-ha: birinchi qadam");
        }
        tracing::info!(
            instance = ha.instance(),
            "Shield roli: yuqori mavjudlik yoqilgan"
        );
        Some(ha)
    } else {
        None
    };
    let ha_task = ha.clone().map(|h| h.spawn(clock.clone()));
    let st = Arc::new(RoleState {
        shield,
        auth: Authenticator::new(&cfg.auth.keys),
        require_mtls: cfg.auth.require_mtls,
        ha: ha.clone(),
        clock: clock.clone(),
    });
    let app = Router::new()
        .route("/internal/shield/idv", post(idv))
        .route("/internal/shield/txn", post(txn))
        .route("/internal/shield/rekey", post(rekey))
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
                    let ha = match &st.ha {
                        Some(ha) => {
                            Some(ha.status(crate::shield_ha::now_ms(st.clock.as_ref())).await)
                        }
                        None => None,
                    };
                    // HA o'chiq — yagona instansiya doim yetakchi (ogohlantirish qoidalari bir xil).
                    t.gauge(
                        "mpay_shield_leader",
                        "Shu instansiya yetakchimi (1) yoki zaxira (0)",
                        "",
                        f64::from(u8::from(ha.as_ref().is_none_or(|h| h.leader))),
                    );
                    if let Some(h) = ha {
                        t.gauge("mpay_shield_epoch", "Yetakchilik davri", "", h.epoch as f64);
                        if let Some(age) = h.snapshot_age_secs {
                            t.gauge(
                                "mpay_shield_snapshot_age_seconds",
                                "Oxirgi snapshot'dan beri (faqat yetakchi)",
                                "",
                                age as f64,
                            );
                        }
                        t.gauge(
                            "mpay_shield_snapshot_bytes",
                            "Oxirgi snapshot hajmi",
                            "",
                            h.snapshot_bytes as f64,
                        );
                    }
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
        ha,
        ha_task,
        clock,
        handle,
    })
}
