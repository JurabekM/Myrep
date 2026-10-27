#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U16b — 8-tamoyil «O'zingizga sarmoya qiling» (docs/uy/SPEC.md 2G): soat qiymati taklifi va
//! hisoblari, bilim rejasi (2 ta faol reja chegarasi, holat o'tishlari), natijani o'lchash, o'qish
//! vaqti, «Ilm zakoti», «O'zimga sarmoya» belgisi (havas chegarasiga kirmaydi) va `.baraka` round-trip.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use baraka_app::*;
use baraka_interchange::canon::Row;
use baraka_storage::repo::sync;
use baraka_storage::Database;
use chrono::{DateTime, Utc};

const PASSWORD: &str = "Baraka-2026!";
const LEARNING_TABLES: [&str; 5] = [
    "learning_hour_values",
    "learning_plans",
    "learning_study_logs",
    "teaching_logs",
    "expenses",
];

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
            clock: Arc::new(FixedClock::new(
                DateTime::parse_from_rfc3339("2026-11-20T09:00:00+05:00")
                    .unwrap()
                    .with_timezone(&Utc),
            )),
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

    fn db(&self) -> Database {
        Database::open(&self.path, &self.key).unwrap()
    }
}

struct Home {
    app: App,
    uy: String,
    kk: String,
    bekzod: String,
    mohira: String,
    feruza: String,
}

fn home(dev: &Device) -> Home {
    let app = dev.app();
    let member = |n: &str| NewMemberInput {
        display_name: n.into(),
        role: "ADULT".into(),
    };
    let h = app
        .bootstrap(BootstrapInput {
            income_rhythm: None,
            debts_declared: false,
            household_name: "Bekzodlar oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "KASBKOR".into()],
            members: vec![member("Bekzod"), member("Mohira"), member("Feruza")],
        })
        .unwrap();
    let space = |k: &str| h.spaces.iter().find(|s| s.kind == k).unwrap().id.clone();
    let m = |n: &str| {
        h.members
            .iter()
            .find(|x| x.display_name == n)
            .unwrap()
            .id
            .clone()
    };
    let o = Home {
        uy: space("UY"),
        kk: space("KASBKOR"),
        bekzod: m("Bekzod"),
        mohira: m("Mohira"),
        feruza: m("Feruza"),
        app,
    };
    // Bekzod: avgust, sentabr (ikki yozuv), oktabr — oxirgi 3 to'liq oy; iyul (4-oy) va noyabr
    // (joriy oy) hisobga kirmaydi. Mohira: faqat oktabr. Feruza: daromad yozuvi yo'q.
    for (who, amount, on, kind) in [
        (&o.bekzod, "50 000 000", "2026-07-10", "TER"),
        (&o.bekzod, "6 000 000", "2026-08-05", "TER"),
        (&o.bekzod, "5 000 000", "2026-09-05", "TER"),
        (&o.bekzod, "2 500 000", "2026-09-25", "TER"),
        (&o.bekzod, "9 000 000", "2026-10-05", "TER"),
        (&o.mohira, "3 000 000", "2026-10-12", "TER"),
        (&o.bekzod, "20 000 000", "2026-11-05", "TER"),
        // Foiz daromadi (ribo) — halol daromad o'rtachasiga kirmaydi (2G.1).
        (&o.bekzod, "4 000 000", "2026-10-20", "RIBO"),
        (&o.feruza, "1 000 000", "2026-10-20", "RIBO"),
    ] {
        o.app
            .record_income(
                &o.uy,
                NewIncomeInput {
                    amount: amount.into(),
                    source: "Taksi".into(),
                    channel: "CARD".into(),
                    member_id: Some(who.clone()),
                    occurred_on: Some(on.into()),
                    source_type: Some(kind.into()),
                    note: None,
                },
            )
            .unwrap();
    }
    o
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

fn hv(member: &str, income: Option<&str>, minutes_per_day: u32, days: u32) -> HourValueInput {
    HourValueInput {
        member_id: member.into(),
        income: income.map(Into::into),
        minutes_per_day,
        days,
    }
}

fn plan(member: &str, skill: &str, paths: &[&str]) -> LearningPlanInput {
    LearningPlanInput {
        member_id: member.into(),
        skill: skill.into(),
        purpose: Some("Buyurtmalar narxi oshadi".into()),
        paths: paths.iter().map(|p| (*p).into()).collect(),
        budget: Some("1 500 000".into()),
        weekly_minutes: 240,
        start_on: Some("2026-11-20".into()),
        review_on: None,
    }
}

fn study(minutes: u32) -> StudyLogInput {
    StudyLogInput {
        occurred_on: Some("2026-11-20".into()),
        minutes,
        note: None,
    }
}

fn teach(member: &str, topic: &str, on: &str) -> TeachingLogInput {
    TeachingLogInput {
        member_id: member.into(),
        occurred_on: Some(on.into()),
        learner: Some("qo\u{2bb}shni".into()),
        topic: topic.into(),
        minutes: Some(45),
    }
}

fn expense(
    o: &Home,
    amount: &str,
    key: &str,
    self_investment: bool,
    plan_id: Option<&str>,
) -> Result<ExpenseDto, AppError> {
    expense_in(o, &o.uy, amount, Some(key), self_investment, plan_id, None)
}

fn expense_in(
    o: &Home,
    space: &str,
    amount: &str,
    key: Option<&str>,
    self_investment: bool,
    plan_id: Option<&str>,
    member: Option<&str>,
) -> Result<ExpenseDto, AppError> {
    let cat = o
        .app
        .categories(space)
        .unwrap()
        .into_iter()
        .find(|c| key.is_none_or(|k| c.name_key == k))
        .unwrap()
        .id;
    o.app.record_expense(
        space,
        NewExpenseInput {
            amount: amount.into(),
            category_id: cat,
            channel: "CARD".into(),
            member_id: member.map(Into::into),
            occurred_on: Some("2026-11-10".into()),
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: None,
            self_investment,
            learning_plan_id: plan_id.map(Into::into),
        },
    )
}

#[test]
fn suggestion_uses_last_three_full_months_with_records() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    // 3 oy: (6 + 7,5 + 9) / 3 = 7,5 mln.
    let s = o.app.hour_value_suggest(&o.uy, &o.bekzod).unwrap();
    let months: Vec<(&str, i64)> = s
        .months
        .iter()
        .map(|m| (m.period_start.as_str(), minor(&m.total)))
        .collect();
    assert_eq!(
        months,
        vec![
            ("2026-10-01", 900_000_000),
            ("2026-09-01", 750_000_000),
            ("2026-08-01", 600_000_000)
        ]
    );
    assert_eq!(s.average.as_ref().map(minor), Some(750_000_000));
    // 1 oy: faqat yozuvi bor oy.
    let s = o.app.hour_value_suggest(&o.uy, &o.mohira).unwrap();
    assert_eq!(s.months.len(), 1);
    assert_eq!(s.average.as_ref().map(minor), Some(300_000_000));
    // 0 oy (faqat ribo yozuvi bor): taklif yo'q, avtomatik hisob sababini aytadi.
    let s = o.app.hour_value_suggest(&o.uy, &o.feruza).unwrap();
    assert!(s.months.is_empty() && s.average.is_none());
    assert_eq!(
        err(o.app.hour_value_save(&o.uy, hv(&o.feruza, None, 480, 22))),
        "NO_INCOME"
    );
    // Faqat Uy makonida; begona a'zo — topilmadi.
    assert_eq!(
        err(o.app.hour_value_suggest(&o.kk, &o.bekzod)),
        "NOT_UY_SPACE"
    );
    assert_eq!(err(o.app.hour_value_suggest(&o.uy, "nobody")), "NOT_FOUND");
}

#[test]
fn hour_value_snapshots_auto_and_manual() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let auto = o
        .app
        .hour_value_save(&o.uy, hv(&o.bekzod, None, 480, 22))
        .unwrap();
    assert_eq!(auto.income_source, "AUTO");
    assert_eq!(minor(&auto.income), 750_000_000);
    assert_eq!(auto.monthly_minutes, 10_560);
    // 750 000 000 × 60 / 10 560 = 4 261 363,6 → 4 261 364 tiyin.
    assert_eq!(minor(&auto.hour_value), 4_261_364);
    assert_eq!(minor(&auto.double_target), 8_522_728);
    assert!(!auto.over_ceiling);
    assert_eq!(auto.computed_on, "2026-11-20");

    let manual = o
        .app
        .hour_value_save(&o.uy, hv(&o.mohira, Some("7 200 000"), 600, 26))
        .unwrap();
    assert_eq!(manual.income_source, "MANUAL");
    assert_eq!(minor(&manual.hour_value), 2_769_231);
    assert!(!manual.over_ceiling);
    let long = o
        .app
        .hour_value_save(&o.uy, hv(&o.mohira, Some("7 200 000"), 660, 26))
        .unwrap();
    assert!(long.over_ceiling);

    assert_eq!(
        err(o
            .app
            .hour_value_save(&o.uy, hv(&o.mohira, Some("0"), 480, 22))),
        "NO_INCOME"
    );
    assert_eq!(
        err(o
            .app
            .hour_value_save(&o.uy, hv(&o.mohira, Some("1"), 0, 22))),
        "INVALID_TIME"
    );
    let bad_days = o
        .app
        .hour_value_save(&o.uy, hv(&o.mohira, Some("1"), 480, 32))
        .unwrap_err();
    assert_eq!(
        (bad_days.code.as_str(), bad_days.field.as_deref()),
        ("INVALID_WORK_DAYS", Some("days"))
    );

    // Tarix o'zgarmaydi: oxirgi hisob — eng so'nggisi.
    let ov = o.app.learning_overview(&o.uy, None).unwrap();
    let mohira = ov.members.iter().find(|m| m.member_id == o.mohira).unwrap();
    assert_eq!(mohira.hour_value.as_ref().unwrap().id, long.id);
    let feruza = ov.members.iter().find(|m| m.member_id == o.feruza).unwrap();
    assert!(feruza.hour_value.is_none());
}

#[test]
fn active_plan_limit_on_open_and_resume_and_closed_stays_closed() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let a = o
        .app
        .learning_plan_create(
            &o.uy,
            plan(
                &o.bekzod,
                "  Buxgalteriya dasturi ",
                &["COURSE", "BOOK", "COURSE"],
            ),
        )
        .unwrap();
    assert_eq!(a.skill, "Buxgalteriya dasturi");
    assert_eq!(a.paths, vec!["BOOK", "COURSE"]);
    assert_eq!(a.review_on, "2027-02-20");
    assert_eq!(a.status, "ACTIVE");
    assert!(a.course_check_suggested);
    assert!(a.baseline_hour_value.is_none());
    assert_eq!(a.budget.as_ref().map(minor), Some(150_000_000));
    let b = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Ingliz tili", &["MENTOR"]))
        .unwrap();
    assert!(!b.course_check_suggested);
    // 3-faol reja — yo'q; boshqa a'zoda chegara alohida.
    assert_eq!(
        err(o
            .app
            .learning_plan_create(&o.uy, plan(&o.bekzod, "Payvandlash", &["PRACTICE"]))),
        "ACTIVE_PLAN_LIMIT"
    );
    o.app
        .learning_plan_create(&o.uy, plan(&o.mohira, "Tikuvchilik", &["PRACTICE"]))
        .unwrap();

    // To'xtatilgan reja hisobga kirmaydi, lekin qayta faollashtirishda chegara tekshiriladi.
    o.app
        .learning_plan_set_status(&o.uy, &b.id, "PAUSED")
        .unwrap();
    let c = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Payvandlash", &["PRACTICE"]))
        .unwrap();
    assert_eq!(
        err(o.app.learning_plan_set_status(&o.uy, &b.id, "ACTIVE")),
        "ACTIVE_PLAN_LIMIT"
    );
    // Yopilgan reja qayta ochilmaydi.
    o.app
        .learning_plan_set_status(&o.uy, &a.id, "DONE")
        .unwrap();
    assert_eq!(
        err(o.app.learning_plan_set_status(&o.uy, &a.id, "ACTIVE")),
        "INVALID_TRANSITION"
    );
    assert_eq!(
        err(o.app.learning_plan_set_status(&o.uy, &c.id, "STOPPED")),
        "INVALID_STATUS"
    );
    // Endi bitta faol reja bor — qayta faollashtirish mumkin.
    let b = o
        .app
        .learning_plan_set_status(&o.uy, &b.id, "ACTIVE")
        .unwrap();
    assert_eq!(b.status, "ACTIVE");

    // Validatsiya xatolari domendan.
    let mut bad = plan(&o.feruza, " ", &["BOOK"]);
    assert_eq!(
        err(o.app.learning_plan_create(&o.uy, bad.clone())),
        "SKILL_REQUIRED"
    );
    bad.skill = "Hisob".into();
    bad.paths = vec![];
    assert_eq!(
        err(o.app.learning_plan_create(&o.uy, bad.clone())),
        "PATH_REQUIRED"
    );
    bad.paths = vec!["VIDEO".into()];
    assert_eq!(
        err(o.app.learning_plan_create(&o.uy, bad.clone())),
        "INVALID_PATH"
    );
    bad.paths = vec!["BOOK".into()];
    bad.review_on = Some("2026-11-20".into());
    assert_eq!(
        err(o.app.learning_plan_create(&o.uy, bad)),
        "INVALID_REVIEW_DATE"
    );
}

#[test]
fn result_compares_latest_hour_value_with_baseline() {
    let dir = tempfile::tempdir().unwrap();
    let dev = Device::new(dir.path(), "desk", 1);
    let o = home(&dev);
    let base = o
        .app
        .hour_value_save(&o.uy, hv(&o.bekzod, None, 480, 22))
        .unwrap();
    let p = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Buxgalteriya", &["COURSE"]))
        .unwrap();
    assert_eq!(p.baseline_hour_value.as_ref().map(minor), Some(4_261_364));
    // Boshlang'ich nuqtadan keyin yangi hisob yo'q — o'lchanmaydi.
    assert_eq!(
        err(o.app.learning_plan_result(&o.uy, &p.id)),
        "NO_NEW_HOUR_VALUE"
    );

    dev.clock.advance(chrono::Duration::days(93));
    o.app
        .hour_value_save(&o.uy, hv(&o.bekzod, Some("15 000 000"), 480, 22))
        .unwrap();
    let r = o.app.learning_plan_result(&o.uy, &p.id).unwrap();
    assert_eq!(r.baseline.as_ref().unwrap().id, base.id);
    assert_eq!(minor(&r.current.hour_value), 8_522_727);
    assert_eq!(r.diff.as_ref().map(minor), Some(4_261_363));
    assert_eq!(r.change_bp, Some(10_000));
    assert_eq!(r.change_percent.as_deref(), Some("100"));
    let card = o.app.learning_overview(&o.uy, None).unwrap();
    let card = card.plans.iter().find(|x| x.id == p.id).unwrap();
    assert_eq!(card.result_hour_value.as_ref().map(minor), Some(8_522_727));
    // Ko'rik sanasi keldi.
    assert!(card.review_due);
    // Ochiq reja qayta o'lchanadi; yopilgan reja — natijasi bo'lmasa bir marta, keyin yo'q.
    assert_eq!(
        o.app.learning_plan_result(&o.uy, &p.id).unwrap().change_bp,
        Some(10_000)
    );
    let closed = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Hisobot", &["BOOK"]))
        .unwrap();
    o.app
        .learning_plan_set_status(&o.uy, &closed.id, "DONE")
        .unwrap();
    dev.clock.advance(chrono::Duration::days(1));
    o.app
        .hour_value_save(&o.uy, hv(&o.bekzod, Some("16 000 000"), 480, 22))
        .unwrap();
    let once = o.app.learning_plan_result(&o.uy, &closed.id).unwrap();
    assert_eq!(minor(&once.current.income), 1_600_000_000);
    assert_eq!(
        err(o.app.learning_plan_result(&o.uy, &closed.id)),
        "PLAN_CLOSED"
    );

    // Boshlang'ich nuqtasiz reja: foiz va farq chiqmaydi, faqat yangi qiymat.
    let q = o
        .app
        .learning_plan_create(&o.uy, plan(&o.feruza, "Dasturlash", &["BOOK"]))
        .unwrap();
    assert_eq!(
        err(o.app.learning_plan_result(&o.uy, &q.id)),
        "NO_HOUR_VALUE"
    );
    o.app
        .hour_value_save(&o.uy, hv(&o.feruza, Some("4 000 000"), 480, 22))
        .unwrap();
    let r = o.app.learning_plan_result(&o.uy, &q.id).unwrap();
    assert!(r.baseline.is_none() && r.diff.is_none() && r.change_bp.is_none());
    assert_eq!(minor(&r.current.income), 400_000_000);
}

#[test]
fn study_and_teaching_logs() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let p = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Buxgalteriya", &["BOOK"]))
        .unwrap();
    o.app.study_log_add(&o.uy, &p.id, study(120)).unwrap();
    let card = o.app.study_log_add(&o.uy, &p.id, study(90)).unwrap();
    assert_eq!(card.study_minutes, 210);
    assert_eq!(
        err(o.app.study_log_add(&o.uy, &p.id, study(0))),
        "INVALID_TIME"
    );
    assert_eq!(
        err(o.app.study_log_add(&o.uy, "missing", study(10))),
        "NOT_FOUND"
    );
    o.app
        .learning_plan_set_status(&o.uy, &p.id, "DROPPED")
        .unwrap();
    assert_eq!(
        err(o.app.study_log_add(&o.uy, &p.id, study(30))),
        "PLAN_CLOSED"
    );

    let t = o
        .app
        .teaching_log_add(
            &o.uy,
            teach(&o.bekzod, "  Smetani hisoblash ", "2026-11-14"),
        )
        .unwrap();
    assert_eq!(t.topic, "Smetani hisoblash");
    assert_eq!(t.minutes, Some(45));
    o.app
        .teaching_log_add(&o.uy, teach(&o.mohira, "Bichish", "2026-11-18"))
        .unwrap();
    o.app
        .teaching_log_add(&o.uy, teach(&o.mohira, "Tikish", "2026-10-30"))
        .unwrap();
    assert_eq!(
        err(o
            .app
            .teaching_log_add(&o.uy, teach(&o.mohira, "  ", "2026-11-18"))),
        "REQUIRED"
    );
    let mut long = teach(&o.mohira, "Dars", "2026-11-18");
    long.minutes = Some(0);
    assert_eq!(err(o.app.teaching_log_add(&o.uy, long)), "INVALID_TIME");
    let ov = o.app.learning_overview(&o.uy, None).unwrap();
    assert_eq!(ov.teaching_count, 2);
    let oct = o.app.learning_overview(&o.uy, Some("2026-10-15")).unwrap();
    assert_eq!(oct.teaching_count, 1);
}

#[test]
fn self_investment_is_outside_havas_limit_and_has_its_own_row() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let p = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Buxgalteriya", &["COURSE"]))
        .unwrap();
    // Havas toifasidagi kurs puli — toifa o'zgarmaydi.
    let course = expense(&o, "1 200 000", "category.entertainment", true, Some(&p.id)).unwrap();
    assert_eq!(course.necessity.as_deref(), Some("HAVAS"));
    assert!(course.self_investment);
    assert_eq!(course.learning_plan_id.as_deref(), Some(p.id.as_str()));
    let book = expense(&o, "450 000", "category.child_education", true, None).unwrap();
    assert_eq!(book.necessity.as_deref(), Some("KERAK"));
    expense(&o, "1 000 000", "category.snacks", false, None).unwrap();

    // Havola faqat belgi bilan va mavjud rejaga.
    assert_eq!(
        err(expense(&o, "10 000", "category.snacks", false, Some(&p.id))),
        "SELF_INVESTMENT_REQUIRED"
    );
    assert_eq!(
        err(expense(
            &o,
            "10 000",
            "category.snacks",
            true,
            Some("missing")
        )),
        "NOT_FOUND"
    );

    // Xarajat a'zosi — reja a'zosi bo'lishi shart.
    let other = expense_in(
        &o,
        &o.uy,
        "10 000",
        Some("category.snacks"),
        true,
        Some(&p.id),
        Some(&o.mohira),
    );
    assert_eq!(err(other), "PLAN_MEMBER_MISMATCH");
    let own = expense_in(
        &o,
        &o.uy,
        "50 000",
        Some("category.snacks"),
        true,
        Some(&p.id),
        Some(&o.bekzod),
    )
    .unwrap();
    assert_eq!(own.learning_plan_id.as_deref(), Some(p.id.as_str()));
    // Yopilgan rejaga bog'lanmaydi.
    let dropped = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Payvandlash", &["PRACTICE"]))
        .unwrap();
    o.app
        .learning_plan_set_status(&o.uy, &dropped.id, "DROPPED")
        .unwrap();
    assert_eq!(
        err(expense(
            &o,
            "10 000",
            "category.snacks",
            true,
            Some(&dropped.id)
        )),
        "PLAN_CLOSED"
    );
    // K9: Kasb-kor chiqimida ham «Sarmoya (o'qish)» belgisi bor, lekin bilim rejasiga bog'lanmaydi.
    assert_eq!(
        err(expense_in(
            &o,
            &o.kk,
            "10 000",
            None,
            true,
            Some(&p.id),
            None
        )),
        "PLAN_LINK_UY_ONLY"
    );
    assert!(
        expense_in(&o, &o.kk, "10 000", None, true, None, None)
            .unwrap()
            .self_investment
    );
    expense_in(&o, &o.kk, "60 000", None, false, None, None).unwrap();
    let kk = o
        .app
        .monthly_summary(&o.kk, Some("2026-11-20"), None)
        .unwrap();
    assert_eq!(minor(&kk.self_investment.total), 1_000_000);
    assert_eq!(minor(&kk.expenses), 7_000_000);

    let s = o
        .app
        .monthly_summary(&o.uy, Some("2026-11-20"), None)
        .unwrap();
    assert_eq!(minor(&s.by_necessity.havas), 225_000_000);
    assert_eq!(minor(&s.havas_for_limit), 100_000_000);
    assert_eq!(minor(&s.self_investment.total), 170_000_000);
    // 1 700 000 / 20 000 000 = 8,5 %.
    assert_eq!(minor(&s.self_investment.income), 2_000_000_000);
    assert_eq!(s.self_investment.share_bp, Some(850));
    assert_eq!(s.self_investment.share_percent.as_deref(), Some("8,5"));

    let ov = o.app.learning_overview(&o.uy, None).unwrap();
    assert_eq!(ov.self_investment, s.self_investment);
    let card = ov.plans.iter().find(|x| x.id == p.id).unwrap();
    assert_eq!(minor(&card.spent), 125_000_000);
    assert_eq!(card.spent.currency, card.budget.as_ref().unwrap().currency);
    let bekzod = ov.members.iter().find(|m| m.member_id == o.bekzod).unwrap();
    assert_eq!(bekzod.active_plans, 1);
    assert_eq!(ov.period_start, "2026-11-01");

    // Daromadsiz oy: ulush chiqmaydi.
    let dec = o.app.learning_overview(&o.uy, Some("2026-12-05")).unwrap();
    assert_eq!(minor(&dec.self_investment.total), 0);
    assert_eq!(dec.self_investment.share_bp, None);
}

#[test]
fn course_check_uses_shared_detector() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let safe = CourseAnswersInput {
        fast_rich: "NO".into(),
        secret_formula: "NO".into(),
        income_guarantee: "NO".into(),
        syllabus: "YES".into(),
        teacher_verifiable: "YES".into(),
        urgency: "NO".into(),
        recruitment: "NO".into(),
        trial_or_refund: "YES".into(),
        job_abroad: None,
    };
    let r = o.app.check_course(safe.clone()).unwrap();
    assert_eq!(
        (r.verdict.as_str(), r.flags.len(), r.signs),
        ("GREEN", 0, 0)
    );
    let r = o
        .app
        .check_course(CourseAnswersInput {
            income_guarantee: "YES".into(),
            ..safe.clone()
        })
        .unwrap();
    assert_eq!(r.verdict, "RED");
    assert_eq!(r.flags[0].code, "INCOME_GUARANTEE");
    let r = o
        .app
        .check_course(CourseAnswersInput {
            syllabus: "UNKNOWN".into(),
            ..safe.clone()
        })
        .unwrap();
    assert_eq!((r.verdict.as_str(), r.signs), ("YELLOW", 0));
    let bad = o
        .app
        .check_course(CourseAnswersInput {
            job_abroad: Some("MAYBE".into()),
            ..safe
        })
        .unwrap_err();
    assert_eq!(
        (bad.code.as_str(), bad.field.as_deref()),
        ("INVALID_ANSWER", Some("jobAbroad"))
    );
}

fn dump(db: &Database, household: &str, table: &str) -> Vec<Row> {
    db.read(|c| sync::dump(c, household, table)).unwrap()
}

#[test]
fn export_import_round_trip_keeps_learning_data() {
    let dir = tempfile::tempdir().unwrap();
    let desk_dev = Device::new(dir.path(), "desk", 1);
    let o = home(&desk_dev);
    o.app
        .hour_value_save(&o.uy, hv(&o.bekzod, None, 480, 22))
        .unwrap();
    let p = o
        .app
        .learning_plan_create(&o.uy, plan(&o.bekzod, "Buxgalteriya", &["COURSE"]))
        .unwrap();
    o.app.study_log_add(&o.uy, &p.id, study(60)).unwrap();
    o.app
        .teaching_log_add(&o.uy, teach(&o.bekzod, "Smeta", "2026-11-14"))
        .unwrap();
    expense(&o, "1 200 000", "category.entertainment", true, Some(&p.id)).unwrap();

    // Ulash fayli: telefon nusxasi 1:1.
    let offer = o
        .app
        .pairing_offer(PairingInput {
            role: None,
            space_id: None,
        })
        .unwrap();
    let phone_dev = Device::new(dir.path(), "phone", 2);
    let phone = phone_dev.app();
    phone
        .join_household(
            &offer.bytes,
            JoinInput {
                secret: offer.code.clone(),
                device_name: "Bekzodning telefoni".into(),
                platform: "android".into(),
            },
        )
        .unwrap();
    let household = o.app.household().unwrap().id;
    let (desk_db, phone_db) = (desk_dev.db(), phone_dev.db());
    for t in LEARNING_TABLES {
        let rows = dump(&desk_db, &household, t);
        assert!(!rows.is_empty(), "{t}");
        assert_eq!(dump(&phone_db, &household, t), rows, "{t}");
    }
    let linked = dump(&phone_db, &household, "expenses")
        .into_iter()
        .find(|r| r["learning_plan_id"] == serde_json::json!(p.id))
        .unwrap();
    assert_eq!(linked["self_investment"], serde_json::json!(1));

    // Telefonda yangi yozuvlar — inkremental fayl bilan kompyuterga.
    phone.study_log_add(&o.uy, &p.id, study(45)).unwrap();
    phone
        .learning_plan_set_status(&o.uy, &p.id, "PAUSED")
        .unwrap();
    phone
        .hour_value_save(&o.uy, hv(&o.mohira, Some("7 200 000"), 600, 26))
        .unwrap();
    let file = phone
        .export_baraka(ExportInput {
            password: PASSWORD.into(),
            mode: "INCREMENTAL".into(),
            peer_device_id: Some(desk_dev.id.clone()),
        })
        .unwrap();
    let res = o.app.apply_baraka(&file.bytes, PASSWORD, vec![]).unwrap();
    assert_eq!(res.conflicts_local + res.conflicts_remote + res.rejected, 0);
    let ov = o.app.learning_overview(&o.uy, None).unwrap();
    let card = ov.plans.iter().find(|x| x.id == p.id).unwrap();
    assert_eq!((card.study_minutes, card.status.as_str()), (105, "PAUSED"));
    assert_eq!(minor(&card.spent), 120_000_000);
    let mohira = ov.members.iter().find(|m| m.member_id == o.mohira).unwrap();
    assert_eq!(
        mohira.hour_value.as_ref().map(|h| minor(&h.hour_value)),
        Some(2_769_231)
    );
    for t in LEARNING_TABLES {
        assert_eq!(
            dump(&desk_dev.db(), &household, t),
            dump(&phone_dev.db(), &household, t),
            "{t}"
        );
    }
}

/// Ko'rik sanasi: yo'q yoki bo'sh satr — standart +3 oy (Musofir bilan bitta qoida); noto'g'ri sana —
/// `INVALID_DATE`.
#[test]
fn empty_review_date_means_default_three_months() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let mut p = plan(&o.bekzod, "Buxgalteriya dasturi", &["BOOK"]);
    p.review_on = Some("  ".into());
    let a = o.app.learning_plan_create(&o.uy, p.clone()).unwrap();
    assert_eq!(a.review_on, "2027-02-20");
    p.review_on = Some("20-02-2027".into());
    assert_eq!(
        o.app
            .learning_plan_create(&o.uy, p)
            .unwrap_err()
            .field
            .as_deref(),
        Some("reviewOn")
    );
}

/// Bo'sh sanalar — bugun (boshlanish va «Ilm zakoti»); kelajakdagi o'rgatish sanasi — `FUTURE_DATE`.
#[test]
fn empty_start_and_teaching_dates_mean_today() {
    let dir = tempfile::tempdir().unwrap();
    let o = home(&Device::new(dir.path(), "desk", 1));
    let mut p = plan(&o.bekzod, "Buxgalteriya dasturi", &["BOOK"]);
    p.start_on = Some(String::new());
    p.review_on = Some(" ".into());
    let a = o.app.learning_plan_create(&o.uy, p).unwrap();
    assert_eq!(
        (a.start_on.as_str(), a.review_on.as_str()),
        ("2026-11-20", "2027-02-20")
    );
    let t = o
        .app
        .teaching_log_add(&o.uy, teach(&o.bekzod, "Smeta tuzish", " "))
        .unwrap();
    assert_eq!(t.occurred_on, "2026-11-20");
    assert_eq!(
        o.app
            .teaching_log_add(&o.uy, teach(&o.bekzod, "Smeta tuzish", "2026-11-21"))
            .unwrap_err()
            .code,
        "FUTURE_DATE"
    );
}
