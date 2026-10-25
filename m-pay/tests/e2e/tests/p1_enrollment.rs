//! 1-faza, P1.7: qurilmani ro'yxatdan o'tkazish — attestatsiya challenge'i = server nonce'i (ADR-0013).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::ports::SecurityLevel;
use mpay_e2e::Sandbox;
use mpay_pqlink::sandbox::SoftDeviceKey;
use mpay_server::config::EnrollmentMode;
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

fn code(e: &WalletError) -> &str {
    match e {
        WalletError::Api { code, .. } => code.as_str(),
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

fn same_key(d: &SoftDeviceKey) -> SoftDeviceKey {
    let (k, chain) = d.to_parts().unwrap();
    SoftDeviceKey::from_parts(&k, chain).unwrap()
}

async fn connect(sb: &Sandbox, client: &ServerClient, d: SoftDeviceKey) -> Result<(), WalletError> {
    let mut w = SoftWallet::new(client.clone(), sb.pinned_identity().await, d);
    w.connect().await.map(|_| ())
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn nonce_bound_enrollment_and_registry() {
    let sb = Sandbox::start().await;
    let c = sb.client();

    // Ixtiyoriy challenge (nonce emas) — rad.
    let e = connect(&sb, &c, sb.device(SecurityLevel::StrongBox))
        .await
        .unwrap_err();
    assert_eq!(code(&e), "PQLINK_ENROLLMENT", "{e:?}");

    // Nonce bilan — ro'yxatga olinadi; keyin o'sha kalit nonce'siz qayta ulanadi.
    let nonce = c.enroll_nonce().await.unwrap();
    let dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce)
        .unwrap();
    let again = same_key(&dev);
    connect(&sb, &c, dev).await.unwrap();
    connect(&sb, &c, again).await.unwrap();

    // Nonce bir martalik: ikkinchi qurilma o'sha nonce bilan — rad.
    let reuse = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce)
        .unwrap();
    let e = connect(&sb, &c, reuse).await.unwrap_err();
    assert_eq!(code(&e), "PQLINK_ENROLLMENT");

    // Reyestr DB'da: o'sha DB bilan qayta ishga tushgan server qurilmani taniydi.
    let nonce2 = c.enroll_nonce().await.unwrap();
    let dev2 = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce2)
        .unwrap();
    let dev2_again = same_key(&dev2);
    connect(&sb, &c, dev2).await.unwrap();
    let mut cfg2 = sb.cfg.clone();
    cfg2.http.listen = "127.0.0.1:0".parse().unwrap();
    let mut srv2 = mpay_server::start(&cfg2).await.unwrap();
    let c2 = ServerClient::new(&format!("http://{}", srv2.addr), None).unwrap();
    connect(&sb, &c2, dev2_again).await.unwrap();
    srv2.shutdown();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn expired_nonce_rejected() {
    let sb = Sandbox::start_with(|c| c.pqlink.enrollment_nonce_ttl_secs = 1).await;
    let c = sb.client();
    let nonce = c.enroll_nonce().await.unwrap();
    tokio::time::sleep(std::time::Duration::from_millis(2100)).await;
    let dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce)
        .unwrap();
    let e = connect(&sb, &c, dev).await.unwrap_err();
    assert_eq!(code(&e), "PQLINK_ENROLLMENT");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn enrollment_off_only_in_sandbox() {
    let sb = Sandbox::start_with(|c| c.pqlink.enrollment = EnrollmentMode::Off).await;
    let c = sb.client();
    let e = c.enroll_nonce().await.unwrap_err();
    assert!(matches!(e, WalletError::Api { status: 404, .. }), "{e:?}");
    connect(&sb, &c, sb.device(SecurityLevel::StrongBox))
        .await
        .unwrap();

    // Production konfiguratsiyasida `off` ishga tushmaydi.
    // Boshqa production talablari qondirilgan — faqat `enrollment = off` sababli rad.
    let mut prod = sb.cfg.clone();
    prod.sandbox = false;
    prod.keystore.backend = mpay_server::config::KeyStoreBackend::Pkcs11;
    prod.sandbox_api.expose_otp = false;
    prod.http.tls_cert = Some("tls-cert.pem".into());
    prod.http.tls_key = Some("tls-key.pem".into());
    let err = prod.validate().unwrap_err().to_string();
    assert!(err.contains("pqlink.enrollment"), "{err}");
    prod.pqlink.enrollment = EnrollmentMode::Required;
    prod.validate().unwrap();
}

/// Regressiya: izoh qatorlari bilan boshlanadigan PEM ildiz (`config/android-emulator-test-root.pem`)
/// DER deb o'qilib server ishga tushmay qolardi (emulyator sinovida topilgan).
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn commented_pem_attestation_root_loads() {
    let root = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../config/android-emulator-test-root.pem"
    );
    assert!(std::fs::read_to_string(root).unwrap().starts_with('#'));
    let sb = Sandbox::start_with(|c| {
        std::fs::copy(root, c.base_dir.join("emu-root.pem")).unwrap();
        c.pqlink.attestation_roots.push("emu-root.pem".into());
    })
    .await;
    // Ishga tushdi va oddiy qurilma hamon ulanadi.
    let _w = sb.wallet().await;
}
