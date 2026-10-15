#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Uy makoni use-case'lari: Anvar ssenariysining birinchi qismi (daromad → ulush → audit → jurnal).

use std::sync::Arc;

use baraka_agreements::{AgreementDraft, Answer};
use baraka_app::*;
use chrono::{DateTime, Duration, Utc};

fn clock(at: &str) -> Arc<FixedClock> {
    Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339(at)
            .unwrap()
            .with_timezone(&Utc),
    ))
}

fn app_at(c: Arc<FixedClock>) -> App {
    App::open_in_memory(
        &DbKey::from_bytes([3; 32]),
        "dev-phone",
        c,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap()
}

fn bootstrap(app: &App) -> (String, String) {
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Anvarlar oilasi".into(),
            device_name: "Anvarning telefoni".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "KASBKOR".into()],
            members: vec![
                NewMemberInput {
                    display_name: "Anvar".into(),
                    role: "ADULT".into(),
                },
                NewMemberInput {
                    display_name: "Gulnora".into(),
                    role: "ADULT".into(),
                },
            ],
        })
        .unwrap();
    let uy = h.spaces.iter().find(|s| s.kind == "UY").unwrap().id.clone();
    let kk = h
        .spaces
        .iter()
        .find(|s| s.kind == "KASBKOR")
        .unwrap()
        .id
        .clone();
    (uy, kk)
}

fn income(amount: &str) -> NewIncomeInput {
    NewIncomeInput {
        amount: amount.into(),
        source: "Taksi".into(),
        channel: "CASH".into(),
        member_id: None,
        occurred_on: None,
        source_type: Some("TER".into()),
        note: None,
    }
}

#[test]
fn bootstrap_creates_spaces_categories_and_rule() {
    let app = app_at(clock("2026-10-15T09:00:00Z"));
    assert!(!app.is_initialized().unwrap());
    let (uy, kk) = bootstrap(&app);
    assert!(app
        .bootstrap(BootstrapInput {
            household_name: "x".into(),
            device_name: "x".into(),
            platform: "x".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![],
        })
        .is_err());
    let cats = app.categories(&uy).unwrap();
    assert!(cats.iter().any(|c| c.name_key == "category.child_education"
        && c.default_necessity.as_deref() == Some("KERAK")));
    assert!(cats
        .iter()
        .any(|c| c.name_key == "category.sadaqa" && c.default_necessity.is_none()));
    assert!(app
        .categories(&kk)
        .unwrap()
        .iter()
        .all(|c| c.name_key.starts_with("category.kk.")));
    let v = app.vault(&uy).unwrap();
    assert_eq!(v.rule.as_ref().and_then(|r| r.bp), Some(500));
    assert_eq!(v.balance.minor, "0");
    assert_eq!(
        app.categories("no-such-space").unwrap_err().code,
        "SPACE_NOT_FOUND"
    );
}

#[test]
fn income_share_vault_and_friction() {
    let app = app_at(clock("2026-10-15T09:00:00Z"));
    let (uy, _) = bootstrap(&app);
    let events = app.subscribe();

    let rec = app.record_income(&uy, income("800 000")).unwrap();
    assert_eq!(rec.income.amount.formatted, "800\u{a0}000\u{a0}so\u{2bb}m");
    assert_eq!(rec.suggested_share.minor, "4000000"); // 5% = 40 000 so'm
    assert_eq!(rec.suggested_share.plain, "40000");
    assert!(events.try_recv().unwrap().topics.contains(&Topic::Incomes));

    assert_eq!(
        app.allocate_to_vault(&uy, &rec.income.id, "900 000")
            .unwrap_err()
            .code,
        "SHARE_EXCEEDS_INCOME"
    );
    app.allocate_to_vault(&uy, &rec.income.id, "40 000")
        .unwrap();
    app.record_initial_balance(&uy, "1 500 000").unwrap();
    let v = app.vault(&uy).unwrap();
    assert_eq!(v.balance.minor, "154000000");
    assert_eq!(v.streak.current_weeks, 1);
    assert!(v.streak.current_week_done);

    // Pul olish: sabab majburiy va qoldiqdan oshmaydi.
    assert_eq!(
        app.withdraw_from_vault(&uy, "10 000", "  ")
            .unwrap_err()
            .field
            .as_deref(),
        Some("reason")
    );
    assert_eq!(
        app.withdraw_from_vault(&uy, "99 000 000", "dori")
            .unwrap_err()
            .code,
        "INSUFFICIENT_VAULT_BALANCE"
    );
    app.withdraw_from_vault(&uy, "100 000", "Dori uchun")
        .unwrap();
    assert_eq!(app.vault(&uy).unwrap().balance.minor, "144000000");

    assert_eq!(
        app.record_income(&uy, income("0")).unwrap_err().code,
        "AMOUNT_NOT_POSITIVE"
    );
    assert_eq!(
        app.record_income(&uy, income("12,345")).unwrap_err().code,
        "PARSE_TOO_MANY_DECIMALS"
    );
}

#[test]
fn progressive_suggestion_after_four_weeks() {
    let c = clock("2026-09-18T09:00:00Z"); // juma
    let app = app_at(c.clone());
    let (uy, _) = bootstrap(&app);
    for _ in 0..4 {
        let rec = app.record_income(&uy, income("1 000 000")).unwrap();
        app.allocate_to_vault(&uy, &rec.income.id, "50 000")
            .unwrap();
        c.advance(Duration::days(7));
    }
    let rec = app.record_income(&uy, income("1 000 000")).unwrap();
    assert_eq!(rec.progressive_suggestion_bp, Some(600));
    assert_eq!(rec.progressive_suggestion_percent.as_deref(), Some("6"));
}

#[test]
fn monthly_audit_counts_cash_left_and_excludes_sadaqa_from_havas() {
    let app = app_at(clock("2026-10-15T09:00:00Z"));
    let (uy, _) = bootstrap(&app);
    let cats = app.categories(&uy).unwrap();
    let cat = |k: &str| cats.iter().find(|c| c.name_key == k).unwrap().id.clone();
    app.record_income(&uy, income("8 000 000")).unwrap();
    let exp = |amount: &str, k: &str| NewExpenseInput {
        amount: amount.into(),
        category_id: cat(k),
        channel: "CASH".into(),
        member_id: None,
        occurred_on: None,
        necessity: None,
        obligation_id: None,
        is_gift: false,
        is_ostentation: false,
        funded_by_debt: false,
        note: None,
    };
    app.record_expense(&uy, exp("5 000 000", "category.rent"))
        .unwrap();
    app.record_expense(&uy, exp("1 000 000", "category.snacks"))
        .unwrap();
    app.record_expense(&uy, exp("300 000", "category.sadaqa"))
        .unwrap();
    app.record_expense(&uy, exp("350 000", "category.clothes"))
        .unwrap();

    let s = app.monthly_summary(&uy, None, None).unwrap();
    assert_eq!(
        (s.period_start.as_str(), s.period_end.as_str()),
        ("2026-10-01", "2026-11-01")
    );
    assert_eq!(s.by_necessity.havas.minor, "100000000");
    assert_eq!(s.by_necessity.sadaqa.minor, "30000000");
    assert_eq!(s.by_necessity.unclassified.minor, "0");
    assert_eq!(s.unexplained_gap.minor, "135000000");
    // Cho'ntakda 1 mln qolgan — «oqib ketgan» deb ko'rsatilmaydi.
    let s = app.monthly_summary(&uy, None, Some("1 000 000")).unwrap();
    assert_eq!(s.unexplained_gap.minor, "35000000");
}

#[test]
fn journal_append_verify_and_keeper_rule() {
    let app = app_at(clock("2026-10-15T09:00:00Z"));
    let (uy, _) = bootstrap(&app);
    let agr = app
        .create_agreement(&uy, "PARTNERSHIP", "Dilshod bilan yetkazib berish")
        .unwrap();
    let e = |kind: &str, amount: Option<&str>, note: &str| NewJournalEntryInput {
        kind: kind.into(),
        party_id: Some("P1".into()),
        amount: amount.map(Into::into),
        currency: None,
        date: Some("2026-10-01".into()),
        note: Some(note.into()),
        corrects_entry_id: None,
        refs: vec![],
    };
    let first = app
        .append_journal(
            &uy,
            &agr.id,
            e("CONTRIBUTION", Some("3 000 000"), "Anvar hissasi"),
        )
        .unwrap();
    assert_eq!(first.seq, 1);
    // NFC: ajratilgan ko'rinishdagi belgi bir xil baytlarga keltiriladi.
    let second = app
        .append_journal(
            &uy,
            &agr.id,
            e("REVENUE", Some("1 400 000"), "Buyurtma\u{0301}"),
        )
        .unwrap();
    assert_eq!(second.note.as_deref(), Some("Buyurtm\u{00e1}"));
    let status = app.verify_journal(&uy, &agr.id).unwrap();
    assert!(status.ok);
    assert_eq!(
        status.short_code.as_deref(),
        Some(second.short_code.as_str())
    );
    assert_eq!(
        app.append_journal(&uy, &agr.id, e("CORRECTION", Some("-1"), "x"))
            .unwrap_err()
            .code,
        "JOURNAL_CORRECTION_TARGET_REQUIRED"
    );
}

#[test]
fn only_the_keeper_device_writes_to_the_journal() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("baraka.db");
    let key = DbKey::from_bytes([4; 32]);
    let ids = Arc::new(SequentialIdGen::default());
    let (uy, agreement_id) = {
        let phone = App::open(
            &path,
            &key,
            "dev-phone",
            clock("2026-10-15T09:00:00Z"),
            ids.clone(),
        )
        .unwrap();
        let (uy, _) = bootstrap(&phone);
        (
            uy.clone(),
            phone
                .create_agreement(&uy, "LOAN", "Qo'shniga qarz")
                .unwrap()
                .id,
        )
    };
    let desktop = App::open(
        &path,
        &key,
        "dev-desktop",
        clock("2026-10-15T09:00:00Z"),
        ids,
    )
    .unwrap();
    let entry = NewJournalEntryInput {
        kind: "REPAYMENT".into(),
        party_id: None,
        amount: Some("100 000".into()),
        currency: None,
        date: None,
        note: None,
        corrects_entry_id: None,
        refs: vec![],
    };
    assert_eq!(
        desktop
            .append_journal(&uy, &agreement_id, entry)
            .unwrap_err()
            .code,
        "NOT_JOURNAL_KEEPER"
    );
    // O'qish va tekshirish boshqa qurilmada ham mumkin.
    assert!(desktop.verify_journal(&uy, &agreement_id).unwrap().ok);
}

#[test]
fn agreement_check_and_loan_simulation_passthrough() {
    let app = app_at(clock("2026-10-15T09:00:00Z"));
    bootstrap(&app);
    let c = app
        .check_agreement("PARTNERSHIP", AgreementDraft::default())
        .unwrap();
    assert_eq!((c.answered, c.can_sign, c.missing.len()), (0, false, 9));
    let d = AgreementDraft {
        arbiter: Answer::NotApplicable {
            reason: String::new(),
        },
        ..AgreementDraft::default()
    };
    assert!(app
        .check_agreement("PARTNERSHIP", d)
        .unwrap()
        .errors
        .contains(&"NA_REASON_REQUIRED"));
    assert_eq!(
        app.check_agreement("NOPE", AgreementDraft::default())
            .unwrap_err()
            .code,
        "INVALID_AGREEMENT_TYPE"
    );

    let sim = app
        .simulate_loan(LoanSimulationInput {
            principal: "39 000 000".into(),
            currency: "UZS".into(),
            annual_bp: 2400,
            months: 14,
            kind: "ANNUITY".into(),
            extra_per_month: "1 600 000".into(),
        })
        .unwrap();
    assert_eq!(
        (sim.base_months, sim.accelerated_months, sim.months_saved),
        (14, 9, 5)
    );
    assert_eq!(sim.payment.minor, "322147684");
    assert_eq!(sim.interest_saved.minor, "213048906");
}

#[test]
fn loan_receipt_rules_and_pdf() {
    let app = app_at(clock("2026-10-15T09:00:00Z"));
    bootstrap(&app);
    let line = |date: &str, amount: &str| ScheduleLineInput {
        date: date.into(),
        amount: amount.into(),
    };
    let mut input = LoanReceiptInput {
        lender: "Gʻayrat".into(),
        borrower: "Karim".into(),
        amount: "2 000 000".into(),
        currency: "UZS".into(),
        issued_on: None,
        place: "Toshkent".into(),
        schedule: vec![],
        witnesses: vec!["Sobir hoji".into(), " ".into()],
        note: None,
    };
    assert_eq!(
        app.render_loan_receipt(input.clone()).unwrap_err().code,
        "SCHEDULE_REQUIRED"
    );
    input.schedule = vec![
        line("2026-11-15", "700 000"),
        line("2026-12-15", "700 000"),
        line("2027-01-15", "500 000"),
    ];
    assert_eq!(
        app.render_loan_receipt(input.clone()).unwrap_err().code,
        "SCHEDULE_SUM_MISMATCH"
    );
    input.schedule[2].amount = "600 000".into();
    input.schedule.swap(0, 1);
    input.schedule[0].date = "2026-12-15".into();
    input.schedule[1].date = "2026-11-15".into();
    assert_eq!(
        app.render_loan_receipt(input.clone()).unwrap_err().code,
        "SCHEDULE_DATES_ORDER"
    );
    input.schedule.swap(0, 1);
    let pdf = app.render_loan_receipt(input.clone()).unwrap();
    assert!(pdf.starts_with(b"%PDF-"));
    input.borrower = "Gʻayrat".into();
    assert_eq!(
        app.render_loan_receipt(input).unwrap_err().code,
        "SAME_PARTY"
    );
}
