#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, CeremonyKind, CeremonyStatus, Clock, Date, FundingSource, IdGen, OffsetDateTime,
};
use money::{Currency, Money};
use services::{
    ceremonies::{self, NewLine},
    goals, setup, Ctx, Env, ServiceError,
};
use storage::Database;

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
}

fn uzs(v: i64) -> Money {
    Money::new(v, Currency::Uzs)
}

fn d(s: &str) -> Date {
    date_from_str(s).unwrap()
}

impl World {
    fn new() -> Self {
        let mut db = Database::open_in_memory(&[9; 32]).unwrap();
        let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-08 05:00 UTC)));
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
        }
    }

    fn plan(&mut self, name: &str, date: Option<Date>) -> String {
        let env = env!(self);
        ceremonies::create(
            &mut self.db,
            &env,
            &self.ctx,
            name,
            CeremonyKind::Wedding,
            date,
        )
        .unwrap()
        .plan
        .meta
        .id
    }

    fn line(&mut self, plan: &str, name: &str, qty: u32, price: i64, f: FundingSource) {
        let env = env!(self);
        ceremonies::add_line(
            &mut self.db,
            &env,
            &self.ctx,
            NewLine {
                plan_id: plan,
                name,
                qty,
                unit_price: uzs(price),
                funding: f,
            },
        )
        .unwrap();
    }

    fn get(&self, id: &str) -> ceremonies::PlanView {
        ceremonies::get(self.db.conn(), &self.ctx, id).unwrap()
    }

    fn status(&mut self, id: &str, s: CeremonyStatus) -> Result<(), ServiceError> {
        let env = env!(self);
        ceremonies::set_status(&mut self.db, &env, &self.ctx, id, s)
    }
}

#[test]
fn totals_follow_funding_sources() {
    let mut w = World::new();
    let p = w.plan("O'g'il to'yi", Some(d("2027-05-01")));
    w.line(&p, "Osh", 200, 15_000_000, FundingSource::Savings);
    w.line(&p, "Xonanda", 1, 500_000_000, FundingSource::Debt);
    w.line(&p, "Sarpo", 3, 100_000_000, FundingSource::Family);
    let v = w.get(&p);
    assert_eq!(v.totals.total.minor(), 3_800_000_000);
    assert_eq!(v.totals.savings.minor(), 3_000_000_000);
    assert_eq!(v.totals.debt.minor(), 500_000_000);
    assert_eq!(v.totals.family.minor(), 300_000_000);
    assert_eq!(v.totals.debt_bp, 1_316);
    assert_eq!(v.lines.len(), 3);
    assert_eq!(v.confirm_blocker, Some("DISCUSSION_REQUIRED"));
}

#[test]
fn line_validation() {
    let mut w = World::new();
    let p = w.plan("X", None);
    let env = env!(w);
    fn bad<'a>(p: &'a str, name: &'a str, qty: u32, price: i64) -> NewLine<'a> {
        NewLine {
            plan_id: p,
            name,
            qty,
            unit_price: uzs(price),
            funding: FundingSource::Savings,
        }
    }
    assert!(ceremonies::add_line(&mut w.db, &env, &w.ctx, bad(&p, "Osh", 0, 1)).is_err());
    assert!(ceremonies::add_line(&mut w.db, &env, &w.ctx, bad(&p, "Osh", 1, -1)).is_err());
    assert!(ceremonies::add_line(&mut w.db, &env, &w.ctx, bad(&p, "  ", 1, 1)).is_err());
    assert!(
        ceremonies::add_line(&mut w.db, &env, &w.ctx, bad(&p, "Osh", u32::MAX, i64::MAX)).is_err()
    );
    assert!(ceremonies::create(&mut w.db, &env, &w.ctx, "", CeremonyKind::Other, None).is_err());
    assert!(w.get(&p).lines.is_empty());
}

/// Qabul mezoni (D11): muhokamasiz `CONFIRMED` ga o'tib bo'lmaydi.
#[test]
fn debt_funded_plan_cannot_be_confirmed_without_discussion() {
    let mut w = World::new();
    let p = w.plan("To'y", Some(d("2027-05-01")));
    w.line(&p, "Osh", 10, 100, FundingSource::Debt);
    let e = w.status(&p, CeremonyStatus::Confirmed).unwrap_err();
    assert!(matches!(e, ServiceError::Invalid(m) if m.contains("muhokama")));
    assert_eq!(w.get(&p).plan.status, CeremonyStatus::Draft);

    let env = env!(w);
    assert!(ceremonies::record_discussion(&mut w.db, &env, &w.ctx, &p, "  ").is_err());
    ceremonies::record_discussion(&mut w.db, &env, &w.ctx, &p, "Kichikroq doirada o'tkazamiz")
        .unwrap();
    assert_eq!(w.get(&p).confirm_blocker, None);
    w.status(&p, CeremonyStatus::Confirmed).unwrap();
    assert_eq!(w.get(&p).plan.status, CeremonyStatus::Confirmed);
}

#[test]
fn debt_free_plan_needs_only_a_date_and_changes_reopen_it() {
    let mut w = World::new();
    let p = w.plan("Beshik to'y", None);
    w.line(&p, "Osh", 10, 100, FundingSource::Savings);
    let e = w.status(&p, CeremonyStatus::Confirmed).unwrap_err();
    assert!(matches!(e, ServiceError::Invalid(m) if m.contains("sana")));
    let env = env!(w);
    ceremonies::set_date(&mut w.db, &env, &w.ctx, &p, Some(d("2027-01-01"))).unwrap();
    w.status(&p, CeremonyStatus::Confirmed).unwrap();

    // Qator o'zgarsa — qayta tasdiqlash kerak.
    w.line(&p, "Musiqa", 1, 50, FundingSource::Debt);
    let v = w.get(&p);
    assert_eq!(v.plan.status, CeremonyStatus::Draft);
    assert_eq!(v.confirm_blocker, Some("DISCUSSION_REQUIRED"));
    // Sanani olib tashlash ham tasdiqni bekor qiladi.
    let q = w.plan("Ikkinchi", Some(d("2027-02-02")));
    w.line(&q, "Osh", 1, 1, FundingSource::Savings);
    w.status(&q, CeremonyStatus::Confirmed).unwrap();
    ceremonies::set_date(&mut w.db, &env!(w), &w.ctx, &q, None).unwrap();
    assert_eq!(w.get(&q).plan.status, CeremonyStatus::Draft);
}

#[test]
fn comparison_shows_debt_repayment_and_alternative_goals() {
    let mut w = World::new();
    let big = w.plan("3 kunlik, 200 kishi", None);
    w.line(&big, "Osh", 200, 15_000_000, FundingSource::Savings);
    w.line(&big, "Boshqa", 1, 2_000_000_000, FundingSource::Debt);
    let small = w.plan("1 kunlik, 100 kishi", None);
    w.line(&small, "Osh", 100, 15_000_000, FundingSource::Savings);
    w.line(&small, "Boshqa", 1, 300_000_000, FundingSource::Debt);
    let env = env!(w);
    goals::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Qizim kontrakti",
        uzs(2_000_000_000),
        None,
    )
    .unwrap();

    let ids = vec![big.clone(), small.clone()];
    let cmp = ceremonies::compare(w.db.conn(), &w.ctx, &ids, Some(uzs(100_000_000)), 0).unwrap();
    assert_eq!(cmp.len(), 2);
    assert_eq!(cmp[0].view.totals.total.minor(), 5_000_000_000);
    assert_eq!(cmp[1].view.totals.total.minor(), 1_800_000_000);
    assert_eq!(cmp[0].cheaper_than_max.minor(), 0);
    assert_eq!(cmp[1].cheaper_than_max.minor(), 3_200_000_000);
    // 2 000 000 000 / 100 000 000 = 20 oy; 300 000 000 / 100 000 000 = 3 oy.
    assert_eq!(cmp[0].repay_months, Some(20));
    assert_eq!(cmp[1].repay_months, Some(3));
    // 50 mln so'm = 5 000 000 000 tiyin → kontrakt (20 mln so'm) ning 2,5 baravari.
    assert_eq!(cmp[0].alternatives[0].times_milli, 2_500);

    // Imkoniyat yo'q → muddat noma'lum; juda kichik imkoniyat → 50 yildan uzoq.
    let none = ceremonies::compare(w.db.conn(), &w.ctx, &ids, None, 0).unwrap();
    assert_eq!(none[0].repay_months, None);
    let tiny = ceremonies::compare(w.db.conn(), &w.ctx, &ids, Some(uzs(1)), 0).unwrap();
    assert!(tiny[0].repay_too_long && tiny[0].repay_months.is_none());

    // 2..=3 stsenariy.
    assert!(ceremonies::compare(w.db.conn(), &w.ctx, &[big], None, 0).is_err());
    assert!(ceremonies::compare(w.db.conn(), &w.ctx, &["x".into(), "y".into()], None, 0).is_err());
}

#[test]
fn gift_goal_budget_pdf_and_removal() {
    let mut w = World::new();
    let p = w.plan("O'g'il to'yi", Some(d("2027-05-01")));
    w.line(&p, "Osh", 2, 100, FundingSource::Debt);
    let env = env!(w);
    ceremonies::open_gift_goal(&mut w.db, &env, &w.ctx, &p, uzs(100_000_000)).unwrap();
    let g = goals::list(w.db.conn(), &w.ctx).unwrap();
    assert_eq!(g.len(), 1);
    assert!(g[0].name.contains("yosh oila jamg'armasi"));
    assert_eq!(g[0].due_on, Some(d("2027-05-01")));
    assert!(ceremonies::open_gift_goal(&mut w.db, &env, &w.ctx, &p, uzs(0)).is_err());

    let pdf = ceremonies::budget_pdf(w.db.conn(), &w.ctx, &p).unwrap();
    assert!(pdf.starts_with(b"%PDF-"));
    ceremonies::remove(&mut w.db, &env, &w.ctx, &p).unwrap();
    assert!(ceremonies::list(w.db.conn(), &w.ctx).unwrap().is_empty());
    assert!(ceremonies::get(w.db.conn(), &w.ctx, &p).is_err());
}
