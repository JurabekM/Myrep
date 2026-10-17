#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K1 — Kasb-kor «ikki cho'ntak» (docs/kasbkor/SPEC.md 2): tushum, chiqim, «egasi oldi», hamyonlar,
//! egasi maoshi va uni Uy makoniga o'tkazish.

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

fn app_with(c: Arc<FixedClock>, spaces: &[&str]) -> (App, Option<String>, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
        "dev-nilufar",
        c,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Nilufarlar".into(),
            device_name: "Atelye kompyuteri".into(),
            platform: "windows".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: spaces.iter().map(|s| s.to_string()).collect(),
            members: vec![NewMemberInput {
                display_name: "Nilufar".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let id = |k: &str| h.spaces.iter().find(|s| s.kind == k).map(|s| s.id.clone());
    (app, id("UY"), id("KASBKOR").unwrap())
}

fn sale(amount: &str, channel: &str) -> KkSaleInput {
    KkSaleInput {
        amount: amount.into(),
        channel: channel.into(),
        occurred_on: None,
        note: Some("Toʻy libosi".into()),
    }
}

fn mv(kind: &str, wallet: &str, amount: &str) -> KkMoveInput {
    KkMoveInput {
        kind: kind.into(),
        wallet: wallet.into(),
        to_wallet: None,
        amount: amount.into(),
        occurred_on: None,
        note: None,
    }
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

#[test]
fn two_pockets_owner_salary_goes_to_uy_atomically() {
    let c = clock("2026-11-20T10:00:00+05:00");
    let (app, uy, kk) = app_with(c.clone(), &["UY", "KASBKOR"]);
    let uy = uy.unwrap();
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(o.owner_salary, None);
    assert_eq!(o.salary_remaining, None);
    assert_eq!(
        app.kk_overview(&uy, None).unwrap_err().code,
        "NOT_KASBKOR_SPACE"
    );

    app.kk_set_owner_salary(&kk, "5 000 000".into()).unwrap();
    app.kk_record_move(&kk, mv("OPENING", "CARD", "3 000 000"))
        .unwrap();
    app.kk_record_sale(&kk, sale("10 000 000", "CARD")).unwrap();
    app.kk_record_sale(&kk, sale("8 000 000", "CASH")).unwrap();
    let materials = app
        .categories(&kk)
        .unwrap()
        .into_iter()
        .find(|c| c.name_key == "category.kk.materials")
        .unwrap();
    app.record_expense(
        &kk,
        NewExpenseInput {
            amount: "8 500 000".into(),
            category_id: materials.id,
            channel: "CARD".into(),
            member_id: None,
            occurred_on: None,
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: None,
        },
    )
    .unwrap();
    // «Egasi oldi» pul oqimini kamaytirmaydi, maoshdan hisoblanadi.
    let o = app
        .kk_record_move(&kk, mv("OWNER_DRAW", "CASH", "1 200 000"))
        .unwrap();
    assert_eq!(minor(&o.cash_flow), 950_000_000);
    assert_eq!(minor(&o.owner_paid), 120_000_000);
    assert_eq!(minor(o.salary_remaining.as_ref().unwrap()), 380_000_000);
    assert_eq!(minor(&o.cash), 680_000_000);
    assert_eq!(minor(&o.card), 450_000_000);
    assert_eq!(o.entries.len(), 5);
    assert_eq!(o.entries.iter().filter(|e| e.kind == "SALE").count(), 2);

    let uy_before = minor(&app.monthly_summary(&uy, None, None).unwrap().income);
    let paid = app
        .kk_pay_owner_salary(
            &kk,
            KkSalaryInput {
                amount: None,
                wallet: "CARD".into(),
                occurred_on: None,
                note: None,
            },
        )
        .unwrap();
    assert_eq!(paid.uy_space_id, uy);
    assert_eq!(minor(&paid.uy_income.income.amount), 380_000_000);
    assert_eq!(paid.uy_income.income.source, "Kasb-kor");
    assert!(
        minor(&paid.uy_income.suggested_share) > 0,
        "Uy'da 1-qonun ulushi taklif qilinadi"
    );
    assert_eq!(minor(&paid.overview.owner_paid), 500_000_000);
    assert_eq!(minor(paid.overview.salary_remaining.as_ref().unwrap()), 0);
    assert_eq!(minor(&paid.overview.card), 70_000_000);
    assert_eq!(
        minor(&app.monthly_summary(&uy, None, None).unwrap().income) - uy_before,
        380_000_000
    );
    // Maosh to'liq o'tkazilgan — summasiz qayta o'tkazib bo'lmaydi.
    let err = app
        .kk_pay_owner_salary(
            &kk,
            KkSalaryInput {
                amount: None,
                wallet: "CARD".into(),
                occurred_on: None,
                note: None,
            },
        )
        .unwrap_err();
    assert_eq!(err.code, "SALARY_ALREADY_PAID");

    // Maoshdan ortiq «egasi oldi» — belgi.
    let o = app
        .kk_record_move(&kk, mv("OWNER_DRAW", "CASH", "500 000"))
        .unwrap();
    assert_eq!(minor(o.overdrawn.as_ref().unwrap()), 50_000_000);

    // Keyingi oy: qoldiqlar o'tadi, oy ko'rsatkichlari va maosh qoldig'i yangilanadi.
    c.set(
        DateTime::parse_from_rfc3339("2026-12-03T10:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    );
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(o.period_start, "2026-12-01");
    assert_eq!(minor(&o.revenue), 0);
    assert_eq!(minor(&o.cash), 630_000_000);
    assert_eq!(minor(&o.card), 70_000_000);
    assert_eq!(minor(o.salary_remaining.as_ref().unwrap()), 500_000_000);
    assert!(o.entries.is_empty());
}

#[test]
fn wallet_transfers_and_validation() {
    let (app, _, kk) = app_with(clock("2026-11-20T10:00:00+05:00"), &["UY", "KASBKOR"]);
    app.kk_record_move(&kk, mv("OPENING", "CASH", "500 000"))
        .unwrap();
    app.kk_record_sale(&kk, sale("3 200 000", "CASH")).unwrap();
    let mut t = mv("TRANSFER", "CASH", "1 500 000");
    t.to_wallet = Some("CARD".into());
    let o = app.kk_record_move(&kk, t.clone()).unwrap();
    assert_eq!(minor(&o.cash), 220_000_000);
    assert_eq!(minor(&o.card), 150_000_000);
    // O'tkazma tushum ham, chiqim ham emas.
    assert_eq!(minor(&o.revenue), 320_000_000);
    assert_eq!(minor(&o.expenses), 0);

    t.to_wallet = Some("CASH".into());
    assert_eq!(app.kk_record_move(&kk, t).unwrap_err().code, "SAME_WALLET");
    assert_eq!(
        app.kk_record_move(&kk, mv("TRANSFER", "CASH", "1"))
            .unwrap_err()
            .code,
        "REQUIRED"
    );
    assert_eq!(
        app.kk_record_move(&kk, mv("OWNER_SALARY", "CASH", "1"))
            .unwrap_err()
            .code,
        "INVALID_KIND"
    );
    assert_eq!(
        app.kk_record_move(&kk, mv("OWNER_DRAW", "SAFE", "1"))
            .unwrap_err()
            .code,
        "INVALID_WALLET"
    );
    assert_eq!(
        app.kk_record_sale(&kk, sale("0", "CASH")).unwrap_err().code,
        "AMOUNT_NOT_POSITIVE"
    );
    assert_eq!(
        app.kk_set_owner_salary(&kk, "-1".into()).unwrap_err().code,
        "AMOUNT_NOT_POSITIVE"
    );
    // Kapital kiritish tushum emas.
    let o = app
        .kk_record_move(&kk, mv("OWNER_CONTRIBUTION", "CARD", "2 000 000"))
        .unwrap();
    assert_eq!(minor(&o.revenue), 320_000_000);
    assert_eq!(minor(&o.contributions), 200_000_000);
    assert_eq!(minor(&o.card), 350_000_000);
}

#[test]
fn salary_needs_uy_space_and_writes_nothing_without_it() {
    let (app, uy, kk) = app_with(clock("2026-11-20T10:00:00+05:00"), &["KASBKOR"]);
    assert!(uy.is_none());
    app.kk_set_owner_salary(&kk, "2 000 000".into()).unwrap();
    let err = app
        .kk_pay_owner_salary(
            &kk,
            KkSalaryInput {
                amount: Some("1 000 000".into()),
                wallet: "CASH".into(),
                occurred_on: None,
                note: None,
            },
        )
        .unwrap_err();
    assert_eq!(err.code, "UY_SPACE_REQUIRED");
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.owner_paid), 0);
    assert!(o.entries.is_empty());
}
