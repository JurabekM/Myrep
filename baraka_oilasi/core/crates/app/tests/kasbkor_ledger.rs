#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K4 — Kasb-kor kunlik kassa yopish va nasiya daftari (docs/kasbkor/SPEC.md 5).

use std::sync::Arc;

use baraka_app::*;
use chrono::{DateTime, Utc};

fn clock(at: &str) -> Arc<FixedClock> {
    Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339(at)
            .unwrap()
            .with_timezone(&Utc),
    ))
}

fn at(c: &FixedClock, t: &str) {
    c.set(DateTime::parse_from_rfc3339(t).unwrap().with_timezone(&Utc));
}

fn app_with(c: Arc<FixedClock>) -> (App, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([9; 32]),
        "dev-bahodir",
        c,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Bahodirlar".into(),
            device_name: "Do'kon kompyuteri".into(),
            platform: "windows".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "KASBKOR".into()],
            members: vec![NewMemberInput {
                display_name: "Bahodir".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let kk = h
        .spaces
        .iter()
        .find(|s| s.kind == "KASBKOR")
        .unwrap()
        .id
        .clone();
    (app, kk)
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn sale(amount: &str, channel: &str) -> KkSaleInput {
    KkSaleInput {
        amount: amount.into(),
        channel: channel.into(),
        occurred_on: None,
        note: None,
    }
}

fn mv(kind: &str, wallet: &str, amount: &str, to: Option<&str>, on: Option<&str>) -> KkMoveInput {
    KkMoveInput {
        kind: kind.into(),
        wallet: wallet.into(),
        to_wallet: to.map(str::to_string),
        amount: amount.into(),
        occurred_on: on.map(str::to_string),
        note: None,
    }
}

fn cash_expense(app: &App, kk: &str, amount: &str) -> String {
    let cat = app
        .categories(kk)
        .unwrap()
        .into_iter()
        .find(|c| c.name_key == "category.kk.other")
        .unwrap();
    app.record_expense(
        kk,
        NewExpenseInput {
            amount: amount.into(),
            category_id: cat.id,
            channel: "CASH".into(),
            member_id: None,
            occurred_on: None,
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: Some("non".into()),
        },
    )
    .unwrap()
    .id
}

fn close(day: &str, counted: &str, reason: Option<&str>) -> KkCashCloseInput {
    KkCashCloseInput {
        day: day.into(),
        counted: counted.into(),
        reason: reason.map(str::to_string),
        note: None,
    }
}

/// SPEC 5.1 Bahodir aka: kutilgan 1 500 000, sanalgan 1 450 000 → −50 000; yopilgan kun o'zgarmas.
#[test]
fn cash_close_bahodir_and_closed_day_guard() {
    let c = clock("2026-11-20T18:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    app.kk_record_move(
        &kk,
        mv("OPENING", "CASH", "500 000", None, Some("2026-11-19")),
    )
    .unwrap();
    app.kk_record_sale(&kk, sale("3 200 000", "CASH")).unwrap();
    app.kk_record_sale(&kk, sale("900 000", "CARD")).unwrap();
    let bread = cash_expense(&app, &kk, "400 000");
    app.kk_record_move(&kk, mv("OWNER_DRAW", "CASH", "300 000", None, None))
        .unwrap();
    app.kk_record_move(&kk, mv("TRANSFER", "CASH", "1 500 000", Some("CARD"), None))
        .unwrap();

    let d = app.kk_cash_draft(&kk, None, None).unwrap();
    assert_eq!(d.day, "2026-11-20");
    assert_eq!(
        (minor(&d.opening), minor(&d.expected)),
        (50_000_000, 150_000_000)
    );
    assert_eq!(
        (minor(&d.cash_sales), minor(&d.handed_over)),
        (320_000_000, 150_000_000)
    );
    assert_eq!(d.difference, None);
    let d = app
        .kk_cash_draft(&kk, None, Some("1 450 000".into()))
        .unwrap();
    assert_eq!(minor(d.difference.as_ref().unwrap()), -5_000_000);
    assert_eq!(d.status.as_deref(), Some("SHORT"));

    let err = app
        .kk_close_cash_day(&kk, close("2026-11-20", "1 450 000", None))
        .unwrap_err();
    assert_eq!(
        (err.code.as_str(), err.field.as_deref()),
        ("REASON_REQUIRED", Some("reason"))
    );
    assert_eq!(
        app.kk_close_cash_day(&kk, close("2026-11-21", "0", None))
            .unwrap_err()
            .code,
        "FUTURE_DAY"
    );
    let day = app
        .kk_close_cash_day(&kk, close("2026-11-20", "1 450 000", Some("UNKNOWN")))
        .unwrap();
    assert_eq!(
        (day.status.as_str(), minor(&day.difference)),
        ("SHORT", -5_000_000)
    );

    // Farq naqd kassani tuzatadi, pul oqimiga kirmaydi.
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.cash), 145_000_000);
    assert_eq!(minor(&o.cash_flow), 410_000_000 - 40_000_000);
    assert_eq!(o.cash_closed_until.as_deref(), Some("2026-11-20"));
    assert!(o.entries.iter().any(|e| e.kind == "CASH_SHORT"));

    // Yopilgan kunga naqd yozuv yo'q (karta — bor); qayta yopish ham yo'q.
    assert_eq!(
        app.kk_record_sale(&kk, sale("10 000", "CASH"))
            .unwrap_err()
            .code,
        "CASH_DAY_CLOSED"
    );
    app.kk_record_sale(&kk, sale("10 000", "CARD")).unwrap();
    assert_eq!(
        app.delete_expense(&kk, &bread).unwrap_err().code,
        "CASH_DAY_CLOSED"
    );
    assert_eq!(
        app.kk_close_cash_day(&kk, close("2026-11-20", "1 450 000", None))
            .unwrap_err()
            .code,
        "CASH_DAY_CLOSED"
    );

    // Ertasi kun: ochilish = sanalgan.
    at(&c, "2026-11-21T18:00:00+05:00");
    let d = app.kk_cash_draft(&kk, None, None).unwrap();
    assert_eq!(minor(&d.opening), 145_000_000);
    assert_eq!(d.last_closed.as_deref(), Some("2026-11-20"));
    assert_eq!(app.kk_cash_days(&kk).unwrap().len(), 1);
}

/// 4 hafta ichida uchinchi kamomad — «xato qidirish» taklifi.
#[test]
fn repeated_shortage_suggests_search() {
    let c = clock("2026-11-10T18:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    app.kk_record_move(
        &kk,
        mv("OPENING", "CASH", "100 000", None, Some("2026-11-09")),
    )
    .unwrap();
    for (i, day) in ["2026-11-10", "2026-11-11", "2026-11-12"]
        .iter()
        .enumerate()
    {
        at(&c, &format!("{day}T18:00:00+05:00"));
        let d = app.kk_cash_draft(&kk, None, None).unwrap();
        let counted = minor(&d.expected) / 100 - 1_000;
        let r = app
            .kk_close_cash_day(&kk, close(day, &counted.to_string(), Some("UNKNOWN")))
            .unwrap();
        assert_eq!(r.suggest_search, i == 2, "{day}");
    }
}

/// SPEC 5.2 Malika: narx qotirilgan, kechikkanda summa o'zgarmaydi; to'lov — tushum.
#[test]
fn credit_sale_malika() {
    let c = clock("2026-11-10T12:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    let err = app
        .kk_add_customer(
            &kk,
            KkCustomerInput {
                name: "Malika".into(),
                phone: Some("+998 90 123 45 67".into()),
                phone_consent: false,
                note: None,
            },
        )
        .unwrap_err();
    assert_eq!(err.code, "PHONE_CONSENT_REQUIRED");
    let customers = app
        .kk_add_customer(
            &kk,
            KkCustomerInput {
                name: "Malika".into(),
                phone: Some("+998 90 123 45 67".into()),
                phone_consent: true,
                note: None,
            },
        )
        .unwrap();
    let malika = customers[0].id.clone();
    let book = app
        .kk_add_credit_sale(
            &kk,
            KkCreditSaleInput {
                customer_id: malika.clone(),
                item: "Koʻylak".into(),
                cash_price: Some("600 000".into()),
                credit_price: "660 000".into(),
                installments: 3,
                sold_on: None,
                first_due: Some("2026-11-10".into()),
                witness: Some("Opasi".into()),
                note: None,
            },
        )
        .unwrap();
    let s = &book.sales[0];
    assert_eq!(s.schedule.len(), 3);
    assert_eq!(minor(s.credit_markup.as_ref().unwrap()), 6_000_000);
    // Savdo paytida tushum yo'q.
    assert_eq!(minor(&app.kk_overview(&kk, None).unwrap().revenue), 0);
    let id = s.id.clone();
    let pay = |a: &str, w: &str, on: Option<&str>| KkCreditPaymentInput {
        amount: a.into(),
        wallet: w.into(),
        paid_on: on.map(str::to_string),
        note: None,
    };
    app.kk_credit_payment(&kk, &id, pay("220 000", "CARD", None))
        .unwrap();
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.revenue), 22_000_000);
    assert_eq!(minor(&o.receivables), 44_000_000);

    at(&c, "2026-12-30T12:00:00+05:00");
    let book = app.kk_credit_book(&kk).unwrap();
    let s = &book.sales[0];
    assert_eq!(
        (s.status.as_str(), s.overdue_days, s.bucket.as_deref()),
        ("OVERDUE", 20, Some("D1_30"))
    );
    assert_eq!(minor(&s.outstanding), 44_000_000);
    assert_eq!(minor(&book.aging.d1_30), 44_000_000);
    assert_eq!(book.week_start, "2026-12-25");
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.receivables_overdue), 44_000_000);
    assert_eq!(
        app.kk_credit_payment(&kk, &id, pay("500 000", "CASH", None))
            .unwrap_err()
            .code,
        "EXCEEDS_OUTSTANDING"
    );
    assert_eq!(
        app.kk_credit_payment(&kk, &id, pay("10 000", "CASH", Some("2026-11-01")))
            .unwrap_err()
            .code,
        "INVALID_DATE"
    );

    // Muddat 2 oyga uzaytirildi — narx o'zgarmaydi, kechikish yo'qoladi.
    let book = app
        .kk_credit_extend(
            &kk,
            &id,
            KkCreditExtendInput {
                months: 2,
                on: None,
                note: Some("kasal boʻldi".into()),
            },
        )
        .unwrap();
    let s = &book.sales[0];
    assert_eq!(
        (s.status.as_str(), minor(&s.outstanding)),
        ("CURRENT", 44_000_000)
    );
    assert_eq!(s.next_due.as_ref().unwrap().date, "2027-02-10");
    let book = app.kk_credit_mark(&kk, &id, true).unwrap();
    assert!(book.sales[0].talk_this_week);

    // Qisman kechirish va qolganini naqd to'lash — yopildi.
    app.kk_credit_forgive(
        &kk,
        &id,
        KkCreditForgiveInput {
            amount: Some("40 000".into()),
            on: None,
            note: None,
        },
    )
    .unwrap();
    let book = app
        .kk_credit_payment(&kk, &id, pay("400 000", "CASH", None))
        .unwrap();
    let s = &book.sales[0];
    assert_eq!(
        (s.status.as_str(), minor(&s.forgiven), s.events.len()),
        ("SETTLED", 4_000_000, 4)
    );
    assert_eq!(minor(&book.aging.total), 0);
    assert_eq!(app.kk_customers(&kk).unwrap()[0].open_sales, 0);
    assert_eq!(
        app.kk_credit_forgive(
            &kk,
            &id,
            KkCreditForgiveInput {
                amount: None,
                on: None,
                note: None
            }
        )
        .unwrap_err()
        .code,
        "ALREADY_SETTLED"
    );
    assert_eq!(
        app.kk_delete_credit_sale(&kk, &id).unwrap_err().code,
        "CREDIT_HAS_EVENTS"
    );
}
