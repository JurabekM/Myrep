//! M4 qabul mezoni — telefonsiz e2e: provisioning → tap (loopback soft-karta) →
//! `/v1/authorizations` → ISO 8583 `0100` → emitent → `0110`: tasdiq va har bir rad kodi.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::config::LukPolicy;
use mpay_common::tlv::{self, Tlv};
use mpay_common::{CardExpiry, Pan, TokenId};
use mpay_crypto::SecretKey16;
use mpay_e2e::{logs, test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_terminal_sim::card::{CardLuk, CardPolicy, CardProfile, SoftCard};

const UZS: u64 = 100; // 1 so'm = 100 tiyin

fn acct(pan: &str, balance_minor: i64) -> TestAccount {
    TestAccount {
        pan: pan.into(),
        balance_minor,
        label: "e2e".into(),
        phone: None,
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn approved_and_every_decline_code() {
    let rich = test_fpan(10, 7001);
    let poor = test_fpan(20, 7002);
    let offline = mpay_common::Pan::from_prefix("990013100007003")
        .unwrap()
        .expose_digits()
        .to_owned();
    let (rich_c, poor_c, off_c) = (rich.clone(), poor.clone(), offline.clone());
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![
            acct(&rich_c, 5_000_000 * 100),
            acct(&poor_c, 10_000 * 100),
            acct(&off_c, 1_000_000 * 100),
        ];
        c.issuer.offline_bins = vec!["990013".into()];
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &rich, CardPolicy::default())
        .await;
    let before = sb.balance(&rich).await;

    // 00 — tasdiq, qoldiq kamayadi, ARPC karta tomonidan tasdiqlanadi.
    let r = sb.pay(&mut card, 12_500 * UZS, "SHOP0000000001", 1).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("00", "APPROVED"),
        "{r:?}"
    );
    assert!(r.approved);
    assert_eq!(sb.balance(&rich).await, before - (12_500 * UZS) as i64);
    let iad = hex::decode(r.issuer_auth_data.as_ref().unwrap()).unwrap();
    assert!(
        card.verify_issuer_auth(&iad),
        "ARPC karta tomonida tekshirilmadi"
    );
    let mut forged = iad.clone();
    forged[0] ^= 1;
    assert!(!card.verify_issuer_auth(&forged));
    assert!(r.dpan_masked.starts_with("990077******"));

    // 59 — Shield DECLINE.
    let r = sb.pay(&mut card, 1_000 * UZS, "RISKY000000001", 2).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("59", "RISK_DECLINE")
    );
    assert!(
        r.issuer_auth_data.is_some(),
        "rad etilganda ham ARPC (ARQC to'g'ri edi)"
    );

    // REVIEW — siyosat bo'yicha tasdiq.
    let r = sb.pay(&mut card, 1_000 * UZS, "REVIEW00000001", 3).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("00", "APPROVED_AFTER_REVIEW")
    );

    // Q1 — ARQC buzilgan.
    let tap = Sandbox::tap(&mut card, 500 * UZS).unwrap();
    let mut icc = tap.icc.clone();
    for t in icc.iter_mut() {
        if t.tag.0 == 0x9F26 {
            if let tlv::Value::Primitive(v) = &mut t.value {
                v[0] ^= 0xFF;
            }
        }
    }
    let r = sb
        .authorize(hex::encode(tlv::encode_all(&icc)), "SHOP0000000001", 4)
        .await
        .unwrap();
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("Q1", "ARQC_MISMATCH")
    );
    assert!(
        r.issuer_auth_data.is_none(),
        "noto'g'ri ARQC uchun ARPC berilmaydi"
    );

    // Q1 — summa o'zgartirilgan (9F02 CDOL ichida → ARQC mos kelmaydi).
    let tap = Sandbox::tap(&mut card, 500 * UZS).unwrap();
    let icc: Vec<Tlv> = tap
        .icc
        .iter()
        .map(|t| {
            if t.tag.0 == 0x9F02 {
                Tlv::primitive(0x9F02, vec![0, 0, 0, 0, 0, 1])
            } else {
                t.clone()
            }
        })
        .collect();
    let r = sb
        .authorize(hex::encode(tlv::encode_all(&icc)), "SHOP0000000001", 5)
        .await
        .unwrap();
    assert_eq!(r.response_code, "Q1");

    // Q1 — takroriy kriptogramma (ATC replay).
    let tap = Sandbox::tap(&mut card, 700 * UZS).unwrap();
    let ok = sb
        .authorize(tap.icc_hex(), "SHOP0000000001", 6)
        .await
        .unwrap();
    assert_eq!(ok.response_code, "00");
    let r = sb
        .authorize(tap.icc_hex(), "SHOP0000000001", 7)
        .await
        .unwrap();
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("Q1", "ATC_REPLAY")
    );
    assert!(r.issuer_auth_data.is_none());

    // 05 — token to'xtatilgan.
    let token = card.profile().token_id.clone();
    let op = Some(sb.operator_key.as_str());
    let _: serde_json::Value = sb
        .client()
        .post_json(
            &format!("/v1/tokens/{token}/suspend"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap();
    let r = sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 8).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("05", "TOKEN_NOT_ACTIVE")
    );
    let _: serde_json::Value = sb
        .client()
        .post_json(
            &format!("/v1/tokens/{token}/resume"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap();
    assert_eq!(
        sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 9)
            .await
            .response_code,
        "00"
    );

    // 05 — noma'lum token (provisioning qilinmagan DPAN va soxta LUK).
    let mut fake = SoftCard::new(
        CardProfile {
            token_id: TokenId::from_random([9; 16]),
            dpan: Pan::from_prefix("990077123456789").unwrap(),
            expiry: CardExpiry::new(2030, 1).unwrap(),
            psn: 0,
            luks: vec![CardLuk {
                seq: 1,
                key: SecretKey16::from_bytes([0x55; 16]),
                expires_at: i64::MAX,
                uses_left: 10,
            }],
            atc: 0,
        },
        CardPolicy::default(),
    );
    let r = sb.pay(&mut fake, 100 * UZS, "SHOP0000000001", 10).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("05", "UNKNOWN_TOKEN")
    );

    // 51 — mablag' yetarli emas.
    let mut poor_card = sb
        .provision_card(&mut w, &poor, CardPolicy::default())
        .await;
    let r = sb
        .pay(&mut poor_card, 20_000 * UZS, "SHOP0000000001", 11)
        .await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("51", "INSUFFICIENT_FUNDS")
    );
    assert_eq!(
        sb.balance(&poor).await,
        (10_000 * UZS) as i64,
        "rad etilganda qoldiq o'zgarmaydi"
    );
    assert_eq!(
        sb.pay(&mut poor_card, 9_000 * UZS, "SHOP0000000001", 12)
            .await
            .response_code,
        "00"
    );

    // 91 — emitent ishlamayapti.
    let mut off_card = sb
        .provision_card(&mut w, &offline, CardPolicy::default())
        .await;
    let r = sb.pay(&mut off_card, 100 * UZS, "SHOP0000000001", 13).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("91", "ISSUER_OFFLINE")
    );

    // Terminal autentifikatsiyasi va noto'g'ri so'rov.
    let tap = Sandbox::tap(&mut card, 100 * UZS).unwrap();
    let req = mpay_common::api::AuthorizationRequest {
        terminal_id: "TERM0001".into(),
        merchant_id: "SHOP0000000001".into(),
        stan: 14,
        icc_data: tap.icc_hex(),
    };
    let e = sb
        .client()
        .post_json::<_, serde_json::Value>("/v1/authorizations", Some(&sb.operator_key), &req)
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("FORBIDDEN"));
    let e = sb
        .authorize("ZZ".into(), "SHOP0000000001", 15)
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("BAD_REQUEST"));

    // Loglarda PAN, DPAN, LUK va kriptogramma yo'q.
    let log = logs().text();
    assert!(log.contains("issuer: avtorizatsiya"));
    for secret in [
        rich.as_str(),
        poor.as_str(),
        offline.as_str(),
        card.profile().dpan.expose_digits(),
    ] {
        assert!(!log.contains(secret), "logda ochiq PAN");
    }
    for l in &card.profile().luks {
        assert!(!log.to_lowercase().contains(&hex::encode(l.key.expose())));
    }
    let arqc_hex = tap
        .icc
        .iter()
        .find(|t| t.tag.0 == 0x9F26)
        .and_then(Tlv::bytes)
        .map(hex::encode)
        .unwrap();
    assert!(!log.to_lowercase().contains(&arqc_hex));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn luk_limits_enforced_by_server() {
    let fpan = test_fpan(10, 8001);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![acct(&f, 1_000_000 * 100)];
        c.vault.luk = LukPolicy {
            max_uses: 2,
            ttl_secs: 2,
            batch_size: 1,
        };
    })
    .await;
    let mut w = sb.wallet().await;
    // Karta lokal limitlarni tekshirmaydi — server himoyasini sinaymiz.
    let policy = CardPolicy {
        enforce_local_limits: false,
        ..CardPolicy::default()
    };
    let mut card = sb.provision_card(&mut w, &fpan, policy).await;
    assert_eq!(
        sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 1)
            .await
            .response_code,
        "00"
    );
    assert_eq!(
        sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 2)
            .await
            .response_code,
        "00"
    );
    let r = sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 3).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("Q1", "LUK_EXHAUSTED")
    );

    // LUK to'ldirish → yangi LUK bilan ishlaydi; muddati o'tgach — Q1.
    let more = w.replenish(&card.profile().token_id).await.unwrap();
    card.profile_mut().luks.clear();
    card.profile_mut().add_luks(&more.luks).unwrap();
    assert_eq!(
        sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 4)
            .await
            .response_code,
        "00"
    );
    tokio::time::sleep(std::time::Duration::from_millis(2500)).await;
    let r = sb.pay(&mut card, 100 * UZS, "SHOP0000000001", 5).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("Q1", "LUK_EXPIRED")
    );

    // Karta o'zi limitlarni tekshirsa — muddati o'tgan LUK bilan GPO rad (6985).
    let mut strict = SoftCard::new(card.profile().clone(), CardPolicy::default());
    assert!(Sandbox::tap(&mut strict, 100 * UZS).is_err());
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn cdcvm_required_above_limit() {
    let fpan = test_fpan(10, 9001);
    let f = fpan.clone();
    let sb =
        Sandbox::start_with(move |c| c.issuer.accounts = vec![acct(&f, 10_000_000 * 100)]).await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    // 2 000 000 UZS > CDCVM limiti (1 000 000 UZS): biometriyasiz — "telefonga qarang".
    let e = Sandbox::tap(&mut card, 2_000_000 * UZS).unwrap_err();
    assert!(e.is_see_phone(), "{e:?}");
    card.set_cdcvm_verified(true);
    let r = sb
        .pay(&mut card, 2_000_000 * UZS, "SHOP0000000001", 1)
        .await;
    assert_eq!(r.response_code, "00");
    // CDCVM bir martalik.
    assert!(Sandbox::tap(&mut card, 2_000_000 * UZS)
        .unwrap_err()
        .is_see_phone());
}
