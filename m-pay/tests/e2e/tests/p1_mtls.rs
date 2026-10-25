//! 1-faza, P1.3: ichki API uchun mTLS — sertifikat CN'i API kaliti ID'siga bog'langan.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::{AuthorizationRequest, AuthorizationResponse};
use mpay_e2e::{test_fpan, Sandbox};
use mpay_terminal_sim::card::CardPolicy;
use mpay_terminal_sim::WalletError;

fn code(e: &WalletError) -> (u16, &str) {
    match e {
        WalletError::Api { status, code, .. } => (*status, code.as_str()),
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn operator_and_terminal_need_matching_client_cert() {
    let sb = Sandbox::start_tls(|_| {}).await;
    assert!(sb.cfg.auth.require_mtls);
    let accounts = "/v1/sandbox/accounts";

    // Sertifikatsiz: Bearer kalit to'g'ri bo'lsa ham — 403 MTLS_REQUIRED.
    let e = sb
        .client_as(None)
        .get_json::<serde_json::Value>(accounts, Some(&sb.operator_key))
        .await
        .unwrap_err();
    assert_eq!(code(&e), (403, "MTLS_REQUIRED"));

    // Boshqa mijozning sertifikati (CN = terminal-1) operator kaliti bilan — 403.
    let e = sb
        .client_as(Some("terminal-1"))
        .get_json::<serde_json::Value>(accounts, Some(&sb.operator_key))
        .await
        .unwrap_err();
    assert_eq!(code(&e), (403, "MTLS_REQUIRED"));

    // To'g'ri juftlik — 200.
    let v: serde_json::Value = sb
        .client_as(Some("operator-1"))
        .get_json(accounts, Some(&sb.operator_key))
        .await
        .unwrap();
    assert!(v.as_array().is_some());

    // Sertifikat bor, Bearer kalit yo'q — avval autentifikatsiya: 401.
    let e = sb
        .client_as(Some("operator-1"))
        .get_json::<serde_json::Value>(accounts, None)
        .await
        .unwrap_err();
    assert_eq!(code(&e).0, 401);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn wallet_without_cert_and_terminal_with_cert_pay_over_tls() {
    let fpan = test_fpan(10, 9201);
    let f = fpan.clone();
    let sb = Sandbox::start_tls(move |c| {
        c.issuer.accounts = vec![mpay_issuer::TestAccount {
            pan: f,
            balance_minor: 1_000_000 * 100,
            label: "mtls".into(),
        }]
    })
    .await;
    // Hamyon sertifikatsiz — PQ Link (TLS ichida) ishlaydi.
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let tap = Sandbox::tap(&mut card, 10_000).unwrap();
    let req = AuthorizationRequest {
        terminal_id: "TERM0001".into(),
        merchant_id: "SHOP0000000001".into(),
        stan: 1,
        icc_data: tap.icc_hex(),
    };
    let e = sb
        .client_as(None)
        .post_json::<_, AuthorizationResponse>("/v1/authorizations", Some(&sb.terminal_key), &req)
        .await
        .unwrap_err();
    assert_eq!(code(&e), (403, "MTLS_REQUIRED"));
    let r: AuthorizationResponse = sb
        .client_as(Some("terminal-1"))
        .post_json("/v1/authorizations", Some(&sb.terminal_key), &req)
        .await
        .unwrap();
    assert_eq!(r.response_code, "00", "{r:?}");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn foreign_client_cert_rejected_at_tls() {
    let sb = Sandbox::start_tls(|_| {}).await;
    // Boshqa sandbox CA'si chiqargan sertifikat — TLS handshake'da rad.
    let other = Sandbox::start_tls(|_| {}).await;
    let root = std::fs::read(sb.dir.path().join(mpay_server::init::TLS_CERT_FILE)).unwrap();
    let (c, k) = mpay_server::init::client_cert_files("operator-1");
    let cert = std::fs::read(other.dir.path().join(c)).unwrap();
    let key = std::fs::read(other.dir.path().join(k)).unwrap();
    let client = mpay_terminal_sim::http::ServerClient::with_identity(
        &sb.base_url(),
        Some(&root),
        Some((&cert, &key)),
    )
    .unwrap();
    let e = client
        .get_json::<serde_json::Value>("/v1/sandbox/accounts", Some(&sb.operator_key))
        .await
        .unwrap_err();
    assert!(matches!(e, WalletError::Http(_)), "{e:?}");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn revoked_client_cert_treated_as_missing() {
    let sb = Sandbox::start_tls(|c| {
        let (crt, _) = mpay_server::init::client_cert_files("terminal-1");
        let fp = mpay_server::auth::cert_fingerprint_pem(&c.base_dir.join(crt)).unwrap();
        c.auth.revoked_client_certs = vec![fp];
    })
    .await;
    // Bekor qilingan terminal sertifikati — 403, kalit to'g'ri bo'lsa ham.
    let e = sb
        .client_as(Some("terminal-1"))
        .get_json::<serde_json::Value>("/v1/terminal/ping", Some(&sb.terminal_key))
        .await
        .unwrap_err();
    assert_eq!(code(&e), (403, "MTLS_REQUIRED"));
    // Boshqa sertifikatlar ishlaydi.
    let v: serde_json::Value = sb
        .client_as(Some("operator-1"))
        .get_json("/v1/sandbox/accounts", Some(&sb.operator_key))
        .await
        .unwrap();
    assert!(v.as_array().is_some());
}
