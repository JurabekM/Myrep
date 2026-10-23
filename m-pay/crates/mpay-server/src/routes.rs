//! HTTP marshrutlari (`docs/specs/api.md`).

use std::future::Future;
use std::sync::Arc;
use std::time::Instant;

use axum::body::Bytes;
use axum::extract::{DefaultBodyLimit, MatchedPath, Path, Request, State};
use axum::http::{header, HeaderMap, HeaderValue, StatusCode};
use axum::middleware::{self, Next};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use mpay_common::api::{
    Empty, Envelope, LukDto, LuksResponse, OtpVerifyRequest, ProvisionRequest as ProvisionDto,
    ProvisionResponse, SandboxOtp, ServerIdentityDto, TokenProfileDto,
};
use mpay_common::{CardExpiry, Pan, PanKind, TokenId};
use mpay_pqlink::SessionInfo;
use mpay_vault::{DeviceContext, LukGrant, ProvisionOutcome, ProvisionRequest, TokenProfile};
use serde::de::DeserializeOwned;
use serde::Serialize;
use zeroize::Zeroizing;

use crate::config::Role;
use crate::error::ApiError;
use crate::state::AppState;

/// PQ Link tanalari uchun Content-Type.
pub const PQLINK_CONTENT_TYPE: &str = "application/x-mpay-pqlink";

type St = State<Arc<AppState>>;

/// Router.
pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/healthz", get(health))
        .route("/v1/pqlink/identity", get(identity))
        .route("/v1/pqlink/hello", post(pq_hello))
        .route("/v1/pqlink/finish", post(pq_finish))
        .route("/v1/tokens", post(provision))
        .route("/v1/tokens/{id}", get(get_token).delete(delete_token))
        .route("/v1/tokens/{id}/idv/verify", post(idv_verify))
        .route("/v1/tokens/{id}/luks", post(replenish))
        .route("/v1/tokens/{id}/suspend", post(suspend))
        .route("/v1/tokens/{id}/resume", post(resume))
        .route("/v1/audit/verify", get(audit_verify))
        .route("/v1/sandbox/otp/{challenge_id}", get(sandbox_otp))
        .route_layer(middleware::from_fn(log_requests))
        .layer(DefaultBodyLimit::max(256 * 1024))
        .with_state(state)
}

/// Har so'rov: metod, marshrut shabloni, status, davomiylik. Tanalar hech qachon logga yozilmaydi.
async fn log_requests(req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let route = req
        .extensions()
        .get::<MatchedPath>()
        .map(|p| p.as_str().to_owned())
        .unwrap_or_default();
    let start = Instant::now();
    let resp = next.run(req).await;
    tracing::info!(%method, route, status = resp.status().as_u16(), ms = start.elapsed().as_millis() as u64, "http");
    resp
}

async fn health(State(s): St) -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "version": crate::VERSION,
        "keystore": s.keystore.backend_name(),
        "sandbox": s.sandbox,
        "pqlink_sessions": s.pqlink.session_count(),
    }))
}

async fn identity(State(s): St) -> Json<ServerIdentityDto> {
    let id = s.pqlink.identity();
    Json(ServerIdentityDto {
        suite: "PQL1_X25519MLKEM768_ED25519MLDSA65_CHACHA20POLY1305_SHA256".into(),
        ed25519: hex::encode(id.ed25519),
        mldsa65: hex::encode(&id.mldsa65),
        fingerprint: hex::encode(id.fingerprint()),
    })
}

fn require_pqlink_ct(headers: &HeaderMap) -> Result<(), ApiError> {
    match headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
    {
        Some(ct) if ct.starts_with(PQLINK_CONTENT_TYPE) => Ok(()),
        _ => Err(ApiError::new(
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "UNSUPPORTED_MEDIA_TYPE",
            format!("Content-Type: {PQLINK_CONTENT_TYPE} kutilgan"),
        )),
    }
}

fn pqlink_body(status: StatusCode, body: Vec<u8>) -> Response {
    (
        status,
        [(
            header::CONTENT_TYPE,
            HeaderValue::from_static(PQLINK_CONTENT_TYPE),
        )],
        body,
    )
        .into_response()
}

async fn pq_hello(State(s): St, headers: HeaderMap, body: Bytes) -> Result<Response, ApiError> {
    require_pqlink_ct(&headers)?;
    let pq = s.pqlink.clone();
    // ML-KEM/ML-DSA hisoblashlari bloklovchi CPU ishi — async ishchilardan tashqarida.
    let sh = tokio::task::spawn_blocking(move || pq.handle_hello(&body))
        .await
        .map_err(|_| {
            ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
        })??;
    Ok(pqlink_body(StatusCode::OK, sh))
}

async fn pq_finish(State(s): St, headers: HeaderMap, body: Bytes) -> Result<Response, ApiError> {
    require_pqlink_ct(&headers)?;
    let pq = s.pqlink.clone();
    let (_info, sa) = tokio::task::spawn_blocking(move || pq.handle_finish(&body))
        .await
        .map_err(|_| {
            ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
        })??;
    Ok(pqlink_body(StatusCode::OK, sa))
}

/// Muhrlangan so'rov → ishlovchi → muhrlangan javob. Yozuvni ochib bo'lmasa — ochiq JSON xato.
async fn sealed<Req, Resp, F, Fut>(s: &AppState, headers: &HeaderMap, body: &[u8], f: F) -> Response
where
    Req: DeserializeOwned,
    Resp: Serialize,
    F: FnOnce(SessionInfo, Req) -> Fut,
    Fut: Future<Output = Result<Resp, ApiError>>,
{
    if let Err(e) = require_pqlink_ct(headers) {
        return e.into_response();
    }
    let (info, plaintext) = match s.pqlink.open(body) {
        Ok(x) => x,
        Err(e) => return ApiError::from(e).into_response(),
    };
    let (status, env) = match serde_json::from_slice::<Req>(&plaintext) {
        Err(_) => (
            StatusCode::BAD_REQUEST,
            Envelope::<Resp>::err("BAD_REQUEST", "JSON so'rov formati noto'g'ri"),
        ),
        Ok(req) => match f(info.clone(), req).await {
            Ok(resp) => (StatusCode::OK, Envelope::ok(resp)),
            Err(e) => (e.status, Envelope::err(e.code, e.message)),
        },
    };
    drop(plaintext);
    let json = match serde_json::to_vec(&env) {
        Ok(j) => Zeroizing::new(j),
        Err(_) => {
            return ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
                .into_response()
        }
    };
    match s.pqlink.seal(&info.session_id, &json) {
        Ok(b) => pqlink_body(status, b),
        Err(e) => ApiError::from(e).into_response(),
    }
}

fn device_ctx(info: &SessionInfo) -> DeviceContext {
    DeviceContext {
        device_id: info.device_id,
        security_level: info.security_level,
    }
}

fn parse_token_id(id: &str) -> Result<TokenId, ApiError> {
    TokenId::parse(id).ok_or_else(|| ApiError::bad_request("token_id formati noto'g'ri"))
}

fn luk_dto(g: &LukGrant) -> LukDto {
    LukDto {
        seq: g.seq,
        key: Zeroizing::new(hex::encode(g.key.expose())),
        issued_at: g.issued_at,
        expires_at: g.expires_at,
        max_uses: g.max_uses,
    }
}

fn profile_dto(p: &TokenProfile) -> TokenProfileDto {
    TokenProfileDto {
        token_id: p.token_id.clone(),
        dpan: Zeroizing::new(p.dpan.expose_digits().to_owned()),
        dpan_expiry: p.dpan_expiry.clone(),
        psn: p.psn,
        aid: p.aid.clone(),
        scheme: p.scheme.clone(),
        luks: p.luks.iter().map(luk_dto).collect(),
    }
}

async fn provision(State(s): St, headers: HeaderMap, body: Bytes) -> Response {
    let vault = s.vault.clone();
    sealed(&s, &headers, &body, |info, req: ProvisionDto| async move {
        let fpan = Pan::parse_kind(&req.pan, PanKind::Funding)
            .map_err(|e| ApiError::bad_request(e.to_string()))?;
        let expiry = CardExpiry::parse_yymm(&req.expiry)
            .ok_or_else(|| ApiError::bad_request("expiry YYMM bo'lishi kerak"))?;
        let out = vault
            .provision(ProvisionRequest { fpan, expiry }, device_ctx(&info))
            .await?;
        Ok(match out {
            ProvisionOutcome::Active { profile, idv } => ProvisionResponse::Active {
                profile: profile_dto(&profile),
                idv,
            },
            ProvisionOutcome::PendingIdv {
                token_id,
                challenge_id,
                otp_expires_at,
                idv,
            } => ProvisionResponse::PendingIdv {
                token_id,
                challenge_id,
                otp_expires_at,
                idv,
            },
            ProvisionOutcome::Declined { idv } => ProvisionResponse::Declined { idv },
        })
    })
    .await
}

async fn idv_verify(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    let vault = s.vault.clone();
    sealed(
        &s,
        &headers,
        &body,
        |info, req: OtpVerifyRequest| async move {
            let token_id = parse_token_id(&id)?;
            let p = vault
                .verify_otp(&token_id, &req.challenge_id, &req.otp, device_ctx(&info))
                .await?;
            Ok(profile_dto(&p))
        },
    )
    .await
}

async fn replenish(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    let vault = s.vault.clone();
    sealed(&s, &headers, &body, |info, _req: Empty| async move {
        let token_id = parse_token_id(&id)?;
        let luks = vault.replenish_luks(&token_id, device_ctx(&info)).await?;
        Ok(LuksResponse {
            luks: luks.iter().map(luk_dto).collect(),
        })
    })
    .await
}

// ---------------------------------------------------------------- operator

async fn get_token(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    s.auth.authorize(&headers, Role::Operator)?;
    Ok(Json(s.vault.summary(&parse_token_id(&id)?).await?).into_response())
}

async fn suspend(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    let c = s.auth.authorize(&headers, Role::Operator)?;
    Ok(Json(s.vault.suspend(&parse_token_id(&id)?, &c.actor()).await?).into_response())
}

async fn resume(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    let c = s.auth.authorize(&headers, Role::Operator)?;
    Ok(Json(s.vault.resume(&parse_token_id(&id)?, &c.actor()).await?).into_response())
}

async fn delete_token(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    let c = s.auth.authorize(&headers, Role::Operator)?;
    Ok(Json(s.vault.delete(&parse_token_id(&id)?, &c.actor()).await?).into_response())
}

async fn audit_verify(State(s): St, headers: HeaderMap) -> Result<Response, ApiError> {
    s.auth.authorize(&headers, Role::Operator)?;
    Ok(Json(s.vault.verify_audit().await?).into_response())
}

async fn sandbox_otp(
    State(s): St,
    Path(challenge_id): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    if !s.expose_otp {
        return Err(ApiError::not_found());
    }
    s.auth.authorize(&headers, Role::Operator)?;
    let otp = s.vault.sandbox_otp(&challenge_id).await?;
    Ok(Json(SandboxOtp {
        challenge_id,
        otp: Zeroizing::new(otp),
    })
    .into_response())
}
