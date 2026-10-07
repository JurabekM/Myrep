#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, BudgetMode, Clock, CreditorType, Date, IdGen, LoanKind, MemberRole,
    OffsetDateTime, PaymentChannel, RecoverySplit, ScheduleKind,
};
use money::{Currency, Money};
use services::{
    contributors,
    debts::{self, NewDebt, ScheduleInput},
    income, members, payoff, recovery, sellables, setup, Ctx, Env, ServiceError,
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
        }
    }

    /// Bir xil oylik to'lovli qarz: `months` ta `each` (birinchi to'lov 2026-11-07).
    fn debt(
        &mut self,
        name: &str,
        kind: CreditorType,
        principal: i64,
        each: i64,
        months: u32,
    ) -> String {
        let rows: Vec<(Date, Money)> = (0..months)
            .map(|i| (domain::add_months(d("2026-11-07"), i), uzs(each)))
            .collect();
        let env = env!(self);
        debts::add(
            &mut self.db,
            &env,
            &self.ctx,
            NewDebt {
                creditor: name.into(),
                creditor_type: kind,
                reason: None,
                principal: uzs(principal),
                schedule_kind: ScheduleKind::Manual,
                schedule: ScheduleInput::Rows(rows),
                borrowed_on: None,
                early_repayment_terms: None,
                check: None,
            },
        )
        .unwrap()
        .debt
        .meta
        .id
    }

    fn pay(&mut self, id: &str, amount: i64) {
        let env = env!(self);
        debts::pay(&mut self.db, &env, &self.ctx, id, uzs(amount), None, None).unwrap();
    }

    fn status(&mut self) -> recovery::Status {
        let env = env!(self);
        recovery::status(&mut self.db, &env, &self.ctx).unwrap()
    }

    fn set_mode(&mut self, m: BudgetMode) -> Result<(), ServiceError> {
        let env = env!(self);
        recovery::set_mode(&mut self.db, &env, &self.ctx, m)
    }

    fn earn(&mut self, amount: i64) {
        let env = env!(self);
        income::record(
            &mut self.db,
            &env,
            &self.ctx,
            income::NewIncome {
                amount: uzs(amount),
                source: "SALARY".into(),
                channel: PaymentChannel::Cash,
                received_on: None,
                share: Some(uzs(0)),
                member_id: None,
                source_type: None,
            },
        )
        .unwrap();
    }

    fn plan(&self, extra: i64, one_off: i64) -> Option<payoff::PlanView> {
        payoff::plan(
            self.db.conn(),
            &env!(self),
            &self.ctx,
            uzs(extra),
            uzs(one_off),
        )
        .unwrap()
    }
}

#[test]
fn recovery_mode_needs_an_active_debt_and_suggests_itself() {
    let mut w = World::new();
    assert!(!w.status().suggest_recovery);
    assert!(w.set_mode(BudgetMode::DebtRecovery).is_err());
    w.debt("Bank", CreditorType::Bank, 100, 50, 2);
    let s = w.status();
    assert!(s.suggest_recovery);
    assert_eq!(s.mode, BudgetMode::Standard);
    assert_eq!(s.split, RecoverySplit::DEFAULT);
    w.set_mode(BudgetMode::DebtRecovery).unwrap();
    let s = w.status();
    assert_eq!(s.mode, BudgetMode::DebtRecovery);
    assert!(!s.suggest_recovery);
}

#[test]
fn income_share_in_recovery_mode_is_the_savings_part_and_never_zero() {
    let mut w = World::new();
    let id = w.debt("Bank", CreditorType::Bank, 100, 50, 2);
    w.set_mode(BudgetMode::DebtRecovery).unwrap();
    let sg = income::suggest(w.db.conn(), &env!(w), &w.ctx, uzs(800_000_000)).unwrap();
    assert_eq!(sg.share.minor(), 80_000_000, "10% jamg'arma");
    // Jamg'arma ulushini 0 qilib bo'lmaydi; yig'indi 100% bo'lishi shart.
    let env = env!(w);
    let zero = RecoverySplit {
        living_bp: 7_000,
        extra_bp: 3_000,
        savings_bp: 0,
    };
    assert!(recovery::set_split(&mut w.db, &env, &w.ctx, zero).is_err());
    let bad_sum = RecoverySplit {
        living_bp: 7_000,
        extra_bp: 2_000,
        savings_bp: 500,
    };
    assert!(recovery::set_split(&mut w.db, &env, &w.ctx, bad_sum).is_err());
    let custom = RecoverySplit {
        living_bp: 6_000,
        extra_bp: 3_000,
        savings_bp: 1_000,
    };
    recovery::set_split(&mut w.db, &env, &w.ctx, custom).unwrap();
    assert_eq!(w.status().split, custom);
    let _ = id;
}

#[test]
fn mode_reverts_to_standard_when_the_last_debt_closes() {
    let mut w = World::new();
    let a = w.debt("A", CreditorType::Bank, 100, 50, 2);
    let b = w.debt("B", CreditorType::Friend, 40, 40, 1);
    w.set_mode(BudgetMode::DebtRecovery).unwrap();
    w.pay(&a, 100);
    assert_eq!(w.status().mode, BudgetMode::DebtRecovery, "B hali ochiq");
    w.pay(&b, 40);
    let s = w.status();
    assert_eq!(s.mode, BudgetMode::Standard);
    assert!(s.reverted_notice);
    let env = env!(w);
    recovery::dismiss_notice(&mut w.db, &env, &w.ctx).unwrap();
    assert!(!w.status().reverted_notice);
    // Standart rejimda ulush yana oddiy qoida bo'yicha (5%).
    let sg = income::suggest(w.db.conn(), &env!(w), &w.ctx, uzs(800_000_000)).unwrap();
    assert_eq!(sg.share.minor(), 40_000_000);
}

#[test]
fn plan_orders_markup_first_and_extra_shortens_the_horizon() {
    let mut w = World::new();
    assert!(w.plan(0, 0).is_none());
    // Do'st: foizsiz 4 oy; bank: ustamali (jami 600 > asosiy 500) 6 oy.
    let friend = w.debt("Do'st", CreditorType::Friend, 400, 100, 4);
    let bank = w.debt("Bank", CreditorType::Bank, 500, 100, 6);
    let p = w.plan(0, 0).unwrap();
    assert_eq!(
        p.order,
        vec![bank.clone(), friend.clone()],
        "ustamali birinchi"
    );
    assert!(!p.manual_order);
    assert_eq!(
        (p.baseline_months, p.accelerated_months, p.months_saved),
        (7, 7, 0)
    );
    assert_eq!(p.debt_free_baseline, Some(d("2027-04-30")));

    let p = w.plan(100, 0).unwrap();
    assert!(p.accelerated_months < p.baseline_months);
    assert_eq!(p.months_saved, p.baseline_months - p.accelerated_months);
    let bank_line = p.lines.iter().find(|l| l.id == bank).unwrap();
    assert!(bank_line.accelerated_months < bank_line.baseline_months);

    // Bir martalik manba (masalan, buyum sotilgan) ham muddatni qisqartiradi.
    let p1 = w.plan(0, 300).unwrap();
    assert!(p1.accelerated_months < 7);

    // Qo'lda tartib.
    let env = env!(w);
    payoff::set_order(&mut w.db, &env, &w.ctx, &[friend.clone(), bank.clone()]).unwrap();
    let p = w.plan(0, 0).unwrap();
    assert_eq!(p.order, vec![friend, bank]);
    assert!(p.manual_order);
    payoff::clear_order(&mut w.db, &env, &w.ctx).unwrap();
    assert!(!w.plan(0, 0).unwrap().manual_order);
    assert!(payoff::set_order(&mut w.db, &env, &w.ctx, &["nope".into()]).is_err());
}

#[test]
fn partial_payments_move_the_remaining_schedule() {
    let mut w = World::new();
    let a = w.debt("A", CreditorType::Bank, 300, 100, 3);
    w.pay(&a, 150); // 1-qator to'liq, 2-qatordan 50 to'langan
    let p = w.plan(0, 0).unwrap();
    assert_eq!(
        p.baseline_months, 4,
        "qolgan: 50 (noyabr), 100 (dekabr→2-oy)"
    );
}

#[test]
fn calculator_reproduces_the_anvar_story() {
    let r = payoff::calculator(
        LoanKind::Annuity,
        uzs(3_900_000_000),
        2_400,
        14,
        uzs(160_000_000),
    )
    .unwrap();
    assert_eq!((r.baseline.months, r.accelerated.months), (14, 9));
    assert_eq!(r.months_saved, 5);
    assert_eq!(r.interest_saved.minor(), 610_067_573 - 397_018_667);
}

#[test]
fn contributors_track_shares_and_who_paid() {
    let mut w = World::new();
    let id = w.debt("Bank", CreditorType::Bank, 300, 100, 3);
    let son = {
        let env = env!(w);
        members::add(&mut w.db, &env, &w.ctx, "Sanjar", MemberRole::Adult).unwrap()
    };
    let env = env!(w);
    contributors::set_share(&mut w.db, &env, &w.ctx, &id, &son.meta.id, uzs(40)).unwrap();
    contributors::set_share(&mut w.db, &env, &w.ctx, &id, &son.meta.id, uzs(50)).unwrap();
    assert!(contributors::set_share(&mut w.db, &env, &w.ctx, &id, "nope", uzs(1)).is_err());
    assert!(contributors::set_share(&mut w.db, &env, &w.ctx, &id, &son.meta.id, uzs(-1)).is_err());
    debts::pay(
        &mut w.db,
        &env,
        &w.ctx,
        &id,
        uzs(30),
        None,
        Some(&son.meta.id),
    )
    .unwrap();
    debts::pay(&mut w.db, &env, &w.ctx, &id, uzs(70), None, None).unwrap();
    let list = contributors::list(w.db.conn(), &env, &w.ctx, &id).unwrap();
    assert_eq!(list.len(), 2);
    let s = list.iter().find(|c| c.name == "Sanjar").unwrap();
    assert_eq!((s.monthly_share, s.paid), (Some(uzs(50)), uzs(30)));
    let me = list.iter().find(|c| c.name == "Men").unwrap();
    assert_eq!((me.monthly_share, me.paid), (None, uzs(70)));
    contributors::remove(&mut w.db, &env, &w.ctx, &id, &son.meta.id).unwrap();
    let after = contributors::list(w.db.conn(), &env, &w.ctx, &id).unwrap();
    assert_eq!(
        after
            .iter()
            .find(|c| c.name == "Sanjar")
            .unwrap()
            .monthly_share,
        None
    );
}

#[test]
fn selling_an_item_pays_the_chosen_debt_up_to_its_remainder() {
    let mut w = World::new();
    let id = w.debt("Bank", CreditorType::Bank, 300, 100, 3);
    let env = env!(w);
    assert!(sellables::add(&mut w.db, &env, &w.ctx, " ", uzs(1), None).is_err());
    let item = sellables::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Velosiped",
        uzs(500),
        Some(d("2026-01-01")),
    )
    .unwrap();
    assert_eq!(
        sellables::listed_total(w.db.conn(), &w.ctx)
            .unwrap()
            .minor(),
        500
    );
    let src = payoff::sources(w.db.conn(), &env, &w.ctx).unwrap();
    assert_eq!(src.sellable_listed.minor(), 500);
    // 500 sotildi, qarz qoldig'i 300: 300 to'lanadi, qarz yopiladi.
    let paid =
        sellables::sell(&mut w.db, &env, &w.ctx, &item.meta.id, uzs(500), Some(&id)).unwrap();
    assert_eq!(paid.minor(), 300);
    assert!(!debts::get(w.db.conn(), &env, &w.ctx, &id).unwrap().active());
    assert!(sellables::sell(&mut w.db, &env, &w.ctx, &item.meta.id, uzs(1), None).is_err());
    assert_eq!(
        sellables::listed_total(w.db.conn(), &w.ctx)
            .unwrap()
            .minor(),
        0
    );
}

#[test]
fn sources_include_the_recovery_extra_share_when_income_is_known() {
    let mut w = World::new();
    w.earn(1_000_000_000);
    let src = payoff::sources(w.db.conn(), &env!(w), &w.ctx).unwrap();
    assert_eq!(src.monthly_share.unwrap().minor(), 200_000_000);
}
