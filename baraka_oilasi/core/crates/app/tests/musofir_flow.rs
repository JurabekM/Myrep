#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! M1 — Musofir makoni (docs/musofir/SPEC.md 2–4): ish valyutasi va kurs, chet eldagi maosh va
//! xarajat, uyga yuborilgan, o'z ulushi va qaytish jamg'armasi prognozi.

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

fn setup() -> (App, String, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
        "dev-bobur",
        clock("2026-10-18T09:00:00+05:00"),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Bobur akaning oilasi".into(),
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
    (app, id("MUSOFIR"), id("UY"))
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

fn settings(currency: &str) -> MfSettingsInput {
    MfSettingsInput {
        country: Some("Koreya".into()),
        work_currency: currency.into(),
        share_percent: "20".into(),
        target: Some("120 000 000".into()),
        return_on: Some("2027-12-01".into()),
    }
}

fn salary(app: &App, mf: &str, amount: &str, on: &str) -> MfIncomeRecordedDto {
    app.mf_record_income(
        mf,
        MfIncomeInput {
            kind: "SALARY".into(),
            amount: amount.into(),
            channel: "CARD".into(),
            occurred_on: Some(on.into()),
            note: Some("Zavod".into()),
        },
    )
    .unwrap()
}

fn mv(kind: &str, amount: &str, on: &str) -> MfMoveInput {
    MfMoveInput {
        kind: kind.into(),
        amount: amount.into(),
        fee: None,
        received: None,
        occurred_on: Some(on.into()),
        note: None,
        purposes: None,
    }
}

#[test]
fn bobur_share_and_return_fund() {
    let (app, mf, uy) = setup();

    // Sozlanmagan: usta ochiladi, yozuv yo'q.
    let o = app.mf_overview(&mf, None).unwrap();
    assert!(o.settings.is_none());
    assert_eq!(o.default_share_percent, "20");
    assert_eq!(
        err(app.mf_record_move(&mf, mv("FUND_IN", "1", "2026-10-01"))),
        "MF_NOT_CONFIGURED"
    );
    assert_eq!(err(app.mf_overview(&uy, None)), "NOT_MUSOFIR_SPACE");
    let mut bad = settings("XYZ");
    assert_eq!(
        err(app.mf_set_settings(&mf, bad.clone())),
        "INVALID_CURRENCY"
    );
    bad.work_currency = "KRW".into();
    bad.share_percent = "120".into();
    assert_eq!(err(app.mf_set_settings(&mf, bad)), "INVALID_PERCENT");

    let o = app.mf_set_settings(&mf, settings("KRW")).unwrap();
    let s = o.settings.unwrap();
    assert_eq!(
        (s.work_currency.as_str(), s.home_currency.as_str()),
        ("KRW", "UZS")
    );
    assert_eq!(s.share_percent, "20");
    assert_eq!(minor(s.target.as_ref().unwrap()), 12_000_000_000);
    assert!(!s.currency_locked);

    // Iyul–sentyabr: maosh 2 600 000 von, o'z ulushi jamg'armaga, qolgani uyga.
    app.mf_record_move(&mf, mv("OPENING", "150 000", "2026-07-01"))
        .unwrap();
    app.mf_record_move(&mf, mv("FUND_OPENING", "4 440 000", "2026-07-01"))
        .unwrap();
    for (month, fund, sent) in [
        ("07", "520 000", "2 080 000"),
        ("08", "500 000", "2 100 000"),
        ("09", "540 000", "2 060 000"),
    ] {
        let on = format!("2026-{month}-25");
        let r = salary(&app, &mf, "2 600 000", &on);
        assert_eq!(minor(&r.suggested_share), 520_000);
        assert_eq!(r.suggested_share.currency, "KRW");
        app.mf_record_move(&mf, mv("FUND_IN", fund, &on)).unwrap();
        app.mf_record_move(&mf, mv("SENT_HOME", sent, &on)).unwrap();
    }

    // Oktyabr: maosh, xarajatlar, uyga 1 200 000 + 5 000 komissiya.
    salary(&app, &mf, "2 600 000", "2026-10-10");
    let cats = app.categories(&mf).unwrap();
    let cat = |key: &str| cats.iter().find(|c| c.name_key == key).unwrap().id.clone();
    for (key, amount) in [
        ("category.mf.rent", "400 000"),
        ("category.mf.food", "350 000"),
        ("category.mf.phone", "60 000"),
    ] {
        app.mf_record_expense(
            &mf,
            MfExpenseInput {
                amount: amount.into(),
                category_id: cat(key),
                channel: "CARD".into(),
                occurred_on: Some("2026-10-12".into()),
                note: None,
            },
        )
        .unwrap();
    }
    let o = app
        .mf_record_move(
            &mf,
            MfMoveInput {
                fee: Some("5 000".into()),
                received: Some("10 900 000".into()),
                ..mv("SENT_HOME", "1 200 000", "2026-10-12")
            },
        )
        .unwrap();
    let sent = o.entries.iter().find(|e| e.kind == "SENT_HOME").unwrap();
    assert_eq!(minor(sent.fee.as_ref().unwrap()), 5_000);
    assert_eq!(sent.received.as_ref().unwrap().currency, "UZS");

    // Ulush hali ajratilmagan: «NO_SHARE»; kurs yo'q — uy valyutasida ko'rsatkich yo'q.
    let m = o.month.unwrap();
    assert_eq!(minor(&m.share_gap), 520_000);
    assert_eq!(m.warnings, vec!["NO_SHARE".to_string()]);
    let f = o.fund.unwrap();
    assert_eq!(minor(&f.balance), 6_000_000);
    assert_eq!(f.status, "NO_RATE");
    assert!(f.balance_home.is_none());
    assert_eq!(f.months_used, 3);
    assert_eq!(minor(f.avg_monthly.as_ref().unwrap()), 520_000);

    // Kurs: kelajak sana — yo'q; 1 KRW = 9,1 so'm.
    let rate = |r: &str, on: &str| MfRateInput {
        rate: r.into(),
        rate_on: Some(on.into()),
        source: Some("Bank".into()),
    };
    assert_eq!(
        err(app.mf_set_rate(&mf, rate("9,1", "2026-10-19"))),
        "FUTURE_DATE"
    );
    assert_eq!(
        err(app.mf_set_rate(&mf, rate("0", "2026-10-15"))),
        "INVALID_FX_RATE"
    );
    let o = app.mf_set_rate(&mf, rate("9,1", "2026-10-15")).unwrap();
    let r = o.rate.unwrap();
    assert_eq!((r.rate.as_str(), r.stale), ("9,1", false));
    // rf-001: 13 oyda 116,1 mln — 3,9 mln kam.
    let f = o.fund.unwrap();
    assert_eq!(f.status, "BEHIND");
    assert_eq!(minor(f.balance_home.as_ref().unwrap()), 5_460_000_000);
    assert_eq!(f.months_until_return, Some(13));
    assert_eq!(minor(f.shortfall_at_return.as_ref().unwrap()), 388_400_000);

    // Shu oy ulushi qo'yildi — mf-001: qo'lda 215 000, ulush bajarildi; endi qaytishga yetadi.
    let o = app
        .mf_record_move(&mf, mv("FUND_IN", "520 000", "2026-10-12"))
        .unwrap();
    let m = o.month.unwrap();
    assert_eq!(minor(&m.pocket), 215_000);
    assert_eq!(minor(&m.share_gap), 0);
    assert_eq!(m.sent_percent.as_deref(), Some("46,35"));
    assert!(m.warnings.is_empty());
    let f = o.fund.unwrap();
    assert_eq!(minor(&f.balance), 6_520_000);
    assert_eq!(minor(f.balance_home.as_ref().unwrap()), 5_933_200_000);
    assert_eq!(f.months_to_target, Some(13));
    assert_eq!(f.status, "ON_TRACK");

    // Jamg'armadan olish — sabab bilan va qoldiqdan oshmaydi.
    assert_eq!(
        err(app.mf_record_move(&mf, mv("FUND_OUT", "800 000", "2026-10-15"))),
        "REASON_REQUIRED"
    );
    let mut out = mv("FUND_OUT", "7 000 000", "2026-10-15");
    out.note = Some("Uy ta'miri".into());
    assert_eq!(
        err(app.mf_record_move(&mf, out.clone())),
        "RETURN_FUND_INSUFFICIENT"
    );
    out.amount = "800 000".into();
    let o = app.mf_record_move(&mf, out).unwrap();
    let m = o.month.unwrap();
    assert!(m.warnings.contains(&"FUND_WITHDRAWN".to_string()));
    assert_eq!(minor(&o.fund.unwrap().balance), 5_720_000);
    let mut fee = mv("FUND_IN", "1 000", "2026-10-15");
    fee.fee = Some("10".into());
    assert_eq!(err(app.mf_record_move(&mf, fee)), "FIELD_NOT_ALLOWED");

    // Yozuvlar bor — ish valyutasi o'zgarmaydi; ulushni o'zgartirish mumkin.
    assert_eq!(
        err(app.mf_set_settings(&mf, settings("RUB"))),
        "WORK_CURRENCY_LOCKED"
    );
    let mut s = settings("KRW");
    s.share_percent = "25".into();
    let o = app.mf_set_settings(&mf, s).unwrap();
    let st = o.settings.unwrap();
    assert!(st.currency_locked);
    assert_eq!(st.share_bp, 2_500);
    assert_eq!(minor(&o.month.unwrap().share_target), 650_000);
}

#[test]
fn stale_rate_and_same_currency() {
    let (app, mf, _) = setup();
    app.mf_set_settings(&mf, settings("RUB")).unwrap();
    let o = app
        .mf_set_rate(
            &mf,
            MfRateInput {
                rate: "150".into(),
                rate_on: Some("2026-09-01".into()),
                source: None,
            },
        )
        .unwrap();
    assert!(o.rate.unwrap().stale);

    // Ichki migratsiya: ish valyutasi = uy valyutasi — kurs 1, kiritish shart emas.
    let (app, mf, _) = setup();
    let mut s = settings("UZS");
    s.target = None;
    let o = app.mf_set_settings(&mf, s).unwrap();
    assert!(o.rate.unwrap().identity);
    assert_eq!(o.fund.unwrap().status, "NO_TARGET");
    assert_eq!(
        err(app.mf_set_rate(
            &mf,
            MfRateInput {
                rate: "1".into(),
                rate_on: None,
                source: None
            }
        )),
        "RATE_NOT_NEEDED"
    );
}

#[test]
fn musofir_data_travels_to_paired_device() {
    let dir = tempfile::tempdir().unwrap();
    let open = |name: &str, key: u8| {
        let app = App::open(
            &dir.path().join(format!("{name}.db")),
            &DbKey::from_bytes([key; 32]),
            &format!("dev-{name}"),
            clock("2026-10-18T09:00:00+05:00"),
            Arc::new(UuidV7Gen),
        )
        .unwrap();
        app.set_interchange_kdf(64, 1, 1);
        app
    };
    let a = open("phone", 1);
    let h = a
        .bootstrap(BootstrapInput {
            household_name: "Bobur akaning oilasi".into(),
            device_name: "Telefon".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["MUSOFIR".into()],
            members: vec![NewMemberInput {
                display_name: "Bobur".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let mf = h.spaces[0].id.clone();
    a.mf_set_settings(&mf, settings("KRW")).unwrap();
    a.mf_set_rate(
        &mf,
        MfRateInput {
            rate: "9,1".into(),
            rate_on: None,
            source: None,
        },
    )
    .unwrap();
    salary(&a, &mf, "2 600 000", "2026-10-10");
    a.mf_record_move(&mf, mv("FUND_IN", "520 000", "2026-10-10"))
        .unwrap();
    let before = a.mf_overview(&mf, None).unwrap();

    let offer = a
        .pairing_offer(PairingInput {
            role: None,
            space_id: None,
        })
        .unwrap();
    let b = open("laptop", 2);
    b.join_household(
        &offer.bytes,
        JoinInput {
            secret: offer.code.clone(),
            device_name: "Noutbuk".into(),
            platform: "linux".into(),
        },
    )
    .unwrap();
    assert_eq!(b.mf_overview(&mf, None).unwrap(), before);
}
