//! To'liq oqim PKCS#11 (SoftHSM2) KeyStore bilan: IMK, KEK, PAN-IDX va Ed25519 server kaliti HSM'da.
//! `scripts/softhsm-test.sh e2e` (Docker) yoki CI'da ishga tushiriladi.
#![cfg(feature = "pkcs11")]
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_server::config::KeyStoreBackend;
use mpay_terminal_sim::card::CardPolicy;

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
#[ignore = "SoftHSM2 kerak"]
async fn pkcs11_provisioning_and_tap() {
    let fpan = test_fpan(10, 4242);
    let f = fpan.clone();
    let sb = Sandbox::start_backend(KeyStoreBackend::Pkcs11, move |c| {
        c.issuer.accounts = vec![TestAccount {
            pan: f,
            balance_minor: 100_000_000,
            label: "hsm".into(),
            phone: None,
        }];
    })
    .await;
    let h: serde_json::Value = sb.client().get_json("/healthz", None).await.unwrap();
    assert_eq!(h["keystore"], "pkcs11");
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let r = sb.pay(&mut card, 1_000_000, "SHOP0000000001", 1).await;
    assert_eq!(r.response_code, "00", "{r:?}");
    assert!(card.verify_issuer_auth(&hex::decode(r.issuer_auth_data.unwrap()).unwrap()));
    // Seed fayli yaratilmagan — kalitlar faqat HSM'da.
    assert!(!sb.dir.path().join(mpay_server::init::SEED_FILE).exists());
}
