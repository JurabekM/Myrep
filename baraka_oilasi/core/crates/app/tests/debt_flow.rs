#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U8: qarz inventari, haqiqiy narx, «to'xta va o'yla», bergan qarzlar, tilxat → jurnal.

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
        &DbKey::from_bytes([4; 32]),
        "dev-desktop",
        clock,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            income_rhythm: None,
            debts_declared: false,
            household_name: "Ravshan akaning oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![NewMemberInput {
                display_name: "Karim".into(),
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

fn manual_debt(creditor: &str, principal: &str, lines: Vec<ScheduleLineInput>) -> NewDebtInput {
    NewDebtInput {
        creditor_type: "RELATIVE".into(),
        creditor: creditor.into(),
        reason: Some("toʻy".into()),
        currency: "UZS".into(),
        principal: principal.into(),
        original_principal: None,
        paid_before: None,
        plan_kind: "MANUAL".into(),
        annual_bp: None,
        markup: None,
        months: None,
        first_date: None,
        schedule: lines,
        early_repayment_terms: None,
        prepayment_fee_bp: None,
        is_new: false,
        borrow_check: None,
    }
}

fn bank_loan() -> NewDebtInput {
    NewDebtInput {
        creditor_type: "BANK".into(),
        creditor: "Avtokredit".into(),
        reason: Some("mashina".into()),
        plan_kind: "ANNUITY".into(),
        annual_bp: Some(2400),
        months: Some(14),
        first_date: Some("05.11.2026".into()),
        schedule: vec![],
        ..manual_debt("", "39 000 000", vec![])
    }
}

fn income(app: &App, uy: &str, amount: &str, on: &str) {
    app.record_income(
        uy,
        NewIncomeInput {
            amount: amount.into(),
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

#[test]
fn karim_true_cost_and_goal_equivalent() {
    let (app, uy) = app_at("2026-10-15T09:00:00+05:00");
    app.add_goal(
        &uy,
        NewGoalInput {
            title: "Qizimning kontrakti".into(),
            target: "12 000 000".into(),
            currency: "UZS".into(),
        },
    )
    .unwrap();
    let mut input = manual_debt(
        "Qoʻshni Toʻlqin aka",
        "9 000 000",
        vec![
            line("15.11.2026", "3 000 000"),
            line("15.12.2026", "3 000 000"),
            line("15.01.2027", "3 000 000"),
        ],
    );
    input.original_principal = Some("40 000 000".into());
    input.paid_before = Some("51 000 000".into());
    let d = app.add_debt(&uy, input).unwrap();
    assert!(!d.is_ribo);
    assert_eq!(d.true_cost.total_cost.minor, "6000000000");
    assert_eq!(d.true_cost.overpay.minor, "2000000000");
    assert_eq!(d.true_cost.overpay_percent, "33,33");
    assert_eq!(d.true_cost.goal_equivalents[0].percent, "166,67");
    assert_eq!(d.status_info.remaining.minor, "900000000");
    assert_eq!(d.status_info.next_due.as_ref().unwrap().date, "2026-11-15");
    assert_eq!(d.status_info.payoff_date.as_deref(), Some("2027-01-15"));
    assert_eq!(d.status_info.reminder, None);
}

#[test]
fn plan_is_mandatory_and_nothing_is_saved_without_it() {
    let (app, uy) = app_at("2026-10-15T09:00:00+05:00");
    let err = app
        .add_debt(&uy, manual_debt("Akam", "1 000 000", vec![]))
        .unwrap_err();
    assert_eq!(err.code, "SCHEDULE_REQUIRED");
    let err = app
        .add_debt(
            &uy,
            manual_debt("Akam", "1 000 000", vec![line("15.11.2026", "900 000")]),
        )
        .unwrap_err();
    assert_eq!(err.code, "SCHEDULE_SUM_MISMATCH");
    let mut bank = bank_loan();
    bank.months = None;
    assert_eq!(app.add_debt(&uy, bank).unwrap_err().code, "INVALID_TERM");
    assert!(app.debts_overview(&uy).unwrap().debts.is_empty());
}

#[test]
fn new_ribo_loan_requires_friction_and_raises_load_warning() {
    let (app, uy) = app_at("2026-11-20T09:00:00+05:00");
    // Oylik yuk daromadsiz noma'lum.
    let mut loan = bank_loan();
    loan.is_new = true;
    assert_eq!(
        app.add_debt(&uy, loan.clone()).unwrap_err().code,
        "BORROW_CHECK_REQUIRED"
    );
    loan.borrow_check = Some(BorrowCheckInput {
        need: "LUXURY".into(),
        alternatives: vec!["SELL_ITEM".into(), "QOROVUL".into(), "SELL_ITEM".into()],
    });
    let preview = app.preview_borrow_check(&uy, loan.clone()).unwrap();
    assert_eq!(
        preview.warnings,
        ["RIBO", "LUXURY", "ALTERNATIVE_AVAILABLE", "LOAD_UNKNOWN"]
    );
    assert_eq!(preview.plan.len(), 14);
    assert_eq!(preview.true_cost.overpay.minor, "610067573");

    // 3 oylik o'rtacha daromad 12 mln: 3 221 476,84 / 12 000 000 = 26,85% (+ shu oyda to'lov yo'q).
    for on in ["2026-08-10", "2026-09-10", "2026-10-10"] {
        income(&app, &uy, "12 000 000", on);
    }
    let preview = app.preview_borrow_check(&uy, loan.clone()).unwrap();
    assert_eq!(preview.projected_load_percent.as_deref(), Some("26,85"));
    assert!(!preview.warnings.contains(&"LOAD_HIGH".to_string()));

    let d = app.add_debt(&uy, loan.clone()).unwrap();
    assert!(d.is_ribo);
    assert_eq!(
        d.borrow_warnings,
        ["RIBO", "LUXURY", "ALTERNATIVE_AVAILABLE"]
    );
    // 05.11 dagi to'lov yozilmagan — kechikkan.
    assert_eq!(d.status_info.reminder.as_deref(), Some("OVERDUE"));
    assert_eq!(d.status_info.overdue.minor, "322147684");
    let o = app.debts_overview(&uy).unwrap();
    assert!(o.has_ribo_debt);
    assert_eq!(o.total_debt[0].minor, "4510067573");
    assert_eq!(o.monthly_income.as_ref().unwrap().minor, "1200000000");
    // Noyabr davrida bitta to'lov (05.11): 322 147 684 tiyin → 26,85%.
    assert_eq!(o.monthly_due.minor, "322147684");
    assert_eq!(o.load_percent.as_deref(), Some("26,85"));

    // Ikkinchi shunday kredit yukni 30% dan oshiradi.
    let preview = app.preview_borrow_check(&uy, loan).unwrap();
    assert!(preview.warnings.contains(&"LOAD_HIGH".to_string()));
}

#[test]
fn four_plan_kinds_true_cost() {
    let (app, uy) = app_at("2026-10-15T09:00:00+05:00");
    let mut diff = bank_loan();
    diff.plan_kind = "DIFFERENTIATED".into();
    diff.principal = "12 000 000".into();
    diff.months = Some(6);
    let d = app.add_debt(&uy, diff).unwrap();
    assert_eq!(d.true_cost.overpay.minor, "84000000");
    let shop = NewDebtInput {
        creditor_type: "SHOP".into(),
        creditor: "Telefon doʻkoni".into(),
        plan_kind: "FIXED_MARKUP".into(),
        principal: "6 000 000".into(),
        markup: Some("1 200 000".into()),
        months: Some(12),
        first_date: Some("2026-10-20".into()),
        ..manual_debt("", "0", vec![])
    };
    let s = app.add_debt(&uy, shop).unwrap();
    assert!(s.is_ribo);
    assert_eq!(s.plan.len(), 12);
    assert_eq!(s.plan[0].amount.minor, "60000000");
    assert_eq!(s.true_cost.overpay_percent, "16,67");
    assert_eq!(s.status_info.reminder.as_deref(), None);
    let a = app.add_debt(&uy, bank_loan()).unwrap();
    assert_eq!(a.true_cost.overpay.minor, "610067573");
}

#[test]
fn receivable_has_no_interest_and_reminds_politely() {
    let (app, uy) = app_at("2026-10-29T09:00:00+05:00");
    let bad = serde_json::json!({
        "debtor": "Qoʻshni", "currency": "UZS", "amount": "200 000", "lentOn": null,
        "schedule": [], "note": null, "interestBp": 500
    });
    assert!(serde_json::from_value::<NewReceivableInput>(bad).is_err());
    let r = app
        .add_receivable(
            &uy,
            NewReceivableInput {
                debtor: "Qoʻshni".into(),
                currency: "UZS".into(),
                amount: "200 000".into(),
                lent_on: Some("01.10.2026".into()),
                schedule: vec![line("31.10.2026", "200 000")],
                note: None,
            },
        )
        .unwrap();
    assert_eq!(r.status_info.reminder.as_deref(), Some("DUE_SOON"));
    let p = app
        .record_repayment(
            &uy,
            "RECEIVABLE",
            &r.id,
            RepaymentInput {
                amount: "200 000".into(),
                date: None,
                is_prepayment: false,
                note: None,
                contributor_id: None,
            },
        )
        .unwrap();
    assert_eq!(p.repayment.journal_short_code, None);
    assert!(p.closed && !p.debt_free);
    let o = app.debts_overview(&uy).unwrap();
    assert_eq!(o.receivables[0].status, "CLOSED");
    assert!(o.total_receivable.is_empty());
}

fn receipt(direction: &str) -> IssueLoanReceiptInput {
    IssueLoanReceiptInput {
        direction: direction.into(),
        creditor_type: Some("RELATIVE".into()),
        reason: Some("davolanish".into()),
        receipt: LoanReceiptInput {
            lender: "Gʻayrat Oʻgʻilov".into(),
            borrower: "Karim Rahmonov".into(),
            amount: "2 000 000".into(),
            currency: "UZS".into(),
            issued_on: Some("15.10.2026".into()),
            place: "Toshkent, Chorsu".into(),
            schedule: vec![
                line("15.11.2026", "1 200 000"),
                line("15.12.2026", "800 000"),
            ],
            witnesses: vec!["Hasan Yusupov".into()],
            note: None,
        },
        is_new: true,
        borrow_check: Some(BorrowCheckInput {
            need: "NECESSITY".into(),
            alternatives: vec![],
        }),
    }
}

#[test]
fn receipt_links_agreement_journal_and_debt() {
    let (app, uy) = app_at("2026-10-15T09:00:00+05:00");
    let mut no_check = receipt("BORROWED");
    no_check.borrow_check = None;
    assert_eq!(
        app.issue_loan_receipt(&uy, no_check).unwrap_err().code,
        "BORROW_CHECK_REQUIRED"
    );
    let issued = app.issue_loan_receipt(&uy, receipt("BORROWED")).unwrap();
    assert_eq!(issued.record_type, "DEBT");
    let o = app.debts_overview(&uy).unwrap();
    let d = &o.debts[0];
    assert_eq!(d.creditor, "Gʻayrat Oʻgʻilov");
    assert_eq!(
        d.agreement_id.as_deref(),
        Some(issued.agreement_id.as_str())
    );
    assert_eq!(d.plan.len(), 2);

    let j = app.journal(&uy, &issued.agreement_id).unwrap();
    assert_eq!(j.len(), 1);
    assert_eq!(j[0].kind, "OPENING_BALANCE");
    assert_eq!(j[0].short_code, issued.short_code);

    let pay = |amount: &str| {
        app.record_repayment(
            &uy,
            "DEBT",
            &issued.record_id,
            RepaymentInput {
                amount: amount.into(),
                date: Some("2026-11-14".into()),
                is_prepayment: false,
                note: Some("Birinchi toʻlov".into()),
                contributor_id: None,
            },
        )
    };
    let p1 = pay("1 200 000").unwrap();
    assert!(p1.repayment.journal_short_code.is_some());
    assert_eq!(
        pay("800 001").unwrap_err().code,
        "PAYMENT_EXCEEDS_REMAINING"
    );

    let pdf = app.loan_receipt_pdf(&uy, &issued.agreement_id).unwrap();
    assert!(pdf.starts_with(b"%PDF"));

    pay("800 000").unwrap();
    assert_eq!(pay("1").unwrap_err().code, "ALREADY_CLOSED");
    let chain = app.verify_journal(&uy, &issued.agreement_id).unwrap();
    assert!(chain.ok);
    assert_eq!(chain.entries, 3);
    let j = app.journal(&uy, &issued.agreement_id).unwrap();
    assert_eq!(
        j.iter().map(|e| e.kind.as_str()).collect::<Vec<_>>(),
        ["OPENING_BALANCE", "REPAYMENT", "REPAYMENT"]
    );
    let o = app.debts_overview(&uy).unwrap();
    assert_eq!(o.debts[0].status, "CLOSED");
    assert_eq!(
        o.debts[0].payments[1].journal_short_code.as_deref(),
        chain.short_code.as_deref()
    );
}

#[test]
fn lent_receipt_creates_receivable() {
    let (app, uy) = app_at("2026-10-15T09:00:00+05:00");
    let mut input = receipt("LENT");
    input.borrow_check = None;
    let issued = app.issue_loan_receipt(&uy, input).unwrap();
    assert_eq!(issued.record_type, "RECEIVABLE");
    let o = app.debts_overview(&uy).unwrap();
    assert!(o.debts.is_empty());
    assert_eq!(o.receivables[0].debtor, "Karim Rahmonov");
    assert_eq!(o.total_receivable[0].minor, "200000000");
    let mut bad = receipt("SIDEWAYS");
    bad.borrow_check = None;
    assert_eq!(
        app.issue_loan_receipt(&uy, bad).unwrap_err().code,
        "INVALID_DIRECTION"
    );
}
