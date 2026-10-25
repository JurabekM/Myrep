//! 1-faza: bekor qilingan server identifikatorlari — oflayn ildiz imzosi (ADR-0014).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::RevocationsDto;
use mpay_e2e::Sandbox;
use mpay_pqlink::revocation::RootKey;

fn write_doc(dir: &std::path::Path, root: &RootKey, version: u64, fps: &[[u8; 32]]) {
    let signed = root.sign_revocations(version, fps).unwrap();
    let dto = mpay_server::revocations::to_dto(&signed);
    std::fs::write(
        dir.join("revocations.json"),
        serde_json::to_vec(&dto).unwrap(),
    )
    .unwrap();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn served_list_verifies_against_pinned_root() {
    let root = RootKey::generate().unwrap();
    let root_fp = root.identity().unwrap().fingerprint();
    let leaked = [0xAB; 32];
    let sb = Sandbox::start_with(|c| {
        write_doc(&c.base_dir, &root, 7, &[leaked]);
        c.pqlink.revocations = Some("revocations.json".into());
        c.pqlink.root_fingerprint = Some(hex::encode(root_fp));
    })
    .await;
    let dto: RevocationsDto = sb
        .client()
        .get_json("/v1/pqlink/revocations", None)
        .await
        .unwrap();
    let signed = mpay_server::revocations::from_dto(&dto).unwrap();
    signed.verify(&root_fp).unwrap();
    assert_eq!(signed.version, 7);
    assert!(signed.is_revoked(&leaked));
    // Boshqa ildiz pinlangan qurilma uchun — ishonchsiz.
    assert!(signed.verify(&[0; 32]).is_err());
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn server_refuses_revoked_own_identity_or_bad_signature() {
    let sb = Sandbox::start().await;
    let own = sb.pinned_identity().await.fingerprint();
    let root = RootKey::generate().unwrap();
    let dir = sb.cfg.base_dir.clone();

    // O'zining joriy identifikatori ro'yxatda — ishga tushmaydi.
    write_doc(&dir, &root, 1, &[own]);
    let mut cfg = sb.cfg.clone();
    cfg.http.listen = "127.0.0.1:0".parse().unwrap();
    cfg.pqlink.revocations = Some("revocations.json".into());
    let err = mpay_server::start(&cfg).await.unwrap_err();
    assert!(err.contains("bekor qilingan"), "{err}");

    // Imzo boshqa ildizdan — `root_fingerprint` bilan tekshirilganda ishga tushmaydi.
    write_doc(&dir, &RootKey::generate().unwrap(), 2, &[[1; 32]]);
    cfg.pqlink.root_fingerprint = Some(hex::encode(root.identity().unwrap().fingerprint()));
    let err = mpay_server::start(&cfg).await.unwrap_err();
    assert!(err.contains("imzosi"), "{err}");

    // To'g'ri ildiz, boshqa barmoq izi — ishlaydi.
    write_doc(&dir, &root, 3, &[[1; 32]]);
    let mut srv = mpay_server::start(&cfg).await.unwrap();
    srv.shutdown();
}
