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
fn month_boundary_next_period_first_day_is_not_counted() {
    let c = clock("2026-11-20T10:00:00+05:00");
    let (app, _, kk) = app_with(c, &["UY", "KASBKOR"]);
    let mut s = sale("1 000 000", "CASH");
    s.occurred_on = Some("2026-12-01".into());
    app.kk_record_sale(&kk, s).unwrap();
    let mut s = sale("400 000", "CASH");
    s.occurred_on = Some("2026-11-30".into());
    app.kk_record_sale(&kk, s).unwrap();

    let nov = app.kk_overview(&kk, None).unwrap();
    assert_eq!(
        (nov.period_start.as_str(), nov.period_end.as_str()),
        ("2026-11-01", "2026-11-30")
    );
    assert_eq!(minor(&nov.revenue), 40_000_000);
    assert_eq!(minor(&nov.cash), 40_000_000);
    assert_eq!(nov.entries.len(), 1);

    let dec = app.kk_overview(&kk, Some("2026-12-15".into())).unwrap();
    assert_eq!(minor(&dec.revenue), 100_000_000);
    assert_eq!(minor(&dec.cash), 140_000_000);
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

fn expense(app: &App, kk: &str, key: &str, amount: &str) {
    let cat = app
        .categories(kk)
        .unwrap()
        .into_iter()
        .find(|c| c.name_key == key)
        .unwrap();
    app.record_expense(
        kk,
        NewExpenseInput {
            amount: amount.into(),
            category_id: cat.id,
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
}

fn machine(cost: &str, months: u32, wallet: Option<&str>) -> KkEquipmentInput {
    KkEquipmentInput {
        name: "Tikuv mashinalari (2 ta)".into(),
        cost: cost.into(),
        salvage: None,
        useful_months: months,
        acquired_on: None,
        wallet: wallet.map(str::to_string),
    }
}

/// SPEC 3.1 Nilufar: ko'rinadigan foyda 9 500 000, haqiqiy foyda 3 100 000.
#[test]
fn true_profit_nilufar_and_equipment_lifecycle() {
    let c = clock("2026-11-20T10:00:00+05:00");
    let (app, _, kk) = app_with(c.clone(), &["UY", "KASBKOR"]);
    app.kk_record_sale(&kk, sale("18 000 000", "CARD")).unwrap();
    expense(&app, &kk, "category.kk.materials", "6 000 000");
    expense(&app, &kk, "category.kk.rent", "2 000 000");
    expense(&app, &kk, "category.kk.other", "500 000");
    app.kk_set_owner_salary(&kk, "4 000 000".into()).unwrap();
    app.kk_set_owner_labor(&kk, "5 000 000".into()).unwrap();
    // Maosh va o'z mehnati bahosi bir-birini o'chirmaydi.
    let o = app.kk_set_owner_salary(&kk, "4 000 000".into()).unwrap();
    assert_eq!(minor(o.profit.owner_labor.as_ref().unwrap()), 500_000_000);
    app.kk_add_family_labor(
        &kk,
        KkFamilyLaborInput {
            person: "Madina (qizim)".into(),
            hours: "80".into(),
            hourly_rate: "15 000".into(),
            paid: false,
            worked_on: None,
            note: None,
        },
    )
    .unwrap();
    // To'langan yordam chiqimda bor — haqiqiy foydadan qayta ayirilmaydi.
    let fl = app
        .kk_add_family_labor(
            &kk,
            KkFamilyLaborInput {
                person: "Jiyanim".into(),
                hours: "2,5".into(),
                hourly_rate: "20 000".into(),
                paid: true,
                worked_on: None,
                note: Some("dazmol".into()),
            },
        )
        .unwrap();
    assert_eq!(fl.len(), 2);
    assert_eq!(fl[1].hours, "2,5");
    assert_eq!(minor(&fl[1].value), 5_000_000);
    let eq = app
        .kk_add_equipment(&kk, machine("12 000 000", 60, Some("CARD")))
        .unwrap();
    assert_eq!(minor(&eq[0].month_depreciation), 20_000_000);
    assert_eq!(eq[0].months_left, 59);

    let o = app.kk_overview(&kk, None).unwrap();
    let p = &o.profit;
    assert_eq!(minor(&p.visible_profit), 950_000_000);
    assert_eq!(minor(&p.family_labor), 120_000_000);
    assert_eq!(minor(&p.family_labor_paid), 5_000_000);
    assert_eq!(minor(&p.depreciation), 20_000_000);
    assert_eq!(minor(&p.true_profit), 310_000_000);
    // Uskuna xaridi pul oqimiga kirmaydi, lekin kartadan chiqdi.
    assert_eq!(minor(&o.cash_flow), 950_000_000);
    assert_eq!(minor(&o.equipment_purchases), 1_200_000_000);
    assert_eq!(minor(&o.card), 1_800_000_000 - 850_000_000 - 1_200_000_000);
    assert!(o.entries.iter().any(|e| e.kind == "EQUIPMENT_PURCHASE"));

    // 10 oydan keyin (2027-09) sotildi: balans 12 mln − 10 × 200 000 = 10 mln; 4 mln ga — 6 mln bir martalik.
    c.set(
        DateTime::parse_from_rfc3339("2027-09-10T10:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    );
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.profit.depreciation), 20_000_000);
    assert_eq!(minor(&o.profit.family_labor), 0);
    let id = eq[0].id.clone();
    let err = app
        .kk_dispose_equipment(
            &kk,
            &id,
            KkDisposeInput {
                proceeds: Some("4 000 000".into()),
                wallet: None,
                disposed_on: None,
            },
        )
        .unwrap_err();
    assert_eq!(
        (err.code.as_str(), err.field.as_deref()),
        ("REQUIRED", Some("wallet"))
    );
    let eq = app
        .kk_dispose_equipment(
            &kk,
            &id,
            KkDisposeInput {
                proceeds: Some("4 000 000".into()),
                wallet: Some("CASH".into()),
                disposed_on: None,
            },
        )
        .unwrap();
    assert_eq!(eq[0].status, "DISPOSED");
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.profit.depreciation), 0);
    assert_eq!(minor(&o.profit.disposal), 600_000_000);
    assert_eq!(minor(&o.equipment_sales), 400_000_000);
    assert_eq!(minor(&o.cash), 400_000_000);
    assert_eq!(
        app.kk_dispose_equipment(
            &kk,
            &id,
            KkDisposeInput {
                proceeds: None,
                wallet: None,
                disposed_on: None
            }
        )
        .unwrap_err()
        .code,
        "ALREADY_DISPOSED"
    );
    // Keyingi oy: eskirish ham, chiqib ketish ham yo'q.
    c.set(
        DateTime::parse_from_rfc3339("2027-10-10T10:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    );
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(
        (minor(&o.profit.depreciation), minor(&o.profit.disposal)),
        (0, 0)
    );
}

#[test]
fn equipment_family_labor_and_quote_validation() {
    let c = clock("2026-11-20T10:00:00+05:00");
    let (app, uy, kk) = app_with(c, &["UY", "KASBKOR"]);
    let code = |r: Result<Vec<KkEquipmentDto>, AppError>| r.unwrap_err().code;
    let mut bad = machine("1 000 000", 12, None);
    bad.salvage = Some("2 000 000".into());
    assert_eq!(code(app.kk_add_equipment(&kk, bad)), "INVALID_SALVAGE");
    assert_eq!(
        code(app.kk_add_equipment(&kk, machine("1 000 000", 0, None))),
        "INVALID_USEFUL_LIFE"
    );
    assert_eq!(
        code(app.kk_add_equipment(&kk, machine("0", 12, None))),
        "AMOUNT_NOT_POSITIVE"
    );
    assert_eq!(
        code(app.kk_add_equipment(&kk, machine("1 000 000", 12, Some("SAFE")))),
        "INVALID_WALLET"
    );
    // Ilovagacha bor edi — hamyonga ta'sir qilmaydi, eskirish esa hisoblanadi.
    let mut old = machine("3 600 000", 36, None);
    old.acquired_on = Some("2026-05-03".into());
    let eq = app.kk_add_equipment(&kk, old).unwrap();
    assert_eq!(eq[0].months_left, 29);
    assert_eq!(minor(&eq[0].book_value), 360_000_000 - 7 * 10_000_000);
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(
        (minor(&o.card), minor(&o.profit.depreciation)),
        (0, 10_000_000)
    );
    let disposed_early = app
        .kk_dispose_equipment(
            &kk,
            &eq[0].id,
            KkDisposeInput {
                proceeds: None,
                wallet: None,
                disposed_on: Some("2026-04-01".into()),
            },
        )
        .unwrap_err();
    assert_eq!(disposed_early.code, "BEFORE_ACQUIRED");
    assert_eq!(app.kk_delete_equipment(&kk, &eq[0].id).unwrap().len(), 0);

    let labor = |hours: &str, rate: &str| {
        app.kk_add_family_labor(
            &kk,
            KkFamilyLaborInput {
                person: "Madina".into(),
                hours: hours.into(),
                hourly_rate: rate.into(),
                paid: false,
                worked_on: None,
                note: None,
            },
        )
    };
    assert_eq!(labor("2,555", "10 000").unwrap_err().code, "INVALID_HOURS");
    assert_eq!(labor("0", "10 000").unwrap_err().code, "INVALID_HOURS");
    assert_eq!(labor("3", "-1").unwrap_err().code, "AMOUNT_NEGATIVE");
    let fl = labor("3", "10 000").unwrap();
    assert_eq!(app.kk_delete_family_labor(&kk, &fl[0].id).unwrap().len(), 0);
    assert_eq!(
        app.kk_family_labor(&uy.unwrap(), None).unwrap_err().code,
        "NOT_KASBKOR_SPACE"
    );

    // SPEC 3.2 Jasur: tannarx 798 000, narx 700 000 — mehnatga 142 000 qoladi; avans materialga yetmaydi.
    let q = app
        .kk_order_quote(
            &kk,
            KkQuoteInput {
                material: Some("450 000".into()),
                hours: Some("6".into()),
                hourly_rate: Some("40 000".into()),
                travel: Some("50 000".into()),
                depreciation: Some("20 000".into()),
                reserve_percent: Some("5".into()),
                price: Some("700 000".into()),
                advance: Some("300 000".into()),
            },
        )
        .unwrap();
    assert_eq!(minor(&q.cost), 79_800_000);
    assert_eq!(q.below_cost, Some(true));
    assert_eq!(minor(q.labor_paid.as_ref().unwrap()), 14_200_000);
    assert_eq!(minor(q.material_shortfall.as_ref().unwrap()), 15_000_000);
    let empty = KkQuoteInput {
        material: None,
        hours: None,
        hourly_rate: None,
        travel: None,
        depreciation: None,
        reserve_percent: Some("100,5".into()),
        price: None,
        advance: None,
    };
    assert_eq!(
        app.kk_order_quote(&kk, empty).unwrap_err().code,
        "INVALID_PERCENT"
    );
}

fn at(c: &FixedClock, t: &str) {
    c.set(DateTime::parse_from_rfc3339(t).unwrap().with_timezone(&Utc));
}

fn rules(tax_base: &str, tax: Option<&str>, split: [&str; 4]) -> KkCloseRulesInput {
    KkCloseRulesInput {
        tax_base: tax_base.into(),
        tax_percent: tax.filter(|_| tax_base != "FIXED").map(str::to_string),
        tax_fixed: tax.filter(|_| tax_base == "FIXED").map(str::to_string),
        reserve_percent: split[0].into(),
        working_percent: split[1].into(),
        expansion_percent: split[2].into(),
        sadaqa_percent: split[3].into(),
    }
}

/// SPEC 4.5 Nilufar: qolgan 2 580 000 → 774 000 / 1 290 000 / 516 000; bayonnoma o'zgarmas, yopilgan
/// oyga yozib bo'lmaydi.
#[test]
fn month_close_nilufar_and_closed_period_guard() {
    let c = clock("2026-11-20T10:00:00+05:00");
    let (app, _, kk) = app_with(c.clone(), &["UY", "KASBKOR"]);
    app.kk_record_sale(&kk, sale("18 000 000", "CARD")).unwrap();
    expense(&app, &kk, "category.kk.materials", "6 000 000");
    expense(&app, &kk, "category.kk.rent", "2 000 000");
    expense(&app, &kk, "category.kk.other", "500 000");
    // Qizining yordami uchun to'langan.
    expense(&app, &kk, "category.kk.wages", "1 200 000");
    app.kk_set_owner_salary(&kk, "5 000 000".into()).unwrap();
    app.kk_record_move(&kk, mv("OWNER_DRAW", "CARD", "5 000 000"))
        .unwrap();
    let r = app
        .kk_set_close_rules(&kk, rules("REVENUE", Some("4"), ["30", "50", "20", "0"]))
        .unwrap();
    assert_eq!(
        (r.tax_percent.as_str(), r.reserve_percent.as_str()),
        ("4", "30")
    );
    let bad = app.kk_set_close_rules(&kk, rules("REVENUE", Some("4"), ["30", "50", "10", "0"]));
    assert_eq!(bad.unwrap_err().code, "INVALID_RULE");
    assert_eq!(
        app.kk_set_close_rules(&kk, rules("MONTHLY", None, ["30", "50", "20", "0"]))
            .unwrap_err()
            .code,
        "INVALID_TAX_BASE"
    );
    // Joriy oy hali tugamagan.
    let err = app
        .kk_close_draft(&kk, Some("2026-11-01".into()))
        .unwrap_err();
    assert_eq!(err.code, "PERIOD_NOT_ENDED");

    at(&c, "2026-12-03T10:00:00+05:00");
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(o.close_due.as_deref(), Some("2026-11-01"));
    let d = app.kk_close_draft(&kk, None).unwrap();
    assert_eq!(
        (d.period_start.as_str(), d.period_end.as_str()),
        ("2026-11-01", "2026-11-30")
    );
    assert_eq!(minor(&d.tax), 72_000_000);
    assert_eq!(minor(&d.remaining), 258_000_000);
    let a = d.allocation.as_ref().unwrap();
    assert_eq!(
        (minor(&a.reserve), minor(&a.working), minor(&a.expansion)),
        (77_400_000, 129_000_000, 51_600_000)
    );
    assert!(!d.needs_explanation);

    let closed = app
        .kk_close_month(
            &kk,
            KkCloseInput {
                period_start: "2026-11-01".into(),
                carry_overdraw: false,
                explanation: None,
            },
        )
        .unwrap();
    assert_eq!(closed.summary, d);
    assert_eq!(closed.short_code.len(), 19);
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(o.close_due, None);
    assert_eq!(o.closed_until.as_deref(), Some("2026-11-30"));
    assert_eq!(
        app.kk_close_month(
            &kk,
            KkCloseInput {
                period_start: "2026-11-01".into(),
                carry_overdraw: false,
                explanation: None
            }
        )
        .unwrap_err()
        .code,
        "ALREADY_CLOSED"
    );
    // Yopilgan oyga yozuv ham, o'chirish ham yo'q; keyingi oyga — bor.
    let mut late = sale("100 000", "CASH");
    late.occurred_on = Some("2026-11-29".into());
    let err = app.kk_record_sale(&kk, late).unwrap_err();
    assert_eq!(
        (err.code.as_str(), err.field.as_deref()),
        ("PERIOD_CLOSED", Some("occurredOn"))
    );
    let nov_expense = o_entry(&app, &kk, "2026-11-15", "EXPENSE");
    assert_eq!(
        app.delete_expense(&kk, &nov_expense).unwrap_err().code,
        "PERIOD_CLOSED"
    );
    app.kk_record_sale(&kk, sale("100 000", "CASH")).unwrap();
    // Oldingi oyni endi yopib bo'lmaydi (zanjir tartibi).
    assert_eq!(
        app.kk_close_draft(&kk, Some("2026-10-01".into()))
            .unwrap_err()
            .code,
        "LATER_PERIOD_CLOSED"
    );

    let list = app.kk_month_closes(&kk).unwrap();
    assert_eq!(list.len(), 1);
    let pdf = app.kk_month_close_pdf(&kk, &list[0].id).unwrap();
    assert!(pdf.starts_with(b"%PDF"));
    if let Ok(dir) = std::env::var("BARAKA_PDF_PREVIEW") {
        std::fs::write(format!("{dir}/kk-close.pdf"), &pdf).unwrap();
    }
}

fn o_entry(app: &App, kk: &str, date: &str, kind: &str) -> String {
    app.kk_overview(kk, Some(date.into()))
        .unwrap()
        .entries
        .into_iter()
        .find(|e| e.kind == kind)
        .unwrap()
        .id
}

/// Manfiy qolgan — izohsiz yopilmaydi; maoshdan ortig'i keyingi oy maoshidan ushlanadi.
#[test]
fn month_close_negative_needs_explanation_and_overdraw_carries() {
    let c = clock("2026-11-20T10:00:00+05:00");
    let (app, _, kk) = app_with(c.clone(), &["UY", "KASBKOR"]);
    app.kk_set_owner_salary(&kk, "3 000 000".into()).unwrap();
    app.kk_record_sale(&kk, sale("4 000 000", "CASH")).unwrap();
    app.kk_record_move(&kk, mv("OWNER_DRAW", "CASH", "4 500 000"))
        .unwrap();
    at(&c, "2026-12-02T10:00:00+05:00");
    let d = app.kk_close_draft(&kk, None).unwrap();
    assert_eq!(minor(&d.owner_pay), 450_000_000);
    assert_eq!(minor(d.overdrawn.as_ref().unwrap()), 150_000_000);
    assert_eq!(minor(&d.remaining), -50_000_000);
    assert!(d.needs_explanation && d.allocation.is_none());
    let input = |e: Option<&str>| KkCloseInput {
        period_start: "2026-11-01".into(),
        carry_overdraw: true,
        explanation: e.map(str::to_string),
    };
    let err = app.kk_close_month(&kk, input(Some("   "))).unwrap_err();
    assert_eq!(
        (err.code.as_str(), err.field.as_deref()),
        ("REQUIRED", Some("explanation"))
    );
    let closed = app
        .kk_close_month(&kk, input(Some("Toʻy uchun koʻproq oldim")))
        .unwrap();
    assert_eq!(minor(&closed.carry_forward), 150_000_000);
    assert_eq!(
        closed.explanation.as_deref(),
        Some("Toʻy uchun koʻproq oldim")
    );
    // Dekabr maoshi: 3 mln − 1,5 mln.
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(o.owner_salary.as_ref().unwrap()), 150_000_000);
    assert_eq!(minor(o.salary_carry.as_ref().unwrap()), 150_000_000);
    assert_eq!(minor(o.salary_remaining.as_ref().unwrap()), 150_000_000);
    // Yanvarda ushlash tugaydi.
    at(&c, "2027-01-05T10:00:00+05:00");
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(o.owner_salary.as_ref().unwrap()), 300_000_000);
    assert_eq!(o.salary_carry, None);
    // Dekabrni yopish: zanjirning ikkinchi bo'g'ini, kod boshqacha.
    let mut dec_sale = sale("3 000 000", "CARD");
    dec_sale.occurred_on = Some("2026-12-10".into());
    app.kk_record_sale(&kk, dec_sale).unwrap();
    let dec = app
        .kk_close_month(
            &kk,
            KkCloseInput {
                period_start: "2026-12-01".into(),
                carry_overdraw: false,
                explanation: None,
            },
        )
        .unwrap();
    assert_ne!(dec.short_code, closed.short_code);
    assert_eq!(app.kk_month_closes(&kk).unwrap()[0].id, dec.id);
}
