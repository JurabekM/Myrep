#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U9: `DEBT_RECOVERY` 70/20/10, rejalovchi, «Qarzsiz kun», tartib, to'lovchilar, buyumlar.

use std::sync::Arc;

use baraka_app::*;
use chrono::{DateTime, Utc};

fn app_at(at: &str) -> (App, String) {
    let clock = Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339(at)
            .unwrap()
            .with_timezone(&Utc),
    ));
    let app = App::open_in_memory(
        &DbKey::from_bytes([5; 32]),
        "dev-desktop",
        clock,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Anvarlar".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![NewMemberInput {
                display_name: "Anvar".into(),
                role: "ADULT".into(),
            }],
        })
        .unwrap();
    let uy = h.spaces[0].id.clone();
    (app, uy)
}

fn line(date: &str, amount: &str) -> ScheduleLineInput {
    ScheduleLineInput {
        date: date.into(),
        amount: amount.into(),
    }
}

fn debt(creditor: &str, kind: &str) -> NewDebtInput {
    NewDebtInput {
        creditor_type: "BANK".into(),
        creditor: creditor.into(),
        reason: None,
        currency: "UZS".into(),
        principal: "39 000 000".into(),
        original_principal: None,
        paid_before: None,
        plan_kind: kind.into(),
        annual_bp: Some(2400),
        markup: None,
        months: Some(14),
        first_date: Some("05.11.2026".into()),
        schedule: vec![],
        early_repayment_terms: None,
        prepayment_fee_bp: None,
        is_new: false,
        borrow_check: None,
    }
}

fn toy() -> NewDebtInput {
    NewDebtInput {
        creditor_type: "RELATIVE".into(),
        principal: "9 000 000".into(),
        annual_bp: None,
        months: None,
        first_date: Some("15.10.2026".into()),
        schedule: vec![
            line("15.11.2026", "3 000 000"),
            line("15.12.2026", "3 000 000"),
            line("15.01.2027", "3 000 000"),
        ],
        ..debt("Toʻlqin aka", "MANUAL")
    }
}

fn pay(amount: &str, date: &str, prepayment: bool) -> RepaymentInput {
    RepaymentInput {
        amount: amount.into(),
        date: Some(date.into()),
        is_prepayment: prepayment,
        note: None,
        contributor_id: None,
    }
}

fn income(app: &App, uy: &str, on: &str) {
    app.record_income(
        uy,
        NewIncomeInput {
            amount: "12 000 000".into(),
            source: "Oylik".into(),
            channel: "CARD".into(),
            member_id: None,
            occurred_on: Some(on.into()),
            source_type: None,
            note: None,
        },
    )
    .unwrap();
}

fn recovery(h: i32, e: i32, s: i32) -> BudgetModeInput {
    BudgetModeInput {
        mode: "DEBT_RECOVERY".into(),
        household_bp: h,
        extra_debt_bp: e,
        savings_bp: s,
    }
}

#[test]
fn recovery_mode_70_20_10_and_planner_match_vectors() {
    let (app, uy) = app_at("2026-11-01T09:00:00+05:00");
    let m = app.budget_mode(&uy).unwrap();
    assert_eq!((m.mode.as_str(), m.suggested), ("STANDARD", false));
    assert_eq!(
        app.set_budget_mode(&uy, recovery(7000, 2000, 1000))
            .unwrap_err()
            .code,
        "NO_ACTIVE_DEBT"
    );
    let mut loan = debt("Avtokredit", "ANNUITY");
    loan.prepayment_fee_bp = Some(100);
    app.add_debt(&uy, loan).unwrap();
    assert!(app.budget_mode(&uy).unwrap().suggested);
    for on in ["2026-08-10", "2026-09-10", "2026-10-10"] {
        income(&app, &uy, on);
    }
    // Jamg'arma ulushi 0 ga tushirilmaydi.
    assert_eq!(
        app.set_budget_mode(&uy, recovery(7000, 3000, 0))
            .unwrap_err()
            .code,
        "SAVINGS_SHARE_TOO_LOW"
    );
    assert_eq!(
        app.set_budget_mode(&uy, recovery(7000, 2000, 900))
            .unwrap_err()
            .code,
        "SPLIT_NOT_100"
    );
    let m = app
        .set_budget_mode(&uy, recovery(7000, 2000, 1000))
        .unwrap();
    assert_eq!(m.mode, "DEBT_RECOVERY");
    assert_eq!(m.household.minor, "840000000");
    assert_eq!(m.extra_debt.minor, "240000000");
    assert_eq!(m.savings.minor, "120000000");
    // Noyabrdagi majburiy to'lov 70% ichida.
    assert_eq!(m.mandatory_debt_payments.minor, "322147684");
    assert_eq!(m.household_after_debts.minor, "517852316");

    // Rejalovchi: 20% ulush (2,4 mln) avtomatik; vektor plan-all-001 dagi avtokredit bilan bir xil.
    let p = app
        .payoff_planner(
            &uy,
            PlannerInput {
                extra_per_month: None,
            },
        )
        .unwrap();
    assert_eq!(p.extra_source, "RECOVERY_SHARE");
    assert_eq!(p.extra_per_month.minor, "240000000");
    assert_eq!((p.base.months, p.accelerated.months), (14, 8));
    assert_eq!(p.base.payoff_date.as_deref(), Some("2027-12-05"));
    assert_eq!(p.accelerated.payoff_date.as_deref(), Some("2027-06-05"));
    assert_eq!(p.months_saved, 6);
    assert_eq!(p.interest_saved.minor, "268310688");
    assert_eq!(p.accelerated.fees.minor, "16800000");
    assert_eq!(p.net_saved.minor, "251510688");
    assert_eq!(p.timeline.len(), 14);
    let o = app.debts_overview(&uy).unwrap();
    assert_eq!(o.debt_free_date.as_deref(), Some("2027-12-05"));
    assert_eq!(o.debt_free_date_with_plan.as_deref(), Some("2027-06-05"));
    assert_eq!(p.timeline[13].accelerated_balance.minor, "0");
    assert_eq!(p.schedule.len(), 8);
    let manual = app
        .payoff_planner(
            &uy,
            PlannerInput {
                extra_per_month: Some("1 600 000".into()),
            },
        )
        .unwrap();
    assert_eq!(
        (manual.extra_source.as_str(), manual.accelerated.months),
        ("MANUAL", 9)
    );
}

#[test]
fn bank_prepayment_shortens_term_and_debt_free_day_moves() {
    let (app, uy) = app_at("2027-01-10T09:00:00+05:00");
    let d = app.add_debt(&uy, debt("Avtokredit", "ANNUITY")).unwrap();
    assert_eq!(d.status_info.payoff_date.as_deref(), Some("2027-12-05"));
    for (a, on, pre) in [
        ("3 221 476,84", "2026-11-05", false),
        ("3 221 476,84", "2026-12-05", false),
    ] {
        app.record_repayment(&uy, "DEBT", &d.id, pay(a, on, pre))
            .unwrap();
    }
    // Asosiy qarzdan ko'p muddatidan oldingi to'lov — rad etiladi.
    assert_eq!(
        app.record_repayment(&uy, "DEBT", &d.id, pay("34 068 216,79", "2026-12-20", true))
            .unwrap_err()
            .code,
        "PAYMENT_EXCEEDS_REMAINING"
    );
    app.record_repayment(&uy, "DEBT", &d.id, pay("5 000 000", "2026-12-20", true))
        .unwrap();
    let o = app.debts_overview(&uy).unwrap();
    let d = &o.debts[0];
    // Vektor payoff-004: qoldiq 29 068 216,78; «Qarzsiz kun» bir oy oldinga siljidi.
    assert_eq!(d.balance.minor, "2906821678");
    assert_eq!(d.status_info.payoff_date.as_deref(), Some("2027-11-05"));
    assert_eq!(o.debt_free_date.as_deref(), Some("2027-11-05"));
    assert_eq!(d.status_info.next_due.as_ref().unwrap().date, "2027-01-05");
    // Haqiqiy narx tejalgan foizni ham ko'rsatadi: 610 067 573 dan kam.
    let overpay: i64 = d.true_cost.overpay.minor.parse().unwrap();
    assert!(overpay < 610_067_573);
}

#[test]
fn last_debt_closed_returns_mode_and_offers_freed_money() {
    let (app, uy) = app_at("2026-11-20T09:00:00+05:00");
    let d = app.add_debt(&uy, toy()).unwrap();
    app.set_budget_mode(&uy, recovery(7000, 2000, 1000))
        .unwrap();
    let r = app
        .record_repayment(&uy, "DEBT", &d.id, pay("3 000 000", "2026-11-15", false))
        .unwrap();
    assert!(!r.closed && !r.debt_free && !r.mode_returned);
    // Muddatidan oldingi to'lov rejaning oxiridan yopiladi: «Qarzsiz kun» 15.12.2026.
    app.record_repayment(&uy, "DEBT", &d.id, pay("3 000 000", "2026-11-18", true))
        .unwrap();
    let o = app.debts_overview(&uy).unwrap();
    assert_eq!(
        o.debts[0].status_info.payoff_date.as_deref(),
        Some("2026-12-15")
    );
    assert_eq!(o.budget_mode, "DEBT_RECOVERY");
    let r = app
        .record_repayment(&uy, "DEBT", &d.id, pay("3 000 000", "2026-11-20", false))
        .unwrap();
    assert!(r.closed && r.debt_free && r.mode_returned);
    assert_eq!(r.freed_monthly.unwrap().minor, "300000000");
    let m = app.budget_mode(&uy).unwrap();
    assert_eq!((m.mode.as_str(), m.suggested), ("STANDARD", false));
    // Ulushlar saqlanib qoladi (keyingi safar uchun).
    assert_eq!(m.savings_bp, 1000);
    assert_eq!(app.debts_overview(&uy).unwrap().debt_free_date, None);
}

#[test]
fn order_items_and_contributors() {
    let (app, uy) = app_at("2026-11-01T09:00:00+05:00");
    let avto = app.add_debt(&uy, debt("Avtokredit", "ANNUITY")).unwrap();
    let t = app.add_debt(&uy, toy()).unwrap();
    let plan = |extra: &str| {
        app.payoff_planner(
            &uy,
            PlannerInput {
                extra_per_month: Some(extra.into()),
            },
        )
        .unwrap()
    };
    // Standart: foizli qarz birinchi.
    let p = plan("2 400 000");
    assert_eq!(p.debts[0].id, avto.id);
    assert!(!p.debts[0].manual_order);
    app.set_debt_order(&uy, vec![t.id.clone(), avto.id.clone()])
        .unwrap();
    let p = plan("2 400 000");
    assert_eq!(
        (
            p.debts[0].id.as_str(),
            p.debts[0].order,
            p.debts[0].manual_order
        ),
        (t.id.as_str(), 1, true)
    );
    // Vektor plan-all-002: to'y qarzi birinchi bo'lsa, avtokredit 9 oyda.
    assert_eq!(p.debts[1].accelerated_payoff.as_deref(), Some("2027-07-05"));
    app.reset_debt_order(&uy).unwrap();
    assert_eq!(plan("0").debts[0].id, avto.id);

    // To'lovchi: o'g'il Sanjar oyiga 1 mln.
    let c = app
        .add_contributor(
            &uy,
            &t.id,
            NewContributorInput {
                name: "Sanjar".into(),
                monthly_share: Some("1 000 000".into()),
            },
        )
        .unwrap();
    let mut p1 = pay("1 000 000", "2026-11-10", false);
    p1.contributor_id = Some(c.id.clone());
    app.record_repayment(&uy, "DEBT", &t.id, p1).unwrap();
    let mut bad = pay("1 000 000", "2026-11-10", false);
    bad.contributor_id = Some(c.id.clone());
    assert_eq!(
        app.record_repayment(&uy, "DEBT", &avto.id, bad)
            .unwrap_err()
            .code,
        "NOT_FOUND"
    );
    let o = app.debts_overview(&uy).unwrap();
    let toy_dto = o.debts.iter().find(|d| d.id == t.id).unwrap();
    assert_eq!(toy_dto.contributors[0].paid.minor, "100000000");

    // Sotiladigan buyum: pul bir bosishda to'y qarziga.
    let item = app
        .add_sellable_item(
            &uy,
            NewSellableItemInput {
                title: "Eski muzlatkich".into(),
                estimated: "2 500 000".into(),
                currency: "UZS".into(),
            },
        )
        .unwrap();
    let sold = app
        .sell_item(
            &uy,
            &item.id,
            SellItemInput {
                price: "2 000 000".into(),
                date: Some("2026-11-12".into()),
                debt_id: Some(t.id.clone()),
            },
        )
        .unwrap();
    assert_eq!(sold.item.status, "SOLD");
    let r = sold.repayment.unwrap();
    assert!(r.repayment.is_prepayment && !r.closed);
    assert_eq!(r.repayment.amount.minor, "200000000");
    let o = app.debts_overview(&uy).unwrap();
    let toy_dto = o.debts.iter().find(|d| d.id == t.id).unwrap();
    // 9 − 1 (odatiy) − 2 (buyum, oxiridan) = 6 mln; oxirgi to'lov 15.01 da 1 mln qoldi.
    assert_eq!(toy_dto.status_info.remaining.minor, "600000000");
    assert_eq!(toy_dto.plan.len(), 3);
    assert_eq!(
        app.sell_item(
            &uy,
            &item.id,
            SellItemInput {
                price: "1".into(),
                date: None,
                debt_id: None
            }
        )
        .unwrap_err()
        .code,
        "ALREADY_SOLD"
    );
    assert_eq!(app.sellable_items(&uy).unwrap()[0].status, "SOLD");
}
