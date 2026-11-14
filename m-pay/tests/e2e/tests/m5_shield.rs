//! M5: haqiqiy Shield dvigateli (qoidalar + graf + ONNX) provisioning va avtorizatsiyaga ulangan.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::{ProvisionResponse, SandboxOtp};
use mpay_common::ports::IdvDecision;
use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_server::config::ShieldEngine;
use mpay_terminal_sim::card::CardPolicy;

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn idv_device_farm_and_second_device() {
    let sb = Sandbox::start_with(|c| c.shield.engine = ShieldEngine::Engine).await;
    let h: serde_json::Value = sb.client().get_json("/healthz", None).await.unwrap();
    assert_eq!(h["status"], "ok");

    // Bitta qurilmada ketma-ket 6 karta: GREEN ×3 → YELLOW → … → RED (qurilma fermasi).
    let mut farm = sb.wallet().await;
    let mut decisions = vec![];
    for i in 0..6 {
        let d = match farm
            .provision(&test_fpan(10, 100 + i), "3112")
            .await
            .unwrap()
        {
            ProvisionResponse::Active { idv, .. }
            | ProvisionResponse::PendingIdv { idv, .. }
            | ProvisionResponse::Declined { idv } => idv,
        };
        decisions.push(d.decision);
        if d.decision == IdvDecision::Red {
            assert!(d.reasons.iter().any(|r| r == "IDV_DEVICE_FARM"), "{d:?}");
        }
    }
    assert_eq!(&decisions[..3], &[IdvDecision::Green; 3], "{decisions:?}");
    assert_eq!(decisions[3], IdvDecision::Yellow, "{decisions:?}");
    assert_eq!(decisions[5], IdvDecision::Red, "{decisions:?}");

    // Mavjud kartani ikkinchi (yangi) qurilmaga qo'shish — step-up OTP.
    let card = test_fpan(10, 900);
    let mut phone1 = sb.wallet().await;
    assert!(matches!(
        phone1.provision(&card, "3112").await.unwrap(),
        ProvisionResponse::Active { .. }
    ));
    let mut phone2 = sb.wallet().await;
    let ProvisionResponse::PendingIdv {
        token_id,
        challenge_id,
        idv,
        ..
    } = phone2.provision(&card, "3112").await.unwrap()
    else {
        panic!("YELLOW kutilgan");
    };
    assert!(
        idv.reasons
            .iter()
            .any(|r| r == "IDV_NEW_DEVICE_EXISTING_CARD"),
        "{idv:?}"
    );
    let otp: SandboxOtp = sb
        .client()
        .get_json(
            &format!("/v1/sandbox/otp/{challenge_id}"),
            Some(&sb.operator_key),
        )
        .await
        .unwrap();
    assert_eq!(
        phone2
            .verify_otp(&token_id, &challenge_id, &otp.otp)
            .await
            .unwrap()
            .luks
            .len(),
        5
    );
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn transaction_scoring_end_to_end() {
    let fpan = test_fpan(10, 777);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.shield.engine = ShieldEngine::Engine;
        c.issuer.accounts = vec![TestAccount {
            pan: f,
            balance_minor: 1_000_000_000,
            label: "m5".into(),
        }];
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;

    let r = sb.pay(&mut card, 85_000 * 100, "SHOP0000000042", 1).await;
    assert_eq!(r.response_code, "00", "{r:?}");
    assert!(r.risk_score.unwrap() < 500, "{r:?}");

    // Bir daqiqada ko'p urinish (karta testlash / bot) → Shield DECLINE → 59.
    let mut codes = vec![];
    for stan in 2..10 {
        codes.push(sb.pay(&mut card, 500 * 100, "WEB0000000003", stan).await);
    }
    let declined = codes
        .iter()
        .find(|r| r.response_code == "59")
        .expect("59 kutilgan");
    assert_eq!(declined.reason, "RISK_DECLINE");
    assert!(declined.risk_score.unwrap() >= 800);
}
