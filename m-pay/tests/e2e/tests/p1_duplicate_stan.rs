//! 1-faza, P1.2: takroriy STAN — idempotent qayta yuborish va `94` (ADR-0010).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_terminal_sim::card::CardPolicy;

const UZS: u64 = 100;

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn retransmission_is_idempotent_and_reused_stan_is_94() {
    let fpan = test_fpan(10, 9101);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![TestAccount {
            pan: f,
            balance_minor: 1_000_000 * 100,
            label: "p1".into(),
            phone: None,
        }]
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let before = sb.balance(&fpan).await;

    // 1) Terminal javobni yo'qotdi va aynan shu so'rovni qayta yubordi: bir xil javob, bitta yechim.
    let tap = Sandbox::tap(&mut card, 12_500 * UZS).unwrap();
    let r1 = sb
        .authorize(tap.icc_hex(), "SHOP0000000001", 1)
        .await
        .unwrap();
    assert_eq!(r1.response_code, "00", "{r1:?}");
    let r2 = sb
        .authorize(tap.icc_hex(), "SHOP0000000001", 1)
        .await
        .unwrap();
    assert_eq!(
        r1, r2,
        "takroriy yuborish o'sha javobni qaytarishi kerak (Q1 emas)"
    );
    assert_eq!(sb.balance(&fpan).await, before - 12_500 * 100);

    // 2) Shu STAN yangi tap bilan — 94, emitentga yetmaydi (balans o'zgarmaydi).
    let tap2 = Sandbox::tap(&mut card, 3_000 * UZS).unwrap();
    let dup = sb
        .authorize(tap2.icc_hex(), "SHOP0000000001", 1)
        .await
        .unwrap();
    assert_eq!(dup.response_code, "94", "{dup:?}");
    assert_eq!(dup.reason, "DUPLICATE_TRANSMISSION");
    assert!(!dup.approved);
    assert_eq!(sb.balance(&fpan).await, before - 12_500 * 100);

    // 3) O'sha tap yangi STAN bilan — emitent uni hali ko'rmagan, demak tasdiqlanadi.
    let r3 = sb
        .authorize(tap2.icc_hex(), "SHOP0000000001", 2)
        .await
        .unwrap();
    assert_eq!(r3.response_code, "00", "{r3:?}");
    assert_eq!(sb.balance(&fpan).await, before - 15_500 * 100);

    // 4) Mazmun bir xil, lekin boshqa merchant — boshqa so'rov: 94.
    let other = sb
        .authorize(tap2.icc_hex(), "SHOP0000000002", 2)
        .await
        .unwrap();
    assert_eq!(other.response_code, "94");
}
