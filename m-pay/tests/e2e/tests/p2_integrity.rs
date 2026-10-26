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
