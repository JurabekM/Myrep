//! 1-faza: davriy qayta attestatsiya — qurilma kalitini almashtirish, tokenlar ko'chadi (ADR-0015).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::ProvisionResponse;
use mpay_common::ports::SecurityLevel;
use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_pqlink::sandbox::SoftDeviceKey;
use mpay_terminal_sim::card::{CardPolicy, CardProfile, SoftCard};
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

fn code(e: &WalletError) -> (u16, &str) {
    match e {
        WalletError::Api { status, code, .. } => (*status, code.as_str()),
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

fn same_key(d: &SoftDeviceKey) -> SoftDeviceKey {
    let (k, chain) = d.to_parts().unwrap();
    SoftDeviceKey::from_parts(&k, chain).unwrap()
}

/// Barcha qurilmalar attestatsiyasini "eskirtiradi" (vaqtni oldinga surish o'rniga).
async fn age_all(sb: &Sandbox) {
    sqlx::query("UPDATE pqlink_devices SET enrolled_at = 0")
        .execute(sb.server.state.vault.pool())
        .await
        .unwrap();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn stale_device_rekeys_and_keeps_tokens() {
    let fpan = test_fpan(10, 9401);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.pqlink.reattest_after_days = 1;
        c.issuer.accounts = vec![TestAccount {
            pan: f,
            balance_minor: 1_000_000 * 100,
            label: "reattest".into(),
        }];
    })
    .await;
    let c = sb.client();
    let old_dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &c.enroll_nonce().await.unwrap())
        .unwrap();
    let old_again = same_key(&old_dev);
    let mut w = SoftWallet::new(c.clone(), sb.pinned_identity().await, old_dev);
    w.connect().await.unwrap();
    let ProvisionResponse::Active { profile, .. } = w.provision(&fpan, "3112").await.unwrap()
    else {
        panic!("ACTIVE kutilgan");
    };
    let token = profile.token_id.clone();
    let mut card = SoftCard::new(
        CardProfile::from_dto(&profile).unwrap(),
        CardPolicy::default(),
    );

    // Muddat o'tdi: muhrlangan so'rovlar REATTEST_REQUIRED (sessiya buzilmaydi).
    age_all(&sb).await;
    let e = w.replenish(&token).await.unwrap_err();
    assert_eq!(code(&e), (403, "REATTEST_REQUIRED"));
    let e = w.replenish(&token).await.unwrap_err();
    assert_eq!(
        code(&e),
        (403, "REATTEST_REQUIRED"),
        "sessiya ketma-ketligi saqlanadi"
    );

    // Nonce'siz yangi kalit — rad (attestatsiya yangiligi isbotlanmagan).
    let e = w
        .rekey(sb.device(SecurityLevel::StrongBox))
        .await
        .unwrap_err();
    assert_eq!(code(&e).1, "PQLINK_ENROLLMENT");

    // To'g'ri almashtirish: token yangi qurilmaga ko'chadi.
    let new_dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &c.enroll_nonce().await.unwrap())
        .unwrap();
    let r = w.rekey(new_dev).await.unwrap();
    assert_eq!(r.tokens_moved, 1);
    w.connect().await.unwrap();
    let luks = w.replenish(&token).await.unwrap();
    assert!(!luks.luks.is_empty());

    // Eski kalit endi reyestrda yo'q.
    let mut old = SoftWallet::new(c.clone(), sb.pinned_identity().await, old_again);
    assert_eq!(
        code(&old.connect().await.unwrap_err()).1,
        "PQLINK_ENROLLMENT"
    );

    // Karta (token) ishlayveradi; audit zanjiri butun (DEVICE_REKEY yozuvi bilan).
    let r = sb.pay(&mut card, 10_000, "SHOP0000000001", 1).await;
    assert_eq!(r.response_code, "00", "{r:?}");
    sb.server.state.vault.verify_audit().await.unwrap();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn rekey_signature_bound_to_session_and_old_device() {
    let sb = Sandbox::start_with(|c| c.pqlink.reattest_after_days = 1).await;
    let c = sb.client();
    let mut w = sb.wallet().await;

    // Boshqa xabarni imzolagan kalit (masalan, boshqa sessiyadan ko'chirilgan) — rad.
    use mpay_pqlink::DeviceSigner;
    let new_dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &c.enroll_nonce().await.unwrap())
        .unwrap();
    let req = mpay_common::api::RekeyRequest {
        cert_chain: new_dev.cert_chain().iter().map(hex::encode).collect(),
        signature: hex::encode(new_dev.sign(b"boshqa xabar").unwrap()),
    };
    let e = w
        .call::<_, mpay_common::api::RekeyResponse>("/v1/devices/rekey", &req)
        .await
        .unwrap_err();
    assert_eq!(code(&e).0, 403, "{e:?}");

    // Muddati o'tmagan qurilma ham ixtiyoriy ravishda kalitni almashtira oladi.
    let fresh = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &c.enroll_nonce().await.unwrap())
        .unwrap();
    w.connect().await.unwrap();
    assert_eq!(w.rekey(fresh).await.unwrap().tokens_moved, 0);
}
