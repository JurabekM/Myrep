#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, BorrowAlternative, BorrowNeed, Clock, CreditorType, Date, IdGen, Necessity,
    OffsetDateTime, PaymentChannel, ReceiptKind, ScheduleKind,
};
use money::{Currency, Money};
use services::{
    debts::{self, NewDebt, ScheduleInput},
    expenses, goals, income, obligations, receipts, receivables, setup, Ctx, Env, ServiceError,
    YearMonth,
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

    fn add(&mut self, new: NewDebt) -> Result<debts::DebtView, ServiceError> {
        let env = env!(self);
        debts::add(&mut self.db, &env, &self.ctx, new)
    }

    fn pay(&mut self, id: &str, amount: i64) -> Result<debts::DebtView, ServiceError> {
        let env = env!(self);
        debts::pay(&mut self.db, &env, &self.ctx, id, uzs(amount), None, None)
    }

    fn view(&self, id: &str) -> debts::DebtView {
        debts::get(self.db.conn(), &env!(self), &self.ctx, id).unwrap()
    }

    fn overview(&self) -> debts::Overview {
        debts::overview(self.db.conn(), &env!(self), &self.ctx).unwrap()
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
}

fn add_rec(
    w: &mut World,
    debtor: &str,
    amount: i64,
    given_on: Option<Date>,
    due_on: Option<Date>,
    note: Option<&str>,
) -> Result<domain::Receivable, ServiceError> {
    let env = env!(w);
    receivables::add(
        &mut w.db,
        &env,
        &w.ctx,
        receivables::NewReceivable {
            debtor,
            amount: uzs(amount),
            given_on,
            due_on,
            note,
        },
    )
}

fn rows(list: &[(&str, i64)]) -> ScheduleInput {
    ScheduleInput::Rows(list.iter().map(|(dt, a)| (d(dt), uzs(*a))).collect())
}

fn debt(principal: i64, kind: ScheduleKind, schedule: ScheduleInput) -> NewDebt {
    NewDebt {
        creditor: "Bank".into(),
        creditor_type: CreditorType::Bank,
        reason: Some("avtokredit".into()),
        principal: uzs(principal),
        schedule_kind: kind,
        schedule,
        borrowed_on: None,
        early_repayment_terms: None,
        check: None,
    }
}

/// 3 000 000 so'm (300 000 000 tiyin) asosiy, 3 oy, ustamasiz.
fn plain() -> NewDebt {
    debt(
        300_000_000,
        ScheduleKind::Manual,
        rows(&[
            ("2026-11-07", 100_000_000),
            ("2026-12-07", 100_000_000),
            ("2027-01-07", 100_000_000),
        ]),
    )
}

#[test]
fn debt_without_a_valid_schedule_is_not_saved() {
    let mut w = World::new();
    // Rejasiz.
    let e = w
        .add(debt(100, ScheduleKind::Manual, rows(&[])))
        .unwrap_err();
    assert!(matches!(e, ServiceError::Invalid(m) if m.contains("rejasiz")));
    // Asosiydan kam jadval.
    assert!(w
        .add(debt(
            500,
            ScheduleKind::Manual,
            rows(&[("2026-11-07", 100)])
        ))
        .is_err());
    // Musbat bo'lmagan qator.
    assert!(w
        .add(debt(
            100,
            ScheduleKind::Manual,
            rows(&[("2026-11-07", 100), ("2026-12-07", 0)])
        ))
        .is_err());
    // Tur va usul mos emas.
    assert!(w
        .add(debt(
            100,
            ScheduleKind::FixedMarkup,
            rows(&[("2026-11-07", 100)])
        ))
        .is_err());
    // Kreditor nomi bo'sh.
    let mut bad = plain();
    bad.creditor = "  ".into();
    assert!(w.add(bad).is_err());
    assert_eq!(w.overview().active_count, 0);
    assert!(debts::list(w.db.conn(), &env!(w), &w.ctx)
        .unwrap()
        .is_empty());
}

#[test]
fn markup_comes_from_the_schedule_and_fixed_markup_splits_evenly() {
    let mut w = World::new();
    let v = w.add(plain()).unwrap();
    assert!(!v.has_markup());
    assert_eq!(v.markup.minor(), 0);
    assert_eq!(v.debt.monthly_payment.minor(), 100_000_000);
    assert_eq!(v.debt.due_date, d("2027-01-07"));
    assert_eq!(v.next_due, Some((d("2026-11-07"), uzs(100_000_000))));

    let fm = w
        .add(debt(
            300_000_000,
            ScheduleKind::FixedMarkup,
            ScheduleInput::FixedMarkup {
                markup: uzs(60_000_000),
                months: 7,
                first_due: d("2026-10-31"),
            },
        ))
        .unwrap();
    assert!(fm.has_markup());
    assert_eq!(fm.markup.minor(), 60_000_000);
    assert_eq!(fm.total_scheduled.minor(), 360_000_000);
    assert_eq!(fm.instalments.len(), 7);
    // 360 000 000 / 7 = 51 428 571 qoldiq 3 → birinchi uchtasi +1.
    assert_eq!(fm.instalments[0].amount.minor(), 51_428_572);
    assert_eq!(fm.instalments[6].amount.minor(), 51_428_571);
    assert_eq!(fm.instalments[1].due_on, d("2026-11-30"));
}

#[test]
fn karim_aka_real_cost_shows_excess_over_principal() {
    let mut w = World::new();
    // 40 mln so'm asosiy; jami to'lanadigan 69 mln (60 mln to'langan + 9 mln qolgan).
    let v = w
        .add(debt(
            4_000_000_000,
            ScheduleKind::Annuity,
            rows(&[("2026-11-07", 6_000_000_000), ("2026-12-07", 900_000_000)]),
        ))
        .unwrap();
    assert_eq!(v.cost.total.minor(), 6_900_000_000);
    assert_eq!(v.cost.excess.minor(), 2_900_000_000);
    assert_eq!(v.cost.excess_bp, 4_203);
    w.pay(&v.debt.meta.id, 6_000_000_000).unwrap();
    let v = w.view(&v.debt.meta.id);
    assert_eq!(v.paid.minor(), 6_000_000_000);
    assert_eq!(v.remaining.minor(), 900_000_000);
    assert_eq!(v.cost.total.minor(), 6_900_000_000, "jami o'zgarmaydi");
    assert_eq!(v.next_due, Some((d("2026-12-07"), uzs(900_000_000))));
}

#[test]
fn payment_creates_zarur_expense_closes_debt_and_rejects_overpay() {
    let mut w = World::new();
    let v = w.add(plain()).unwrap();
    let id = v.debt.meta.id.clone();
    assert!(w.pay(&id, 0).is_err());
    assert!(w.pay(&id, 300_000_001).is_err());
    let v = w.pay(&id, 100_000_000).unwrap();
    assert!(v.active());
    assert_eq!(v.remaining.minor(), 200_000_000);

    let spent =
        expenses::list_range(w.db.conn(), &w.ctx, d("2026-10-01"), d("2026-10-31")).unwrap();
    assert_eq!(spent.len(), 1);
    let cat = services::categories::by_name(w.db.conn(), &w.ctx, "Qarz to'lovi")
        .unwrap()
        .unwrap();
    assert_eq!(spent[0].category_id, cat.meta.id);
    assert_eq!(cat.necessity, Some(Necessity::Zarur));

    let v = w.pay(&id, 200_000_000).unwrap();
    assert!(!v.active());
    assert_eq!(v.debt.closed_on, Some(d("2026-10-07")));
    assert!(w.pay(&id, 1).is_err(), "yopilgan qarzga to'lov yo'q");
    assert_eq!(w.overview().active_count, 0);
}

#[test]
fn overdue_is_detected_from_the_schedule() {
    let mut w = World::new();
    let v = w
        .add(debt(
            100,
            ScheduleKind::Manual,
            rows(&[("2026-10-01", 50), ("2026-12-01", 50)]),
        ))
        .unwrap();
    assert!(v.overdue);
    assert!(w.overview().any_overdue);
    w.pay(&v.debt.meta.id, 50).unwrap();
    assert!(!w.view(&v.debt.meta.id).overdue);
}

#[test]
fn overview_totals_burden_and_nasiya() {
    let mut w = World::new();
    assert_eq!(w.overview().burden_bp, None, "daromadsiz yuk hisoblanmaydi");
    w.add(plain()).unwrap();
    {
        let env = env!(w);
        obligations::add_nasiya(&mut w.db, &env, &w.ctx, "Do'kon", uzs(50_000_000)).unwrap();
    }
    w.earn(1_000_000_000);
    let o = w.overview();
    assert_eq!(o.active_count, 1);
    assert_eq!(o.nasiya_remaining.minor(), 50_000_000);
    assert_eq!(o.total_remaining.minor(), 350_000_000);
    assert_eq!(o.monthly_load.minor(), 100_000_000);
    assert_eq!(o.burden_bp, Some(1_000));
    assert!(!o.has_markup_debt);
}

#[test]
fn friction_check_stores_the_projected_burden() {
    let mut w = World::new();
    w.earn(1_000_000_000);
    w.add(plain()).unwrap();
    let mut new = plain();
    new.check = Some((BorrowNeed::Luxury, BorrowAlternative::Guard));
    let preview = {
        let env = env!(w);
        debts::burden_preview(w.db.conn(), &env, &w.ctx, &new).unwrap()
    };
    // Mavjud 100M + yangi 100M, daromad 1 000M → 20%.
    assert_eq!(preview, Some(2_000));
    let v = w.add(new).unwrap();
    let c = v.debt.check.unwrap();
    assert_eq!(
        (c.need, c.alternative, c.burden_bp),
        (BorrowNeed::Luxury, BorrowAlternative::Guard, 2_000)
    );
}

#[test]
fn receivables_are_interest_free_and_remind_when_due() {
    let mut w = World::new();
    assert!(add_rec(&mut w, " ", 1, None, None, None).is_err());
    assert!(add_rec(&mut w, "Qo'shni", 0, None, None, None).is_err());
    assert!(add_rec(
        &mut w,
        "Qo'shni",
        1,
        Some(d("2026-10-07")),
        Some(d("2026-10-01")),
        None,
    )
    .is_err());
    let r = add_rec(
        &mut w,
        "Qo'shni",
        20_000_000,
        Some(d("2026-09-20")),
        Some(d("2026-10-07")),
        Some("oy oxirigacha"),
    )
    .unwrap();
    let list = receivables::list(w.db.conn(), &env!(w), &w.ctx).unwrap();
    assert!(list[0].due);
    assert_eq!(list[0].outstanding.minor(), 20_000_000);
    receivables::record_return(&mut w.db, &env!(w), &w.ctx, &r.meta.id, uzs(5_000_000)).unwrap();
    assert!(
        receivables::record_return(&mut w.db, &env!(w), &w.ctx, &r.meta.id, uzs(15_000_001))
            .is_err()
    );
    receivables::record_return(&mut w.db, &env!(w), &w.ctx, &r.meta.id, uzs(15_000_000)).unwrap();
    let list = receivables::list(w.db.conn(), &env!(w), &w.ctx).unwrap();
    assert!(!list[0].due, "to'liq qaytgach eslatma yo'q");
    assert_eq!(
        receivables::outstanding_total(w.db.conn(), &env!(w), &w.ctx)
            .unwrap()
            .minor(),
        0
    );
}

#[test]
fn goals_give_opportunity_cost_equivalence() {
    let mut w = World::new();
    let env = env!(w);
    assert!(goals::add(&mut w.db, &env, &w.ctx, "", uzs(1), None).is_err());
    let g = goals::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Qizim kontrakti",
        uzs(2_000_000_000),
        None,
    )
    .unwrap();
    goals::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Katta maqsad",
        uzs(900_000_000_000),
        None,
    )
    .unwrap();
    let eq = goals::equivalences(w.db.conn(), &w.ctx, uzs(2_900_000_000)).unwrap();
    // 29 mln / 20 mln = 1,45 → 1450 (1/1000); juda kichik nisbat chiqarib tashlanadi.
    assert_eq!(eq.len(), 1);
    assert_eq!(eq[0].goal_name, "Qizim kontrakti");
    assert_eq!(eq[0].times_milli, 1_450);
    let g = goals::contribute(&mut w.db, &env, &w.ctx, &g.meta.id, uzs(100)).unwrap();
    assert_eq!(g.saved.minor(), 100);
    assert!(goals::contribute(&mut w.db, &env, &w.ctx, &g.meta.id, uzs(0)).is_err());
}

#[test]
fn receipt_data_for_debt_and_receivable_with_witnesses() {
    let mut w = World::new();
    let v = w.add(plain()).unwrap();
    let id = v.debt.meta.id.clone();
    let rd = receipts::data(w.db.conn(), &env!(w), &w.ctx, ReceiptKind::Debt, &id).unwrap();
    assert_eq!(rd.lender, "Bank");
    assert_eq!(rd.borrower, "Men");
    assert_eq!(rd.schedule.len(), 3);
    assert!(!rd.has_markup && rd.witnesses.is_empty() && !rd.confirmed_by_counterparty);

    let names: Vec<String> = ["  Anvar   Karimov ", "", "Dilshod", "A", "B", "C"]
        .iter()
        .map(ToString::to_string)
        .collect();
    receipts::save_details(
        &mut w.db,
        &env!(w),
        &w.ctx,
        ReceiptKind::Debt,
        &id,
        &names,
        true,
    )
    .unwrap();
    let rd = receipts::data(w.db.conn(), &env!(w), &w.ctx, ReceiptKind::Debt, &id).unwrap();
    assert_eq!(rd.witnesses, vec!["Anvar Karimov", "Dilshod", "A", "B"]);
    assert!(rd.confirmed_by_counterparty);
    receipts::save_details(
        &mut w.db,
        &env!(w),
        &w.ctx,
        ReceiptKind::Debt,
        &id,
        &[],
        false,
    )
    .unwrap();
    assert!(
        !receipts::data(w.db.conn(), &env!(w), &w.ctx, ReceiptKind::Debt, &id)
            .unwrap()
            .confirmed_by_counterparty
    );

    let r = add_rec(&mut w, "Qo'shni", 5, None, None, None).unwrap();
    let rd = receipts::data(
        w.db.conn(),
        &env!(w),
        &w.ctx,
        ReceiptKind::Receivable,
        &r.meta.id,
    )
    .unwrap();
    assert_eq!(
        (rd.lender.as_str(), rd.borrower.as_str()),
        ("Men", "Qo'shni")
    );
    assert!(!rd.has_markup);
    assert!(receipts::data(w.db.conn(), &env!(w), &w.ctx, ReceiptKind::Debt, "nope").is_err());
}

#[test]
fn removing_a_debt_removes_schedule_and_payments() {
    let mut w = World::new();
    let v = w.add(plain()).unwrap();
    w.pay(&v.debt.meta.id, 1).unwrap();
    {
        let env = env!(w);
        debts::remove(&mut w.db, &env, &w.ctx, &v.debt.meta.id).unwrap();
    }
    assert_eq!(w.overview().active_count, 0);
    assert!(
        storage::repo::list::<domain::DebtInstalment>(w.db.conn(), &w.ctx.household_id)
            .unwrap()
            .is_empty()
    );
    let _ = YearMonth::parse("2026-10").unwrap();
}
