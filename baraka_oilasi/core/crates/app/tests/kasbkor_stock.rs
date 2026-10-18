#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K5 — Kasb-kor tovar qoldig'i, tannarx, qayta tiklash narxi va muzlagan tovar (docs/kasbkor/SPEC.md 4).

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

fn item(name: &str, method: &str) -> KkItemInput {
    KkItemInput {
        name: name.into(),
        unit: "G".into(),
        method: Some(method.into()),
        sale_price: None,
        replacement_price: None,
        min_qty: None,
        frozen_days: None,
        note: None,
    }
}

fn mv(
    kind: &str,
    qty: &str,
    amount: Option<&str>,
    wallet: Option<&str>,
    on: &str,
) -> KkStockMoveInput {
    KkStockMoveInput {
        kind: kind.into(),
        qty: qty.into(),
        amount: amount.map(str::to_string),
        wallet: wallet.map(str::to_string),
        occurred_on: Some(on.into()),
        reason: None,
    }
}

/// SPEC 4.2: 50 kg × 11 000 (ilovagacha bor edi) + 100 kg × 12 500 (kartadan), 80 kg 1 120 000 ga sotildi.
fn sugar(app: &App, kk: &str, method: &str) -> String {
    let s = app.kk_add_item(kk, item("Shakar", method)).unwrap();
    let id = s.items[0].id.clone();
    app.kk_stock_move(
        kk,
        &id,
        mv("PURCHASE", "50", Some("550 000"), None, "2026-11-01"),
    )
    .unwrap();
    app.kk_stock_move(
        kk,
        &id,
        mv(
            "PURCHASE",
            "100",
            Some("1 250 000"),
            Some("CARD"),
            "2026-11-02",
        ),
    )
    .unwrap();
    app.kk_stock_move(
        kk,
        &id,
        mv("SALE", "80", Some("1 120 000"), Some("CASH"), "2026-11-03"),
    )
    .unwrap();
    id
}

#[test]
fn sugar_average_cost_flows_into_true_profit() {
    let c = clock("2026-11-20T18:00:00+05:00");
    let (app, kk) = app_with(c);
    let id = sugar(&app, &kk, "AVERAGE");
    let s = app.kk_stock(&kk).unwrap();
    let it = &s.items[0];
    assert_eq!((it.qty.as_str(), minor(&it.value)), ("70", 84_000_000));
    assert_eq!(minor(it.unit_cost.as_ref().unwrap()), 1_200_000);
    assert_eq!(it.moves.len(), 3);
    assert_eq!(
        (
            it.moves[0].kind.as_str(),
            it.moves[0].qty.as_str(),
            minor(&it.moves[0].cost)
        ),
        ("SALE", "-80", 96_000_000)
    );
    // Oxirgi xarid narxi — qayta tiklash narxi.
    assert_eq!(minor(it.replacement_price.as_ref().unwrap()), 1_250_000);

    // Sotuv — Kasb-kor tushumi; tovar xaridi pul oqimiga kirmaydi, lekin kartadan chiqadi.
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.revenue), 112_000_000);
    assert_eq!(minor(&o.profit.cogs), 96_000_000);
    assert_eq!(minor(&o.profit.visible_profit), 16_000_000);
    assert_eq!(minor(&o.cash_flow), 112_000_000);
    assert_eq!(minor(&o.stock_purchases), 125_000_000);
    assert_eq!(
        (minor(&o.cash), minor(&o.card)),
        (112_000_000, -125_000_000)
    );
    assert_eq!(minor(&o.stock_value), 84_000_000);
    let p = o
        .entries
        .iter()
        .find(|e| e.kind == "STOCK_PURCHASE")
        .unwrap();
    assert_eq!(p.note.as_deref(), Some("Shakar"));
    let sale = o.entries.iter().find(|e| e.kind == "SALE").unwrap();
    assert_eq!(sale.note.as_deref(), Some("Shakar"));

    // Inventarizatsiya: 69,5 kg sanaldi → 0,5 kg kamomad o'rtacha tannarxda (6 000) — yo'qotish.
    let mut count = mv("COUNT", "69,5", None, None, "2026-11-20");
    assert_eq!(
        app.kk_stock_move(&kk, &id, count.clone())
            .unwrap_err()
            .field
            .as_deref(),
        Some("reason")
    );
    count.reason = Some("Toʻkilgan".into());
    let s = app.kk_stock_move(&kk, &id, count).unwrap();
    assert_eq!(s.items[0].qty, "69,5");
    assert_eq!(s.items[0].moves[0].kind, "ADJUST");
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.profit.stock_losses), 600_000);
    assert_eq!(minor(&o.profit.visible_profit), 15_400_000);
    let mut same = mv("COUNT", "69.5", None, None, "2026-11-20");
    same.reason = Some("x".into());
    assert_eq!(
        app.kk_stock_move(&kk, &id, same).unwrap_err().code,
        "NO_DIFFERENCE"
    );

    // Harakatdan keyin usul va birlik o'zgarmaydi.
    let mut fifo = item("Shakar", "FIFO");
    assert_eq!(
        app.kk_update_item(&kk, &id, fifo.clone()).unwrap_err().code,
        "METHOD_LOCKED"
    );
    fifo.method = Some("AVERAGE".into());
    fifo.unit = "PCS".into();
    assert_eq!(
        app.kk_update_item(&kk, &id, fifo).unwrap_err().code,
        "UNIT_LOCKED"
    );
    assert_eq!(
        app.kk_delete_item(&kk, &id).unwrap_err().code,
        "ITEM_HAS_MOVES"
    );
}

#[test]
fn sugar_fifo_cost() {
    let (app, kk) = app_with(clock("2026-11-20T18:00:00+05:00"));
    sugar(&app, &kk, "FIFO");
    let it = &app.kk_stock(&kk).unwrap().items[0];
    assert_eq!((it.qty.as_str(), minor(&it.value)), ("70", 87_500_000));
    assert_eq!(minor(&it.moves[0].cost), 92_500_000);
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.profit.visible_profit), 19_500_000);
}

/// SPEC 4.3: joriy xarid narxi 13 500 → 945 000, farq 105 000; 13 000 ga sotish — ogohlantirish.
#[test]
fn replacement_gap_and_sale_warning() {
    let (app, kk) = app_with(clock("2026-11-20T18:00:00+05:00"));
    let id = sugar(&app, &kk, "AVERAGE");
    let mut input = item("Shakar", "AVERAGE");
    input.replacement_price = Some("13 500".into());
    input.sale_price = Some("13 000".into());
    input.min_qty = Some("100".into());
    let s = app.kk_update_item(&kk, &id, input.clone()).unwrap();
    let it = &s.items[0];
    assert_eq!(minor(it.replacement_value.as_ref().unwrap()), 94_500_000);
    assert_eq!(minor(it.inflation_gap.as_ref().unwrap()), 10_500_000);
    assert!(it.sale_below_replacement);
    assert!(it.below_min);
    assert_eq!(it.min_qty.as_deref(), Some("100"));
    assert_eq!(minor(&s.inflation_gap), 10_500_000);

    input.sale_price = Some("14 000".into());
    let s = app.kk_update_item(&kk, &id, input).unwrap();
    assert!(!s.items[0].sale_below_replacement);

    // Summasiz sotuv — sotuv narxi × miqdor: 1,5 kg × 14 000 = 21 000.
    let s = app
        .kk_stock_move(
            &kk,
            &id,
            mv("SALE", "1,5", None, Some("CARD"), "2026-11-20"),
        )
        .unwrap();
    assert_eq!(
        minor(s.items[0].moves[0].amount.as_ref().unwrap()),
        2_100_000
    );
    assert_eq!(s.items[0].qty, "68,5");
}

#[test]
fn oversell_and_backdated_moves_are_rejected() {
    let (app, kk) = app_with(clock("2026-11-20T18:00:00+05:00"));
    let id = sugar(&app, &kk, "AVERAGE");
    let err = app
        .kk_stock_move(
            &kk,
            &id,
            mv("SALE", "71", Some("1 000"), Some("CASH"), "2026-11-20"),
        )
        .unwrap_err();
    assert_eq!(
        (err.code.as_str(), err.field.as_deref()),
        ("INSUFFICIENT_STOCK", Some("qty"))
    );
    // 2-noyabrda 100 kg hisobdan chiqarilsa, 3-noyabrdagi 80 kg sotuvga yetmaydi.
    let mut w = mv("WRITE_OFF", "100", None, None, "2026-11-02");
    w.reason = Some("Namlangan".into());
    assert_eq!(
        app.kk_stock_move(&kk, &id, w.clone()).unwrap_err().code,
        "INSUFFICIENT_STOCK"
    );
    w.qty = "60".into();
    let s = app.kk_stock_move(&kk, &id, w).unwrap();
    assert_eq!(s.items[0].qty, "10");
    let mut no_reason = mv("WRITE_OFF", "1", None, None, "2026-11-20");
    no_reason.reason = Some("  ".into());
    assert_eq!(
        app.kk_stock_move(&kk, &id, no_reason)
            .unwrap_err()
            .field
            .as_deref(),
        Some("reason")
    );
    assert_eq!(
        app.kk_stock_move(&kk, &id, mv("SALE", "1", None, Some("CASH"), "2026-11-20"))
            .unwrap_err()
            .field
            .as_deref(),
        Some("amount")
    );
    assert_eq!(
        app.kk_stock_move(&kk, &id, mv("SALE", "1", Some("1 000"), None, "2026-11-20"))
            .unwrap_err()
            .field
            .as_deref(),
        Some("wallet")
    );
    assert_eq!(
        app.kk_stock_move(
            &kk,
            &id,
            mv("PURCHASE", "0,0001", Some("1"), None, "2026-11-20")
        )
        .unwrap_err()
        .code,
        "INVALID_QTY"
    );
}

/// SPEC 4.4: oxirgi sotuvdan 90 kundan ko'p o'tsa — muzlagan; bosh sahifada qayta tiklash narxida.
#[test]
fn frozen_goods_after_threshold() {
    let c = clock("2026-11-20T18:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    sugar(&app, &kk, "AVERAGE");
    let s = app.kk_add_item(&kk, item("Tuz", "AVERAGE")).unwrap();
    let salt = s.items.iter().find(|i| i.name == "Tuz").unwrap().id.clone();
    app.kk_stock_move(
        &kk,
        &salt,
        mv("PURCHASE", "10", Some("30 000"), None, "2026-11-01"),
    )
    .unwrap();
    assert_eq!(app.kk_stock(&kk).unwrap().frozen_count, 0);

    at(&c, "2027-02-01T18:00:00+05:00");
    let s = app.kk_stock(&kk).unwrap();
    let tuz = s.items.iter().find(|i| i.name == "Tuz").unwrap();
    let shakar = s.items.iter().find(|i| i.name == "Shakar").unwrap();
    // Tuz hech sotilmagan: birinchi xariddan 92 kun; shakar oxirgi sotuvdan 90 kun — hali emas.
    assert!(tuz.frozen && !shakar.frozen);
    assert_eq!(shakar.last_sale_on.as_deref(), Some("2026-11-03"));
    assert_eq!((s.frozen_count, minor(&s.frozen_value)), (1, 3_000_000));

    at(&c, "2027-02-02T18:00:00+05:00");
    let s = app.kk_stock(&kk).unwrap();
    // Shakar: 70 kg × 12 500 (oxirgi xarid) = 875 000.
    assert_eq!((s.frozen_count, minor(&s.frozen_value)), (2, 90_500_000));
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(
        (o.stock_frozen_count, minor(&o.stock_frozen_value)),
        (2, 90_500_000)
    );
}

#[test]
fn closed_cash_day_and_month_guard_stock_moves() {
    let c = clock("2026-11-20T18:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    let id = sugar(&app, &kk, "AVERAGE");
    app.kk_close_cash_day(
        &kk,
        KkCashCloseInput {
            day: "2026-11-20".into(),
            counted: "1 120 000".into(),
            reason: None,
            note: None,
        },
    )
    .unwrap();
    assert_eq!(
        app.kk_stock_move(
            &kk,
            &id,
            mv("SALE", "1", Some("14 000"), Some("CASH"), "2026-11-20")
        )
        .unwrap_err()
        .code,
        "CASH_DAY_CLOSED"
    );
    // Karta va tovar-faqat harakatlar erkin.
    app.kk_stock_move(
        &kk,
        &id,
        mv("SALE", "1", Some("14 000"), Some("CARD"), "2026-11-20"),
    )
    .unwrap();

    // «Hisob kuni»: chiqim = sotilgan tovar tannarxi (xarid emas).
    at(&c, "2026-12-02T10:00:00+05:00");
    let d = app.kk_close_draft(&kk, None).unwrap();
    assert_eq!(minor(&d.revenue), 113_400_000);
    assert_eq!(minor(&d.expenses), 96_000_000 + 1_200_000);
    app.kk_close_month(
        &kk,
        KkCloseInput {
            period_start: "2026-11-01".into(),
            carry_overdraw: false,
            explanation: None,
        },
    )
    .unwrap();
    assert_eq!(
        app.kk_stock_move(
            &kk,
            &id,
            mv("PURCHASE", "1", Some("12 000"), None, "2026-11-25")
        )
        .unwrap_err()
        .code,
        "PERIOD_CLOSED"
    );
}
