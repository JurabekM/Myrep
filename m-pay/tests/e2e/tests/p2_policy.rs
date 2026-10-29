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

/// Token muddatiga `months` oy qo'shilgan YYMM (sxema vaqti, UTC+5) — sinov uchun muddatni surish.
fn yymm_shift(months: i32) -> String {
    use mpay_common::clock::Clock as _;
    let c = mpay_common::CardExpiry::current(mpay_common::clock::SystemClock.now());
    let total = i32::from(c.year) * 12 + i32::from(c.month) - 1 + months;
    mpay_common::CardExpiry::new((total / 12) as u16, (total % 12 + 1) as u8)
        .unwrap()
        .to_yymm()
}

/// 3-faza tayyorgarligi (ADR-0022): token muddatini yangilash HTTP orqali — oynadan oldin o'zgarmaydi,
/// muddati yaqinlashgan va hatto o'tgan token karta muddati doirasida uzaytiriladi, to'lov davom etadi.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn token_renewal_over_http() {
    let pan = test_fpan(10, 7401);
    let p2 = pan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![acct(&p2)];
        c.vault.token_renew_before_days = 60;
    })
    .await;
    let mut w = sb.wallet().await;
    let ProvisionResponse::Active { profile, .. } = w.provision(&pan, "3112").await.unwrap() else {
        panic!("ACTIVE kutilgan")
    };
    let t = profile.token_id.clone();
    assert_eq!(profile.dpan_expiry, yymm_shift(36));
    assert!(profile.renew_after.is_some());

    // Hali erta — o'zgarishsiz.
    let r = w.renew(&t).await.unwrap();
    assert!(!r.renewed);
    assert_eq!(r.profile.dpan_expiry, profile.dpan_expiry);

    let set_expiry = |yymm: String| {
        let pool = sb.server.state.vault.pool().clone();
        let t = t.to_string();
        async move {
            sqlx::query("UPDATE vault_tokens SET dpan_expiry = $1 WHERE token_id = $2")
                .bind(yymm)
                .bind(t)
                .execute(&pool)
                .await
                .unwrap();
        }
    };
    let card_from = |p: &mpay_common::api::TokenProfileDto| {
        let mut p = p.clone();
        p.luks = profile.luks.clone();
        SoftCard::new(CardProfile::from_dto(&p).unwrap(), CardPolicy::default())
    };

    // Muddati o'tgan token: to'lov `54`, LUK berilmaydi.
    set_expiry(yymm_shift(-1)).await;
    let mut old = card_from(&profile);
    assert_eq!(
        sb.pay(&mut old, 10_000 * UZS, "SHOP0000000001", 1)
            .await
            .response_code,
        "54"
    );
    assert_eq!(
        api_code(w.replenish(&t).await),
        (410, "TOKEN_EXPIRED".into())
    );

    // Yangilash: karta (31/12) doirasida yana 36 oy; takroriy chaqiruv o'zgartirmaydi.
    let r = w.renew(&t).await.unwrap();
    assert!(r.renewed);
    assert_eq!(r.profile.dpan_expiry, yymm_shift(36));
    assert!(r.profile.luks.is_empty());
    let again = w.renew(&t).await.unwrap();
    assert!(!again.renewed);
    assert_eq!(again.profile.dpan_expiry, r.profile.dpan_expiry);

    // Yangi muddatli profil bilan to'lov va LUK to'ldirish yana ishlaydi.
    let mut card = card_from(&r.profile);
    assert_eq!(
        sb.pay(&mut card, 10_000 * UZS, "SHOP0000000001", 2)
            .await
            .response_code,
        "00"
    );
    assert!(!w.replenish(&t).await.unwrap().luks.is_empty());
    sb.server.state.vault.verify_audit().await.unwrap();
}
