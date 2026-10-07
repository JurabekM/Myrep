#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use content::{Catalog, ReleaseMode, TaskTrigger, UnlockDecision};
use domain::{date_from_str, Clock, IdGen, OffsetDateTime, PaymentChannel};
use money::{Currency, Money};
use services::{
    audit, income,
    learning::{self, ChapterStatus},
    setup, Ctx, Env, ServiceError, YearMonth,
};
use storage::Database;
use time::Duration;

struct TestClock(Cell<OffsetDateTime>);
impl Clock for TestClock {
    fn now(&self) -> OffsetDateTime {
        self.0.get()
    }
}

struct Seq(Cell<u64>);
impl IdGen for Seq {
    fn new_id(&self) -> String {
        let n = self.0.get();
        self.0.set(n + 1);
        format!("00000000-0000-7000-8000-{n:012}")
    }
}

macro_rules! env {
    ($w:expr) => {
        Env {
            clock: &$w.clock,
            ids: &$w.ids,
            device_id: "dev",
        }
    };
}

struct World {
    db: Database,
    clock: TestClock,
    ids: Seq,
    ctx: Ctx,
    catalog: &'static Catalog,
}

impl World {
    /// 2026-10-07 (chorshanba) 10:00 Toshkent; joriy hafta 2026-10-02 (juma) dan boshlanadi.
    fn new() -> Self {
        let mut db = Database::open_in_memory(&[6; 32]).unwrap();
        let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-07 05:00 UTC)));
        let ids = Seq(Cell::new(1));
        let ctx = setup::ensure_household(
            &mut db,
            &Env {
                clock: &clock,
                ids: &ids,
                device_id: "dev",
            },
        )
        .unwrap();
        Self {
            db,
            clock,
            ids,
            ctx,
            catalog: Catalog::bundled().unwrap(),
        }
    }

    fn days(&self, n: i64) {
        self.clock.0.set(self.clock.0.get() + Duration::days(n));
    }

    fn earn(&mut self) {
        let env = env!(self);
        income::record(
            &mut self.db,
            &env,
            &self.ctx,
            income::NewIncome {
                amount: Money::new(1_000_000, Currency::Uzs),
                source: "DAILY_WORK".into(),
                channel: PaymentChannel::Cash,
                received_on: None,
                share: None,
                member_id: None,
                source_type: None,
            },
        )
        .unwrap();
    }

    fn journey(&mut self) -> learning::Journey {
        let env = env!(self);
        learning::journey(&mut self.db, &env, &self.ctx, self.catalog).unwrap()
    }

    fn detail(
        &mut self,
        id: &str,
        mode: ReleaseMode,
    ) -> Result<learning::ChapterDetail, ServiceError> {
        let env = env!(self);
        learning::chapter_detail(&mut self.db, &env, &self.ctx, self.catalog, id, mode)
    }

    fn set_policy(&mut self, a: u32, b: u32, c: u32) -> Result<(), ServiceError> {
        let env = env!(self);
        learning::set_policy(&mut self.db, &env, &self.ctx, a, b, c)
    }

    fn save_page(&mut self, chapter: &str, body: &str) -> Result<(), ServiceError> {
        let env = env!(self);
        learning::save_page(&mut self.db, &env, &self.ctx, self.catalog, chapter, body)
    }

    fn set_task(&mut self, chapter: &str, task: &str, done: bool) -> Result<(), ServiceError> {
        let env = env!(self);
        learning::set_task_done(
            &mut self.db,
            &env,
            &self.ctx,
            self.catalog,
            chapter,
            task,
            done,
        )
    }

    fn audit_total(
        &mut self,
        month: YearMonth,
        category: &str,
        v: i64,
    ) -> Result<(), ServiceError> {
        let env = env!(self);
        audit::set_category_total(
            &mut self.db,
            &env,
            &self.ctx,
            month,
            category,
            Money::new(v, Currency::Uzs),
        )
    }

    /// Joriy haftada 2 ta vazifa (daromad + ajratma) bajaradi.
    fn good_week(&mut self) {
        self.earn();
    }
}

fn done_ids(j: &learning::Journey) -> Vec<&str> {
    j.week_tasks
        .iter()
        .filter(|t| t.done)
        .map(|t| t.id.as_str())
        .collect()
}

fn status(j: &learning::Journey, id: &str) -> ChapterStatus {
    j.chapters.iter().find(|c| c.id == id).unwrap().status
}

#[test]
fn first_visit_opens_chapter_one_this_week_and_locks_the_rest() {
    let mut w = World::new();
    let j = w.journey();
    assert_eq!(j.current_id, "ch01");
    assert!(j.opened_this_week);
    assert_eq!(j.week_start, date_from_str("2026-10-02").unwrap());
    assert_eq!(j.week_tasks.len(), 3);
    assert!(done_ids(&j).is_empty());
    assert!(matches!(status(&j, "ch01"), ChapterStatus::Opened { .. }));
    for id in ["ch02", "ch03", "ch04", "ch05"] {
        assert_eq!(status(&j, id), ChapterStatus::Locked, "{id}");
    }
    assert_eq!(
        j.unlock,
        Some(UnlockDecision::Locked {
            satisfied_weeks: 0,
            needed_weeks: 2,
            weeks_in_window: 0
        })
    );
}

#[test]
fn opening_is_idempotent() {
    let mut w = World::new();
    let a = w.journey();
    let b = w.journey();
    assert_eq!(a.chapters.len(), b.chapters.len());
    assert_eq!(status(&a, "ch01"), status(&b, "ch01"));
}

#[test]
fn auto_tasks_are_detected_from_app_data() {
    let mut w = World::new();
    w.journey();
    w.earn(); // daromad + ajratma
    let j = w.journey();
    assert_eq!(done_ids(&j), ["ch01-t1", "ch01-t2"]);
    assert!(j.week_tasks.iter().filter(|t| t.done).all(|t| t.auto));

    // Audit: o'tgan oy uchun kamida bitta kategoriya.
    let cat = storage::repo::list::<domain::Category>(w.db.conn(), &w.ctx.household_id).unwrap()[0]
        .meta
        .id
        .clone();
    w.audit_total(YearMonth::parse("2026-09").unwrap(), &cat, 100)
        .unwrap();
    assert_eq!(done_ids(&w.journey()), ["ch01-t1", "ch01-t2", "ch01-t3"]);
}

/// Qabul mezoni (D5): ikki yaxshi hafta → keyingi juma yangi bob ochiladi; vaqt o'zi yetmaydi.
#[test]
fn two_good_weeks_open_chapter_two_on_the_next_friday_only() {
    let mut w = World::new();
    w.journey();
    w.good_week(); // hafta 10-02 (2 vazifa)
    w.days(7);
    w.good_week(); // hafta 10-09 (2 vazifa)

    // 10-14 (chorshanba): ikkinchi hafta hali tugamagan.
    let j = w.journey();
    assert_eq!(status(&j, "ch02"), ChapterStatus::Locked);
    assert_eq!(
        j.unlock,
        Some(UnlockDecision::Locked {
            satisfied_weeks: 1,
            needed_weeks: 2,
            weeks_in_window: 1
        })
    );

    w.days(2); // 10-16: juma
    let j = w.journey();
    assert_eq!(j.current_id, "ch02");
    assert!(j.opened_this_week);
    assert!(matches!(status(&j, "ch02"), ChapterStatus::Opened { .. }));
    assert_eq!(status(&j, "ch03"), ChapterStatus::Locked);
    // Yangi bobning vazifalari yangi hafta uchun nolda boshlanadi.
    assert!(done_ids(&j).iter().all(|id| id.starts_with("ch02")));
}

#[test]
fn time_alone_never_unlocks() {
    let mut w = World::new();
    w.journey();
    w.days(7 * 8);
    let j = w.journey();
    assert_eq!(j.current_id, "ch01");
    assert_eq!(status(&j, "ch02"), ChapterStatus::Locked);
    assert_eq!(
        j.unlock,
        Some(UnlockDecision::Locked {
            satisfied_weeks: 0,
            needed_weeks: 2,
            weeks_in_window: 3
        })
    );
}

#[test]
fn at_most_one_chapter_opens_per_week() {
    let mut w = World::new();
    w.journey();
    for _ in 0..2 {
        w.good_week();
        w.days(7);
    }
    let j = w.journey(); // 10-16 -> ch02 ochildi
    assert_eq!(j.current_id, "ch02");
    // Shu haftaning o'zida qayta chaqirilsa ham ch03 ochilmaydi.
    assert_eq!(w.journey().current_id, "ch02");
}

#[test]
fn unlock_policy_is_configurable_and_validated() {
    let mut w = World::new();
    assert_eq!(
        learning::policy(w.db.conn(), &w.ctx).unwrap(),
        content::UnlockPolicy::DEFAULT
    );
    assert!(w.set_policy(0, 0, 0).is_err());
    assert!(w.set_policy(3, 4, 1).is_err());
    assert!(w.set_policy(3, 1, 4).is_err());
    assert_eq!(
        learning::policy(w.db.conn(), &w.ctx).unwrap(),
        content::UnlockPolicy::DEFAULT
    );

    w.set_policy(2, 1, 1).unwrap();
    w.set_policy(2, 1, 2).unwrap(); // qayta yozish (upsert)
    let p = learning::policy(w.db.conn(), &w.ctx).unwrap();
    assert_eq!(
        (
            p.window_weeks(),
            p.min_satisfied_weeks(),
            p.min_tasks_per_week()
        ),
        (2, 1, 2)
    );

    // Yumshoq shart bilan bitta yaxshi hafta yetadi.
    w.set_policy(3, 1, 1).unwrap();
    w.journey();
    w.good_week();
    w.days(7);
    assert_eq!(w.journey().current_id, "ch02");
}

/// Qabul mezoni (D5): tasdiqlanmagan diniy blok release'da ko'rinmaydi.
#[test]
fn release_hides_pending_religious_blocks_dev_shows_them_marked() {
    let mut w = World::new();
    w.journey();
    let release = w.detail("ch01", ReleaseMode::Release).unwrap();
    assert!(release
        .blocks
        .iter()
        .all(|b| b.source.is_none() && !b.unreviewed));
    assert_eq!(release.blocks.len(), 2);
    let dev = w.detail("ch01", ReleaseMode::Dev).unwrap();
    assert_eq!(dev.blocks.len(), 3);
    assert!(dev
        .blocks
        .iter()
        .any(|b| b.unreviewed && b.source.is_some()));
}

#[test]
fn locked_chapter_cannot_be_read_or_written() {
    let mut w = World::new();
    w.journey();
    assert!(matches!(
        w.detail("ch02", ReleaseMode::Release),
        Err(ServiceError::Invalid(_))
    ));
    assert!(matches!(
        w.detail("nope", ReleaseMode::Release),
        Err(ServiceError::NotFound)
    ));
    assert!(w.save_page("ch02", "x").is_err());
    assert!(w.set_task("ch02", "ch02-t1", true).is_err());
}

#[test]
fn daftar_page_is_saved_updated_and_bounded() {
    let mut w = World::new();
    w.journey();
    assert_eq!(
        w.detail("ch01", ReleaseMode::Release).unwrap().page_body,
        ""
    );
    w.save_page("ch01", "Daromadning o'ndan birini o'zimga ajrataman.")
        .unwrap();
    w.save_page("ch01", "Qayta yozildi").unwrap();
    assert_eq!(
        w.detail("ch01", ReleaseMode::Release).unwrap().page_body,
        "Qayta yozildi"
    );
    w.save_page("ch01", "").unwrap();
    assert_eq!(
        w.detail("ch01", ReleaseMode::Release).unwrap().page_body,
        ""
    );
    let long = "a".repeat(learning::MAX_PAGE_CHARS + 1);
    assert!(w.save_page("ch01", &long).is_err());
    let ok = "ў".repeat(learning::MAX_PAGE_CHARS);
    w.save_page("ch01", &ok).unwrap();
}

#[test]
fn manual_tasks_toggle_for_this_week_only() {
    let mut w = World::new();
    w.journey();
    // ch02 ni ochish uchun yumshoq shart + 1 yaxshi hafta.
    w.set_policy(3, 1, 1).unwrap();
    w.good_week();
    w.days(7);
    assert_eq!(w.journey().current_id, "ch02");

    let manual = w.catalog.chapter("ch02").unwrap().tasks[0].clone();
    assert_eq!(manual.trigger, TaskTrigger::Manual);
    w.set_task("ch02", &manual.id, true).unwrap();
    w.set_task("ch02", &manual.id, true).unwrap(); // idempotent
    let j = w.journey();
    let t = j.week_tasks.iter().find(|t| t.id == manual.id).unwrap();
    assert!(t.done && !t.auto);

    w.set_task("ch02", &manual.id, false).unwrap();
    assert!(
        !w.journey()
            .week_tasks
            .iter()
            .find(|t| t.id == manual.id)
            .unwrap()
            .done
    );
    w.set_task("ch02", &manual.id, true).unwrap();

    // Keyingi haftada belgi qaytadan boshlanadi. (Yumshoq shart ch03 ni ochadi, shuning uchun
    // ch02 vazifalari bob tafsilotidan o'qiladi.)
    w.days(7);
    let again = w.detail("ch02", ReleaseMode::Release).unwrap();
    assert!(!again.tasks.iter().find(|t| t.id == manual.id).unwrap().done);
}

#[test]
fn auto_tasks_cannot_be_toggled_by_hand() {
    let mut w = World::new();
    w.journey();
    assert!(matches!(
        w.set_task("ch01", "ch01-t1", true),
        Err(ServiceError::Invalid(_))
    ));
    assert!(matches!(
        w.set_task("ch01", "nope", true),
        Err(ServiceError::NotFound)
    ));
}

#[test]
fn manual_completions_count_toward_unlocking() {
    let mut w = World::new();
    // ch01 vazifalari avto; unlock uchun 2 ta: daromad+ajratma. Bu testda ikki hafta davomida shuni qilamiz.
    w.journey();
    w.set_policy(3, 2, 3).unwrap(); // 3 ta vazifa talab
    w.earn();
    // audit ham kerak (3-vazifa)
    let cat = storage::repo::list::<domain::Category>(w.db.conn(), &w.ctx.household_id).unwrap()[0]
        .meta
        .id
        .clone();
    for _ in 0..2 {
        w.audit_total(YearMonth::parse("2026-09").unwrap(), &cat, 5)
            .unwrap();
        w.days(7);
        w.earn();
    }
    w.days(2);
    // 1-hafta: 3 vazifa; 2-hafta: 3 vazifa (audit qayta yozildi + daromad) => ochiladi.
    assert_eq!(w.journey().current_id, "ch02");
}
