//! 2-faza P2.4 (ADR-0019): Shield roli — ikki API instansiyasi bitta Shield belgilar omboridan
//! foydalanadi; Shield yiqilsa mahalliy zaxira (`SHIELD_DEGRADED`).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::ProvisionResponse;
use mpay_common::ports::{IdvDecision, SecurityLevel};
use mpay_e2e::{test_fpan, Sandbox};
use mpay_server::config::{
    ApiKey, Config, Role, SessionStoreKind, ShieldEngine, ShieldMode, ShieldRemoteConfig,
};
use mpay_server::init::{self, InitOptions};
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::wallet::SoftWallet;
use sha2::{Digest, Sha256};

const SHIELD_KEY: &str = "e2e-shield-mijoz-kaliti-0123456789abcdef";

/// Alohida katalogdagi konfiguratsiya bilan Shield roli (port 0).
async fn start_shield() -> (tempfile::TempDir, mpay_server::shield_role::RunningShield) {
    let dir = tempfile::tempdir().unwrap();
    let out = init::run(&InitOptions {
        dir: dir.path().to_path_buf(),
        listen: "127.0.0.1:0".parse().unwrap(),
        tls: false,
        force: false,
        keystore: mpay_server::config::KeyStoreBackend::Memory,
    })
    .unwrap();
    let mut cfg = Config::load(&out.config_path).unwrap();
    cfg.shield.engine = ShieldEngine::Engine;
    cfg.auth.keys = vec![ApiKey {
        id: "api-1".into(),
        role: Role::Shield,
        sha256: hex::encode(Sha256::digest(SHIELD_KEY.as_bytes())),
    }];
    let s = mpay_server::shield_role::start(&cfg).await.unwrap();
    (dir, s)
}

fn remote(url: String) -> ShieldRemoteConfig {
    ShieldRemoteConfig {
        url,
        key_env: None,
        key: Some(SHIELD_KEY.into()),
        ca_file: None,
        client_cert: None,
        client_key: None,
        timeout_ms: 2000,
    }
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
async fn two_api_instances_share_shield_features() {
    let (_sd, mut shield) = start_shield().await;
    let url = format!("http://{}", shield.addr);
    let u = url.clone();
    let sb = Sandbox::start_with(move |c| {
        c.pqlink.session_store = SessionStoreKind::Database;
        c.shield.engine = ShieldEngine::Engine;
        c.shield.mode = ShieldMode::Remote;
        c.shield.remote = Some(remote(u));
    })
    .await;
    let mut cfg_b = sb.cfg.clone();
    cfg_b.http.listen = "127.0.0.1:0".parse().unwrap();
    let mut b = mpay_server::start(&cfg_b).await.unwrap();
    let ca = sb.client();
    let cb = ServerClient::new(&format!("http://{}", b.addr), None).unwrap();

    // Bitta qurilma, kartalar navbat bilan A va B orqali — qurilma fermasi qoidasi bitta
    // instansiyadagidek ishlaydi (m5_shield: GREEN ×3 → YELLOW → … → RED).
    let dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &ca.enroll_nonce().await.unwrap())
        .unwrap();
    let mut w = SoftWallet::new(ca.clone(), sb.pinned_identity().await, dev);
    w.connect().await.unwrap();
    let mut decisions = vec![];
    for i in 0..6u32 {
        w.set_client(if i % 2 == 0 { ca.clone() } else { cb.clone() });
        let (d, reasons) = decision(&mut w, &test_fpan(10, 5200 + i)).await;
        assert!(
            !reasons.iter().any(|r| r == "SHIELD_DEGRADED"),
            "{reasons:?}"
        );
        decisions.push(d);
    }
    assert_eq!(&decisions[..3], &[IdvDecision::Green; 3], "{decisions:?}");
    assert_eq!(decisions[3], IdvDecision::Yellow, "{decisions:?}");
    assert_eq!(decisions[5], IdvDecision::Red, "{decisions:?}");

    // Shield'da bitta qurilma va 6 karta — ikkala instansiya bitta omborni to'ldirgan.
    let h: serde_json::Value = reqwest_get(&format!("{url}/healthz")).await;
    assert_eq!(h["role"], "shield");
    assert_eq!(h["devices"], 1, "{h}");
    // 6 karta va qurilma–karta grafi (7 tugun) — A va B hodisalari bitta omborda.
    assert_eq!(h["cards"], 6, "{h}");
    assert_eq!(h["graph_nodes"], 7, "{h}");

    // Kalitsiz yoki noto'g'ri kalit bilan ichki API yopiq.
    assert_eq!(
        reqwest_post_status(&format!("{url}/internal/shield/idv"), None).await,
        401
    );

    // Shield to'xtadi — so'rovlar ishlayveradi (mahalliy zaxira), sababda SHIELD_DEGRADED.
    shield.shutdown();
    tokio::time::sleep(std::time::Duration::from_millis(300)).await;
    let mut w2 = sb.wallet().await;
    let (_, reasons) = decision(&mut w2, &test_fpan(10, 5299)).await;
    assert!(
        reasons.iter().any(|r| r == "SHIELD_DEGRADED"),
        "{reasons:?}"
    );
    b.shutdown();
}

async fn reqwest_get(url: &str) -> serde_json::Value {
    let c = ServerClient::new(url.rsplit_once('/').unwrap().0, None).unwrap();
    c.get_json("/healthz", None).await.unwrap()
}

async fn reqwest_post_status(url: &str, key: Option<&str>) -> u16 {
    let (base, path) = url.split_at(url.find("/internal").unwrap());
    let c = ServerClient::new(base, None).unwrap();
    let r: Result<serde_json::Value, _> = c.post_json(path, key, &serde_json::json!({})).await;
    match r {
        Err(mpay_terminal_sim::WalletError::Api { status, .. }) => status,
        other => panic!("{other:?}"),
    }
}
