//! Shield yuqori mavjudligi (ADR-0026): ikki Shield instansiyasi bitta bazada — yetakchi va zaxira.
//! Yetakchi yiqilsa zaxira oxirgi snapshot'ni tiklab davom etadi; API mijozi zaxira URL'ga o'tadi va
//! qurilma tarixi saqlanadi (qurilma fermasi qoidasi uzilishsiz ishlaydi).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::time::Duration;

use mpay_common::api::ProvisionResponse;
use mpay_common::ports::IdvDecision;
use mpay_e2e::{test_fpan, Sandbox};
use mpay_server::config::{
    ApiKey, Config, Role, ShieldEngine, ShieldHaConfig, ShieldMode, ShieldRemoteConfig,
};
use mpay_server::init::{self, InitOptions};
use mpay_server::shield_role::RunningShield;
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::wallet::SoftWallet;
use sha2::{Digest, Sha256};

const SHIELD_KEY: &str = "e2e-shield-ha-mijoz-kaliti-0123456789ab";

/// Ikki Shield instansiyasi uchun umumiy baza: SQLite fayli yoki (`MPAY_TEST_PG_URL`) PostgreSQL.
async fn shared_db(dir: &std::path::Path) -> (Option<std::path::PathBuf>, Option<String>) {
    match std::env::var("MPAY_TEST_PG_URL") {
        Ok(admin) => (
            None,
            Some(mpay_db::fresh_test_database(&admin).await.unwrap()),
        ),
        Err(_) => (Some(dir.join("shield-ha.db")), None),
    }
}

async fn start_shield(
    dir: &tempfile::TempDir,
    instance: &str,
    listen: std::net::SocketAddr,
    db: &(Option<std::path::PathBuf>, Option<String>),
) -> RunningShield {
    let sub = dir.path().join(instance);
    let out = init::run(&InitOptions {
        dir: sub,
        listen,
        tls: false,
        force: true,
        keystore: mpay_server::config::KeyStoreBackend::Memory,
        tls_names: Vec::new(),
    })
    .unwrap();
    let mut cfg = Config::load(&out.config_path).unwrap();
    cfg.shield.engine = ShieldEngine::Engine;
    cfg.auth.keys = vec![ApiKey {
        id: "api-1".into(),
        role: Role::Shield,
        sha256: hex::encode(Sha256::digest(SHIELD_KEY.as_bytes())),
    }];
    cfg.database.path = db.0.clone();
    cfg.database.url = db.1.clone();
    cfg.shield_ha = ShieldHaConfig {
        enabled: true,
        instance_id: Some(instance.into()),
        lease_ttl_ms: 1_500,
        renew_interval_ms: 200,
        snapshot_interval_secs: 1,
        snapshots_keep: 3,
    };
    cfg.validate().unwrap();
    mpay_server::shield_role::start(&cfg).await.unwrap()
}

async fn health(s: &RunningShield) -> serde_json::Value {
    ServerClient::new(&format!("http://{}", s.addr), None)
        .unwrap()
        .get_json("/healthz", None)
        .await
        .unwrap()
}

async fn eventually<F, Fut>(what: &str, mut f: F)
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = bool>,
{
    for _ in 0..100 {
        if f().await {
            return;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    panic!("kutilgan holat bo'lmadi: {what}");
}

async fn decision(w: &mut SoftWallet, pan: &str) -> (IdvDecision, Vec<String>) {
    let idv = match w.provision(pan, "3112").await.unwrap() {
        ProvisionResponse::Active { idv, .. }
        | ProvisionResponse::PendingIdv { idv, .. }
        | ProvisionResponse::Declined { idv } => idv,
    };
    (idv.decision, idv.reasons)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn standby_takes_over_with_snapshot_after_leader_crash_and_handover() {
    let dir = tempfile::tempdir().unwrap();
    let db = shared_db(dir.path()).await;
    let any = "127.0.0.1:0".parse().unwrap();
    let mut a = start_shield(&dir, "a", any, &db).await;
    let mut b = start_shield(&dir, "b", any, &db).await;
    // Qayta ishga tushadigan A uchun manzil oldindan (mijoz ro'yxatida uchinchi URL).
    let a2_addr = std::net::TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap();
    assert_eq!(health(&a).await["leader"], true);
    assert_eq!(health(&b).await["leader"], false);

    // Zaxira ichki API'ga xizmat qilmaydi.
    let standby = ServerClient::new(&format!("http://{}", b.addr), None).unwrap();
    let err = standby
        .post_json::<_, serde_json::Value>(
            "/internal/shield/idv",
            Some(SHIELD_KEY),
            &serde_json::json!({}),
        )
        .await
        .unwrap_err();
    assert!(
        matches!(&err, mpay_terminal_sim::WalletError::Api { status: 503, code, .. } if code == "SHIELD_STANDBY"),
        "{err:?}"
    );

    let (ua, ub, ua2) = (
        format!("http://{}", a.addr),
        format!("http://{}", b.addr),
        format!("http://{a2_addr}"),
    );
    let sb = Sandbox::start_with(move |c| {
        c.shield.engine = ShieldEngine::Engine;
        c.shield.mode = ShieldMode::Remote;
        c.shield.remote = Some(ShieldRemoteConfig {
            url: ua,
            standby_urls: vec![ub, ua2],
            key_env: None,
            key: Some(SHIELD_KEY.into()),
            ca_file: None,
            client_cert: None,
            client_key: None,
            timeout_ms: 1_000,
        });
    })
    .await;

    // Bitta qurilmaga 3 karta (GREEN) — tarix yetakchi A'da.
    let mut w = sb.wallet().await;
    let mut decisions = Vec::new();
    for i in 0..3u32 {
        let (d, reasons) = decision(&mut w, &test_fpan(10, 5600 + i)).await;
        assert!(
            !reasons.iter().any(|r| r == "SHIELD_DEGRADED"),
            "{reasons:?}"
        );
        decisions.push(d);
    }
    assert_eq!(decisions, [IdvDecision::Green; 3]);
    // A davriy snapshot'ni yozguncha kutamiz (3 karta bilan).
    eventually("A snapshot'i 3 karta bilan", || async {
        let h = health(&a).await;
        h["cards"] == 3
            && h["ha"]["snapshot_age_secs"] == 0
            && h["ha"]["snapshot_bytes"].as_u64() > Some(100)
    })
    .await;
    tokio::time::sleep(Duration::from_millis(1_100)).await;

    // A "yiqildi" (yakuniy snapshot va ijara bo'shatishsiz). B ijara tugagach oladi.
    a.shutdown();
    eventually("B yetakchi", || async {
        health(&b).await["leader"] == true
    })
    .await;
    let hb = health(&b).await;
    assert_eq!(hb["cards"], 3, "B snapshot'dan tiklandi: {hb}");
    assert_eq!(hb["devices"], 1, "{hb}");
    assert_eq!(hb["ha"]["epoch"], 2, "{hb}");

    // 4-karta: mijoz B'ga o'tadi, qurilma tarixi bor — qurilma fermasi qoidasi ishlaydi (YELLOW).
    let (d, reasons) = decision(&mut w, &test_fpan(10, 5603)).await;
    assert!(
        !reasons.iter().any(|r| r == "SHIELD_DEGRADED"),
        "{reasons:?}"
    );
    assert_eq!(d, IdvDecision::Yellow, "{reasons:?}");
    assert_eq!(health(&b).await["cards"], 4);

    // A qayta ishga tushdi — zaxira. B to'g'ri to'xtatiladi: yakuniy snapshot, ijara bo'shatiladi,
    // A darhol oladi va hech narsa yo'qolmaydi (4 karta).
    let mut a2 = start_shield(&dir, "a", a2_addr, &db).await;
    assert_eq!(health(&a2).await["leader"], false);
    b.step_down().await;
    b.shutdown();
    eventually("A yetakchi", || async {
        health(&a2).await["leader"] == true
    })
    .await;
    let ha = health(&a2).await;
    assert_eq!(ha["cards"], 4, "{ha}");
    assert_eq!(ha["ha"]["epoch"], 3, "{ha}");
    let (d, reasons) = decision(&mut w, &test_fpan(10, 5604)).await;
    assert!(
        !reasons.iter().any(|r| r == "SHIELD_DEGRADED"),
        "{reasons:?}"
    );
    assert_ne!(d, IdvDecision::Green, "{reasons:?}");
    assert_eq!(health(&a2).await["cards"], 5);
    a2.step_down().await;
    a2.shutdown();
}
