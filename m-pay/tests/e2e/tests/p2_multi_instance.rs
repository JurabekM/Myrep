//! 2-faza P2.4: bir nechta `mpay-server` instansiyasi bitta ombor bilan. PQ Link sessiyalari va
//! ro'yxatdan o'tish nonce'lari umumiy (`[pqlink] session_store = "database"`): handshake bir
//! instansiyada boshlanib boshqasida tugaydi, so'rovlar instansiyalar orasida almashadi, takror
//! hech qayerda o'tmaydi. `MPAY_TEST_PG_URL` bo'lsa — PostgreSQL, aks holda bitta SQLite fayl.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::ProvisionResponse;
use mpay_common::ports::SecurityLevel;
use mpay_e2e::{test_fpan, Sandbox};
use mpay_server::config::SessionStoreKind;
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

/// Sandbox (A) va o'sha konfiguratsiya/ombor bilan ikkinchi instansiya (B).
async fn two_instances() -> (Sandbox, mpay_server::RunningServer) {
    let sb = Sandbox::start_with(|c| c.pqlink.session_store = SessionStoreKind::Database).await;
    let mut cfg = sb.cfg.clone();
    cfg.http.listen = "127.0.0.1:0".parse().unwrap();
    let b = mpay_server::start(&cfg).await.unwrap();
    (sb, b)
}

fn client(addr: std::net::SocketAddr) -> ServerClient {
    ServerClient::new(&format!("http://{addr}"), None).unwrap()
}

fn code(e: &WalletError) -> &str {
    match e {
        WalletError::Api { code, .. } => code,
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn session_spans_instances() {
    let (sb, mut b) = two_instances().await;
    let ca = sb.client();
    let cb = client(b.addr);
    // Ikkala instansiya — bir xil server identifikatori (pin).
    assert_eq!(
        ca.identity().await.unwrap().1,
        cb.identity().await.unwrap().1
    );

    // Nonce A'dan, handshake: hello — A, finish — B (nonce B'da iste'mol qilinadi).
    let nonce = ca.enroll_nonce().await.unwrap();
    let dev = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce)
        .unwrap();
    let mut w = SoftWallet::new(ca.clone(), sb.pinned_identity().await, dev);
    w.connect_split(&cb).await.unwrap();

    // Muhrlangan so'rovlar instansiyalar orasida almashadi — seq hisoblagichlari umumiy.
    let card = test_fpan(10, 5101);
    let ProvisionResponse::Active { profile, .. } = w.provision(&card, "3112").await.unwrap()
    else {
        panic!("ACTIVE kutilgan");
    };
    let token = profile.token_id.clone();
    for i in 0..6 {
        w.set_client(if i % 2 == 0 { cb.clone() } else { ca.clone() });
        let r = w.replenish(&token).await;
        // LUK limiti (2 × partiya) to'lgach TOO_MANY_LUKS — muhimi, sessiya ikkala instansiyada ishlaydi.
        if let Err(e) = r {
            assert_eq!(code(&e), "TOO_MANY_LUKS", "{e:?}");
        }
    }

    // O'sha nonce bilan boshqa qurilma — rad (A'da ham, B'da ham ishlatilgan).
    let dev2 = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce)
        .unwrap();
    let mut w2 = SoftWallet::new(ca.clone(), sb.pinned_identity().await, dev2);
    assert_eq!(code(&w2.connect().await.unwrap_err()), "PQLINK_ENROLLMENT");

    // A to'xtadi — sessiya B'da davom etadi (instansiya yiqilishi foydalanuvchini uzmaydi).
    w.set_client(cb.clone());
    sb.server.state.vault.verify_audit().await.unwrap();
    drop(sb);
    w.replenish(&token)
        .await
        .map(|_| ())
        .or_else(|e| {
            if code(&e) == "TOO_MANY_LUKS" {
                Ok(())
            } else {
                Err(e)
            }
        })
        .unwrap();
    b.shutdown();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn replay_rejected_across_instances() {
    let (sb, mut b) = two_instances().await;
    let ca = sb.client();
    let cb = client(b.addr);
    let mut w = sb.wallet().await;
    // Bitta muhrlangan yozuv: A qabul qiladi, aynan o'sha bayt B'ga — takror.
    let body = w
        .seal_request(&mpay_common::api::ProvisionRequest {
            pan: zeroize::Zeroizing::new(test_fpan(10, 5102)),
            expiry: "3112".into(),
            integrity_token: None,
        })
        .unwrap();
    let ra = ca.post_pqlink("/v1/tokens", body.clone()).await.unwrap();
    assert!(ra.status.is_success() && ra.sealed, "{:?}", ra.status);
    let rb = cb.post_pqlink("/v1/tokens", body).await.unwrap();
    assert!(!rb.sealed);
    let e: serde_json::Value = serde_json::from_slice(&rb.body).unwrap();
    assert_eq!(e["error"]["code"], "PQLINK_REPLAY", "{e}");
    b.shutdown();
}
