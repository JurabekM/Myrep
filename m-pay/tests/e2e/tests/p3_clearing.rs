//! Kunlik kliring va hisob-kitob (ADR-0025): paket → emitent tasdig'i → pozitsiyalar; qayta ishga
//! tushirish xavfsiz; rad etilgan yozuvlar va solishtirish.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::clearing::{ClearingAck, ClearingFile};
use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_server::clearing::BatchReport;
use mpay_server::recon::{ReconKind, ReconReport};
use mpay_terminal_sim::card::CardPolicy;
use mpay_terminal_sim::WalletError;
use serde_json::json;

const UZS: u64 = 100;

async fn run(sb: &Sandbox, date: &str) -> Result<BatchReport, WalletError> {
    sb.client()
        .post_json(
            "/v1/clearing/run",
            Some(&sb.operator_key),
            &json!({ "date": date }),
        )
        .await
}

/// Matnli javob (kliring fayllari) — oddiy HTTP (sandbox TLS'siz).
async fn text(sb: &Sandbox, path: &str) -> String {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    let mut s = tokio::net::TcpStream::connect(sb.addr()).await.unwrap();
    let req = format!(
        "GET {path} HTTP/1.1\r\nHost: t\r\nAuthorization: Bearer {}\r\nConnection: close\r\n\r\n",
        sb.operator_key
    );
    s.write_all(req.as_bytes()).await.unwrap();
    let mut buf = Vec::new();
    s.read_to_end(&mut buf).await.unwrap();
    let raw = String::from_utf8(buf).unwrap();
    let (head, body) = raw.split_once("\r\n\r\n").unwrap();
    assert!(head.starts_with("HTTP/1.1 200"), "{path}: {head}");
    assert!(!head
        .to_ascii_lowercase()
        .contains("transfer-encoding: chunked"));
    body.to_owned()
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn daily_clearing_settles_once_and_reports_rejections() {
    let fpan = test_fpan(10, 9401);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = vec![TestAccount {
            pan: f,
            balance_minor: 1_000_000 * 100,
            label: "p3".into(),
            phone: None,
        }];
        c.clearing.cutoff_grace_secs = 0;
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let pool = sb.server.state.vault.pool();
    let now = sb.server.state.clock.now();

    for (stan, merchant, amount) in [
        (1, "SHOP0000000001", 10_000),
        (2, "SHOP0000000002", 5_000),
        (3, "SHOP0000000001", 2_500),
    ] {
        let r = sb.pay(&mut card, amount * UZS, merchant, stan).await;
        assert_eq!(r.response_code, "00", "{r:?}");
    }
    // Rad etilgan avtorizatsiya (mablag' yetarli emas) kliringga kirmaydi.
    let declined = sb.pay(&mut card, 999_000 * UZS, "SHOP0000000001", 4).await;
    assert_eq!(declined.response_code, "51", "{declined:?}");

    // Kun hali tugamagan — paket yaratilmaydi.
    let today = mpay_server::recon::today(now);
    let err = run(&sb, &today).await.unwrap_err();
    assert!(
        matches!(&err, WalletError::Api { status: 409, code, .. } if code == "CLEARING_NOT_READY"),
        "{err:?}"
    );

    // Tranzaksiyalarni "kecha"ga ko'chiramiz (ikkala tomonda) — kun yopilgan.
    sqlx::query("UPDATE acquirer_requests SET created_at = created_at - 86400")
        .execute(pool)
        .await
        .unwrap();
    sqlx::query("UPDATE issuer_authorizations SET ts = ts - 86400")
        .execute(pool)
        .await
        .unwrap();
    // Emitent STAN 3 ni o'z qaydnomasida tasdiqlangan deb bilmaydi — kliringda rad etadi.
    sqlx::query("UPDATE issuer_authorizations SET response_code = '05' WHERE stan = '000003'")
        .execute(pool)
        .await
        .unwrap();
    let before = sb.balance(&fpan).await;

    let date = mpay_server::clearing::yesterday(now);
    let r = run(&sb, &date).await.unwrap();
    assert_eq!(r.batch_id, format!("MPAY{}", date.replace('-', "")));
    assert_eq!(r.state, "SETTLED");
    assert_eq!((r.records, r.accepted, r.rejected), (3, Some(2), Some(1)));
    assert_eq!(r.totals[0].amount_minor, 1_750_000);
    assert_eq!(r.rejected_items.len(), 1);
    let rej = &r.rejected_items[0];
    assert_eq!(
        (
            rej.stan.as_str(),
            rej.code.as_deref(),
            rej.reason.as_deref()
        ),
        ("000003", Some("12"), Some("NOT_APPROVED"))
    );
    assert!(rej.dpan_masked.contains("******"));
    assert_eq!(
        (r.merchant_fee_bps, r.interchange_bps),
        (Some(150), Some(100))
    );
    let pos = |party: &str, id: &str| {
        r.positions
            .iter()
            .find(|p| p.party == party && p.party_id == id)
            .map(|p| (p.count, p.gross_minor, p.fee_minor, p.net_minor))
            .unwrap()
    };
    assert_eq!(
        pos("MERCHANT", "SHOP0000000001"),
        (1, 1_000_000, 15_000, 985_000)
    );
    assert_eq!(
        pos("MERCHANT", "SHOP0000000002"),
        (1, 500_000, 7_500, 492_500)
    );
    assert_eq!(pos("ISSUER", "issuer"), (2, 1_500_000, 15_000, 1_485_000));
    assert_eq!(pos("ACQUIRER", "mpay"), (2, 22_500, 15_000, 7_500));
    // Kliring balansni o'zgartirmaydi (emulyator avtorizatsiyada yechgan).
    assert_eq!(sb.balance(&fpan).await, before);

    // Qayta ishga tushirish — o'sha natija, pozitsiyalar ikki marta yozilmaydi.
    assert_eq!(run(&sb, &date).await.unwrap(), r);
    let n: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM settlement_positions")
        .fetch_one(pool)
        .await
        .unwrap();
    assert_eq!(n, 4);
    let got: BatchReport = sb
        .client()
        .get_json(&format!("/v1/clearing/{date}"), Some(&sb.operator_key))
        .await
        .unwrap();
    assert_eq!(got, r);

    // Fayllar: kliring fayli va tasdiq o'z formatida o'qiladi, PAN yo'q; to'lovlar CSV.
    let file = text(&sb, &format!("/v1/clearing/{date}/clearing.txt")).await;
    let parsed = ClearingFile::parse(file.as_bytes()).unwrap();
    assert_eq!(parsed.records.len(), 3);
    assert!(!file.contains(&fpan));
    let ack = text(&sb, &format!("/v1/clearing/{date}/ack.txt")).await;
    assert_eq!(ClearingAck::parse(ack.as_bytes()).unwrap().accepted(), 2);
    let csv = text(&sb, &format!("/v1/clearing/{date}/payouts.csv")).await;
    assert_eq!(
        csv,
        format!(
            "batch_id,merchant_id,currency,count,gross_minor,fee_minor,net_minor\n\
             {id},SHOP0000000001,860,1,1000000,15000,985000\n\
             {id},SHOP0000000002,860,1,500000,7500,492500\n",
            id = r.batch_id
        )
    );

    // Solishtirish: STAN 3 — terminal tasdiqlagan, emitentda yo'q (kliring ham rad etgan).
    let recon: ReconReport = sb
        .client()
        .get_json(&format!("/v1/recon?date={date}"), Some(&sb.operator_key))
        .await
        .unwrap();
    assert_eq!(recon.cleared, 2);
    assert_eq!(recon.discrepancies.len(), 1, "{recon:?}");
    assert_eq!(recon.discrepancies[0].kind, ReconKind::AcquirerOnlyApproved);
    assert_eq!(
        recon.discrepancies[0].clearing.as_deref(),
        Some("REJECTED:NOT_APPROVED")
    );
    // Emitent qaydnomasi keyin tuzatilsa ham — kliringda rad etilgan, savdo nuqtasiga to'lanmagan.
    sqlx::query("UPDATE issuer_authorizations SET response_code = '00' WHERE stan = '000003'")
        .execute(pool)
        .await
        .unwrap();
    let recon: ReconReport = sb
        .client()
        .get_json(&format!("/v1/recon?date={date}"), Some(&sb.operator_key))
        .await
        .unwrap();
    assert_eq!(recon.discrepancies[0].kind, ReconKind::ClearingRejected);

    // Ruxsat va kiritish xatolari.
    let err = sb
        .client()
        .post_json::<_, BatchReport>(
            "/v1/clearing/run",
            Some(&sb.terminal_key),
            &json!({ "date": date }),
        )
        .await
        .unwrap_err();
    assert!(
        matches!(err, WalletError::Api { status: 403, .. }),
        "{err:?}"
    );
    for (path, status) in [
        ("/v1/clearing/2026-13-01", 400),
        ("/v1/clearing/2020-01-01", 404),
        (&*format!("/v1/clearing/{date}/other.txt"), 404),
    ] {
        let err = sb
            .client()
            .get_json::<serde_json::Value>(path, Some(&sb.operator_key))
            .await
            .unwrap_err();
        assert!(
            matches!(err, WalletError::Api { status: s, .. } if s == status),
            "{path}: {err:?}"
        );
    }
    let err = run(&sb, "2020-01-01").await.unwrap_err();
    assert!(
        matches!(err, WalletError::Api { status: 400, .. }),
        "{err:?}"
    );
}
