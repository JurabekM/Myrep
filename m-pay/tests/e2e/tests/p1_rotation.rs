//! 1-faza, P1.6: PQ Link server kalitini almashtirish — e'lon, tasdiq (endorsement), o'tish.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::ServerIdentityDto;
use mpay_common::ports::SecurityLevel;
use mpay_crypto::keystore::{KeyKind, KeyLabel};
use mpay_e2e::{test_fpan, Sandbox};
use mpay_pqlink::{MlDsaSeedBlob, ServerIdentity};
use mpay_server::config::NextIdentityConfig;
use mpay_terminal_sim::wallet::SoftWallet;

const NEXT_LABEL: &str = "mpay.srv-ed25519.v2";
const NEXT_BLOB: &str = "pqlink-mldsa65.v2.blob";

fn id_from(ed: &str, ml: &str) -> ServerIdentity {
    let mut e = [0u8; 32];
    hex::decode_to_slice(ed, &mut e).unwrap();
    ServerIdentity::new(e, hex::decode(ml).unwrap()).unwrap()
}

fn hex64(s: &str) -> [u8; 64] {
    let mut b = [0u8; 64];
    hex::decode_to_slice(s, &mut b).unwrap();
    b
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn announce_endorse_and_switch_identity() {
    // `mpay-server identity-next --version 2` bilan bir xil: kalit KeyStore'da, blob KEK bilan.
    let sb = Sandbox::start_with(|c| {
        let ks = mpay_server::state::open_keystore(c).unwrap();
        ks.ensure_key(&KeyLabel::new(NEXT_LABEL), KeyKind::Ed25519)
            .unwrap();
        let blob = MlDsaSeedBlob::generate(ks.as_ref(), &KeyLabel::new(KeyLabel::KEK)).unwrap();
        std::fs::write(c.base_dir.join(NEXT_BLOB), blob.to_bytes()).unwrap();
        c.pqlink.next = Some(NextIdentityConfig {
            mldsa_blob: NEXT_BLOB.into(),
            ed25519_label: NEXT_LABEL.into(),
        });
    })
    .await;

    // 1) Qurilma joriy (pinlangan) identifikator orqali keyingisini o'rganadi.
    let dto: ServerIdentityDto = sb
        .client()
        .get_json("/v1/pqlink/identity", None)
        .await
        .unwrap();
    let current = sb.pinned_identity().await;
    assert_eq!(hex::encode(current.fingerprint()), dto.fingerprint);
    let n = dto
        .next
        .clone()
        .expect("next e'lon qilingan bo'lishi kerak");
    let next = id_from(&n.ed25519, &n.mldsa65);
    assert_eq!(hex::encode(next.fingerprint()), n.fingerprint);
    assert_ne!(n.fingerprint, dto.fingerprint);
    current
        .verify_endorsement(
            &next.fingerprint(),
            &hex64(&n.endorsement_ed25519),
            &hex::decode(&n.endorsement_mldsa65).unwrap(),
        )
        .unwrap();
    // Soxta "keyingi" identifikator (boshqa barmoq izi) shu tasdiq bilan o'tmaydi.
    let mut forged = next.fingerprint();
    forged[0] ^= 1;
    assert!(current
        .verify_endorsement(
            &forged,
            &hex64(&n.endorsement_ed25519),
            &hex::decode(&n.endorsement_mldsa65).unwrap(),
        )
        .is_err());

    // 2) O'tish: o'sha DB/KeyStore, joriy identifikator — v2 ([pqlink.next] o'chirilgan).
    let mut cfg2 = sb.cfg.clone();
    cfg2.pqlink.mldsa_blob = NEXT_BLOB.into();
    cfg2.pqlink.ed25519_label = NEXT_LABEL.into();
    cfg2.pqlink.next = None;
    cfg2.http.listen = "127.0.0.1:0".parse().unwrap();
    let mut srv2 = mpay_server::start(&cfg2).await.unwrap();
    let url2 = format!("http://{}", srv2.addr);
    let client2 = mpay_terminal_sim::http::ServerClient::new(&url2, None).unwrap();
    let (served, fp2) = client2.identity().await.unwrap();
    assert_eq!(fp2, n.fingerprint);
    assert_eq!(served, next);

    // Yangi pin (o'rganilgan v2) bilan hamyon ulanadi va token oladi.
    let nonce = client2.enroll_nonce().await.unwrap();
    let device = sb
        .ca
        .issue_device(SecurityLevel::StrongBox, &nonce)
        .unwrap();
    let mut w = SoftWallet::new(client2.clone(), next.clone(), device);
    w.connect().await.unwrap();
    w.provision(&test_fpan(10, 9301), "3112").await.unwrap();

    // Faqat eski (v1) pinli hamyon v2 serveriga ulanmaydi.
    let mut old = SoftWallet::new(client2, current, sb.device(SecurityLevel::StrongBox));
    assert!(old.connect().await.is_err());
    srv2.shutdown();
}
