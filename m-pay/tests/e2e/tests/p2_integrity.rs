//! 2-faza P2.6 (ADR-0021): provisioning'da Play Integrity (sandbox mock) — token haqiqiyligi va
//! PQ Link sessiyasiga bog'lanish serverda, verdict sifati Shield qoidalarida.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::{ProvisionResponse, SandboxIntegrityRequest, SandboxIntegrityResponse};
use mpay_common::ports::{IdvAssessment, IdvDecision};
use mpay_e2e::{logs, now_ms, test_fpan, Sandbox};
use mpay_integrity::mock::{MockIssuer, Preset};
use mpay_server::config::{IntegrityMode, ShieldEngine};
use mpay_server::init;
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

async fn strict() -> Sandbox {
    Sandbox::start_with(|c| {
        c.integrity.required = true;
        c.shield.engine = ShieldEngine::Engine;
    })
    .await
}

fn api_code(r: Result<ProvisionResponse, WalletError>) -> (u16, String) {
    match r {
        Err(WalletError::Api { status, code, .. }) => (status, code),
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

fn idv(r: ProvisionResponse) -> IdvAssessment {
    match r {
        ProvisionResponse::Active { idv, .. }
        | ProvisionResponse::PendingIdv { idv, .. }
        | ProvisionResponse::Declined { idv } => idv,
    }
}

/// Tokensiz hamyon (provider o'rnatilmagan).
async fn bare_wallet(sb: &Sandbox) -> SoftWallet {
    let mut w = sb.wallet().await;
    w.set_integrity(None);
    w
}

fn raw_issuer(sb: &Sandbox) -> MockIssuer {
    let pem = std::fs::read_to_string(sb.dir.path().join(init::INTEGRITY_MOCK_KEY_FILE)).unwrap();
    MockIssuer::from_pkcs8_pem(&pem).unwrap()
}

#[tokio::test]
async fn required_token_and_binding() {
    let sb = strict().await;

    // Tokensiz — rad, token yaratilmaydi.
    let mut w = bare_wallet(&sb).await;
    assert_eq!(
        api_code(w.provision(&test_fpan(10, 6001), "3112").await),
        (403, "INTEGRITY_REQUIRED".into())
    );

    // To'g'ri token — GREEN.
    let mut w = sb.wallet().await;
    let r = w.provision(&test_fpan(10, 6002), "3112").await.unwrap();
    assert!(matches!(r, ProvisionResponse::Active { .. }), "{r:?}");

    // Boshqa sessiyaning tokeni (qayta ulangandan keyin) — rad.
    let iss = mpay_server::integrity::sandbox_issuer(&sb.cfg)
        .unwrap()
        .unwrap();
    let mut w = bare_wallet(&sb).await;
    let old = iss.issue(
        Preset::Strong,
        &w.integrity_request_hash().unwrap(),
        now_ms(),
    );
    w.connect().await.unwrap();
    assert_eq!(
        api_code(
            w.provision_with(&test_fpan(10, 6003), "3112", Some(old))
                .await
        ),
        (403, "INTEGRITY_INVALID".into())
    );

    // Eskirgan (200 s), boshqa paket, boshqa imzo sertifikati, begona kalit, buzilgan token.
    let h = w.integrity_request_hash().unwrap();
    let raw = raw_issuer(&sb);
    let pkg = init::WALLET_PACKAGE;
    let cert = init::SANDBOX_WALLET_CERT;
    let foreign_key = rcgen::KeyPair::generate().unwrap().serialize_pem();
    let foreign = MockIssuer::from_pkcs8_pem(&foreign_key).unwrap();
    let mut tampered = iss.issue(Preset::Strong, &h, now_ms());
    tampered.pop();
    for (what, token) in [
        (
            "eskirgan",
            iss.issue(Preset::Strong, &h, now_ms() - 200_000),
        ),
        (
            "paket",
            raw.issue(&Preset::Strong.payload("evil.repack", cert, &h, now_ms())),
        ),
        (
            "sertifikat",
            raw.issue(&Preset::Strong.payload(pkg, "QAYTA-IMZOLANGAN", &h, now_ms())),
        ),
        (
            "begona kalit",
            foreign.issue_preset(Preset::Strong, pkg, cert, &h, now_ms()),
        ),
        ("buzilgan", tampered),
        ("axlat", "not-a-jws".into()),
    ] {
        assert_eq!(
            api_code(
                w.provision_with(&test_fpan(10, 6004), "3112", Some(token))
                    .await
            ),
            (403, "INTEGRITY_INVALID".into()),
            "{what}"
        );
    }
    // Rad etilgan urinishlar karta yaratmagan: o'sha karta to'g'ri token bilan hali ham GREEN.
    let ok = iss.issue(Preset::Strong, &h, now_ms());
    let r = w
        .provision_with(&test_fpan(10, 6004), "3112", Some(ok))
        .await
        .unwrap();
    assert_eq!(idv(r).decision, IdvDecision::Green);

    // Token va kalit logga tushmaydi.
    let log = logs().text();
    assert!(log.contains("integrity: token rad etildi"));
    assert!(!log.contains(&h), "requestHash logda");
    assert!(!log.contains("eyJhbGciOiJFUzI1NiI"), "JWS sarlavhasi logda");
}

#[tokio::test]
async fn verdict_drives_shield() {
    let sb = strict().await;
    let case = |preset: Preset, acct: u32| {
        let sb = &sb;
        async move {
            let mut w = sb.wallet().await;
            w.set_integrity(sb.integrity_provider(preset));
            idv(w.provision(&test_fpan(10, acct), "3112").await.unwrap())
        }
    };
    let a = case(Preset::Device, 6101).await;
    assert_eq!(a.decision, IdvDecision::Green, "{a:?}");

    let a = case(Preset::Basic, 6102).await;
    assert_eq!(a.decision, IdvDecision::Yellow, "{a:?}");
    assert!(a.reasons.contains(&"IDV_INTEGRITY_BASIC_ONLY".into()));

    let a = case(Preset::PlayProtectRisk, 6103).await;
    assert_eq!(a.decision, IdvDecision::Yellow, "{a:?}");
    assert!(a.reasons.contains(&"IDV_INTEGRITY_ENV_RISK".into()));

    for (preset, acct, rule) in [
        (Preset::NoIntegrity, 6104, "IDV_INTEGRITY_DEVICE_NONE"),
        (Preset::Unrecognized, 6105, "IDV_INTEGRITY_APP_UNRECOGNIZED"),
        (Preset::RemoteControl, 6106, "IDV_INTEGRITY_ENV_HIGH_RISK"),
    ] {
        let a = case(preset, acct).await;
        assert_eq!(a.decision, IdvDecision::Red, "{preset:?}: {a:?}");
        assert!(a.reasons.contains(&rule.into()), "{preset:?}: {a:?}");
    }
}

#[tokio::test]
async fn sandbox_token_endpoint() {
    let sb = strict().await;
    let c = sb.client();
    let mut w = bare_wallet(&sb).await;
    let req = SandboxIntegrityRequest {
        request_hash: w.integrity_request_hash().unwrap(),
        preset: None,
    };
    // Kalitsiz — 401.
    assert!(c
        .post_json::<_, SandboxIntegrityResponse>("/v1/sandbox/integrity-token", None, &req)
        .await
        .is_err());
    // Operator kaliti bilan (emulyatordagi demo ilova shunday oladi).
    let t: SandboxIntegrityResponse = c
        .post_json("/v1/sandbox/integrity-token", Some(&sb.operator_key), &req)
        .await
        .unwrap();
    let r = w
        .provision_with(&test_fpan(10, 6201), "3112", Some(t.integrity_token))
        .await
        .unwrap();
    assert_eq!(idv(r).decision, IdvDecision::Green);
    let bad = SandboxIntegrityRequest {
        request_hash: req.request_hash.clone(),
        preset: Some("ishonchli".into()),
    };
    assert!(c
        .post_json::<_, SandboxIntegrityResponse>(
            "/v1/sandbox/integrity-token",
            Some(&sb.operator_key),
            &bad
        )
        .await
        .is_err());

    // `mode = off` — endpoint yo'q, token talab qilinmaydi.
    let off = Sandbox::start_with(|c| c.integrity.mode = IntegrityMode::Off).await;
    assert!(off
        .client()
        .post_json::<_, SandboxIntegrityResponse>(
            "/v1/sandbox/integrity-token",
            Some(&off.operator_key),
            &req
        )
        .await
        .is_err());
    let mut w = bare_wallet(&off).await;
    w.provision(&test_fpan(10, 6202), "3112").await.unwrap();
}

#[tokio::test]
async fn config_guards() {
    let sb = Sandbox::start().await;
    let mut prod = sb.cfg.clone();
    prod.sandbox = false;
    prod.keystore.backend = mpay_server::config::KeyStoreBackend::Pkcs11;
    prod.sandbox_api.expose_otp = false;
    prod.http.tls_cert = Some("tls-cert.pem".into());
    prod.http.tls_key = Some("tls-key.pem".into());
    let e = prod.validate().unwrap_err().to_string();
    assert!(e.contains("mock"), "{e}");
    let mut c = sb.cfg.clone();
    c.integrity.package_name.clear();
    assert!(c
        .validate()
        .unwrap_err()
        .to_string()
        .contains("package_name"));
    let mut c = sb.cfg.clone();
    c.integrity.mode = IntegrityMode::Google;
    assert!(c
        .validate()
        .unwrap_err()
        .to_string()
        .contains("integrity.google"));
}

/// TLS + mTLS sandbox: demo ilova operator sertifikatisiz — mock tokenni o'z PQ Link sessiyasi orqali
/// oladi (`/v1/sandbox/integrity-token/device`); boshqa sessiya uchun token yasab bo'lmaydi.
#[tokio::test]
async fn device_endpoint_over_tls() {
    let sb = Sandbox::start_tls(|c| c.integrity.required = true).await;
    let mut w = bare_wallet(&sb).await;

    // Operator yo'li: kalit bor, lekin mijoz sertifikati yo'q — 403 (demo ilova muammosi shu edi).
    let req = SandboxIntegrityRequest {
        request_hash: w.integrity_request_hash().unwrap(),
        preset: None,
    };
    let e = sb
        .client()
        .post_json::<_, SandboxIntegrityResponse>(
            "/v1/sandbox/integrity-token",
            Some(&sb.operator_key),
            &req,
        )
        .await
        .unwrap_err();
    assert!(
        matches!(&e, WalletError::Api { code, .. } if code == "MTLS_REQUIRED"),
        "{e:?}"
    );

    // Qurilma yo'li — muhrlangan, kalitsiz.
    let token = w.sandbox_integrity_token(None).await.unwrap();
    let r = w
        .provision_with(&test_fpan(10, 6301), "3112", Some(token))
        .await
        .unwrap();
    assert_eq!(idv(r).decision, IdvDecision::Green);

    // Boshqa sessiya hash'i — rad.
    let mut other = bare_wallet(&sb).await;
    let foreign = SandboxIntegrityRequest {
        request_hash: other.integrity_request_hash().unwrap(),
        preset: None,
    };
    let e = w
        .call::<_, SandboxIntegrityResponse>("/v1/sandbox/integrity-token/device", &foreign)
        .await
        .unwrap_err();
    assert!(matches!(&e, WalletError::Api { status: 400, .. }), "{e:?}");
    // Stsenariy ham o'tadi (Shield stub — verdict qoidalari dvigatelda; bu yerda faqat qabul).
    let t = other.sandbox_integrity_token(Some("basic")).await.unwrap();
    other
        .provision_with(&test_fpan(10, 6302), "3112", Some(t))
        .await
        .unwrap();

    // `mode = off` — 404 (muhrlangan konvert ichida).
    let off = Sandbox::start_tls(|c| c.integrity.mode = IntegrityMode::Off).await;
    let mut w = bare_wallet(&off).await;
    let e = w.sandbox_integrity_token(None).await.unwrap_err();
    assert!(matches!(&e, WalletError::Api { status: 404, .. }), "{e:?}");
}

/// `mode = "google"` + xizmat akkaunti: server JWT bilan OAuth token oladi (emulyator imzoni ochiq
/// kalit bilan tekshiradi), `decodeIntegrityToken` ga shu token bilan murojaat qiladi, verdict
/// bog'lanish tekshiruvidan o'tadi; token keshlanadi (ikki provisioning — bitta almashuv).
#[tokio::test]
async fn google_mode_with_service_account() {
    use axum::extract::Path;
    use axum::http::{HeaderMap, StatusCode};
    use axum::routing::post;
    use axum::Json;
    use base64::engine::general_purpose::URL_SAFE_NO_PAD as B64;
    use base64::Engine as _;
    use rsa::pkcs1::EncodeRsaPublicKey;
    use rsa::pkcs8::EncodePrivateKey;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    let key = rsa::RsaPrivateKey::new(&mut rand_core06::OsRng, 2048).unwrap();
    let pem = key
        .to_pkcs8_pem(rsa::pkcs8::LineEnding::LF)
        .unwrap()
        .to_string();
    let public = key
        .to_public_key()
        .to_pkcs1_der()
        .unwrap()
        .as_bytes()
        .to_vec();
    let token_hits = Arc::new(AtomicU32::new(0));
    let hits = token_hits.clone();
    // Google emulyatori: /token (JWT → access token) va decodeIntegrityToken (token = base64url(verdict)).
    let app = axum::Router::new()
        .route(
            "/token",
            post(move |body: String| {
                let (public, hits) = (public.clone(), hits.clone());
                async move {
                    hits.fetch_add(1, Ordering::SeqCst);
                    let jwt = body
                        .split('&')
                        .find_map(|kv| kv.strip_prefix("assertion="))
                        .unwrap_or("");
                    let p: Vec<&str> = jwt.split('.').collect();
                    let ok = p.len() == 3
                        && ring::signature::UnparsedPublicKey::new(
                            &ring::signature::RSA_PKCS1_2048_8192_SHA256,
                            &public,
                        )
                        .verify(
                            format!("{}.{}", p[0], p[1]).as_bytes(),
                            &B64.decode(p[2]).unwrap_or_default(),
                        )
                        .is_ok();
                    if ok {
                        (StatusCode::OK, Json(serde_json::json!({"access_token": "at-e2e", "expires_in": 3599})))
                    } else {
                        (StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": "invalid_grant"})))
                    }
                }
            }),
        )
        .route(
            "/v1/{call}",
            post(|Path(call): Path<String>, h: HeaderMap, Json(b): Json<serde_json::Value>| async move {
                if h.get("authorization").and_then(|v| v.to_str().ok()) != Some("Bearer at-e2e")
                    || call != format!("{}:decodeIntegrityToken", init::WALLET_PACKAGE)
                {
                    return (StatusCode::UNAUTHORIZED, Json(serde_json::json!({})));
                }
                let payload: serde_json::Value = b["integrityToken"]
                    .as_str()
                    .and_then(|t| B64.decode(t).ok())
                    .and_then(|v| serde_json::from_slice(&v).ok())
                    .unwrap_or_default();
                if payload.is_null() {
                    return (StatusCode::BAD_REQUEST, Json(serde_json::json!({})));
                }
                (StatusCode::OK, Json(serde_json::json!({ "tokenPayloadExternal": payload })))
            }),
        );
    let l = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = l.local_addr().unwrap();
    tokio::spawn(async move { axum::serve(l, app).await.unwrap() });

    let keydir = tempfile::tempdir().unwrap();
    let sa_path = keydir.path().join("sa.json");
    std::fs::write(
        &sa_path,
        serde_json::json!({
            "type": "service_account",
            "client_email": "mpay@sandbox.iam.gserviceaccount.com",
            "private_key": pem,
            "token_uri": format!("http://{addr}/token"),
        })
        .to_string(),
    )
    .unwrap();
    let sb = Sandbox::start_with(move |c| {
        c.integrity.mode = IntegrityMode::Google;
        c.integrity.required = true;
        c.integrity.mock_key = None;
        c.integrity.google = Some(mpay_server::config::GoogleIntegrityConfig {
            base_url: format!("http://{addr}"),
            access_token_env: None,
            access_token_file: None,
            service_account_file: Some(sa_path),
            timeout_ms: 2000,
        });
    })
    .await;
    for acct in [6401, 6402] {
        let mut w = bare_wallet(&sb).await;
        let p = Preset::Strong.payload(
            init::WALLET_PACKAGE,
            init::SANDBOX_WALLET_CERT,
            &w.integrity_request_hash().unwrap(),
            now_ms(),
        );
        let token = B64.encode(serde_json::to_vec(&p).unwrap());
        let r = w
            .provision_with(&test_fpan(10, acct), "3112", Some(token))
            .await
            .unwrap();
        assert_eq!(idv(r).decision, IdvDecision::Green);
    }
    assert_eq!(
        token_hits.load(Ordering::SeqCst),
        1,
        "OAuth token keshlanadi"
    );
    // Emulyator rad etgan token (400) — INTEGRITY_INVALID.
    let mut w = bare_wallet(&sb).await;
    assert_eq!(
        api_code(
            w.provision_with(&test_fpan(10, 6403), "3112", Some("bad!".into()))
                .await
        ),
        (403, "INTEGRITY_INVALID".into())
    );
}
