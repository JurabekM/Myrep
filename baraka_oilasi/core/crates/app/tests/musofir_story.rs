#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! M5 — qaytish xavfsizligi (SPEC 6.8): Bobur Koreyadan
//! 18 000 dollar bilan qaytdi; sinfdoshi «Oltin foyda»ga 10 000 ni qo'yishga undaydi — «oyiga 35 % kafolatli»,
//! «joy kam», tekshirtirmaydi, pulni qaytarib olish qiyin. Oilaning 6 oylik ro'zg'ori — «qal'a devori».

use std::sync::Arc;

use baraka_app::*;
use chrono::{DateTime, Utc};

fn setup() -> (App, String, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
        "dev-bobur",
        Arc::new(FixedClock::new(
            DateTime::parse_from_rfc3339("2026-10-20T09:00:00+05:00")
                .unwrap()
                .with_timezone(&Utc),
        )),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Boburning oilasi".into(),
            device_name: "Boburning telefoni".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "MUSOFIR".into()],
            members: vec![NewMemberInput {
                display_name: "Bobur".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let id = |k: &str| h.spaces.iter().find(|s| s.kind == k).unwrap().id.clone();
    let (mf, uy) = (id("MUSOFIR"), id("UY"));
    app.mf_set_settings(
        &mf,
        MfSettingsInput {
            country: Some("Koreya".into()),
            work_currency: "KRW".into(),
            share_percent: "20".into(),
            target: None,
            return_on: None,
        },
    )
    .unwrap();
    (app, mf, uy)
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

fn uy_expense(app: &App, uy: &str, amount: &str, on: &str) {
    let cat = app.categories(uy).unwrap()[0].id.clone();
    app.record_expense(
        uy,
        NewExpenseInput {
            amount: amount.into(),
            category_id: cat,
            channel: "CASH".into(),
            member_id: None,
            occurred_on: Some(on.into()),
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: None,
            self_investment: false,
            learning_plan_id: None,
        },
    )
    .unwrap();
}

fn returned(currency: Option<&str>, amount: &str, rate: Option<&str>) -> MfReturnInput {
    MfReturnInput {
        returned_on: Some("2026-10-17".into()),
        brought_home: Some(amount.into()),
        brought_currency: currency.map(Into::into),
        brought_rate: rate.map(Into::into),
    }
}

fn decision(
    kind: &str,
    amount: &str,
    a: &[(&str, &str)],
    promised: Option<&str>,
) -> MfDecisionInput {
    MfDecisionInput {
        kind: kind.into(),
        title: "«Oltin foyda»ga sarmoya".into(),
        amount: amount.into(),
        answers: a
            .iter()
            .map(|(k, r)| MfAnswerInput {
                key: (*k).into(),
                reply: (*r).into(),
            })
            .collect(),
        choice: None,
        note: None,
        promised_percent: promised.map(Into::into),
    }
}

#[test]
fn migrant_brings_dollars_and_meets_scam_offer() {
    let (app, mf, uy) = setup();
    // Uyda oyiga ~8 mln so'm (wl-001): qal'a devori — 48 mln.
    for (amount, on) in [
        ("8 000 000", "2026-07-15"),
        ("7 800 000", "2026-08-15"),
        ("8 200 000", "2026-09-15"),
    ] {
        uy_expense(&app, &uy, amount, on);
    }

    // 18 000 dollar — kurs majburiy.
    assert_eq!(
        err(app.mf_set_return(&mf, returned(Some("USD"), "18 000", None))),
        "RATE_REQUIRED"
    );
    assert_eq!(
        err(app.mf_set_return(&mf, returned(Some("XYZ"), "18 000", None))),
        "INVALID_CURRENCY"
    );
    let c = app
        .mf_set_return(&mf, returned(Some("USD"), "18 000", Some("12 650")))
        .unwrap()
        .cooling
        .unwrap();
    assert_eq!(
        (
            minor(c.brought_home.as_ref().unwrap()),
            c.brought_home.as_ref().unwrap().currency.as_str()
        ),
        (1_800_000, "USD")
    );
    assert_eq!(minor(c.brought_value.as_ref().unwrap()), 22_770_000_000);
    assert_eq!(c.brought_rate.as_deref(), Some("12\u{a0}650"));
    assert_eq!(minor(c.wall.as_ref().unwrap()), 4_800_000_000);
    assert_eq!(c.wall_months_used, 3);
    assert_eq!(minor(c.free.as_ref().unwrap()), 17_970_000_000);
    assert_eq!(c.days_left, 87);

    // «Oltin foyda» (co-009): 10 000 $ ≈ 126,5 mln — kafolat, shoshirish, tekshirtirmaydi, chiqish qiyin,
    // oila bilan maslahatlashmadi; va'da — oyiga 35 %.
    let scam = [
        ("guaranteed", "YES"),
        ("lossShared", "YES"),
        ("realActivity", "UNKNOWN"),
        ("recruitment", "NO"),
        ("urgency", "YES"),
        ("written", "YES"),
        ("licensed", "YES"),
        ("inspection", "NO"),
        ("exitEasy", "NO"),
        ("approached", "YES"),
        ("upfront", "NO"),
        ("abroadJobFee", "NO"),
        ("familyDiscussed", "NO"),
    ];
    assert_eq!(
        err(app.mf_check_decision(&mf, decision("INVEST", "126 500 000", &scam, Some("0")))),
        "INVALID_PERCENT"
    );
    let r = app
        .mf_check_decision(&mf, decision("INVEST", "126 500 000", &scam, Some("35")))
        .unwrap();
    assert_eq!((r.verdict.as_str(), r.signs), ("RED", 4));
    let codes: Vec<&str> = r.flags.iter().map(|f| f.code.as_str()).collect();
    for c in [
        "GUARANTEED_PROFIT",
        "INSPECTION_REFUSED",
        "EXIT_HARD",
        "TWO_SIGNS",
        "LARGE_SHARE",
        "NOT_DISCUSSED",
    ] {
        assert!(codes.contains(&c), "{c}: {codes:?}");
    }
    assert!(!codes.contains(&"FORTRESS_WALL"));
    assert_eq!(r.share_percent.as_deref(), Some("55,56"));
    assert_eq!(
        (
            r.promised_yearly_percent.as_deref(),
            r.promised_times.as_deref()
        ),
        (Some("420"), Some("5,2"))
    );
    assert_eq!(minor(r.free.as_ref().unwrap()), 17_970_000_000);

    // Hammasi joyida, lekin 180 mln — qal'a devoriga tegadi.
    let calm = [
        ("approached", "NO"),
        ("upfront", "NO"),
        ("abroadJobFee", "NO"),
        ("familyDiscussed", "YES"),
    ];
    let r = app
        .mf_check_decision(&mf, decision("PURCHASE", "180 000 000", &calm, None))
        .unwrap();
    let codes: Vec<&str> = r.flags.iter().map(|f| f.code.as_str()).collect();
    assert!(codes.contains(&"FORTRESS_WALL"), "{codes:?}");
    assert_eq!(r.verdict, "RED");

    // Uy valyutasida — kurs kerak emas, saqlanmaydi.
    let c = app
        .mf_set_return(&mf, returned(None, "120 000 000", Some("1")))
        .unwrap()
        .cooling
        .unwrap();
    assert_eq!(c.brought_rate, None);
    assert_eq!(minor(c.brought_value.as_ref().unwrap()), 12_000_000_000);
}
