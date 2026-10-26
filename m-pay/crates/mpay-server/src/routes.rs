//! HTTP marshrutlari (`docs/specs/api.md`).

use std::future::Future;
use std::sync::Arc;

use axum::body::Bytes;
use std::net::SocketAddr;

use axum::extract::{ConnectInfo, DefaultBodyLimit, Path, State};
use axum::http::{header, HeaderMap, HeaderValue, StatusCode};
use axum::middleware;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use mpay_common::api::{
    AuthorizationRequest, Empty, Envelope, LukDto, LuksResponse, OtpVerifyRequest,
    ProvisionRequest as ProvisionDto, ProvisionResponse, SandboxOtp, ServerIdentityDto,
    TokenProfileDto,
};
use mpay_common::{CardExpiry, Pan, PanKind, TokenId};
use mpay_pqlink::SessionInfo;
use mpay_vault::{DeviceContext, LukGrant, ProvisionOutcome, ProvisionRequest, TokenProfile};
use serde::de::DeserializeOwned;
use serde::Serialize;
use zeroize::Zeroizing;

use crate::auth::Mtls;
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
        .route("/v1/pqlink/enroll", post(pq_enroll))
        .route("/v1/pqlink/revocations", get(pq_revocations))
        .route("/v1/pqlink/hello", post(pq_hello))
        .route("/v1/pqlink/finish", post(pq_finish))
        .route("/v1/tokens", post(provision))
        .route("/v1/tokens/{id}", get(get_token).delete(delete_token))
        .route("/v1/tokens/{id}/idv/verify", post(idv_verify))
        .route("/v1/tokens/{id}/idv/resend", post(idv_resend))
        .route("/v1/tokens/{id}/luks", post(replenish))
        .route("/v1/devices/rekey", post(rekey))
        .route("/v1/tokens/{id}/suspend", post(suspend))
        .route("/v1/tokens/{id}/resume", post(resume))
        .route("/v1/audit/verify", get(audit_verify))
        .route("/v1/sandbox/otp/{challenge_id}", get(sandbox_otp))
        .route("/v1/sandbox/accounts", get(sandbox_accounts))
        .route("/v1/sandbox/integrity-token", post(sandbox_integrity))
        .route("/v1/authorizations", post(authorize))
        .route("/v1/terminal/ping", get(terminal_ping))
        .route_layer(middleware::from_fn(crate::metrics::track))
        .layer(DefaultBodyLimit::max(256 * 1024))
        .with_state(state)
}

async fn health(State(s): St) -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "version": crate::VERSION,
        "keystore": s.keystore.backend_name(),
        "sandbox": s.sandbox,
        "pqlink_sessions": s.pqlink.session_count().await,
    }))
}

async fn identity(State(s): St) -> Json<ServerIdentityDto> {
    let id = s.pqlink.identity();
    Json(ServerIdentityDto {
        suite: "PQL1_X25519MLKEM768_ED25519MLDSA65_CHACHA20POLY1305_SHA256".into(),
        ed25519: hex::encode(id.ed25519),
        mldsa65: hex::encode(&id.mldsa65),
        fingerprint: hex::encode(id.fingerprint()),
        next: s
            .next_identity
            .as_ref()
            .map(|n| mpay_common::api::NextIdentityDto {
                ed25519: hex::encode(n.identity.ed25519),
                mldsa65: hex::encode(&n.identity.mldsa65),
                fingerprint: hex::encode(n.identity.fingerprint()),
                endorsement_ed25519: hex::encode(n.sig_ed25519),
                endorsement_mldsa65: hex::encode(&n.sig_mldsa65),
            }),
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

/// Handshake oldidan: IP chegarasi va global parallellik ruxsati (tahdid modeli D2).
fn handshake_guard(
    s: &AppState,
    peer: SocketAddr,
    headers: &HeaderMap,
) -> Result<Option<tokio::sync::OwnedSemaphorePermit>, ApiError> {
    let ip = s.client_ip(peer, headers);
    s.limits.ip(&crate::clientip::rate_key(ip)).map_err(|l| {
        crate::metrics::rate_limited(crate::metrics::Limit::Ip);
        tracing::warn!(%ip, "rate-limit: handshake IP");
        ApiError::rate_limited(l, false)
    })?;
    s.limits.handshake_permit().map_err(|l| {
        crate::metrics::rate_limited(crate::metrics::Limit::Handshake);
        tracing::warn!("rate-limit: handshake navbati to'la");
        ApiError::rate_limited(l, true)
    })
}

/// Qurilma kalitini almashtirish (ADR-0015): yangi kalit (nonce bilan attestatsiya) sessiya va eski
/// qurilmaga bog'langan xabarni imzolaydi; tokenlar yangi qurilmaga ko'chadi, eski qurilma reyestrdan
/// o'chadi. Muddati o'tgan attestatsiyali qurilma uchun ham ruxsat.
async fn rekey(State(s): St, headers: HeaderMap, body: Bytes) -> Response {
    let st = s.clone();
    sealed_with(
        &s,
        &headers,
        &body,
        true,
        |info, req: mpay_common::api::RekeyRequest| async move {
            let Some(enroll) = &st.enrollment else {
                return Err(ApiError::not_found());
            };
            let bad = |m: &str| ApiError::bad_request(m.to_owned());
            let chain = req
                .cert_chain
                .iter()
                .map(|h| hex::decode(h).map_err(|_| bad("cert_chain hex emas")))
                .collect::<Result<Vec<_>, _>>()?;
            let sig = hex::decode(&req.signature).map_err(|_| bad("signature hex emas"))?;
            let pq = st.pqlink.clone();
            let new = tokio::task::spawn_blocking(move || pq.verify_device_chain(&chain))
                .await
                .map_err(|_| {
                    ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
                })??;
            if new.device_id == info.device_id {
                return Err(bad("yangi kalit eskisidan farq qilishi kerak"));
            }
            let msg = [
                mpay_pqlink::crypto::REKEY_LABEL,
                &info.session_id[..],
                &info.device_id.0[..],
            ]
            .concat();
            new.verify_signature(&msg, &sig)?;
            enroll.consume(&new.attestation_challenge).await?;
            let db = |e: sqlx::Error| {
                tracing::error!(error = %e, "pqlink_devices");
                ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
            };
            if enroll
                .attested_at(&new.device_id.to_hex())
                .await
                .map_err(db)?
                .is_some()
            {
                return Err(bad("yangi kalit allaqachon ro'yxatda"));
            }
            // Tartib: yangi qurilma reyestrga → tokenlar ko'chadi (bitta Vault tranzaksiyasi) → eskisi
            // o'chadi. Tokenlar hech qachon reyestrda yo'q qurilmaga bog'lanib qolmaydi: ko'chirish
            // yiqilsa yangi yozuv qaytariladi, eski kalit esa ishlayveradi (qayta urinish mumkin).
            let new_hex = new.device_id.to_hex();
            enroll.register_new(&new).await.map_err(db)?;
            let moved = match st
                .vault
                .rebind_device(&info.device_id, &new.device_id)
                .await
            {
                Ok(n) => n,
                Err(e) => {
                    if let Err(r) = enroll.remove(&new_hex).await {
                        tracing::error!(error = %r, "rekey: yangi qurilma reyestrdan qaytarilmadi");
                    }
                    return Err(e.into());
                }
            };
            // Eski yozuvni o'chirib bo'lmasa — xavfsiz (eski kalitda endi token yo'q), faqat log.
            if let Err(e) = enroll.remove(&info.device_id.to_hex()).await {
                tracing::error!(error = %e, "rekey: eski qurilma reyestrdan o'chirilmadi");
            }
            Ok(mpay_common::api::RekeyResponse {
                device_id: new.device_id.to_hex(),
                tokens_moved: moved,
            })
        },
    )
    .await
}

/// Oflayn ildiz imzolagan bekor qilingan identifikatorlar (ADR-0014); sozlanmagan bo'lsa 404.
async fn pq_revocations(State(s): St) -> Result<Response, ApiError> {
    s.revocations
        .as_ref()
        .map(|r| Json(r.clone()).into_response())
        .ok_or_else(ApiError::not_found)
}

/// Yangi qurilma uchun bir martalik nonce (P1.7): qurilma kalitini `attestationChallenge = nonce`
/// bilan yaratadi. IP chegarasi handshake bilan umumiy.
async fn pq_enroll(
    State(s): St,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    let Some(e) = &s.enrollment else {
        return Err(ApiError::not_found());
    };
    let ip = s.client_ip(peer, &headers);
    s.limits.ip(&crate::clientip::rate_key(ip)).map_err(|l| {
        crate::metrics::rate_limited(crate::metrics::Limit::Ip);
        tracing::warn!(%ip, "rate-limit: enroll IP");
        ApiError::rate_limited(l, false)
    })?;
    let (nonce, expires_at) = e.issue()?;
    Ok(Json(serde_json::json!({
        "nonce": hex::encode(nonce),
        "expires_at": expires_at,
    }))
    .into_response())
}

async fn pq_hello(
    State(s): St,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, ApiError> {
    require_pqlink_ct(&headers)?;
    let _permit = handshake_guard(&s, peer, &headers)?;
    // Joy yo'q bo'lsa qimmat hisoblashdan oldin rad (sessiyalar ombori umumiy bo'lishi mumkin).
    if !s.pqlink.has_room().await? {
        return Err(mpay_pqlink::PqLinkError::TooManySessions.into());
    }
    let pq = s.pqlink.clone();
    // ML-KEM/ML-DSA hisoblashlari bloklovchi CPU ishi — async ishchilardan tashqarida.
    let prepared = tokio::task::spawn_blocking(move || pq.hello_crypto(&body))
        .await
        .map_err(|_| {
            ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
        })??;
    let sh = s.pqlink.commit_hello(prepared).await?;
    Ok(pqlink_body(StatusCode::OK, sh))
}

async fn pq_finish(
    State(s): St,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, ApiError> {
    require_pqlink_ct(&headers)?;
    let _permit = handshake_guard(&s, peer, &headers)?;
    let start = s.pqlink.begin_finish(&body).await?;
    let pq = s.pqlink.clone();
    // Attestatsiya zanjiri va imzolar — bloklovchi CPU ishi.
    let verified = tokio::task::spawn_blocking(move || pq.finish_crypto(start))
        .await
        .map_err(|_| {
            ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
        })??;
    let (_info, sa) = s.pqlink.commit_finish(verified).await?;
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
    sealed_with(s, headers, body, false, f).await
}

/// `stale_ok` — muddati o'tgan attestatsiyali qurilmaga ham ruxsat (faqat `/v1/devices/rekey`).
async fn sealed_with<Req, Resp, F, Fut>(
    s: &AppState,
    headers: &HeaderMap,
    body: &[u8],
    stale_ok: bool,
    f: F,
) -> Response
where
    Req: DeserializeOwned,
    Resp: Serialize,
    F: FnOnce(SessionInfo, Req) -> Fut,
    Fut: Future<Output = Result<Resp, ApiError>>,
{
    if let Err(e) = require_pqlink_ct(headers) {
        return e.into_response();
    }
    let (info, plaintext) = match s.pqlink.open(body).await {
        Ok(x) => x,
        Err(e) => return ApiError::from(e).into_response(),
    };
    // Qurilma chegarasi: javob baribir muhrlanadi — sessiya ketma-ketligi buzilmaydi.
    let limited = s.limits.device(&info.device_id.to_string()).err();
    let stale = !stale_ok && s.reattest_due(&info);
    let (status, env) = match serde_json::from_slice::<Req>(&plaintext) {
        _ if stale => (
            StatusCode::FORBIDDEN,
            Envelope::<Resp>::err(
                "REATTEST_REQUIRED",
                "qurilma attestatsiyasi eskirgan — kalitni almashtiring (/v1/devices/rekey)",
            ),
        ),
        _ if limited.is_some() => {
            crate::metrics::rate_limited(crate::metrics::Limit::Device);
            tracing::warn!(device = %info.device_id, "rate-limit: qurilma");
            (
                StatusCode::TOO_MANY_REQUESTS,
                Envelope::<Resp>::err("RATE_LIMITED", "so'rovlar chegarasidan oshdi"),
            )
        }
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
    match s.pqlink.seal(&info.session_id, &json).await {
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
    let st = s.clone();
    sealed(&s, &headers, &body, |info, req: ProvisionDto| async move {
        let fpan = Pan::parse_kind(&req.pan, PanKind::Funding)
            .map_err(|e| ApiError::bad_request(e.to_string()))?;
        let expiry = CardExpiry::parse_yymm(&req.expiry)
            .ok_or_else(|| ApiError::bad_request("expiry YYMM bo'lishi kerak"))?;
        let integrity = check_integrity(&st, &info, req.integrity_token.as_deref()).await?;
        // OTP SMS uchun emitentdan telefonni topishga — faqat kanal SMS yuborsa (nusxa `Drop` da tozalanadi).
        let fpan_for_otp = st.otp.sends().then(|| fpan.clone());
        let out = st
            .vault
            .provision(
                ProvisionRequest {
                    fpan,
                    expiry,
                    integrity,
                },
                device_ctx(&info),
            )
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
            } => {
                let ttl = otp_expires_at - st.clock.unix();
                let otp_sent_to = match &fpan_for_otp {
                    Some(fpan) => queue_otp(&st, fpan, &challenge_id, ttl).await,
                    None => None,
                };
                ProvisionResponse::PendingIdv {
                    token_id,
                    challenge_id,
                    otp_expires_at,
                    idv,
                    otp_sent_to,
                }
            }
            ProvisionOutcome::Declined { idv } => ProvisionResponse::Declined { idv },
        })
    })
    .await
}

/// Play Integrity tokeni (ADR-0021): haqiqiylik va sessiyaga bog'lanish — shu yerda (buzilsa
/// so'rov rad etiladi), verdict sifati — Shield'da. Token va verdict logga yozilmaydi.
async fn check_integrity(
    s: &AppState,
    info: &SessionInfo,
    token: Option<&str>,
) -> Result<Option<mpay_common::ports::IntegritySignals>, ApiError> {
    let Some(pi) = &s.integrity else {
        return Ok(None);
    };
    let now_ms = s.clock.now().unix_timestamp() * 1000;
    let r = pi
        .verify(
            token,
            mpay_integrity::Purpose::Provision,
            &info.session_id,
            now_ms,
        )
        .await;
    match &r {
        Ok(Some(sig)) => {
            crate::metrics::integrity_check("ok");
            tracing::info!(device = %info.device_id, app = sig.app, level = sig.device, licensed = sig.licensed, env_risk = sig.env_risk, "integrity: verdict");
        }
        Ok(None) => crate::metrics::integrity_check("absent"),
        Err(e) => {
            crate::metrics::integrity_check(match e {
                mpay_integrity::IntegrityError::Missing => "missing",
                mpay_integrity::IntegrityError::Unavailable(_) => "unavailable",
                _ => "invalid",
            });
            tracing::warn!(device = %info.device_id, error = %e, "integrity: token rad etildi");
        }
    }
    r.map_err(|e| crate::integrity::api_error(&e))
}

/// Sandbox: emulyatordagi demo ilova uchun mock yaxlitlik tokeni (haqiqiy Play Integrity o'rnida).
/// Faqat `[integrity] mode = "mock"` (u faqat `sandbox = true` bilan ruxsat) va operator kaliti.
async fn sandbox_integrity(
    State(s): St,
    headers: HeaderMap,
    mtls: Mtls,
    Json(req): Json<mpay_common::api::SandboxIntegrityRequest>,
) -> Result<Response, ApiError> {
    let Some(issuer) = s.integrity_mock.as_ref().filter(|_| s.sandbox) else {
        return Err(ApiError::not_found());
    };
    s.caller(&headers, &mtls, Role::Operator)?;
    let preset = match req.preset.as_deref() {
        None => mpay_integrity::mock::Preset::Strong,
        Some(p) => mpay_integrity::mock::Preset::parse(p)
            .ok_or_else(|| ApiError::bad_request("preset noma'lum"))?,
    };
    if req.request_hash.len() != 43 {
        return Err(ApiError::bad_request(
            "request_hash: base64url SHA-256 (43 belgi)",
        ));
    }
    let now_ms = s.clock.now().unix_timestamp() * 1000;
    Ok(Json(mpay_common::api::SandboxIntegrityResponse {
        integrity_token: issuer.issue(preset, &req.request_hash, now_ms),
    })
    .into_response())
}

/// OTP'ni karta egasining emitentdagi telefoniga yuborishga qo'yadi (2-faza P2.1, ADR-0016).
/// Telefon va kod shu yerda olinadi, SMS esa fonda yuboriladi — sekin yoki osilgan shlyuz provisioning
/// javobini ushlab turmasin (aks holda mijoz `challenge_id` ni olmay qolishi mumkin). Yetkazilmasa
/// qurilma `/idv/resend` qiladi. Qaytaradi: maskalangan telefon (yuborishga qo'yilgan bo'lsa).
async fn queue_otp(s: &Arc<AppState>, fpan: &Pan, challenge_id: &str, ttl: i64) -> Option<String> {
    let phone = match s.issuer.contact_phone(fpan).await {
        Ok(Some(p)) => p,
        Ok(None) => {
            tracing::warn!(pan = %fpan.masked(), "otp: emitentda telefon yo'q — SMS yuborilmadi");
            return None;
        }
        Err(e) => {
            tracing::error!(error = %e, "otp: emitentdan telefon olinmadi");
            return None;
        }
    };
    let otp = match s.vault.sandbox_otp(challenge_id).await {
        Ok(o) => Zeroizing::new(o),
        Err(e) => {
            tracing::error!(error = %e, "otp: kod hosil qilinmadi");
            return None;
        }
    };
    let masked = crate::otp::mask_phone(&phone);
    let (st, reference) = (s.clone(), challenge_id.to_owned());
    tokio::spawn(async move {
        if let Err(e) = st.otp.deliver(&phone, &otp, ttl, &reference).await {
            crate::metrics::otp_failed();
            tracing::error!(to = %crate::otp::mask_phone(&phone), error = %e, "otp: SMS yuborilmadi");
        }
    });
    Some(masked)
}

/// OTP'ni qayta yuborish (sealed; qurilma chegarasi amal qiladi).
async fn idv_resend(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    let st = s.clone();
    sealed(&s, &headers, &body, |info, req: mpay_common::api::OtpResendRequest| async move {
        let token_id = parse_token_id(&id)?;
        if !st.otp.sends() {
            return Err(ApiError::new(
                StatusCode::CONFLICT,
                "OTP_CHANNEL_DISABLED",
                "OTP kanali sozlanmagan (sandbox)",
            ));
        }
        let (fpan, otp, ttl) = st
            .vault
            .otp_resend_material(&token_id, &req.challenge_id, &device_ctx(&info))
            .await?;
        // SMS aniq ketmagan holatlarda hisoblagich qaytariladi (ADR-0016).
        let refund = |e: ApiError| async {
            if let Err(r) = st.vault.otp_resend_refund(&req.challenge_id).await {
                tracing::error!(error = %r, "otp: qayta yuborish hisoblagichi qaytarilmadi");
            }
            e
        };
        let phone = match st.issuer.contact_phone(&fpan).await {
            Ok(Some(p)) => p,
            Ok(None) => {
                return Err(refund(ApiError::new(
                    StatusCode::CONFLICT,
                    "NO_CONTACT",
                    "emitentda telefon raqami yo'q",
                ))
                .await)
            }
            Err(e) => {
                tracing::error!(error = %e, "otp: emitentdan telefon olinmadi");
                return Err(refund(ApiError::new(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "INTERNAL",
                    "ichki xato",
                ))
                .await);
            }
        };
        if let Err(e) = st.otp.deliver(&phone, &otp, ttl, &req.challenge_id).await {
            crate::metrics::otp_failed();
            tracing::error!(to = %crate::otp::mask_phone(&phone), error = %e, "otp: qayta yuborilmadi");
            let err = ApiError::new(
                StatusCode::BAD_GATEWAY,
                "OTP_DELIVERY_FAILED",
                "SMS yuborilmadi, keyinroq urinib ko'ring",
            );
            return Err(if e.not_sent { refund(err).await } else { err });
        }
        Ok(mpay_common::api::OtpResendResponse {
            otp_sent_to: crate::otp::mask_phone(&phone),
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
    mtls: Mtls,
) -> Result<Response, ApiError> {
    s.caller(&headers, &mtls, Role::Operator)?;
    Ok(Json(s.vault.summary(&parse_token_id(&id)?).await?).into_response())
}

async fn suspend(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
    mtls: Mtls,
) -> Result<Response, ApiError> {
    let c = s.caller(&headers, &mtls, Role::Operator)?;
    Ok(Json(s.vault.suspend(&parse_token_id(&id)?, &c.actor()).await?).into_response())
}

async fn resume(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
    mtls: Mtls,
) -> Result<Response, ApiError> {
    let c = s.caller(&headers, &mtls, Role::Operator)?;
    Ok(Json(s.vault.resume(&parse_token_id(&id)?, &c.actor()).await?).into_response())
}

async fn delete_token(
    State(s): St,
    Path(id): Path<String>,
    headers: HeaderMap,
    mtls: Mtls,
) -> Result<Response, ApiError> {
    let c = s.caller(&headers, &mtls, Role::Operator)?;
    Ok(Json(s.vault.delete(&parse_token_id(&id)?, &c.actor()).await?).into_response())
}

async fn audit_verify(State(s): St, headers: HeaderMap, mtls: Mtls) -> Result<Response, ApiError> {
    s.caller(&headers, &mtls, Role::Operator)?;
    Ok(Json(s.vault.verify_audit().await?).into_response())
}

async fn sandbox_otp(
    State(s): St,
    Path(challenge_id): Path<String>,
    headers: HeaderMap,
    mtls: Mtls,
) -> Result<Response, ApiError> {
    if !s.expose_otp {
        return Err(ApiError::not_found());
    }
    s.caller(&headers, &mtls, Role::Operator)?;
    let otp = s.vault.sandbox_otp(&challenge_id).await?;
    Ok(Json(SandboxOtp {
        challenge_id,
        otp: Zeroizing::new(otp),
    })
    .into_response())
}

async fn sandbox_accounts(
    State(s): St,
    headers: HeaderMap,
    mtls: Mtls,
) -> Result<Response, ApiError> {
    if !s.sandbox {
        return Err(ApiError::not_found());
    }
    s.caller(&headers, &mtls, Role::Operator)?;
    let accts = s.issuer.accounts().await.map_err(|e| {
        tracing::error!(error = %e, "issuer hisoblari");
        ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
    })?;
    Ok(Json(accts).into_response())
}

// ---------------------------------------------------------------- terminal

/// Terminal diagnostikasi: kalit, mTLS va rate-limit tekshiruvidan o'tganini tasdiqlaydi.
async fn terminal_ping(State(s): St, headers: HeaderMap, mtls: Mtls) -> Result<Response, ApiError> {
    let c = s.caller(&headers, &mtls, Role::Terminal)?;
    Ok(Json(serde_json::json!({
        "key_id": c.id,
        "mtls": mtls.0.is_some(),
        "server_time": s.clock.now().unix_timestamp(),
    }))
    .into_response())
}

async fn authorize(
    State(s): St,
    headers: HeaderMap,
    mtls: Mtls,
    Json(req): Json<AuthorizationRequest>,
) -> Result<Response, ApiError> {
    let caller = s.caller(&headers, &mtls, Role::Terminal)?;
    let built = crate::acquirer::build_0100(&req, s.clock.now())?;
    // Ishlov alohida vazifada: terminal javobni kutmay ulanishni uzsa (timeout), hyper handler'ni
    // bekor qiladi — emitent ishlagan bo'lishi mumkin, yozuv esa `PENDING` da qotib qolardi.
    // `spawn` qilingan vazifa mijozdan qat'i nazar oxirigacha bajariladi va javobni saqlaydi.
    let st = s.clone();
    let key_id = caller.id.clone();
    let out = tokio::spawn(async move { process_authorization(&st, &key_id, &req, &built).await })
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "acquirer: avtorizatsiya vazifasi");
            ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
        })??;
    crate::metrics::observe_authorization(&out.response_code);
    Ok(Json(out).into_response())
}

/// Takroriy so'rov tekshiruvi → emitent → javobni saqlash (ADR-0010).
async fn process_authorization(
    s: &AppState,
    key_id: &str,
    req: &AuthorizationRequest,
    built: &crate::acquirer::Built,
) -> Result<mpay_common::api::AuthorizationResponse, ApiError> {
    use crate::dedup::{self, Begin};
    let pool = s.vault.pool();
    let db_err = |e: sqlx::Error| {
        tracing::error!(error = %e, "acquirer: takroriy so'rovlar jadvali");
        ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL", "ichki xato")
    };
    let key = dedup::RequestKey::new(req, key_id, built.txn_date.clone());
    let sys_err = |reason: &str| {
        dedup::system_error_response(
            req,
            built.dpan_masked.clone(),
            built.amount_minor,
            built.currency,
            reason,
        )
    };
    match dedup::begin(pool, &key, s.clock.unix())
        .await
        .map_err(db_err)?
    {
        Begin::New => {}
        Begin::Replay(r) => {
            tracing::info!(terminal = %key_id, stan = req.stan, rrn = %r.rrn, "acquirer: takroriy so'rov — avvalgi javob");
            return Ok(r);
        }
        Begin::Duplicate => {
            tracing::warn!(terminal = %key_id, stan = req.stan, "acquirer: STAN boshqa mazmun bilan takrorlandi (94)");
            return Ok(dedup::duplicate_response(
                req,
                built.dpan_masked.clone(),
                built.amount_minor,
                built.currency,
            ));
        }
        Begin::InProgress => {
            let mut e = ApiError::new(
                StatusCode::CONFLICT,
                "REQUEST_IN_PROGRESS",
                "shu so'rov hali ishlanmoqda",
            );
            e.retry_after = Some(1);
            return Err(e);
        }
        Begin::Stale => {
            // Avvalgi ishlov tugamagan: emitent pul yechgan bo'lishi mumkin — qayta yuborilmaydi.
            tracing::error!(terminal = %key_id, stan = req.stan, "acquirer: natija noma'lum (qotib qolgan PENDING) — 96");
            let r = sys_err("OUTCOME_UNKNOWN");
            dedup::finish(pool, &key, &r).await.map_err(db_err)?;
            return Ok(r);
        }
    }
    let bytes = built.msg.pack();
    let (resp, outcome) = match s.issuer.process_bytes(&bytes).await {
        Ok(x) => x,
        Err(e) => {
            // Emitent so'rovni qayta ishlamadi — yozuv o'chiriladi, terminal qayta urinishi mumkin.
            tracing::warn!(error = %e, "issuer 0100 ni qayta ishlay olmadi");
            dedup::abort(pool, &key).await.map_err(db_err)?;
            return Err(ApiError::new(
                StatusCode::BAD_GATEWAY,
                "ISSUER_ERROR",
                "emitent so'rovni qayta ishlay olmadi",
            ));
        }
    };
    // Emitent ishladi (pul yechilgan bo'lishi mumkin): javobni o'qib bo'lmasa ham yozuv o'chirilmaydi —
    // qayta urinish ATC replay (Q1) bo'lardi. `96` saqlanadi va qaytariladi.
    let out = match crate::acquirer::parse_0110(
        &resp,
        built,
        req.stan,
        outcome.reason.as_str(),
        outcome.risk_score,
    ) {
        Ok(o) => o,
        Err(e) => {
            tracing::error!(code = e.code, error = %e.message, stan = req.stan, "acquirer: emitent javobini o'qib bo'lmadi — 96");
            sys_err("ISSUER_RESPONSE_UNREADABLE")
        }
    };
    dedup::finish(pool, &key, &out).await.map_err(db_err)?;
    tracing::info!(
        terminal = %key_id,
        dpan = %out.dpan_masked,
        code = %out.response_code,
        reason = %out.reason,
        stan = out.stan,
        "acquirer: avtorizatsiya"
    );
    Ok(out)
}
