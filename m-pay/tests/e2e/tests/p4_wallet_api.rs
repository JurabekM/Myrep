//! Hamyon API (ADR-0030): mijoz ilovasi o'z kartalari ro'yxatini oladi, kartani o'zi to'xtatadi,
//! qayta yoqadi va o'chiradi, karta bo'yicha tranzaksiyalar tarixini sahifalab o'qiydi. Bank
//! to'xtatgan kartani ilova yoqa olmaydi; begona qurilma boshqa kartaga tega olmaydi.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::ports::TokenState;
use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_terminal_sim::card::CardPolicy;

const UZS: u64 = 100;
const MERCHANT: &str = "SHOP0000000001";

fn acct(pan: &str, balance_minor: i64) -> TestAccount {
    TestAccount {
        pan: pan.into(),
        balance_minor,
        label: "p4".into(),
        phone: None,
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn wallet_lists_controls_and_shows_history() {
    let a = test_fpan(10, 9401);
    let b = test_fpan(10, 9402);
    let (ac, bc) = (a.clone(), b.clone());
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![acct(&ac, 100_000 * 100), acct(&bc, 100_000 * 100)];
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card_a = sb.provision_card(&mut w, &a, CardPolicy::default()).await;
    let mut card_b = sb.provision_card(&mut w, &b, CardPolicy::default()).await;
    let ta = card_a.profile().token_id.clone();
    let tb = card_b.profile().token_id.clone();

    // Ro'yxat: ikkala karta, faqat maskalangan PAN. Tartib — `created_at` (bir soniyada — token ID),
    // ilovadagi ko'rinish tartibini (asosiy karta) ilova o'zi saqlaydi.
    let list = w.wallet_tokens().await.unwrap().tokens;
    let find = |l: &[mpay_common::api::WalletTokenDto], id| {
        l.iter().find(|t| &t.token_id == id).cloned().unwrap()
    };
    assert_eq!(list.len(), 2);
    assert!(list.iter().all(|t| t.state == TokenState::Active));
    assert_eq!(
        find(&list, &ta).fpan_masked,
        format!("{}******{}", &a[..6], &a[12..])
    );
    let json = serde_json::to_string(&list).unwrap();
    assert!(!json.contains(&a) && !json.contains(&b), "ochiq PAN");

    // Tarix: A — 4 tasdiq + 1 rad (mablag' yetmaydi), B — 1 tasdiq.
    let mut stan = 1;
    for amount in [100, 200, 300, 400] {
        let r = sb.pay(&mut card_a, amount * UZS, MERCHANT, stan).await;
        assert_eq!(r.response_code, "00");
        stan += 1;
    }
    let r = sb.pay(&mut card_a, 1_000_000 * UZS, MERCHANT, stan).await;
    assert_eq!(r.response_code, "51");
    stan += 1;
    assert_eq!(
        sb.pay(&mut card_b, 777 * UZS, MERCHANT, stan)
            .await
            .response_code,
        "00"
    );
    stan += 1;

    let mut seen = Vec::new();
    let mut cursor: Option<String> = None;
    let mut pages = 0;
    loop {
        let p = w
            .wallet_transactions(&ta, cursor.as_deref(), Some(2))
            .await
            .unwrap();
        assert!(p.transactions.len() <= 2);
        seen.extend(p.transactions);
        pages += 1;
        match p.next_cursor {
            Some(c) => cursor = Some(c),
            None => break,
        }
    }
    assert_eq!(pages, 3);
    // Yangilari birinchi; bir soniyadagi yozuvlar ham tushib qolmaydi va takrorlanmaydi.
    assert_eq!(
        seen.iter().map(|t| t.amount_minor).collect::<Vec<_>>(),
        [1_000_000 * 100, 40_000, 30_000, 20_000, 10_000]
    );
    assert_eq!(seen[0].status, "DECLINED");
    assert_eq!(seen[0].response_code, "51");
    assert!(seen[1..]
        .iter()
        .all(|t| t.status == "APPROVED" && !t.cleared));
    assert!(seen
        .iter()
        .all(|t| t.merchant_id == MERCHANT && t.currency == 860));
    let hb = w.wallet_transactions(&tb, None, None).await.unwrap();
    assert_eq!(hb.transactions.len(), 1);
    assert_eq!(hb.transactions[0].amount_minor, 77_700);
    assert!(hb.next_cursor.is_none());
    assert_eq!(
        w.wallet_transactions(&ta, Some("1.1.ath_00' OR 1=1"), None)
            .await
            .unwrap_err()
            .code(),
        Some("BAD_REQUEST")
    );

    // Foydalanuvchi kartani o'zi to'xtatadi → tap rad; o'zi qayta yoqadi → tasdiq.
    let t = w.wallet_set_state(&ta, "suspend").await.unwrap();
    assert_eq!(
        (t.state, t.suspended_by.as_deref()),
        (TokenState::Suspended, Some("DEVICE"))
    );
    let r = sb.pay(&mut card_a, 50 * UZS, MERCHANT, stan).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("05", "TOKEN_NOT_ACTIVE")
    );
    stan += 1;
    let t = w.wallet_set_state(&ta, "resume").await.unwrap();
    assert_eq!((t.state, t.suspended_by), (TokenState::Active, None));
    assert_eq!(
        sb.pay(&mut card_a, 50 * UZS, MERCHANT, stan)
            .await
            .response_code,
        "00"
    );
    stan += 1;

    // Bank to'xtatgan kartani ilova yoqa olmaydi.
    let op = Some(sb.operator_key.as_str());
    let _: serde_json::Value = sb
        .client()
        .post_json(
            &format!("/v1/tokens/{tb}/suspend"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap();
    let list = w.wallet_tokens().await.unwrap().tokens;
    assert_eq!(find(&list, &tb).suspended_by.as_deref(), Some("BANK"));
    assert_eq!(
        w.wallet_set_state(&tb, "resume").await.unwrap_err().code(),
        Some("SUSPENDED_BY_BANK")
    );
    let r = sb.pay(&mut card_b, 10 * UZS, MERCHANT, stan).await;
    assert_eq!(r.response_code, "05");
    stan += 1;
    // Bank qayta yoqadi; foydalanuvchi o'zi to'xtatib, o'zi yoqa oladi.
    let _: serde_json::Value = sb
        .client()
        .post_json(
            &format!("/v1/tokens/{tb}/resume"),
            op,
            &serde_json::json!({}),
        )
        .await
        .unwrap();
    w.wallet_set_state(&tb, "suspend").await.unwrap();
    w.wallet_set_state(&tb, "resume").await.unwrap();

    // Begona qurilma na ro'yxatda ko'radi, na boshqaradi, na tarixni o'qiydi.
    let mut other = sb.wallet().await;
    assert!(other.wallet_tokens().await.unwrap().tokens.is_empty());
    for e in [
        other.wallet_set_state(&ta, "suspend").await.unwrap_err(),
        other
            .wallet_transactions(&ta, None, None)
            .await
            .unwrap_err(),
    ] {
        assert_eq!(e.code(), Some("DEVICE_MISMATCH"));
    }

    // O'chirish: ro'yxatdan chiqadi, tap rad, qayta yoqib bo'lmaydi.
    let t = w.wallet_set_state(&ta, "delete").await.unwrap();
    assert_eq!(t.state, TokenState::Deleted);
    let list = w.wallet_tokens().await.unwrap().tokens;
    assert_eq!(list.iter().map(|t| &t.token_id).collect::<Vec<_>>(), [&tb]);
    assert_ne!(
        sb.pay(&mut card_a, 10 * UZS, MERCHANT, stan)
            .await
            .response_code,
        "00",
        "o'chirilgan token rad etilishi kerak"
    );
    assert!(w.wallet_set_state(&ta, "resume").await.is_err());

    // Audit: qurilma harakatlari `device:` aktori bilan, zanjir butun.
    let actors: Vec<String> = sqlx::query_scalar(
        "SELECT actor FROM vault_audit WHERE action IN ('TOKEN_SUSPENDED', 'TOKEN_RESUMED', 'TOKEN_DELETED') ORDER BY seq",
    )
    .fetch_all(sb.server.state.vault.pool())
    .await
    .unwrap();
    assert_eq!(
        actors.iter().filter(|a| a.starts_with("device:")).count(),
        5
    );
    sb.server.state.vault.verify_audit().await.unwrap();
}
