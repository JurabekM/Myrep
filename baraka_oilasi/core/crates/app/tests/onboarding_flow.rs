#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U15: onboarding javoblari (daromad ritmi, «qarzim bor»), bosh sahifa eslatmalari, zaxira
//! nusxa eslatmasi va qurilmaning o'z tili.

use std::sync::Arc;

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
    let app = App::open_in_memory(
        &DbKey::from_bytes([5; 32]),
        "dev-bekzod",
        c,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    app.set_interchange_kdf(64, 1, 1);
    app
}

fn bootstrap(app: &App, rhythm: Option<&str>, debts: bool, month_start_day: u32) -> String {
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Bekzodlar oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "windows".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day,
            spaces: vec!["UY".into()],
            members: vec![
                NewMemberInput {
                    display_name: "Bekzod".into(),
                    role: "ADULT".into(),
                },
                NewMemberInput {
                    display_name: "Mohira".into(),
                    role: "ADULT".into(),
                },
                NewMemberInput {
                    display_name: "Jasur".into(),
                    role: "CHILD".into(),
                },
            ],
            income_rhythm: rhythm.map(str::to_string),
            debts_declared: debts,
        })
        .unwrap();
    h.spaces[0].id.clone()
}

fn kinds(app: &App, uy: &str) -> Vec<(String, Option<u32>)> {
    app.home_nudges(uy)
        .unwrap()
        .into_iter()
        .map(|n| (n.kind, n.days))
        .collect()
}

fn income(amount: &str, on: Option<&str>) -> NewIncomeInput {
    NewIncomeInput {
        amount: amount.into(),
        source: "Taksi".into(),
        channel: "CASH".into(),
        member_id: None,
        occurred_on: on.map(str::to_string),
        source_type: None,
        note: None,
    }
}

fn akam_debt() -> NewDebtInput {
    NewDebtInput {
        creditor_type: "RELATIVE".into(),
        creditor: "Akam".into(),
        reason: None,
        currency: "UZS".into(),
        principal: "1 000 000".into(),
        original_principal: None,
        paid_before: None,
        plan_kind: "MANUAL".into(),
        annual_bp: None,
        markup: None,
        months: None,
        first_date: None,
        schedule: vec![ScheduleLineInput {
            date: "15.12.2026".into(),
            amount: "1 000 000".into(),
        }],
        early_repayment_terms: None,
        prepayment_fee_bp: None,
        is_new: false,
        borrow_check: None,
    }
}

#[test]
fn daily_rhythm_debts_and_backup_reminders() {
    let c = clock("2026-10-15T09:00:00+05:00");
    let app = app_at(c.clone());
    let uy = bootstrap(&app, Some("DAILY"), true, 1);
    let s = app.settings().unwrap();
    assert_eq!(s.income_rhythm.as_deref(), Some("DAILY"));
    assert!(s.debts_declared);
    assert_eq!(
        kinds(&app, &uy),
        vec![
            ("INCOME_TODAY".to_string(), None),
            ("DEBT_INVENTORY".to_string(), None)
        ]
    );

    // Bugungi tushum yozildi — eslatma ketadi; ertaga yana chiqadi.
    app.record_income(&uy, income("350 000", None)).unwrap();
    assert_eq!(kinds(&app, &uy), vec![("DEBT_INVENTORY".to_string(), None)]);
    c.advance(Duration::days(1));
    assert_eq!(kinds(&app, &uy)[0].0, "INCOME_TODAY");

    // Qarz inventarga kiritildi — taklif yo'qoladi (70/20/10 taklifi qarzlar ekranida).
    app.add_debt(&uy, akam_debt()).unwrap();
    assert!(app.budget_mode(&uy).unwrap().suggested);
    assert_eq!(kinds(&app, &uy), vec![("INCOME_TODAY".to_string(), None)]);

    // 30 kun zaxira nusxa olinmagan — eslatma; to'liq eksportdan keyin yo'q.
    c.set(
        DateTime::parse_from_rfc3339("2026-11-14T09:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    );
    app.record_income(&uy, income("200 000", None)).unwrap();
    assert_eq!(kinds(&app, &uy), vec![("BACKUP".to_string(), Some(30))]);
    // Qurilma uchun inkremental eksport zaxira hisoblanmaydi — faqat FULL.
    app.export_baraka(ExportInput {
        password: "Baraka-2026!".into(),
        mode: "FULL".into(),
        peer_device_id: None,
    })
    .unwrap();
    assert!(kinds(&app, &uy).is_empty());
    c.advance(Duration::days(30));
    app.record_income(&uy, income("200 000", None)).unwrap();
    assert_eq!(kinds(&app, &uy), vec![("BACKUP".to_string(), Some(30))]);
}

#[test]
fn orders_and_monthly_rhythms() {
    let c = clock("2027-01-20T09:00:00+05:00");
    let app = app_at(c.clone());
    let uy = bootstrap(&app, Some("ORDERS"), false, 10);
    assert_eq!(kinds(&app, &uy), vec![("INCOME_QUIET".to_string(), None)]);
    app.record_income(&uy, income("2 000 000", Some("2027-01-07")))
        .unwrap();
    assert!(kinds(&app, &uy).is_empty());
    c.advance(Duration::days(1));
    assert_eq!(
        kinds(&app, &uy),
        vec![("INCOME_QUIET".to_string(), Some(14))]
    );

    // Oylik maoshga o'tildi: oy 10-dan boshlanadi, 10–13-kunlari eslatiladi.
    let s = app.settings().unwrap();
    app.update_settings(SettingsInput {
        locale: s.device_locale,
        income_rhythm: Some("MONTHLY".into()),
        debts_declared: false,
    })
    .unwrap();
    assert!(kinds(&app, &uy).is_empty());
    c.set(
        DateTime::parse_from_rfc3339("2027-02-11T09:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    );
    assert_eq!(kinds(&app, &uy), vec![("PAYDAY".to_string(), None)]);
    app.record_income(&uy, income("6 000 000", None)).unwrap();
    assert!(kinds(&app, &uy).is_empty());
}

#[test]
fn device_locale_formats_money_and_is_not_household_wide() {
    let c = clock("2026-10-15T09:00:00+05:00");
    let app = app_at(c);
    let uy = bootstrap(&app, None, false, 1);
    let before = app.record_income(&uy, income("1 500 000", None)).unwrap();
    assert!(
        before.income.amount.formatted.ends_with("soʻm"),
        "{}",
        before.income.amount.formatted
    );
    assert!(kinds(&app, &uy).is_empty());

    let s = app
        .update_settings(SettingsInput {
            locale: Some("ru".into()),
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    assert_eq!(s.locale, "ru");
    assert_eq!(s.device_locale.as_deref(), Some("ru"));
    assert_eq!(s.household_locale, "uz");
    assert_eq!(app.household().unwrap().locale, "uz");
    let sum = app.monthly_summary(&uy, None, None).unwrap();
    assert!(
        sum.paid_to_self.formatted.contains("сум"),
        "{}",
        sum.paid_to_self.formatted
    );

    // Qurilma tili olib tashlansa — xonadon tili.
    let s = app
        .update_settings(SettingsInput {
            locale: None,
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    assert_eq!(s.locale, "uz");

    for (locale, rhythm, code) in [
        (Some("en"), None, "INVALID_LOCALE"),
        (None, Some("WEEKLY"), "INVALID_INCOME_RHYTHM"),
    ] {
        let err = app
            .update_settings(SettingsInput {
                locale: locale.map(str::to_string),
                income_rhythm: rhythm.map(str::to_string),
                debts_declared: false,
            })
            .unwrap_err();
        assert_eq!(err.code, code);
    }
}

#[test]
fn onboarding_rejects_unknown_rhythm() {
    let app = app_at(clock("2026-10-15T09:00:00+05:00"));
    let err = app
        .bootstrap(BootstrapInput {
            household_name: "x".into(),
            device_name: "y".into(),
            platform: "windows".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![NewMemberInput {
                display_name: "A".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: Some("HOURLY".into()),
            debts_declared: false,
        })
        .unwrap_err();
    assert_eq!(err.code, "INVALID_INCOME_RHYTHM");
    assert!(!app.is_initialized().unwrap());
}
