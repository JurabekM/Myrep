#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K7 — Kasb-kor kengayish darvozasi, konvertlar, zakot hisobi, inventarizatsiya va tarozi
//! (docs/kasbkor/SPEC.md 6, 8).

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

fn expense(app: &App, kk: &str, key: &str, amount: &str, on: &str) {
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
            occurred_on: Some(on.into()),
            necessity: None,
            note: None,
            member_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            obligation_id: None,
            self_investment: false,
            learning_plan_id: None,
        },
    )
    .unwrap();
}

fn fund(dto: &KkGateDto, f: &str) -> i64 {
    minor(&dto.funds.iter().find(|x| x.fund == f).unwrap().balance)
}

fn settings() -> KkGrowthSettingsInput {
    KkGrowthSettingsInput {
        reserve_months: 3,
        max_bad_percent: "10".into(),
        zakat_month: None,
        zakat_day: None,
        gold_price: None,
        nisab_grams: 85,
        stock_valuation: "REPLACEMENT".into(),
        scale_reminder: false,
    }
}

/// Oktyabr: tushum 10 mln, chiqim 2 mln, soliq 4% → qolgan 7,6 mln → 30/50/20. Soliq to'langani soliq
/// zaxirasidan; zaxiradan foydalanish qoldiqdan oshmaydi; darvoza sabablari.
#[test]
fn funds_from_closes_and_gate_reasons() {
    let c = clock("2026-10-20T12:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    app.kk_set_close_rules(
        &kk,
        KkCloseRulesInput {
            tax_base: "REVENUE".into(),
            tax_percent: Some("4".into()),
            tax_fixed: None,
            reserve_percent: "30".into(),
            working_percent: "50".into(),
            expansion_percent: "20".into(),
            sadaqa_percent: "0".into(),
        },
    )
    .unwrap();
    app.kk_record_sale(
        &kk,
        KkSaleInput {
            amount: "10 000 000".into(),
            channel: "CARD".into(),
            occurred_on: Some("2026-10-05".into()),
            note: None,
        },
    )
    .unwrap();
    expense(&app, &kk, "category.kk.other", "2 000 000", "2026-10-06");
    at(&c, "2026-11-02T10:00:00+05:00");
    app.kk_close_month(
        &kk,
        KkCloseInput {
            period_start: "2026-10-01".into(),
            carry_overdraw: false,
            explanation: None,
        },
    )
    .unwrap();
    let g = app.kk_gate(&kk).unwrap();
    assert_eq!(
        (
            fund(&g, "TAX"),
            fund(&g, "RESERVE"),
            fund(&g, "WORKING"),
            fund(&g, "EXPANSION")
        ),
        (40_000_000, 228_000_000, 380_000_000, 152_000_000)
    );
    // Soliq to'landi: zaxiradan; zaxiradan ko'pi — xato emas, zaxira 0 da to'xtaydi.
    expense(&app, &kk, "category.kk.tax", "300 000", "2026-11-05");
    expense(&app, &kk, "category.kk.tax", "200 000", "2026-11-06");
    at(&c, "2026-11-07T10:00:00+05:00");
    let g = app.kk_gate(&kk).unwrap();
    assert_eq!(fund(&g, "TAX"), 0);

    let use_fund = |f: &str, amount: &str| KkFundUseInput {
        fund: f.into(),
        amount: amount.into(),
        used_on: None,
        note: Some("Tikuv mashinasi ta'miri".into()),
    };
    let g = app
        .kk_use_fund(&kk, use_fund("RESERVE", "500 000"))
        .unwrap();
    assert_eq!(fund(&g, "RESERVE"), 178_000_000);
    assert_eq!(
        app.kk_use_fund(&kk, use_fund("RESERVE", "2 000 000"))
            .unwrap_err()
            .code,
        "FUND_INSUFFICIENT"
    );
    assert_eq!(
        app.kk_use_fund(&kk, use_fund("TAX", "1")).unwrap_err().code,
        "INVALID_FUND"
    );

    // Darvoza: zaxira 1,78 mln < 3 × 2 mln; bitta «Hisob kuni»; reja yo'q.
    assert!(!g.open);
    assert_eq!(g.reasons, ["RESERVE", "PROFIT", "PLAN"]);
    assert_eq!(minor(g.required_reserve.as_ref().unwrap()), 600_000_000);
    assert_eq!(g.coverage_months.as_deref(), Some("0,89"));
    assert_eq!(g.true_profits.len(), 1);
    // Kengayish rejasi — «Hunardan ishga» kalkulyatori shu makonda.
    let sc = |name: &str, income: &str| IdeaScenarioInput {
        name: name.into(),
        income: income.into(),
        expense: "4 000 000".into(),
    };
    app.create_venture_idea(
        &kk,
        VentureIdeaInput {
            title: "Ikkinchi tikuv sexi".into(),
            skill_id: None,
            capex: vec![CapexLineInput {
                title: "Mashinalar".into(),
                amount: "24 000 000".into(),
            }],
            scenarios: vec![
                sc("PESSIMISTIC", "5 000 000"),
                sc("BASE", "7 000 000"),
                sc("OPTIMISTIC", "9 000 000"),
            ],
            worker_share_bp: None,
        },
    )
    .unwrap();
    let g = app.kk_gate(&kk).unwrap();
    assert_eq!(
        (g.plans, g.reasons.clone()),
        (1, vec!["RESERVE".to_string(), "PROFIT".to_string()])
    );
}

/// SPEC 8.3 Bahodir aka: tovar 90 mln + naqd 12 mln + nasiya 8 mln − ta'minotchiga qarz 10 mln = 100 mln;
/// nisob 1 100 000 × 85 = 93,5 mln → 2 500 000 (hisob, fatvo emas).
#[test]
fn zakat_calculation_and_snapshot() {
    let c = clock("2026-11-20T12:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    let item = app
        .kk_add_item(
            &kk,
            KkItemInput {
                name: "Mato".into(),
                unit: "PCS".into(),
                method: None,
                sale_price: None,
                replacement_price: None,
                min_qty: None,
                frozen_days: None,
                note: None,
            },
        )
        .unwrap()
        .items[0]
        .id
        .clone();
    app.kk_stock_move(
        &kk,
        &item,
        KkStockMoveInput {
            kind: "PURCHASE".into(),
            qty: "1".into(),
            amount: Some("90 000 000".into()),
            wallet: None,
            occurred_on: None,
            reason: None,
        },
    )
    .unwrap();
    app.kk_record_move(
        &kk,
        KkMoveInput {
            kind: "OPENING".into(),
            wallet: "CASH".into(),
            to_wallet: None,
            amount: "12 000 000".into(),
            occurred_on: None,
            note: None,
        },
    )
    .unwrap();
    let customer = app
        .kk_add_customer(
            &kk,
            KkCustomerInput {
                name: "Malika".into(),
                phone: None,
                phone_consent: false,
                note: None,
            },
        )
        .unwrap()[0]
        .id
        .clone();
    app.kk_add_credit_sale(
        &kk,
        KkCreditSaleInput {
            customer_id: customer,
            item: "Ko'ylaklar".into(),
            cash_price: None,
            credit_price: "8 000 000".into(),
            installments: 1,
            sold_on: None,
            first_due: None,
            witness: None,
            note: None,
        },
    )
    .unwrap();
    let sup = app
        .kk_add_supplier(
            &kk,
            KkSupplierInput {
                name: "Ulgurji baza".into(),
                phone: None,
                phone_consent: false,
                goods: Some("Mato".into()),
                item_id: None,
                unit_price: None,
                payment_days: 30,
                delivery: None,
                returns: None,
                started_on: None,
                arbiter: None,
                review_on: None,
                note: None,
            },
        )
        .unwrap()
        .suppliers[0]
        .id
        .clone();
    app.kk_sign_agreement(
        &kk,
        &sup,
        KkSignInput {
            signed_on: None,
            effective_from: None,
        },
    )
    .unwrap();
    app.kk_supply_delivery(
        &kk,
        &sup,
        KkDeliveryInput {
            delivered_on: None,
            qty: None,
            amount: Some("10 000 000".into()),
            note: None,
        },
    )
    .unwrap();

    let input = |gold: Option<&str>, hawl: Option<bool>| KkZakatInput {
        gold_price: gold.map(str::to_string),
        nisab_grams: None,
        valuation: None,
        hopeless_sale_ids: vec![],
        hawl_complete: hawl,
    };
    // Oltin narxi kiritilmagan — hisob yo'q; diniy matn tasdiqlanmagan — ko'rsatilmaydi.
    let z = app.kk_zakat_draft(&kk, input(None, None)).unwrap();
    assert_eq!(z.reason.as_deref(), Some("GOLD_PRICE_MISSING"));
    assert_eq!(
        (z.religious_note, z.religious_review.as_str()),
        (None, "PENDING")
    );
    assert_eq!(
        app.kk_save_zakat(&kk, input(None, None))
            .unwrap_err()
            .field
            .as_deref(),
        Some("goldPrice")
    );
    // Birinchi yozuv bugun — hawl to'lmagan (taklif).
    let z = app
        .kk_zakat_draft(&kk, input(Some("1 100 000"), None))
        .unwrap();
    assert!(!z.hawl_suggested);
    assert_eq!(z.reason.as_deref(), Some("HAWL_NOT_COMPLETE"));
    assert_eq!(minor(&z.base), 10_000_000_000);
    // Egasi biznes bir yildan beri borligini tasdiqladi.
    let z = app
        .kk_zakat_draft(&kk, input(Some("1 100 000"), Some(true)))
        .unwrap();
    assert_eq!(
        (
            minor(&z.stock),
            minor(&z.cash),
            minor(&z.receivables),
            minor(&z.debts)
        ),
        (9_000_000_000, 1_200_000_000, 800_000_000, 1_000_000_000)
    );
    assert_eq!(minor(z.nisab.as_ref().unwrap()), 9_350_000_000);
    assert_eq!((minor(&z.zakat), z.due), (250_000_000, true));
    assert_eq!(z.hijri_date, "1448-06-09");
    // 90+ bo'lmagan nasiyani «umidsiz» deb bo'lmaydi.
    let mut bad = input(Some("1 100 000"), Some(true));
    bad.hopeless_sale_ids = vec![z.receivable_lines[0].sale_id.clone()];
    assert_eq!(
        app.kk_zakat_draft(&kk, bad).unwrap_err().code,
        "HOPELESS_NOT_90"
    );
    let h = app
        .kk_save_zakat(&kk, input(Some("1 100 000"), Some(true)))
        .unwrap();
    assert_eq!((h.len(), minor(&h[0].zakat)), (1, 250_000_000));

    // «Zakot kuni» 30 kun ichida — bosh sahifada eslatma.
    let mut s = settings();
    s.zakat_month = Some(6);
    s.zakat_day = Some(20);
    let st = app.kk_set_growth_settings(&kk, s).unwrap();
    assert_eq!(st.next_zakat_day.as_deref(), Some("2026-12-01"));
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(o.zakat_reminder.as_deref(), Some("2026-12-01"));
    at(&c, "2026-10-20T12:00:00+05:00");
    assert_eq!(app.kk_overview(&kk, None).unwrap().zakat_reminder, None);
}

#[test]
fn inventory_count_in_one_transaction() {
    let (app, kk) = app_with(clock("2026-11-20T12:00:00+05:00"));
    let add = |name: &str| {
        app.kk_add_item(
            &kk,
            KkItemInput {
                name: name.into(),
                unit: "G".into(),
                method: None,
                sale_price: None,
                replacement_price: None,
                min_qty: None,
                frozen_days: None,
                note: None,
            },
        )
        .unwrap()
        .items
        .into_iter()
        .find(|i| i.name == name)
        .unwrap()
        .id
    };
    let (sugar, salt, rice) = (add("Shakar"), add("Tuz"), add("Guruch"));
    for (id, amount) in [(&sugar, "120 000"), (&salt, "30 000"), (&rice, "150 000")] {
        app.kk_stock_move(
            &kk,
            id,
            KkStockMoveInput {
                kind: "PURCHASE".into(),
                qty: "10".into(),
                amount: Some(amount.into()),
                wallet: None,
                occurred_on: Some("2026-11-01".into()),
                reason: None,
            },
        )
        .unwrap();
    }
    let line = |id: &str, counted: &str| KkInventoryLineInput {
        item_id: id.into(),
        counted: counted.into(),
    };
    let mut input = KkInventoryInput {
        counted_on: None,
        reason: " ".into(),
        lines: vec![line(&sugar, "9,5"), line(&salt, "10"), line(&rice, "")],
    };
    assert_eq!(
        app.kk_inventory(&kk, input.clone())
            .unwrap_err()
            .field
            .as_deref(),
        Some("reason")
    );
    input.reason = "Yillik inventarizatsiya".into();
    input.lines.push(line(&rice, "-1"));
    assert_eq!(
        app.kk_inventory(&kk, input.clone())
            .unwrap_err()
            .field
            .as_deref(),
        Some("lines.3")
    );
    input.lines.pop();
    let s = app.kk_inventory(&kk, input).unwrap();
    let qty = |n: &str| s.items.iter().find(|i| i.name == n).unwrap().qty.clone();
    assert_eq!(
        (qty("Shakar"), qty("Tuz"), qty("Guruch")),
        ("9,5".into(), "10".into(), "10".into())
    );
    let counts = app.kk_stock_counts(&kk).unwrap();
    assert_eq!((counts[0].counted, counts[0].changed), (2, 1));
    assert_eq!(
        (
            minor(&counts[0].value_before),
            minor(&counts[0].value_after)
        ),
        (30_000_000, 29_400_000)
    );
}

#[test]
fn scale_check_reminder() {
    let c = clock("2026-11-20T12:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    assert!(!app.kk_scale(&kk).unwrap().due);
    let mut s = settings();
    s.scale_reminder = true;
    app.kk_set_growth_settings(&kk, s).unwrap();
    assert!(app.kk_overview(&kk, None).unwrap().scale_check_due);
    let check = |result: &str, note: Option<&str>| KkScaleCheckInput {
        result: result.into(),
        checked_on: None,
        note: note.map(str::to_string),
    };
    assert_eq!(
        app.kk_scale_check(&kk, check("ADJUSTED", None))
            .unwrap_err()
            .field
            .as_deref(),
        Some("note")
    );
    let sc = app.kk_scale_check(&kk, check("OK", None)).unwrap();
    assert!(!sc.due && sc.checks.len() == 1);
    at(&c, "2026-12-21T12:00:00+05:00");
    assert!(app.kk_scale(&kk).unwrap().due);
}
