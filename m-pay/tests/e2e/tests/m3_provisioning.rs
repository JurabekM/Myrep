//! M3 qabul mezoni: provisioning → LUK → suspend/delete — haqiqiy HTTP (TCP) va PQ Link orqali;
//! PAN DB'da faqat shifrlangan, loglarda yo'q.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::{ProvisionResponse, SandboxOtp};
use mpay_common::ports::{IdvDecision, SecurityLevel};
use mpay_e2e::{contains, logs, test_fpan, Sandbox};
use mpay_terminal_sim::wallet::SoftWallet;
use serde_json::Value;

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn green_provisioning_lifecycle_over_http() {
    let sb = Sandbox::start().await;
    let mut w = sb.wallet().await;
    let fpan = test_fpan(10, 1001);

    let ProvisionResponse::Active { profile, idv } = w.provision(&fpan, "3112").await.unwrap()
    else {
        panic!("ACTIVE kutilgan");
    };
    assert_eq!(idv.decision, IdvDecision::Green);
    assert_eq!(profile.luks.len(), 5);
    assert_eq!(profile.aid, "F04D50415901");
    assert!(profile.dpan.starts_with("990077"));
    let token = profile.token_id.clone();

    // Operator ko'rinishi maskalangan.
    let op = Some(sb.operator_key.as_str());
    let c = sb.client();
    let sum: Value = c
        .get_json(&format!("/v1/tokens/{token}"), op)
        .await
        .unwrap();
    assert_eq!(sum["state"], "ACTIVE");
    assert_eq!(sum["luks_active"], 5);
    assert!(sum["fpan_masked"].as_str().unwrap().contains("******"));
    assert!(!sum.to_string().contains(&fpan));
    assert!(!sum.to_string().contains(profile.dpan.as_str()));

    // LUK to'ldirish.
    let more = w.replenish(&token).await.unwrap();
    assert_eq!(more.luks.first().unwrap().seq, 6);

    // suspend → to'ldirish rad → resume → delete.
    let s: Value = c
        .post_json(
            &format!("/v1/tokens/{token}/suspend"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap();
    assert_eq!(s["state"], "SUSPENDED");
    assert_eq!(
        w.replenish(&token).await.unwrap_err().code(),
        Some("INVALID_STATE")
    );
    let s: Value = c
        .post_json(
            &format!("/v1/tokens/{token}/resume"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap();
    assert_eq!(s["state"], "ACTIVE");
    let s: Value = c
        .delete_json(&format!("/v1/tokens/{token}"), op)
        .await
        .unwrap();
    assert_eq!(s["state"], "DELETED");
    assert_eq!(s["luks_active"], 0);
    let e = c
        .post_json::<_, Value>(
            &format!("/v1/tokens/{token}/resume"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("INVALID_STATE"));
    assert_eq!(
        w.replenish(&token).await.unwrap_err().code(),
        Some("INVALID_STATE")
    );

    // Audit zanjiri to'g'ri.
    let a: Value = c.get_json("/v1/audit/verify", op).await.unwrap();
    // DEK_CREATED, TOKEN_CREATED, LUKS_ISSUED ×2, SUSPENDED, RESUMED, DELETED
    assert_eq!(a["entries"].as_i64().unwrap(), 7, "{a}");

    // PAN, DPAN va LUK'lar DB fayllarida ochiq ko'rinishda yo'q.
    let raw = sb.db_bytes();
    for secret in [fpan.as_str(), profile.dpan.as_str()] {
        assert!(!contains(&raw, secret.as_bytes()), "DB'da ochiq PAN");
    }
    for l in &profile.luks {
        assert!(!contains(&raw, l.key.as_bytes()));
        assert!(!contains(&raw, &hex_bytes(&l.key)));
    }

    // Loglarda PAN, DPAN, LUK yo'q.
    let log = logs().text();
    assert!(log.contains("vault: token yaratildi"), "loglar ushlanmadi");
    assert!(!log.contains(&fpan));
    assert!(!log.contains(profile.dpan.as_str()));
    for l in &profile.luks {
        assert!(!log.contains(l.key.as_str()));
    }
}

fn hex_bytes(h: &str) -> Vec<u8> {
    (0..h.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap())
        .collect()
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn yellow_and_red_paths() {
    let sb = Sandbox::start().await;
    let mut w = sb.wallet().await;

    let ProvisionResponse::PendingIdv {
        token_id,
        challenge_id,
        idv,
        ..
    } = w.provision(&test_fpan(85, 2002), "3112").await.unwrap()
    else {
        panic!("PENDING_IDV kutilgan");
    };
    assert_eq!(idv.decision, IdvDecision::Yellow);
    // Sandbox OTP — faqat operator kaliti bilan.
    let c = sb.client();
    assert_eq!(
        c.get_json::<SandboxOtp>(&format!("/v1/sandbox/otp/{challenge_id}"), None)
            .await
            .unwrap_err()
            .code(),
        Some("UNAUTHORIZED")
    );
    assert_eq!(
        c.get_json::<SandboxOtp>(
            &format!("/v1/sandbox/otp/{challenge_id}"),
            Some(&sb.terminal_key)
        )
        .await
        .unwrap_err()
        .code(),
        Some("FORBIDDEN")
    );
    let otp: SandboxOtp = c
        .get_json(
            &format!("/v1/sandbox/otp/{challenge_id}"),
            Some(&sb.operator_key),
        )
        .await
        .unwrap();
    let bad = if otp.otp.as_str() == "000000" {
        "000001"
    } else {
        "000000"
    };
    assert_eq!(
        w.verify_otp(&token_id, &challenge_id, bad)
            .await
            .unwrap_err()
            .code(),
        Some("OTP_INVALID")
    );
    let profile = w
        .verify_otp(&token_id, &challenge_id, &otp.otp)
        .await
        .unwrap();
    assert_eq!(profile.luks.len(), 5);

    let d = w.provision(&test_fpan(95, 3003), "3112").await.unwrap();
    assert!(matches!(d, ProvisionResponse::Declined { .. }));

    // Noto'g'ri so'rovlar: DPAN bilan provisioning, real BIN, buzilgan muddat.
    assert_eq!(
        w.provision(&profile.dpan, "3112").await.unwrap_err().code(),
        Some("BAD_REQUEST")
    );
    assert_eq!(
        w.provision("4111111111111111", "3112")
            .await
            .unwrap_err()
            .code(),
        Some("BAD_REQUEST")
    );
    assert_eq!(
        w.provision(&test_fpan(1, 4004), "31")
            .await
            .unwrap_err()
            .code(),
        Some("BAD_REQUEST")
    );
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn pqlink_protections_over_http() {
    let sb = Sandbox::start().await;
    let mut w = sb.wallet().await;

    // HTTP darajasidagi replay: bir xil muhrlangan tana ikki marta.
    let req = mpay_common::api::ProvisionRequest {
        pan: zeroize::Zeroizing::new(test_fpan(1, 5005)),
        expiry: "3112".into(),
    };
    let body = w.seal_request(&req).unwrap();
    let _: ProvisionResponse = w.send_sealed("/v1/tokens", body.clone()).await.unwrap();
    let e = w
        .send_sealed::<ProvisionResponse>("/v1/tokens", body)
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("PQLINK_REPLAY"));
    // Sessiya buzilmagan.
    assert!(w.provision(&test_fpan(1, 5006), "3112").await.is_ok());

    // Begona CA bergan qurilma handshake'dan o'tmaydi.
    let rogue_ca = mpay_pqlink::sandbox::SandboxAttestationCa::generate().unwrap();
    let mut rogue = SoftWallet::new(
        sb.client(),
        sb.pinned_identity().await,
        rogue_ca
            .issue_device(SecurityLevel::StrongBox, b"")
            .unwrap(),
    );
    assert_eq!(
        rogue.connect().await.unwrap_err().code(),
        Some("PQLINK_ATTESTATION")
    );

    // TEE darajasidagi qurilma (siyosat StrongBox) ham rad.
    let mut tee = SoftWallet::new(
        sb.client(),
        sb.pinned_identity().await,
        sb.device(SecurityLevel::TrustedEnvironment),
    );
    assert_eq!(
        tee.connect().await.unwrap_err().code(),
        Some("PQLINK_ATTESTATION")
    );

    // Boshqa qurilma birinchi qurilma tokeni uchun LUK so'ray olmaydi.
    let ProvisionResponse::Active { profile, .. } =
        w.provision(&test_fpan(1, 5007), "3112").await.unwrap()
    else {
        panic!()
    };
    let mut other = sb.wallet().await;
    assert_eq!(
        other.replenish(&profile.token_id).await.unwrap_err().code(),
        Some("DEVICE_MISMATCH")
    );

    // Noto'g'ri Content-Type va sessiyasiz yozuv.
    let c = sb.client();
    let r = c.post_pqlink("/v1/tokens", vec![1, 2, 3]).await.unwrap();
    assert_eq!(r.status.as_u16(), 400);
    let h: Value = c.get_json("/healthz", None).await.unwrap();
    assert_eq!(h["status"], "ok");
    assert_eq!(h["keystore"], "memory");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn operator_api_requires_keys() {
    let sb = Sandbox::start().await;
    let c = sb.client();
    let id = "tok_00000000000000000000000000000000";
    let e = c
        .get_json::<Value>(&format!("/v1/tokens/{id}"), None)
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("UNAUTHORIZED"));
    let e = c
        .get_json::<Value>(&format!("/v1/tokens/{id}"), Some("noto'g'ri"))
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("UNAUTHORIZED"));
    let e = c
        .get_json::<Value>(&format!("/v1/tokens/{id}"), Some(&sb.terminal_key))
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("FORBIDDEN"));
    let e = c
        .get_json::<Value>(&format!("/v1/tokens/{id}"), Some(&sb.operator_key))
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("TOKEN_NOT_FOUND"));
    let e = c
        .get_json::<Value>("/v1/tokens/not-a-token", Some(&sb.operator_key))
        .await
        .unwrap_err();
    assert_eq!(e.code(), Some("BAD_REQUEST"));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn server_restart_keeps_tokens_readable() {
    let mut sb = Sandbox::start().await;
    let mut w = sb.wallet().await;
    let ProvisionResponse::Active { profile, .. } =
        w.provision(&test_fpan(2, 6006), "3112").await.unwrap()
    else {
        panic!()
    };
    // Serverni to'xtatib, o'sha konfiguratsiya (dev-urug') bilan qayta ishga tushiramiz.
    sb.server.shutdown();
    let mut cfg = sb.cfg.clone();
    cfg.http.listen = "127.0.0.1:0".parse().unwrap();
    sb.server = mpay_server::start(&cfg).await.unwrap();
    // PQ Link sessiyalari xotirada edi — qayta ulanish kerak, token esa saqlangan.
    let mut w2 = sb.wallet().await;
    assert_eq!(
        w2.replenish(&profile.token_id).await.unwrap_err().code(),
        Some("DEVICE_MISMATCH")
    );
    let sum: Value = sb
        .client()
        .get_json(
            &format!("/v1/tokens/{}", profile.token_id),
            Some(&sb.operator_key),
        )
        .await
        .unwrap();
    assert_eq!(sum["state"], "ACTIVE");
}
