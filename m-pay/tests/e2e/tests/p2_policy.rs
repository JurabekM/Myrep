//! 2-faza P2.7 (ADR-0022): mahsulot siyosatlari HTTP orqali — CVM chegarasi (tokenga beriladi va
//! emitentda tekshiriladi), REVIEW `step_up`, karta–qurilma chegaralari.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::ProvisionResponse;
use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_terminal_sim::card::{CardPolicy, CardProfile, SoftCard};
use mpay_terminal_sim::WalletError;

const UZS: u64 = 100;

fn acct(pan: &str) -> TestAccount {
    TestAccount {
        pan: pan.into(),
        balance_minor: 100_000_000 * 100,
        label: "p2.7".into(),
        phone: None,
    }
}

fn api_code<T: std::fmt::Debug>(r: Result<T, WalletError>) -> (u16, String) {
    match r {
        Err(WalletError::Api { status, code, .. }) => (status, code),
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn cvm_limit_is_provisioned_and_enforced_by_issuer() {
    let pan = test_fpan(10, 7301);
    let p2 = pan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![acct(&p2)];
        c.issuer.cvm_limit_minor = 200_000 * UZS;
    })
    .await;
    let mut w = sb.wallet().await;
    let ProvisionResponse::Active { profile, .. } = w.provision(&pan, "3112").await.unwrap() else {
        panic!("ACTIVE kutilgan")
    };
    // Bank siyosati tokenga keladi — qurilma o'zi biometriya so'raydi.
    assert_eq!(profile.cvm_limit_minor, Some(200_000 * UZS));
    // LUK to'ldirishda ham joriy chegara keladi (bank o'zgartirsa qurilma yangilaydi).
    let r = w.replenish(&profile.token_id).await.unwrap();
    assert_eq!(r.cvm_limit_minor, Some(200_000 * UZS));

    // "O'zgartirilgan hamyon": karta chegarani e'tiborsiz qoldiradi (CDCVM so'ramaydi).
    let mut card = SoftCard::new(
        CardProfile::from_dto(&profile).unwrap(),
        CardPolicy {
            cdcvm_limit_minor: u64::MAX,
            ..CardPolicy::default()
        },
    );
    let r = sb.pay(&mut card, 150_000 * UZS, "SHOP0000000001", 1).await;
    assert_eq!(r.response_code, "00", "chegaradan past: {r:?}");
    let r = sb.pay(&mut card, 250_000 * UZS, "SHOP0000000001", 2).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("Q2", "CVM_REQUIRED"),
        "emitent CVM'ni o'zi tekshiradi"
    );
    assert!(
        r.issuer_auth_data.is_some(),
        "Q2 ham ARPC bilan (karta tasdiqlaydi)"
    );
    card.set_cdcvm_verified(true);
    let r = sb.pay(&mut card, 250_000 * UZS, "SHOP0000000001", 3).await;
    assert_eq!(r.response_code, "00", "CDCVM bilan: {r:?}");

    // Haqiqiy hamyon (server chegarasi bilan) katta summada o'zi telefonga yo'naltiradi.
    let mut honest = SoftCard::new(
        CardProfile::from_dto(&profile).unwrap(),
        CardPolicy {
            cdcvm_limit_minor: profile.cvm_limit_minor.unwrap(),
            ..CardPolicy::default()
        },
    );
    let e = Sandbox::tap(&mut honest, 250_000 * UZS).unwrap_err();
    assert!(e.is_see_phone(), "{e:?}");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn card_device_limits_over_http() {
    let sb = Sandbox::start_with(|c| c.vault.max_devices_per_card = 2).await;
    let pan = test_fpan(10, 7401);
    let mut a = sb.wallet().await;
    a.provision(&pan, "3112").await.unwrap();
    assert_eq!(
        api_code(a.provision(&pan, "3112").await),
        (409, "CARD_ALREADY_ON_DEVICE".into())
    );
    let mut b = sb.wallet().await;
    b.provision(&pan, "3112").await.unwrap();
    let mut c = sb.wallet().await;
    assert_eq!(
        api_code(c.provision(&pan, "3112").await),
        (409, "TOO_MANY_DEVICES".into())
    );
    // Boshqa karta o'sha qurilmada — mumkin.
    c.provision(&test_fpan(10, 7402), "3112").await.unwrap();
}
