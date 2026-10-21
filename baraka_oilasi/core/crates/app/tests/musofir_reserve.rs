#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! M4 — qorovul pul, ish boshlash summasi va qaror natijasi (docs/musofir/SPEC.md 6.4, 6.6).

use std::sync::Arc;

use baraka_app::*;
use chrono::{DateTime, Utc};

fn setup() -> (App, String, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
        "dev-rustam",
        Arc::new(FixedClock::new(
            DateTime::parse_from_rfc3339("2026-10-18T09:00:00+05:00")
                .unwrap()
                .with_timezone(&Utc),
        )),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Rustam akaning oilasi".into(),
            device_name: "Rustamning telefoni".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "MUSOFIR".into()],
            members: vec![NewMemberInput {
                display_name: "Rustam".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let id = |k: &str| h.spaces.iter().find(|s| s.kind == k).unwrap().id.clone();
    let (mf, uy) = (id("MUSOFIR"), id("UY"));
    app.mf_set_settings(&mf, settings("120 000 000")).unwrap();
    (app, mf, uy)
}

fn settings(target: &str) -> MfSettingsInput {
    MfSettingsInput {
        country: Some("Koreya".into()),
        work_currency: "KRW".into(),
        share_percent: "20".into(),
        target: Some(target.into()),
        return_on: Some("2027-12-01".into()),
    }
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

fn mv(kind: &str, amount: &str, on: &str, note: Option<&str>) -> MfMoveInput {
    MfMoveInput {
        kind: kind.into(),
        amount: amount.into(),
        fee: None,
        received: None,
        occurred_on: Some(on.into()),
        note: note.map(Into::into),
        purposes: None,
    }
}

fn salary(app: &App, mf: &str, on: &str) -> (i64, i64) {
    let r = app
        .mf_record_income(
            mf,
            MfIncomeInput {
                kind: "SALARY".into(),
                amount: "2 600 000".into(),
                channel: "CARD".into(),
                occurred_on: Some(on.into()),
                note: None,
            },
        )
        .unwrap();
    assert_eq!(minor(&r.suggested_share), 520_000);
    (minor(&r.suggested_reserve), minor(&r.suggested_fund))
}

fn expense(app: &App, mf: &str, amount: &str, on: &str) {
    let cat = app.categories(mf).unwrap()[0].id.clone();
    app.mf_record_expense(
        mf,
        MfExpenseInput {
            amount: amount.into(),
            category_id: cat,
            channel: "CARD".into(),
            occurred_on: Some(on.into()),
            note: None,
        },
    )
    .unwrap();
}

fn plan(months: Option<u32>, startup: Option<&str>, idea: Option<&str>) -> MfPlanInput {
    MfPlanInput {
        reserve_months: months,
        startup: startup.map(Into::into),
        startup_idea_id: idea.map(Into::into),
    }
}

#[test]
fn share_fills_reserve_first_then_fund() {
    let (app, mf, _) = setup();
    // Iyul: tarix yo'q — ulush jamg'armaga.
    assert_eq!(salary(&app, &mf, "2026-07-25"), (0, 520_000));
    expense(&app, &mf, "810 000", "2026-07-26");
    app.mf_record_move(&mf, mv("FUND_IN", "520 000", "2026-07-25", None))
        .unwrap();
    // Avgust: maqsad 810 000, qorovul bo'sh — ulush hammasi qorovulga.
    assert_eq!(salary(&app, &mf, "2026-08-25"), (520_000, 0));
    app.mf_record_move(&mf, mv("RESERVE_IN", "520 000", "2026-08-25", None))
        .unwrap();
    expense(&app, &mf, "790 000", "2026-08-26");
    // Sentyabr: maqsad 800 000, qoldiq 520 000 — 280 000 qorovulga, 240 000 jamg'armaga.
    assert_eq!(salary(&app, &mf, "2026-09-25"), (280_000, 240_000));
    app.mf_record_move(&mf, mv("RESERVE_IN", "280 000", "2026-09-25", None))
        .unwrap();
    app.mf_record_move(&mf, mv("FUND_IN", "240 000", "2026-09-25", None))
        .unwrap();
    expense(&app, &mf, "815 000", "2026-09-26");

    // Oktyabr: o'rtacha 805 000 (rs-001 kabi), qoldiq 800 000 — 99,38 %.
    let o = app.mf_overview(&mf, None).unwrap();
    let r = o.reserve.unwrap();
    assert_eq!(
        (
            minor(&r.balance),
            r.status.as_str(),
            r.months,
            r.months_used
        ),
        (800_000, "PARTIAL", 1, 3)
    );
    assert_eq!(minor(r.target.as_ref().unwrap()), 805_000);
    assert_eq!(minor(r.gap.as_ref().unwrap()), 5_000);
    assert_eq!(r.progress_percent.as_deref(), Some("99,38"));
    assert_eq!(salary(&app, &mf, "2026-10-10"), (5_000, 515_000));
    app.mf_record_move(&mf, mv("RESERVE_IN", "5 000", "2026-10-10", None))
        .unwrap();
    let o = app
        .mf_record_move(&mf, mv("FUND_IN", "515 000", "2026-10-10", None))
        .unwrap();
    let m = o.month.unwrap();
    assert_eq!(minor(&m.saved_net), 520_000);
    assert_eq!(minor(&m.share_gap), 0);
    assert_eq!(o.reserve.unwrap().status, "FULL");

    // Kasal bo'ldi: qorovul puldan — sabab bilan, qoldiqdan oshmaydi; ulush kamaymaydi.
    assert_eq!(
        err(app.mf_record_move(&mf, mv("RESERVE_OUT", "300 000", "2026-10-15", None))),
        "REASON_REQUIRED"
    );
    assert_eq!(
        err(app.mf_record_move(
            &mf,
            mv("RESERVE_OUT", "900 000", "2026-10-15", Some("Kasalxona"))
        )),
        "RESERVE_INSUFFICIENT"
    );
    let o = app
        .mf_record_move(
            &mf,
            mv("RESERVE_OUT", "300 000", "2026-10-15", Some("Kasalxona")),
        )
        .unwrap();
    let m = o.month.unwrap();
    assert_eq!(minor(&m.reserve_out), 300_000);
    assert_eq!(minor(&m.saved_net), 520_000);
    assert!(m.warnings.is_empty(), "{:?}", m.warnings);
    assert!(o.entries.iter().any(|e| e.kind == "RESERVE_OUT"));
    let r = o.reserve.unwrap();
    assert_eq!((minor(&r.balance), r.status.as_str()), (505_000, "PARTIAL"));

    // 2 oylik maqsad.
    assert_eq!(
        err(app.mf_set_plan(&mf, plan(Some(4), None, None))),
        "INVALID_MONTHS"
    );
    let r = app
        .mf_set_plan(&mf, plan(Some(2), None, None))
        .unwrap()
        .reserve
        .unwrap();
    assert_eq!(minor(r.target.as_ref().unwrap()), 1_610_000);
    assert_eq!(r.months, 2);
}

#[test]
fn startup_amount_and_decision_outcome() {
    let (app, mf, uy) = setup();
    let sc = |name: &str, income: &str| IdeaScenarioInput {
        name: name.into(),
        income: income.into(),
        expense: "4 000 000".into(),
    };
    let idea = app
        .create_venture_idea(
            &uy,
            VentureIdeaInput {
                title: "Tikuv sexi".into(),
                skill_id: None,
                capex: vec![CapexLineInput {
                    title: "Mashinalar".into(),
                    amount: "30 000 000".into(),
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
    assert_eq!(
        err(app.mf_set_plan(&mf, plan(None, Some("130 000 000"), None))),
        "STARTUP_EXCEEDS_TARGET"
    );
    assert_eq!(
        err(app.mf_set_plan(&mf, plan(None, Some("30 000 000"), Some("yoq")))),
        "NOT_FOUND"
    );
    // su-001: 120 mln, shundan ish boshlash 30 mln — yashash uchun 90 mln.
    let s = app
        .mf_set_plan(&mf, plan(None, Some("30 000 000"), Some(&idea.id)))
        .unwrap()
        .startup
        .unwrap();
    assert_eq!(minor(s.living.as_ref().unwrap()), 9_000_000_000);
    assert_eq!(s.startup_percent.as_deref(), Some("25"));
    assert_eq!(s.idea_title.as_deref(), Some("Tikuv sexi"));
    assert!(!s.exceeds_target);
    // Maqsad keyin kamaytirildi — ish boshlash summasi undan katta: belgi bilan ko'rsatiladi.
    let s = app
        .mf_set_settings(&mf, settings("20 000 000"))
        .unwrap()
        .startup
        .unwrap();
    assert!(s.exceeds_target);
    assert!(s.living.is_none());
    // Belgini olib tashlash.
    assert!(app
        .mf_set_plan(&mf, plan(None, None, None))
        .unwrap()
        .startup
        .is_none());

    // Qaror natijasi: bir marta, o'zgarmas.
    let answers = [
        "approached",
        "upfront",
        "abroadJobFee",
        "repaymentDate",
        "familyDiscussed",
    ]
    .iter()
    .map(|k| MfAnswerInput {
        key: (*k).into(),
        reply: "NO".into(),
    })
    .collect();
    let log = app
        .mf_record_decision(
            &mf,
            MfDecisionInput {
                kind: "LEND".into(),
                title: "Do'stga qarz".into(),
                amount: "5 000 000".into(),
                answers,
                choice: Some("WAIT".into()),
                note: None,
                promised_percent: None,
            },
        )
        .unwrap();
    let id = log[0].id.clone();
    assert!(log[0].outcome.is_none());
    let outcome = |o: &str, on: Option<&str>| MfOutcomeInput {
        outcome: o.into(),
        outcome_on: on.map(Into::into),
        note: Some("Muddat yozilmadi — bermadim".into()),
    };
    assert_eq!(
        err(app.mf_set_outcome(&mf, &id, outcome("MAYBE", None))),
        "INVALID_OUTCOME"
    );
    assert_eq!(
        err(app.mf_set_outcome(&mf, &id, outcome("DROPPED", Some("2026-10-19")))),
        "FUTURE_DATE"
    );
    assert_eq!(
        err(app.mf_set_outcome(&mf, &id, outcome("DROPPED", Some("2026-10-17")))),
        "BEFORE_DECISION"
    );
    assert_eq!(
        err(app.mf_set_outcome(&mf, "yoq", outcome("DROPPED", None))),
        "NOT_FOUND"
    );
    let log = app
        .mf_set_outcome(&mf, &id, outcome("DROPPED", None))
        .unwrap();
    let o = log[0].outcome.as_ref().unwrap();
    assert_eq!(
        (o.outcome.as_str(), o.outcome_on.as_str()),
        ("DROPPED", "2026-10-18")
    );
    assert_eq!(
        err(app.mf_set_outcome(&mf, &id, outcome("DONE", None))),
        "OUTCOME_ALREADY_SET"
    );
}
