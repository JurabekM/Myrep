#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K9 — Kasb-kor makonida 8-tamoyil «O'zingizga sarmoya qiling» (docs/kasbkor/SPEC.md 8A): egasining
//! soat qiymati yopilgan oylardan (to'langan maosh qo'shilmaydi), «O'zim qilaymi yoki o'rgatib
//! topshiraymi?», xodimga o'rgatish, «Sarmoya (o'qish)» belgisi va «Hisob kuni» qatori.

use std::sync::Arc;

use baraka_app::*;
use baraka_interchange::tables::{table, TableMode};
use chrono::{DateTime, Utc};

fn clock(at: &str) -> Arc<FixedClock> {
    Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339(at)
            .unwrap()
            .with_timezone(&Utc),
    ))
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

struct Atelier {
    app: App,
    uy: String,
    kk: String,
    member: String,
}

fn setup() -> Atelier {
    let app = App::open_in_memory(
        &DbKey::from_bytes([9; 32]),
        "dev-atelye",
        clock("2026-12-02T10:00:00+05:00"),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    bootstrap(app)
}

fn bootstrap(app: App) -> Atelier {
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Feruzalar".into(),
            device_name: "Atelye kompyuteri".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "KASBKOR".into()],
            members: vec![NewMemberInput {
                display_name: "Feruza".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let id = |k: &str| {
        h.spaces
            .iter()
            .find(|s| s.kind == k)
            .map(|s| s.id.clone())
            .unwrap()
    };
    let member = h.members[0].id.clone();
    Atelier {
        uy: id("UY"),
        kk: id("KASBKOR"),
        member,
        app,
    }
}

fn category(app: &App, space: &str, key: &str) -> String {
    app.categories(space)
        .unwrap()
        .into_iter()
        .find(|c| c.name_key == key)
        .unwrap()
        .id
}

fn expense(category_id: &str, amount: &str, on: &str, invest: bool) -> NewExpenseInput {
    NewExpenseInput {
        amount: amount.into(),
        category_id: category_id.into(),
        channel: "CARD".into(),
        member_id: None,
        occurred_on: Some(on.into()),
        necessity: None,
        obligation_id: None,
        is_gift: false,
        is_ostentation: false,
        funded_by_debt: false,
        note: None,
        self_investment: invest,
        learning_plan_id: None,
        study_debt: None,
    }
}

fn employee() -> KkEmployeeInput {
    KkEmployeeInput {
        name: "Sardor".into(),
        role: Some("Tikuvchi".into()),
        phone: None,
        phone_consent: false,
        duties: Some("Tikish va dazmollash".into()),
        hours: Some("9:00–18:00".into()),
        salary: "2 500 000".into(),
        pay_day: 5,
        notice_days: 14,
        max_advance: None,
        max_advance_installments: None,
        started_on: Some("2026-11-01".into()),
        opening_balance: None,
        arbiter: None,
        review_on: None,
        note: None,
    }
}

fn delegate_input(owner: Option<&str>, helper: &str) -> KkDelegateInput {
    KkDelegateInput {
        task: "Mato qabul qilish".into(),
        agreement_id: None,
        owner_hour_value: owner.map(str::to_string),
        task_minutes: 1_200,
        helper_hour_cost: helper.into(),
        training_money: Some("500 000".into()),
        training_minutes: 600,
    }
}

/// Feruza (kasbkor/SPEC 3.1): noyabr — tushum 18 mln, chiqim 8,5 mln (shundan 300 ming — o'qish),
/// o'z mehnati 5 mln, qizining 80 soati × 15 000, 2 mashina 12 mln / 60 oy → haqiqiy foyda 3,1 mln.
fn november(a: &Atelier) {
    let app = &a.app;
    app.kk_set_owner_labor(&a.kk, "5 000 000".into()).unwrap();
    app.kk_set_owner_salary(&a.kk, "2 000 000".into()).unwrap();
    app.kk_record_sale(
        &a.kk,
        KkSaleInput {
            amount: "18 000 000".into(),
            channel: "CARD".into(),
            occurred_on: Some("2026-11-10".into()),
            note: None,
        },
    )
    .unwrap();
    let materials = category(app, &a.kk, "category.kk.materials");
    let other = category(app, &a.kk, "category.kk.other");
    app.record_expense(&a.kk, expense(&materials, "8 200 000", "2026-11-12", false))
        .unwrap();
    // «Sarmoya (o'qish)»: buxgalteriya kursi — haqiqiy foydani baribir kamaytiradi.
    let course = app
        .record_expense(&a.kk, expense(&other, "300 000", "2026-11-14", true))
        .unwrap();
    assert!(course.self_investment && course.learning_plan_id.is_none());
    app.kk_add_family_labor(
        &a.kk,
        KkFamilyLaborInput {
            person: "Qizi".into(),
            hours: "80".into(),
            hourly_rate: "15 000".into(),
            paid: false,
            worked_on: Some("2026-11-15".into()),
            note: None,
        },
    )
    .unwrap();
    app.kk_add_equipment(
        &a.kk,
        KkEquipmentInput {
            name: "2 ta tikuv mashinasi".into(),
            cost: "12 000 000".into(),
            salvage: None,
            useful_months: 60,
            acquired_on: Some("2026-11-01".into()),
            wallet: None,
        },
    )
    .unwrap();
    // Egasiga 2 mln maosh haqiqatda to'langan — soat qiymatiga qo'shilmaydi.
    app.kk_pay_owner_salary(
        &a.kk,
        KkSalaryInput {
            amount: Some("2 000 000".into()),
            wallet: "CARD".into(),
            occurred_on: Some("2026-11-30".into()),
            note: None,
        },
    )
    .unwrap();
}

#[test]
fn owner_hour_value_comes_from_closed_months_without_salary() {
    let a = setup();
    let app = &a.app;
    november(&a);
    // Yopilgan oy yo'q — taklif yo'q, AUTO hisob chiqmaydi.
    let s = app.kk_owner_hour_suggest(&a.kk).unwrap();
    assert!(s.months.is_empty() && s.average.is_none());
    let auto = KkOwnerHourInput {
        income: None,
        minutes_per_day: 600,
        days: 26,
    };
    assert_eq!(
        err(app.kk_owner_hour_save(&a.kk, auto.clone())),
        "NO_INCOME"
    );

    let draft = app.kk_close_draft(&a.kk, None).unwrap();
    assert_eq!(minor(&draft.true_profit), 310_000_000);
    // «Hisob kuni»: «Sarmoya (o'qish)» — alohida qator, chiqimlar ichida.
    assert_eq!(minor(&draft.self_investment), 30_000_000);
    assert_eq!(minor(&draft.expenses), 850_000_000);
    let closed = app
        .kk_close_month(
            &a.kk,
            KkCloseInput {
                period_start: "2026-11-01".into(),
                carry_overdraw: false,
                explanation: None,
            },
        )
        .unwrap();
    assert_eq!(minor(&closed.summary.self_investment), 30_000_000);
    assert!(!app
        .kk_month_close_pdf(&a.kk, &closed.id)
        .unwrap()
        .is_empty());

    // 8A.1: 5 000 000 + 3 100 000 = 8 100 000 (2 mln maosh qo'shilmaydi).
    let s = app.kk_owner_hour_suggest(&a.kk).unwrap();
    assert_eq!(s.months.len(), 1);
    assert_eq!(minor(&s.months[0].earnings), 810_000_000);
    assert_eq!(minor(&s.months[0].owner_labor), 500_000_000);
    assert_eq!(minor(s.average.as_ref().unwrap()), 810_000_000);
    // O'z mehnati bahosi keyin o'zgarsa ham topgani o'zgarmaydi (qo'shilib-ayiriladi).
    app.kk_set_owner_labor(&a.kk, "4 000 000".into()).unwrap();
    let s2 = app.kk_owner_hour_suggest(&a.kk).unwrap();
    assert_eq!(minor(&s2.months[0].earnings), 810_000_000);

    let h = app.kk_owner_hour_save(&a.kk, auto).unwrap();
    assert_eq!(
        (h.income_source.as_str(), h.months, minor(&h.hour_value)),
        ("AUTO", 1, 3_115_385)
    );
    assert_eq!(minor(&h.double_target), 6_230_770);
    assert!(!h.over_ceiling);
    let manual = app
        .kk_owner_hour_save(
            &a.kk,
            KkOwnerHourInput {
                income: Some("7 000 000".into()),
                minutes_per_day: 600,
                days: 26,
            },
        )
        .unwrap();
    assert_eq!(
        (manual.income_source.as_str(), manual.months),
        ("MANUAL", 0)
    );
    assert_eq!(
        err(app.kk_owner_hour_save(
            &a.kk,
            KkOwnerHourInput {
                income: None,
                minutes_per_day: 600,
                days: 32,
            }
        )),
        "INVALID_WORK_DAYS"
    );
    let o = app.kk_learning_overview(&a.kk, None).unwrap();
    assert_eq!(o.hour_value.unwrap().id, manual.id);
    // Uy makonida — Kasb-kor emas.
    assert_eq!(err(app.kk_owner_hour_suggest(&a.uy)), "NOT_KASBKOR_SPACE");
}

/// Topgani qotirilgan bayonnomadan: yopilgandan keyin sozlamalar (o'z mehnati, oilaviy mehnat,
/// uskuna, oy boshi kuni) o'zgarsa ham taklif o'zgarmaydi — daftar qayta o'ynalmaydi.
#[test]
fn owner_earnings_come_from_the_frozen_close() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("atelye.db");
    let key = DbKey::from_bytes([9; 32]);
    let app = App::open(
        &path,
        &key,
        "dev-atelye",
        clock("2026-12-02T10:00:00+05:00"),
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let a = bootstrap(app);
    november(&a);
    a.app
        .kk_close_month(
            &a.kk,
            KkCloseInput {
                period_start: "2026-11-01".into(),
                carry_overdraw: false,
                explanation: None,
            },
        )
        .unwrap();
    let before = a.app.kk_owner_hour_suggest(&a.kk).unwrap();
    assert_eq!(minor(&before.months[0].earnings), 810_000_000);

    a.app.kk_set_owner_labor(&a.kk, "3 000 000".into()).unwrap();
    // Boshqa qurilmadan kelgan o'zgarishlar kabi: oilaviy mehnat, uskuna muddati, oy boshi kuni.
    let db = baraka_storage::Database::open(&path, &key).unwrap();
    db.write(|tx| {
        tx.execute_batch(
            "UPDATE kk_family_labor SET hours100 = 20000;
             UPDATE kk_equipment SET useful_months = 12;
             UPDATE households SET month_start_day = 15;",
        )?;
        Ok(())
    })
    .unwrap();
    let after = a.app.kk_owner_hour_suggest(&a.kk).unwrap();
    assert_eq!(after, before);
    // Haqiqiy foyda va o'z mehnati — bayonnomadagi qiymatlar.
    assert_eq!(minor(&after.months[0].owner_labor), 500_000_000);
    assert_eq!(minor(&after.months[0].true_profit), 310_000_000);
}

#[test]
fn delegate_calculator_saves_decisions_on_staff_cards() {
    let a = setup();
    let app = &a.app;
    // Soat qiymati saqlanmagan — bo'sh maydon bilan hisob chiqmaydi.
    assert_eq!(
        err(app.kk_delegate_calc(&a.kk, delegate_input(None, "15 000"))),
        "KK_NO_HOUR_VALUE"
    );
    // 8A.2: egasi 31 153,85; yordamchi 15 000; 20 soat; o'rgatish 500 000 + 10 soat.
    let r = app
        .kk_delegate_calc(&a.kk, delegate_input(Some("31 153,85"), "15 000"))
        .unwrap();
    assert_eq!(r.verdict, "DELEGATE");
    assert_eq!(minor(&r.monthly_benefit), 32_307_700);
    assert_eq!(minor(&r.full_cost), 81_153_850);
    assert_eq!(r.payback_months, Some(3));
    let dearer = app
        .kk_delegate_calc(&a.kk, delegate_input(Some("31 153,85"), "40 000"))
        .unwrap();
    assert_eq!(
        (dearer.verdict.as_str(), dearer.payback_months),
        ("SELF_CHEAPER", None)
    );
    assert!(minor(&dearer.monthly_benefit) < 0);
    let mut bad = delegate_input(Some("31 153,85"), "15 000");
    bad.task_minutes = 0;
    assert_eq!(err(app.kk_delegate_calc(&a.kk, bad)), "INVALID_TASK_TIME");

    app.kk_owner_hour_save(
        &a.kk,
        KkOwnerHourInput {
            income: Some("8 100 000".into()),
            minutes_per_day: 600,
            days: 26,
        },
    )
    .unwrap();
    // Bo'sh maydon — oxirgi saqlangan soat qiymati.
    let latest = app
        .kk_delegate_calc(&a.kk, delegate_input(None, "15 000"))
        .unwrap();
    assert_eq!(minor(&latest.owner_hour_value), 3_115_385);

    let staff = app.kk_add_employee(&a.kk, employee()).unwrap();
    let sardor = staff.employees[0].id.clone();
    let supplier = app
        .kk_add_supplier(
            &a.kk,
            KkSupplierInput {
                name: "Mato ombori".into(),
                phone: None,
                phone_consent: false,
                goods: Some("Mato".into()),
                item_id: None,
                unit_price: None,
                payment_days: 0,
                delivery: None,
                returns: None,
                started_on: None,
                arbiter: None,
                review_on: None,
                note: None,
            },
        )
        .unwrap()
        .suppliers[0]
        .id
        .clone();
    let mut linked = delegate_input(None, "15 000");
    linked.agreement_id = Some(supplier);
    let ended = app
        .kk_add_employee(
            &a.kk,
            KkEmployeeInput {
                name: "Avvalgi tikuvchi".into(),
                ..employee()
            },
        )
        .unwrap()
        .employees
        .into_iter()
        .find(|e| e.name == "Avvalgi tikuvchi")
        .unwrap()
        .id;
    app.kk_end_agreement(&a.kk, &ended, Some("2026-11-30".into()))
        .unwrap();
    let mut gone = delegate_input(None, "15 000");
    gone.agreement_id = Some(ended);
    assert_eq!(err(app.kk_delegation_save(&a.kk, gone)), "AGREEMENT_ENDED");
    assert_eq!(
        err(app.kk_delegation_save(&a.kk, linked.clone())),
        "NOT_EMPLOYMENT"
    );
    linked.agreement_id = Some(sardor.clone());
    linked.task = "  ".into();
    assert_eq!(
        err(app.kk_delegation_save(&a.kk, linked.clone())),
        "REQUIRED"
    );
    linked.task = "Mato qabul qilish".into();
    let saved = app.kk_delegation_save(&a.kk, linked).unwrap();
    assert_eq!(saved.staff_name.as_deref(), Some("Sardor"));
    assert_eq!(saved.result.payback_months, Some(3));
    assert_eq!(saved.decided_on, "2026-12-02");

    let o = app.kk_learning_overview(&a.kk, None).unwrap();
    assert_eq!(o.delegations.len(), 1);
    assert_eq!(o.staff.len(), 1);
    assert_eq!(o.staff[0].name, "Sardor");
    app.kk_delegation_delete(&a.kk, &saved.id).unwrap();
    assert!(app
        .kk_learning_overview(&a.kk, None)
        .unwrap()
        .delegations
        .is_empty());
    assert_eq!(err(app.kk_delegation_delete(&a.kk, &saved.id)), "NOT_FOUND");

    // «Ilm zakoti»: kimga — xodim kartochkasidan yoki ism bilan (ikkalasi birga emas).
    let t = app
        .kk_teaching_add(
            &a.kk,
            KkTeachingInput {
                occurred_on: None,
                agreement_id: Some(sardor.clone()),
                learner: None,
                topic: "Buyurtma qabul qilish".into(),
                minutes: Some(90),
            },
        )
        .unwrap();
    assert_eq!(t.learner.as_deref(), Some("Sardor"));
    assert_eq!(
        err(app.kk_teaching_add(
            &a.kk,
            KkTeachingInput {
                occurred_on: None,
                agreement_id: Some(sardor),
                learner: Some("Qizi".into()),
                topic: "Dazmollash".into(),
                minutes: None,
            }
        )),
        "LEARNER_TWICE"
    );
    app.kk_teaching_add(
        &a.kk,
        KkTeachingInput {
            occurred_on: Some("2026-12-01".into()),
            agreement_id: None,
            learner: Some("Qizi".into()),
            topic: "Tugma qadash".into(),
            minutes: None,
        },
    )
    .unwrap();
    let o = app.kk_learning_overview(&a.kk, None).unwrap();
    assert_eq!(o.teaching_count, 2);
    assert_eq!(
        err(app.kk_learning_overview(&a.uy, None)),
        "NOT_KASBKOR_SPACE"
    );
}

#[test]
fn self_investment_flag_in_kasbkor_has_no_plan_link() {
    let a = setup();
    let app = &a.app;
    let other = category(app, &a.kk, "category.kk.other");
    let plan = app
        .learning_plan_create(
            &a.uy,
            LearningPlanInput {
                member_id: a.member.clone(),
                skill: "Buxgalteriya".into(),
                purpose: None,
                paths: vec!["COURSE".into()],
                budget: None,
                weekly_minutes: 120,
                start_on: None,
                review_on: None,
            },
        )
        .unwrap();
    let mut linked = expense(&other, "300 000", "2026-12-01", true);
    linked.learning_plan_id = Some(plan.id.clone());
    assert_eq!(
        err(app.record_expense(&a.kk, linked.clone())),
        "PLAN_LINK_UY_ONLY"
    );
    linked.self_investment = false;
    assert_eq!(err(app.record_expense(&a.kk, linked)), "PLAN_LINK_UY_ONLY");
    app.record_expense(&a.kk, expense(&other, "300 000", "2026-12-01", true))
        .unwrap();
    app.record_expense(&a.kk, expense(&other, "100 000", "2026-12-01", false))
        .unwrap();
    let o = app.kk_learning_overview(&a.kk, None).unwrap();
    assert_eq!(minor(&o.self_investment), 30_000_000);
    // Haqiqiy foydani baribir kamaytiradi: ikkala chiqim ham operatsion.
    let ov = app.kk_overview(&a.kk, None).unwrap();
    assert_eq!(minor(&ov.expenses), 40_000_000);
    // Uy makonida reja havolasi avvalgidek ishlaydi.
    let uy_other = app
        .categories(&a.uy)
        .unwrap()
        .into_iter()
        .next()
        .unwrap()
        .id;
    let mut uy = expense(&uy_other, "50 000", "2026-12-01", true);
    uy.channel = "CASH".into();
    uy.learning_plan_id = Some(plan.id);
    assert!(app.record_expense(&a.uy, uy).is_ok());
}

#[test]
fn new_tables_are_synced() {
    assert_eq!(
        table("kk_owner_hours").map(|t| t.mode),
        Some(TableMode::AppendOnly)
    );
    assert_eq!(
        table("kk_delegations").map(|t| t.mode),
        Some(TableMode::Mutable)
    );
    assert_eq!(
        table("kk_teaching_logs").map(|t| t.mode),
        Some(TableMode::Mutable)
    );
}

/// «Ilm zakoti» sanasi: bo'sh satr — bugun, kelajakdagi sana — `FUTURE_DATE` (uchala makonda bir xil).
#[test]
fn teaching_empty_date_is_today_and_future_is_rejected() {
    let a = setup();
    let input = |on: &str| KkTeachingInput {
        occurred_on: Some(on.into()),
        agreement_id: None,
        learner: None,
        topic: "Narx yorligʻi yozish".into(),
        minutes: Some(20),
    };
    let t = a.app.kk_teaching_add(&a.kk, input("  ")).unwrap();
    assert_eq!(t.occurred_on, "2026-12-02");
    assert_eq!(
        err(a.app.kk_teaching_add(&a.kk, input("2026-12-03"))),
        "FUTURE_DATE"
    );
}
