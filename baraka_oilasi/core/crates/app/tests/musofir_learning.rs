#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! M6 — Musofir makonida 8-tamoyil «O'zingizga sarmoya qiling» (docs/musofir/SPEC.md 6A): Bobur aka
//! (Koreya, zavod, KRW) bir soatining qiymatini vonda va kurs bilan so'mda ko'radi, ikki maqsadli bilim
//! rejasi tuzadi (ish joyidagi koreys tili — chet elda; payvandlash — qaytgandan keyin uyda), kursni
//! tekshiradi, yangi kelgan hamyurtiga hujjatlar bo'yicha yordam berganini yozadi. Hammasi shaxsiy —
//! uydagi oila qurilmasiga yuborilmaydi.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use baraka_app::*;
use baraka_storage::repo::sync;
use baraka_storage::Database;
use chrono::{DateTime, Utc};
use serde_json::{json, Value};

const PASSWORD: &str = "Ozimga-sarmoya-2026!";

fn clock() -> Arc<FixedClock> {
    Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339("2026-10-20T09:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    ))
}

fn bootstrap(app: &App) -> (String, String) {
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Bobur akaning oilasi".into(),
            device_name: "Boburning telefoni".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "MUSOFIR".into()],
            members: vec![
                NewMemberInput {
                    display_name: "Bobur".into(),
                    role: "ADULT".into(),
                },
                NewMemberInput {
                    display_name: "Mohira".into(),
                    role: "ADULT".into(),
                },
            ],
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
            target: Some("120 000 000".into()),
            return_on: Some("2027-12-01".into()),
        },
    )
    .unwrap();
    (mf, uy)
}

fn setup() -> (App, String, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
        "dev-bobur",
        clock(),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let (mf, uy) = bootstrap(&app);
    (app, mf, uy)
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

fn income(app: &App, mf: &str, kind: &str, amount: &str, on: &str) {
    app.mf_record_income(
        mf,
        MfIncomeInput {
            kind: kind.into(),
            amount: amount.into(),
            channel: "CARD".into(),
            occurred_on: Some(on.into()),
            note: None,
        },
    )
    .unwrap();
}

/// Iyul va sentyabr — 2 600 000, avgust — maosh + 150 000 qo'shimcha ish; oktyabr (joriy oy) hisobga kirmaydi.
fn three_months(app: &App, mf: &str) {
    income(app, mf, "SALARY", "2 600 000", "2026-07-10");
    income(app, mf, "SALARY", "2 600 000", "2026-08-10");
    income(app, mf, "OTHER_INCOME", "150 000", "2026-08-20");
    income(app, mf, "SALARY", "2 600 000", "2026-09-10");
    income(app, mf, "SALARY", "2 700 000", "2026-10-10");
}

fn rate(app: &App, mf: &str, r: &str, on: &str) {
    app.mf_set_rate(
        mf,
        MfRateInput {
            rate: r.into(),
            rate_on: Some(on.into()),
            source: Some("Bank".into()),
        },
    )
    .unwrap();
}

fn hour(income: Option<&str>) -> MfHourInput {
    MfHourInput {
        income: income.map(Into::into),
        minutes_per_day: 600,
        days: 22,
    }
}

fn plan(goal: &str, skill: &str, paths: &[&str], idea: Option<&str>) -> MfLearningPlanInput {
    MfLearningPlanInput {
        goal: goal.into(),
        skill: skill.into(),
        purpose: None,
        paths: paths.iter().map(|p| (*p).to_string()).collect(),
        budget: Some("300 000".into()),
        weekly_minutes: 240,
        start_on: None,
        review_on: None,
        venture_idea_id: idea.map(Into::into),
    }
}

fn expense(app: &App, mf: &str, amount: &str, invest: bool) -> MfOverviewDto {
    let cat = app.categories(mf).unwrap()[0].id.clone();
    app.mf_record_expense(
        mf,
        MfExpenseInput {
            amount: amount.into(),
            category_id: cat,
            channel: "CARD".into(),
            occurred_on: Some("2026-10-12".into()),
            note: Some("Til kursi".into()),
            self_investment: invest,
        },
    )
    .unwrap()
}

fn idea(app: &App, uy: &str) -> String {
    let sc = |name: &str, income: &str| IdeaScenarioInput {
        name: name.into(),
        income: income.into(),
        expense: "4 000 000".into(),
    };
    app.create_venture_idea(
        uy,
        VentureIdeaInput {
            title: "Payvandlash ustaxonasi".into(),
            skill_id: None,
            capex: vec![CapexLineInput {
                title: "Payvandlash apparati".into(),
                amount: "12 000 000".into(),
            }],
            scenarios: vec![
                sc("PESSIMISTIC", "5 000 000"),
                sc("BASE", "7 000 000"),
                sc("OPTIMISTIC", "9 000 000"),
            ],
            worker_share_bp: None,
        },
    )
    .unwrap()
    .id
}

#[test]
fn hour_value_in_work_currency_and_home_only_with_rate() {
    let (app, mf, _) = setup();
    assert_eq!(
        err(app.mf_hour_save(&mf, hour(None))),
        "NO_INCOME",
        "daromad yozuvi yo'q — taxmin yo'q"
    );
    three_months(&app, &mf);
    let s = app.mf_hour_suggest(&mf).unwrap();
    let totals: Vec<i64> = s.months.iter().map(|m| minor(&m.total)).collect();
    // Yangisidan eskisiga: sentyabr, avgust (maosh + boshqa daromad), iyul.
    assert_eq!(totals, [2_600_000, 2_750_000, 2_600_000]);
    assert_eq!(s.months[0].period_start, "2026-09-01");
    assert_eq!(s.months[0].period_end, "2026-09-30");
    assert_eq!(minor(s.average.as_ref().unwrap()), 2_650_000);
    assert_eq!(s.average.as_ref().unwrap().currency, "KRW");

    // mhv-002: kurs yo'q — uy valyutasidagi qiymat umuman yo'q.
    let h = app.mf_hour_save(&mf, hour(None)).unwrap();
    assert_eq!((h.income_source.as_str(), h.months), ("AUTO", 3));
    assert_eq!(minor(&h.hour_value), 12_045);
    assert_eq!(h.hour_value.currency, "KRW");
    assert_eq!(minor(&h.double_target), 24_090);
    assert_eq!(h.home.rate_status, "NO_RATE");
    assert!(h.home.hour_value.is_none() && h.home.double_target.is_none() && h.home.rate.is_none());

    // Eski kurs (49 kun) — qiymat bor, «yangilang» belgisi bilan.
    rate(&app, &mf, "9,0", "2026-09-01");
    let o = app.mf_learning_overview(&mf, None).unwrap();
    let home = &o.hour_value.as_ref().unwrap().home;
    assert_eq!(home.rate_status, "STALE");
    assert_eq!(minor(home.hour_value.as_ref().unwrap()), 10_840_500);
    assert!(home.rate.as_ref().unwrap().stale);

    // mhv-001: yangi kurs — 12 045 × 9,1 = 109 609,50 so'm; ikki barobar — 2 × shu.
    rate(&app, &mf, "9,1", "2026-10-15");
    let o = app.mf_learning_overview(&mf, None).unwrap();
    assert_eq!(
        (o.work_currency.as_str(), o.home_currency.as_str()),
        ("KRW", "UZS")
    );
    let home = &o.hour_value.as_ref().unwrap().home;
    assert_eq!(home.rate_status, "FRESH");
    assert_eq!(minor(home.hour_value.as_ref().unwrap()), 10_960_950);
    assert_eq!(home.hour_value.as_ref().unwrap().currency, "UZS");
    assert_eq!(minor(home.double_target.as_ref().unwrap()), 21_921_900);
    assert_eq!(home.rate.as_ref().unwrap().rate, "9,1");

    // Qo'lda kiritilgan daromad ustun (MANUAL, 0 oy); soat chegarasi — Uy bilan bir xil.
    let m = app
        .mf_hour_save(
            &mf,
            MfHourInput {
                income: Some("3 000 000".into()),
                minutes_per_day: 720,
                days: 26,
            },
        )
        .unwrap();
    assert_eq!((m.income_source.as_str(), m.months), ("MANUAL", 0));
    assert_eq!(minor(&m.hour_value), 9_615);
    assert!(m.over_ceiling);
    assert_eq!(
        err(app.mf_hour_save(
            &mf,
            MfHourInput {
                income: None,
                minutes_per_day: 600,
                days: 32,
            }
        )),
        "INVALID_WORK_DAYS"
    );
}

#[test]
fn same_currency_needs_no_rate() {
    let app = App::open_in_memory(
        &DbKey::from_bytes([8; 32]),
        "dev-farrux",
        clock(),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let (mf, _) = bootstrap(&app);
    // Ichki migratsiya: ish valyutasi = uy valyutasi (yozuvlar hali yo'q — o'zgartirish mumkin).
    app.mf_set_settings(
        &mf,
        MfSettingsInput {
            country: None,
            work_currency: "UZS".into(),
            share_percent: "20".into(),
            target: None,
            return_on: None,
        },
    )
    .unwrap();
    let h = app.mf_hour_save(&mf, hour(Some("6 500 000"))).unwrap();
    assert_eq!(h.home.rate_status, "SAME_CURRENCY");
    assert_eq!(h.home.hour_value, Some(h.hour_value.clone()));
}

#[test]
fn two_goal_plans_respect_limit_and_transitions() {
    let (app, mf, uy) = setup();
    three_months(&app, &mf);
    let base = app.mf_hour_save(&mf, hour(None)).unwrap();
    let welding = idea(&app, &uy);
    assert_eq!(
        err(app.mf_learning_plan_create(&mf, plan("SOMEWHERE", "Til", &["BOOK"], None))),
        "INVALID_GOAL"
    );
    // «Hunardan ishga» g'oyasi — faqat uyga qaytgandan keyingi hunar rejasida.
    assert_eq!(
        err(app.mf_learning_plan_create(&mf, plan("ABROAD", "Til", &["BOOK"], Some(&welding)))),
        "IDEA_HOME_ONLY"
    );
    assert_eq!(
        err(app.mf_learning_plan_create(&mf, plan("HOME", "Payvandlash", &["MENTOR"], Some("yoq")))),
        "NOT_FOUND"
    );
    let abroad = app
        .mf_learning_plan_create(
            &mf,
            plan(
                "ABROAD",
                "Ish joyidagi koreys tili (TOPIK 2)",
                &["COURSE", "BOOK", "COURSE"],
                None,
            ),
        )
        .unwrap();
    assert_eq!(abroad.goal, "ABROAD");
    assert_eq!(abroad.paths, ["BOOK", "COURSE"]);
    assert!(abroad.course_check_suggested);
    assert_eq!(abroad.budget.as_ref().unwrap().currency, "KRW");
    assert_eq!(minor(abroad.baseline_hour_value.as_ref().unwrap()), 12_045);
    assert_eq!(abroad.review_on, "2027-01-20");
    let home = app
        .mf_learning_plan_create(
            &mf,
            plan(
                "HOME",
                "Payvandlash",
                &["MENTOR", "PRACTICE"],
                Some(&welding),
            ),
        )
        .unwrap();
    assert_eq!(
        home.venture_idea_title.as_deref(),
        Some("Payvandlash ustaxonasi")
    );
    // Ikki maqsad birga — bir odam: 3-faol reja yo'q.
    assert_eq!(
        err(app.mf_learning_plan_create(&mf, plan("ABROAD", "Guvohnoma", &["COURSE"], None))),
        "ACTIVE_PLAN_LIMIT"
    );
    app.mf_learning_plan_set_status(&mf, &home.id, "PAUSED")
        .unwrap();
    let third = app
        .mf_learning_plan_create(
            &mf,
            plan("ABROAD", "Forklift guvohnomasi", &["COURSE"], None),
        )
        .unwrap();
    assert_eq!(
        err(app.mf_learning_plan_set_status(&mf, &home.id, "ACTIVE")),
        "ACTIVE_PLAN_LIMIT"
    );
    app.mf_learning_plan_set_status(&mf, &third.id, "DROPPED")
        .unwrap();
    assert_eq!(
        app.mf_learning_plan_set_status(&mf, &home.id, "ACTIVE")
            .unwrap()
            .status,
        "ACTIVE"
    );
    assert_eq!(
        err(app.mf_learning_plan_set_status(&mf, &third.id, "ACTIVE")),
        "INVALID_TRANSITION"
    );
    // Natija: yangi hisob bo'lmaguncha o'lchanmaydi; keyin farq — va'dasiz, faqat raqam.
    assert_eq!(
        err(app.mf_learning_plan_result(&mf, &abroad.id)),
        "NO_NEW_HOUR_VALUE"
    );
    app.mf_hour_save(&mf, hour(Some("2 915 000"))).unwrap();
    let r = app.mf_learning_plan_result(&mf, &abroad.id).unwrap();
    assert_eq!(r.baseline.as_ref().unwrap().id, base.id);
    assert_eq!(minor(&r.current.hour_value), 13_250);
    assert_eq!(minor(r.diff.as_ref().unwrap()), 1_205);
    assert_eq!(r.change_percent.as_deref(), Some("10"));
    let o = app.mf_learning_overview(&mf, None).unwrap();
    assert_eq!(o.active_plans, 2);
    assert_eq!(o.plans.len(), 3);
    assert_eq!(o.ideas.len(), 1);
    assert_eq!(
        minor(o.plans[0].result_hour_value.as_ref().unwrap()),
        13_250
    );
}

#[test]
fn self_investment_flag_keeps_category_share_and_fund() {
    let (app, mf, _) = setup();
    three_months(&app, &mf);
    let before = app.mf_overview(&mf, None).unwrap().month.unwrap();
    assert_eq!(minor(&before.self_investment.total), 0);
    expense(&app, &mf, "400 000", false);
    let plain = app.mf_overview(&mf, None).unwrap();
    // Bir xil summa — «Sarmoya» belgisi bilan: oy hisobi (xarajat, qo'ldagi pul, ulush maqsadi) o'zgarmaydi.
    let o = expense(&app, &mf, "135 000", true);
    let m = o.month.as_ref().unwrap();
    assert_eq!(minor(&m.expenses), 535_000);
    assert_eq!(
        minor(&m.share_target),
        minor(&plain.month.as_ref().unwrap().share_target)
    );
    assert_eq!(minor(&m.share_target), 540_000);
    assert_eq!(minor(&m.fund_net), 0);
    assert_eq!(minor(&o.fund.as_ref().unwrap().balance), 0);
    // «Oʻzimga sarmoya: 135 000 KRW — daromadning 5 %».
    assert_eq!(minor(&m.self_investment.total), 135_000);
    assert_eq!(m.self_investment.total.currency, "KRW");
    assert_eq!(minor(&m.self_investment.income), 2_700_000);
    assert_eq!(m.self_investment.share_percent.as_deref(), Some("5"));
    let flagged: Vec<bool> = o
        .entries
        .iter()
        .filter(|e| e.kind == "EXPENSE")
        .map(|e| e.self_investment)
        .collect();
    assert_eq!(flagged.iter().filter(|f| **f).count(), 1);
    // Toifa o'zgarmaydi; zaxira pul va jamg'arma harakatlari yo'q.
    let cat = app.categories(&mf).unwrap()[0].id.clone();
    assert!(o
        .entries
        .iter()
        .filter(|e| e.kind == "EXPENSE")
        .all(|e| e.category_id.as_deref() == Some(cat.as_str())));
    assert_eq!(minor(&m.reserve_in), 0);
    let l = app.mf_learning_overview(&mf, None).unwrap();
    assert_eq!(l.self_investment, m.self_investment);
}

#[test]
fn teaching_log_counts_help_for_newcomers() {
    let (app, mf, _) = setup();
    let t = app
        .mf_teaching_add(
            &mf,
            MfTeachingInput {
                occurred_on: Some("2026-10-18".into()),
                area: "DOCUMENTS".into(),
                learner: Some("Yangi kelgan hamyurt".into()),
                topic: "Chet ellik karta va bank hisobini ochish".into(),
                minutes: Some(60),
            },
        )
        .unwrap();
    assert_eq!(t.area, "DOCUMENTS");
    app.mf_teaching_add(
        &mf,
        MfTeachingInput {
            occurred_on: None,
            area: "LANGUAGE".into(),
            learner: None,
            topic: "Sexdagi xavfsizlik so'zlari".into(),
            minutes: None,
        },
    )
    .unwrap();
    let bad = |area: &str, topic: &str, minutes: Option<u32>, on: Option<&str>| {
        err(app.mf_teaching_add(
            &mf,
            MfTeachingInput {
                occurred_on: on.map(Into::into),
                area: area.into(),
                learner: None,
                topic: topic.into(),
                minutes,
            },
        ))
    };
    assert_eq!(bad("MONEY", "x", None, None), "INVALID_AREA");
    assert_eq!(bad("WORK", "  ", None, None), "REQUIRED");
    assert_eq!(bad("WORK", "x", Some(0), None), "INVALID_TIME");
    assert_eq!(bad("WORK", "x", None, Some("2026-10-21")), "FUTURE_DATE");
    let o = app.mf_learning_overview(&mf, None).unwrap();
    assert_eq!(o.teaching_count, 2);
    assert_eq!(
        o.teaching[0].topic,
        "Chet ellik karta va bank hisobini ochish"
    );
    // Boshqa oy — yozuv yo'q.
    assert_eq!(
        app.mf_learning_overview(&mf, Some("2026-09-15"))
            .unwrap()
            .teaching_count,
        0
    );
}

#[test]
fn only_musofir_space_and_configured() {
    let (app, mf, uy) = setup();
    assert_eq!(
        err(app.mf_learning_overview(&uy, None)),
        "NOT_MUSOFIR_SPACE"
    );
    assert_eq!(err(app.mf_hour_suggest(&uy)), "NOT_MUSOFIR_SPACE");
    // Umumiy (Uy) xarajat yo'lida Musofir makonida «Sarmoya» belgisi rad — belgi faqat
    // `mf_record_expense` orqali, ish valyutasida.
    let cat = app.categories(&mf).unwrap()[0].id.clone();
    assert_eq!(
        err(app.record_expense(
            &mf,
            NewExpenseInput {
                amount: "1 000".into(),
                category_id: cat,
                channel: "CASH".into(),
                member_id: None,
                occurred_on: None,
                necessity: None,
                obligation_id: None,
                is_gift: false,
                is_ostentation: false,
                funded_by_debt: false,
                note: None,
                self_investment: true,
                learning_plan_id: None,
                study_debt: None,
            },
        )),
        "NOT_UY_SPACE"
    );
    // Course tekshiruvi: Musofir savoli `jobAbroad` — o'zi qizil.
    let course = |job: Option<&str>| {
        app.check_course(CourseAnswersInput {
            fast_rich: "NO".into(),
            secret_formula: "NO".into(),
            income_guarantee: "NO".into(),
            syllabus: "YES".into(),
            teacher_verifiable: "YES".into(),
            urgency: "NO".into(),
            recruitment: "NO".into(),
            trial_or_refund: "YES".into(),
            job_abroad: job.map(Into::into),
        })
        .unwrap()
    };
    assert_eq!(course(None).verdict, "GREEN");
    let red = course(Some("YES"));
    assert_eq!(red.verdict, "RED");
    assert!(red.flags.iter().any(|f| f.code == "JOB_ABROAD_PROMISE"));
    assert_eq!(course(Some("UNKNOWN")).verdict, "YELLOW");
}

// ---- Maxfiylik: uydagi oila qurilmasi (HOME, ADR-0004) ----

struct Device {
    path: PathBuf,
    key: DbKey,
    id: String,
    clock: Arc<FixedClock>,
}

impl Device {
    fn new(dir: &Path, name: &str, key: u8) -> Self {
        Self {
            path: dir.join(format!("{name}.db")),
            key: DbKey::from_bytes([key; 32]),
            id: format!("dev-{name}"),
            clock: clock(),
        }
    }

    fn app(&self) -> App {
        let app = App::open(
            &self.path,
            &self.key,
            &self.id,
            self.clock.clone(),
            Arc::new(UuidV7Gen),
        )
        .unwrap();
        app.set_interchange_kdf(64, 1, 1);
        app
    }

    fn rows(&self, table: &str) -> Vec<serde_json::Map<String, Value>> {
        Database::open(&self.path, &self.key)
            .unwrap()
            .read(|c| {
                let hid: String = c.query_row("SELECT id FROM households", [], |r| r.get(0))?;
                sync::dump(c, &hid, table)
            })
            .unwrap()
    }
}

#[test]
fn home_device_never_receives_hour_value_plans_or_teaching() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "bobur", 1);
    let home_dev = Device::new(dir.path(), "uy", 2);
    let owner = owner_dev.app();
    let (mf, uy) = bootstrap(&owner);
    three_months(&owner, &mf);
    rate(&owner, &mf, "9,1", "2026-10-15");
    owner.mf_hour_save(&mf, hour(None)).unwrap();
    let welding = idea(&owner, &uy);
    owner
        .mf_learning_plan_create(
            &mf,
            plan("HOME", "Payvandlash", &["MENTOR"], Some(&welding)),
        )
        .unwrap();
    owner
        .mf_teaching_add(
            &mf,
            MfTeachingInput {
                occurred_on: None,
                area: "WORK".into(),
                learner: None,
                topic: "Smena jadvalini o'qish".into(),
                minutes: Some(30),
            },
        )
        .unwrap();
    expense(&owner, &mf, "135 000", true);
    for t in ["mf_hour_values", "mf_learning_plans", "mf_teaching_logs"] {
        assert_eq!(owner_dev.rows(t).len(), 1, "{t}");
    }

    let offer = owner
        .pairing_offer(PairingInput {
            role: Some("HOME".into()),
            space_id: Some(mf.clone()),
        })
        .unwrap();
    let home = home_dev.app();
    home.join_household(
        &offer.bytes,
        JoinInput {
            secret: offer.code.clone(),
            device_name: "Uydagi kompyuter".into(),
            platform: "windows".into(),
        },
    )
    .unwrap();
    // Keyingi almashishdan keyin ham (oila → musofir, yangi yozuv, musofir → oila) — yo'q.
    let export = |app: &App, peer: &str| {
        app.export_baraka(ExportInput {
            password: PASSWORD.into(),
            mode: "INCREMENTAL".into(),
            peer_device_id: Some(peer.into()),
        })
        .unwrap()
    };
    let back = export(&home, &owner_dev.id);
    owner.apply_baraka(&back.bytes, PASSWORD, vec![]).unwrap();
    owner.mf_hour_save(&mf, hour(Some("2 900 000"))).unwrap();
    let file = export(&owner, &home_dev.id);
    home.apply_baraka(&file.bytes, PASSWORD, vec![]).unwrap();
    assert_eq!(owner_dev.rows("mf_hour_values").len(), 2);
    assert_eq!(home.device_role().unwrap().role, "HOME");
    for t in ["mf_hour_values", "mf_learning_plans", "mf_teaching_logs"] {
        assert!(
            home_dev.rows(t).is_empty(),
            "{t}: maoshdan hisoblangan shaxsiy yozuv oilaga yuborilmasligi kerak"
        );
    }
    // Sarmoya belgili chet el xarajati ham (chet eldagi xarajatlar — shaxsiy).
    assert!(home_dev
        .rows("expenses")
        .iter()
        .all(|r| r["space_id"] != json!(mf)));
    // Uy makonidagi g'oya — oilaga umumiy.
    assert_eq!(home_dev.rows("venture_ideas").len(), 1);
    // Yadro: shaxsiy bo'lim oila qurilmasida yopiq.
    assert_eq!(err(home.mf_learning_overview(&mf, None)), "ROLE_FORBIDDEN");
    assert_eq!(err(home.mf_hour_suggest(&mf)), "ROLE_FORBIDDEN");
    assert_eq!(
        err(home.mf_hour_save(&mf, hour(Some("1")))),
        "ROLE_FORBIDDEN"
    );
    assert_eq!(
        err(home.mf_teaching_add(
            &mf,
            MfTeachingInput {
                occurred_on: None,
                area: "WORK".into(),
                learner: None,
                topic: "x".into(),
                minutes: None,
            }
        )),
        "ROLE_FORBIDDEN"
    );
}

#[test]
fn tables_are_in_the_sync_registry() {
    use baraka_interchange::tables::{table, TableMode};
    assert_eq!(
        table("mf_hour_values").map(|t| t.mode),
        Some(TableMode::AppendOnly)
    );
    for t in ["mf_learning_plans", "mf_teaching_logs"] {
        assert_eq!(table(t).map(|t| t.mode), Some(TableMode::Mutable), "{t}");
    }
}

/// Ko'rik sanasi: yo'q yoki bo'sh satr — standart +3 oy (Uy bilan bitta qoida).
#[test]
fn empty_review_date_means_default_three_months() {
    let (app, mf, _) = setup();
    let mut p = plan("ABROAD", "Ish joyidagi koreys tili", &["BOOK"], None);
    p.review_on = Some(String::new());
    assert_eq!(
        app.mf_learning_plan_create(&mf, p.clone())
            .unwrap()
            .review_on,
        "2027-01-20"
    );
    p.review_on = Some("ertaga".into());
    assert_eq!(
        app.mf_learning_plan_create(&mf, p)
            .unwrap_err()
            .field
            .as_deref(),
        Some("reviewOn")
    );
}

/// Bo'sh sanalar — bugun (reja boshlanishi va «Ilm zakoti»), Uy bilan bitta qoida.
#[test]
fn empty_start_and_teaching_dates_mean_today() {
    let (app, mf, _) = setup();
    let mut p = plan("ABROAD", "Ish joyidagi koreys tili", &["BOOK"], None);
    p.start_on = Some("  ".into());
    let a = app.mf_learning_plan_create(&mf, p).unwrap();
    assert_eq!(
        (a.start_on.as_str(), a.review_on.as_str()),
        ("2026-10-20", "2027-01-20")
    );
    let t = app
        .mf_teaching_add(
            &mf,
            MfTeachingInput {
                occurred_on: Some(String::new()),
                area: "WORK".into(),
                learner: None,
                topic: "Smena jadvali".into(),
                minutes: None,
            },
        )
        .unwrap();
    assert_eq!(t.occurred_on, "2026-10-20");
}

/// Faol rejalar chegarasi bir vaqtdagi so'rovlarda ham: sanoq va yozuv bitta tranzaksiyada.
#[test]
fn concurrent_plan_creates_never_exceed_the_limit() {
    let (app, mf, _) = setup();
    let codes: Vec<Result<(), String>> = std::thread::scope(|s| {
        let handles: Vec<_> = (0..8)
            .map(|i| {
                let (app, mf) = (&app, &mf);
                s.spawn(move || {
                    app.mf_learning_plan_create(
                        mf,
                        plan("ABROAD", &format!("Koʻnikma {i}"), &["BOOK"], None),
                    )
                    .map(|_| ())
                    .map_err(|e| e.code)
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).collect()
    });
    assert_eq!(codes.iter().filter(|c| c.is_ok()).count(), 2);
    assert!(codes
        .iter()
        .filter_map(|c| c.as_ref().err())
        .all(|c| c == "ACTIVE_PLAN_LIMIT"));
    assert_eq!(app.mf_learning_overview(&mf, None).unwrap().active_plans, 2);
}

/// Javob tayyorlanmasa (bu yerda — buzilgan kurs yozuvi), o'zgarmas soat qiymati ham, reja natijasi
/// ham saqlanmaydi.
#[test]
fn failed_save_or_result_leaves_nothing_behind() {
    let dir = tempfile::tempdir().unwrap();
    let dev = Device::new(dir.path(), "bobur", 3);
    let app = dev.app();
    let (mf, _) = bootstrap(&app);
    three_months(&app, &mf);
    app.mf_hour_save(&mf, hour(None)).unwrap();
    let p = app
        .mf_learning_plan_create(&mf, plan("ABROAD", "Til", &["BOOK"], None))
        .unwrap();
    app.mf_hour_save(&mf, hour(Some("2 915 000"))).unwrap();
    // Sanasi o'qilmaydigan kurs (bugungacha eng so'nggisi bo'lib tanlanadi).
    Database::open(&dev.path, &dev.key)
        .unwrap()
        .write(|tx| {
            let hid: String = tx.query_row("SELECT id FROM households", [], |r| r.get(0))?;
            tx.execute(
                "INSERT INTO mf_rates (id, household_id, space_id, rate_on, from_currency, to_currency,
                    rate_num, rate_den, created_at, origin_device_id)
                 VALUES ('bad', ?1, ?2, '2026-0x-01', 'KRW', 'UZS', 91, 10, '2026-10-20T00:00:00Z', 'dev')",
                [hid.as_str(), mf.as_str()],
            )?;
            Ok(())
        })
        .unwrap();
    assert_eq!(
        err(app.mf_hour_save(&mf, hour(Some("1 000 000")))),
        "CORRUPT_ROW"
    );
    assert_eq!(dev.rows("mf_hour_values").len(), 2);
    assert_eq!(err(app.mf_learning_plan_result(&mf, &p.id)), "CORRUPT_ROW");
    let plans = dev.rows("mf_learning_plans");
    assert_eq!(plans[0]["result_hour_value_id"], Value::Null);
}

/// Juma ritmi (6A «Ilm zakoti»): rejasi yoki soat qiymati bor musofirga — shu hafta o'rgatish yozuvi
/// bo'lmasa, juma eslatmasi (Musofir rejasida o'qish vaqti yozuvi yo'q — faqat «Ilm zakoti»). Shaxsiy:
/// uydagi oila qurilmasida (HOME) Musofir bosh sahifasida eslatma yo'q.
#[test]
fn friday_teaching_nudge_is_private_to_the_musofir() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "bobur", 1);
    let home_dev = Device::new(dir.path(), "uy", 2);
    let owner = owner_dev.app();
    let (mf, uy) = bootstrap(&owner);
    let kinds = |app: &App, space: &str| {
        app.home_nudges(space)
            .unwrap()
            .into_iter()
            .map(|n| n.kind)
            .collect::<Vec<_>>()
    };
    let friday = DateTime::parse_from_rfc3339("2026-10-23T09:00:00+05:00")
        .unwrap()
        .with_timezone(&Utc);
    owner_dev.clock.set(friday);
    // Hali hech narsa boshlanmagan.
    assert!(kinds(&owner, &mf).is_empty());
    owner
        .mf_learning_plan_create(&mf, plan("ABROAD", "Koreys tili", &["COURSE"], None))
        .unwrap();
    assert_eq!(kinds(&owner, &mf), ["MF_TEACH_WEEK"]);
    // Musofir rejasi Uy a'zosiniki emas — Uy bosh sahifasida juma eslatmasi yo'q.
    assert!(kinds(&owner, &uy).iter().all(|k| !k.ends_with("_WEEK")));

    let offer = owner
        .pairing_offer(PairingInput {
            role: Some("HOME".into()),
            space_id: Some(mf.clone()),
        })
        .unwrap();
    let home = home_dev.app();
    home.join_household(
        &offer.bytes,
        JoinInput {
            secret: offer.code.clone(),
            device_name: "Uydagi kompyuter".into(),
            platform: "windows".into(),
        },
    )
    .unwrap();
    home_dev.clock.set(friday);
    assert_eq!(home.device_role().unwrap().role, "HOME");
    assert!(kinds(&home, &mf).is_empty());

    owner
        .mf_teaching_add(
            &mf,
            MfTeachingInput {
                occurred_on: None,
                area: "DOCUMENTS".into(),
                learner: Some("yangi kelgan hamyurt".into()),
                topic: "Ijara shartnomasini oʻqish".into(),
                minutes: Some(40),
            },
        )
        .unwrap();
    assert!(kinds(&owner, &mf).is_empty());
}
