//! Avtomatik reversal va solishtirish (ADR-0024): natijasi noma'lum avtorizatsiyada mijozning puli
//! qaytadi, acquirer jurnali va emitent qaydnomasidagi tafovutlar hisobotda chiqadi.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::time::Duration;

use mpay_common::api::{AuthorizationRequest, AuthorizationResponse};
use mpay_e2e::{test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_server::recon::{ReconKind, ReconReport};
use mpay_terminal_sim::card::{CardPolicy, SoftCard};
use mpay_terminal_sim::WalletError;

const UZS: u64 = 100;
const MERCHANT: &str = "SHOP0000000001";

fn account(fpan: &str) -> Vec<TestAccount> {
    vec![TestAccount {
        pan: fpan.into(),
        balance_minor: 1_000_000 * 100,
        label: "p3".into(),
        phone: None,
    }]
}

/// Shart bajarilguncha (≤ 15 s) kutadi.
async fn eventually<F, Fut>(what: &str, mut f: F)
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = bool>,
{
    for _ in 0..150 {
        if f().await {
            return;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    panic!("kutilgan holat bo'lmadi: {what}");
}

async fn reversal_row(sb: &Sandbox, stan: i64) -> Option<(String, Option<String>, i64)> {
    sqlx::query_as("SELECT state, result, attempts FROM acquirer_reversals WHERE stan = $1")
        .bind(stan)
        .fetch_optional(sb.server.state.vault.pool())
        .await
        .unwrap()
}

async fn recon(sb: &Sandbox) -> ReconReport {
    sb.client()
        .get_json("/v1/recon", Some(&sb.operator_key))
        .await
        .unwrap()
}

/// Terminal so'rovi (acquirer'ni chetlab, emitentga to'g'ridan-to'g'ri yuborish uchun ham).
fn request(card: &mut SoftCard, amount: u64, stan: u32) -> AuthorizationRequest {
    let tap = Sandbox::tap(card, amount).unwrap();
    AuthorizationRequest {
        terminal_id: "TERM0001".into(),
        merchant_id: MERCHANT.into(),
        stan,
        icc_data: tap.icc_hex(),
    }
}

async fn send(sb: &Sandbox, req: &AuthorizationRequest) -> AuthorizationResponse {
    sb.client()
        .post_json("/v1/authorizations", Some(&sb.terminal_key), req)
        .await
        .unwrap()
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn issuer_timeout_is_reversed_and_retries_until_issuer_answers() {
    let fpan = test_fpan(10, 9301);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = account(&f);
        // Emitent yechimni commit qiladi, javobni esa kechiktiradi — acquirer timeout'i.
        c.issuer.response_delay_ms = 1_000;
        c.acquirer.issuer_timeout_ms = 200;
        c.acquirer.reversal_delay_secs = 0;
        c.acquirer.reversal_interval_ms = 100;
        c.acquirer.reversal_max_backoff_secs = 1;
        c.metrics.listen = Some("127.0.0.1:0".parse().unwrap());
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let before = sb.balance(&fpan).await;
    let pool = sb.server.state.vault.pool();

    // Emitent reversal'larni qayd eta olmaydi (jadval vaqtincha yo'q) — "emitentga yetib bo'lmadi".
    sqlx::query("ALTER TABLE issuer_reversals RENAME TO issuer_reversals_off")
        .execute(pool)
        .await
        .unwrap();

    let req = request(&mut card, 12_500 * UZS, 1);
    let r = send(&sb, &req).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("96", "ISSUER_TIMEOUT"),
        "{r:?}"
    );
    assert!(!r.approved);
    // Emitent baribir yechgan.
    eventually("emitent yechimi", || async {
        sb.balance(&fpan).await == before - 12_500 * 100
    })
    .await;
    // Qayta urinishlar: yozuv PENDING da qoladi, urinishlar ortadi, pul hali qaytmagan.
    eventually("ikki muvaffaqiyatsiz urinish", || async {
        matches!(reversal_row(&sb, 1).await, Some((s, _, n)) if s == "PENDING" && n >= 2)
    })
    .await;
    assert_eq!(sb.balance(&fpan).await, before - 12_500 * 100);
    let report = recon(&sb).await;
    assert!(
        report.is_clean(),
        "yuborilayotgan reversal — tafovut emas: {report:?}"
    );
    assert_eq!(report.notes[0].kind, ReconKind::ReversalPending);

    // Emitent tiklandi — reversal o'tadi, pul qaytadi.
    sqlx::query("ALTER TABLE issuer_reversals_off RENAME TO issuer_reversals")
        .execute(pool)
        .await
        .unwrap();
    eventually("reversal yakunlandi", || async {
        matches!(reversal_row(&sb, 1).await, Some((s, _, _)) if s == "DONE")
    })
    .await;
    let (_, result, attempts) = reversal_row(&sb, 1).await.unwrap();
    assert_eq!(result.as_deref(), Some("REVERSED"));
    assert!(attempts >= 3);
    assert_eq!(sb.balance(&fpan).await, before);
    // Muvaffaqiyatli xabar — takror (0401), chunki birinchi 0400 ga javob bo'lmagan.
    let mti: String = sqlx::query_scalar("SELECT mti FROM issuer_reversals")
        .fetch_one(pool)
        .await
        .unwrap();
    assert_eq!(mti, "0401");

    // Terminal qayta yuborsa — o'sha 96 (emitentga qayta yuborilmaydi, ATC replay yo'q).
    let again = send(&sb, &req).await;
    assert_eq!(again, r);
    assert_eq!(sb.balance(&fpan).await, before);

    // Solishtirish: 96 ↔ qaytarilgan — mos; tafovut yo'q.
    let report = recon(&sb).await;
    assert!(report.is_clean(), "{report:?}");
    assert!(report.notes.is_empty(), "{report:?}");
    assert_eq!(report.matched, 1);

    let m = metrics_text(&sb).await;
    assert!(
        m.contains("mpay_reversals_enqueued_total{cause=\"timeout\"}"),
        "{m}"
    );
    assert!(m.contains("mpay_reversals{state=\"pending\"} 0"), "{m}");
    assert!(m.contains("mpay_reversals{state=\"failed\"} 0"), "{m}");
    assert!(m.contains("mpay_reversals_total{result=\"retry\"}"), "{m}");
    // Loglarda PAN yo'q (ADR: faqat maskalangan).
    assert!(!mpay_e2e::logs().text().contains(&fpan));
}

async fn metrics_text(sb: &Sandbox) -> String {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    let addr = sb.server.metrics_addr.expect("metrics porti");
    let mut s = tokio::net::TcpStream::connect(addr).await.unwrap();
    s.write_all(b"GET /metrics HTTP/1.1\r\nHost: m\r\nConnection: close\r\n\r\n")
        .await
        .unwrap();
    let mut buf = Vec::new();
    s.read_to_end(&mut buf).await.unwrap();
    String::from_utf8(buf).unwrap()
}

/// Jarayon emitent yechganidan keyin, javobni saqlashdan oldin to'xtadi: yozuv `PENDING` da qotgan,
/// terminal qayta yubormagan. Ishchi uni topadi, `96` bilan yopadi va pulni qaytaradi.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn crashed_authorization_is_swept_and_reversed() {
    use mpay_server::dedup::{self, Begin};
    let fpan = test_fpan(10, 9302);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| {
        c.issuer.accounts = account(&f);
        // Ishchi yozuvni emitent ishlashidan oldin yopishi mumkin — reversal kechikkan asl
        // xabardan keyin borsin (ADR-0024: `reversal_delay_secs`).
        c.acquirer.reversal_delay_secs = 2;
        c.acquirer.reversal_interval_ms = 100;
    })
    .await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let before = sb.balance(&fpan).await;
    let st = &sb.server.state;

    // Acquirer'ning birinchi yarmi: yozuv (3 daqiqa oldin) va 0100 → emitent (pul yechiladi).
    let req = request(&mut card, 7_000 * UZS, 5);
    let now = st.clock.now();
    let built = mpay_server::acquirer::build_0100(&req, now).unwrap();
    let key = dedup::RequestKey::new(&req, mpay_server::init::TERMINAL_ID, built.txn_date.clone());
    let begun = dedup::begin(
        st.vault.pool(),
        &key,
        &dedup::Journal::new(&req, &built),
        now.unix_timestamp() - 180,
    )
    .await
    .unwrap();
    assert!(matches!(begun, Begin::New));
    let (_, out) = st.issuer.process_bytes(&built.msg.pack()).await.unwrap();
    assert_eq!(out.code.as_str(), "00");
    assert_eq!(sb.balance(&fpan).await, before - 7_000 * 100);

    // Emitent pulni qaytarishni commit qiladi, acquirer esa navbat yozuvini javobdan keyin yopadi —
    // ikkalasini ham kutamiz (faqat balansni kutish poyga edi: yozuv hali PENDING bo'lishi mumkin).
    eventually("qotgan yozuv yopildi va pul qaytdi", || async {
        sb.balance(&fpan).await == before
            && matches!(reversal_row(&sb, 5).await, Some((s, _, _)) if s == "DONE")
    })
    .await;
    let (state, result, _) = reversal_row(&sb, 5).await.unwrap();
    assert_eq!(
        (state.as_str(), result.as_deref()),
        ("DONE", Some("REVERSED"))
    );
    // Terminal endi qayta yuborsa — 96 OUTCOME_UNKNOWN, emitentga qayta bormaydi.
    let r = send(&sb, &req).await;
    assert_eq!(
        (r.response_code.as_str(), r.reason.as_str()),
        ("96", "OUTCOME_UNKNOWN")
    );
    assert_eq!(sb.balance(&fpan).await, before);
    assert!(recon(&sb).await.is_clean());
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn recon_reports_each_discrepancy() {
    let fpan = test_fpan(10, 9303);
    let f = fpan.clone();
    let sb = Sandbox::start_with(move |c| c.issuer.accounts = account(&f)).await;
    let mut w = sb.wallet().await;
    let mut card = sb
        .provision_card(&mut w, &fpan, CardPolicy::default())
        .await;
    let st = &sb.server.state;
    let pool = st.vault.pool();

    // Mos: oddiy to'lov.
    let ok = send(&sb, &request(&mut card, 1_000 * UZS, 10)).await;
    assert_eq!(ok.response_code, "00");
    let clean = recon(&sb).await;
    assert!(clean.is_clean(), "{clean:?}");
    assert_eq!(clean.matched, 1);
    assert_eq!(clean.approved[0].amount_minor, 1_000 * 100);

    // Emitent yechgan, acquirer yozuvi yo'q (masalan, boshqa yo'l bilan kelgan xabar).
    let lost = request(&mut card, 2_000 * UZS, 11);
    let built = mpay_server::acquirer::build_0100(&lost, st.clock.now()).unwrap();
    let (_, out) = st.issuer.process_bytes(&built.msg.pack()).await.unwrap();
    assert_eq!(out.code.as_str(), "00");
    // Terminal tasdiq oldi, emitent qaydnomasida yechim yo'q.
    let r12 = send(&sb, &request(&mut card, 3_000 * UZS, 12)).await;
    sqlx::query(
        "UPDATE issuer_authorizations SET response_code = '05' WHERE rrn = $1 AND stan = '000012'",
    )
    .bind(&r12.rrn)
    .execute(pool)
    .await
    .unwrap();
    // Summa farqli.
    let r13 = send(&sb, &request(&mut card, 4_000 * UZS, 13)).await;
    sqlx::query(
        "UPDATE issuer_authorizations SET amount_minor = amount_minor + 1 WHERE rrn = $1 AND stan = '000013'",
    )
    .bind(&r13.rrn)
    .execute(pool)
    .await
    .unwrap();

    let rep = recon(&sb).await;
    let kinds: Vec<(&str, ReconKind)> = rep
        .discrepancies
        .iter()
        .map(|i| (i.stan.as_str(), i.kind))
        .collect();
    assert_eq!(
        kinds,
        vec![
            ("000011", ReconKind::IssuerOnlyApproved),
            ("000012", ReconKind::AcquirerOnlyApproved),
            ("000013", ReconKind::AmountMismatch),
        ],
        "{rep:?}"
    );
    assert_eq!(rep.matched, 1);
    let mm = &rep.discrepancies[2];
    assert_eq!(
        (mm.acquirer_amount_minor, mm.issuer_amount_minor),
        (Some(400_000), Some(400_001))
    );
    assert!(mm.dpan_masked.as_deref().unwrap().contains("******"));
    let json = serde_json::to_string(&rep).unwrap();
    assert!(!json.contains(&fpan));

    // Kun bo'yicha ham xuddi shu (bugun — sxema vaqti).
    let today = mpay_server::recon::today(st.clock.now());
    let by_day: ReconReport = sb
        .client()
        .get_json(&format!("/v1/recon?date={today}"), Some(&sb.operator_key))
        .await
        .unwrap();
    assert_eq!(by_day.discrepancies.len(), 3);

    // Faqat operator; davr tekshiriladi.
    let err = sb
        .client()
        .get_json::<ReconReport>("/v1/recon", Some(&sb.terminal_key))
        .await
        .unwrap_err();
    assert!(
        matches!(err, WalletError::Api { status: 403, .. }),
        "{err:?}"
    );
    let err = sb
        .client()
        .get_json::<ReconReport>("/v1/recon", None)
        .await
        .unwrap_err();
    assert!(
        matches!(err, WalletError::Api { status: 401, .. }),
        "{err:?}"
    );
    for bad in [
        "?date=2020-01-01",
        "?date=27.10.2026",
        "?from=10&to=5",
        "?date=2026-10-27&from=1",
    ] {
        let err = sb
            .client()
            .get_json::<ReconReport>(&format!("/v1/recon{bad}"), Some(&sb.operator_key))
            .await
            .unwrap_err();
        assert!(
            matches!(err, WalletError::Api { status: 400, .. }),
            "{bad}: {err:?}"
        );
    }
}
