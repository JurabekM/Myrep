#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, Clock, Date, GateReason, IdGen, IncomeSourceType, Necessity, OffsetDateTime,
    PaymentChannel,
};
use money::{Currency, Money};
use services::{
    categories,
    expenses::{self, NewExpense},
    guard, income, obligations, prices, setup, vault, Ctx, Env, ServiceError,
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
    /// 2026-10-07; oxirgi tugagan oylar: sentabr, avgust, iyul.
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

    fn spend(&mut self, category: &str, amount: i64, date: &str, nec: Option<Necessity>) {
        let cat = categories::by_name(self.db.conn(), &self.ctx, category)
            .unwrap()
            .unwrap()
            .meta
            .id;
        let env = env!(self);
        expenses::add_many(
            &mut self.db,
            &env,
            &self.ctx,
            vec![NewExpense {
                date: d(date),
                category_id: cat,
                amount: uzs(amount),
                channel: PaymentChannel::Cash,
                note: None,
                necessity: nec,
                is_gift: false,
                is_ostentation: false,
                funded_by_debt: false,
                member_id: None,
            }],
        )
        .unwrap();
    }

    /// Uch oy: har oy 1 000 000 (ZARUR) + 500 000 (KERAK) + 300 000 HAVAS (hisobga kirmaydi).
    fn three_months(&mut self) {
        for m in ["2026-07-10", "2026-08-10", "2026-09-10"] {
            self.spend("Oziq-ovqat", 1_000_000, m, None);
            self.spend("Kiyim", 500_000, m, None);
            self.spend("Gazak va ichimlik", 300_000, m, None);
        }
    }

    fn overview(&self) -> guard::Overview {
        guard::overview(self.db.conn(), &env!(self), &self.ctx).unwrap()
    }

    fn gate(&self) -> guard::Gate {
        guard::gate(self.db.conn(), &env!(self), &self.ctx).unwrap()
    }

    fn earn(&mut self, amount: i64, share: i64) -> income::Recorded {
        let env = env!(self);
        income::record(
            &mut self.db,
            &env,
            &self.ctx,
            income::NewIncome {
                amount: uzs(amount),
                source: "ORDER".into(),
                channel: PaymentChannel::Cash,
                received_on: None,
                share: Some(uzs(share)),
                member_id: None,
                source_type: Some(IncomeSourceType::Ter),
            },
        )
        .unwrap()
    }

    fn deposit_guard(&mut self, amount: i64) {
        let env = env!(self);
        vault::set_opening_balance(&mut self.db, &env, &self.ctx, uzs(amount)).unwrap();
    }
}

#[test]
fn target_is_six_times_average_necessity_without_havas() {
    let mut w = World::new();
    assert_eq!(w.overview().target.minor(), 0, "ma'lumotsiz maqsad 0");
    assert_eq!(w.overview().basis_months, 0);

    w.three_months();
    let ov = w.overview();
    assert_eq!(ov.basis_months, 3);
    assert_eq!(ov.monthly_need.minor(), 1_500_000);
    assert_eq!(ov.target.minor(), 9_000_000);
    assert_eq!(ov.milestone.minor(), 4_500_000);
    assert_eq!(ov.gap.minor(), 9_000_000);
}

#[test]
fn recurring_obligations_count_and_category_override_applies() {
    let mut w = World::new();
    w.three_months();
    let env = env!(w);
    obligations::add_recurring(
        &mut w.db,
        &env,
        &w.ctx,
        "Ijara",
        uzs(2_000_000),
        5,
        domain::MoneyOwner::Landlord,
    )
    .unwrap();
    // Havas deb belgilangan emas, lekin xarajatning o'zi ZARUR deb qayta belgilansa hisobga kiradi.
    w.spend(
        "Gazak va ichimlik",
        600_000,
        "2026-09-12",
        Some(Necessity::Zarur),
    );
    let ov = w.overview();
    // Sentabr: 1.5M + 0.6M + 2M = 4.1M; iyul/avgust: 3.5M. O'rtacha = 11.1M/3 = 3.7M.
    assert_eq!(ov.monthly_need.minor(), 3_700_000);
}

#[test]
fn only_obligations_form_a_target_when_there_are_no_expenses() {
    let mut w = World::new();
    let env = env!(w);
    obligations::add_recurring(
        &mut w.db,
        &env,
        &w.ctx,
        "Ijara",
        uzs(2_000_000),
        5,
        domain::MoneyOwner::Landlord,
    )
    .unwrap();
    assert_eq!(w.overview().target.minor(), 12_000_000);
}

#[test]
fn gate_matrix_and_locked_reasons() {
    let mut w = World::new();
    w.three_months();
    let g = w.gate();
    assert!(!g.open);
    assert_eq!(g.reasons, vec![GateReason::GuardBelowTarget]);
    assert_eq!(g.months_x100, 0);

    w.deposit_guard(9_000_000);
    let g = w.gate();
    assert!(g.open && g.rules_open && !g.bypassed);

    // Foizli qarz bor, rejasi yo'q → qulf.
    let env = env!(w);
    guard::set_debt_declaration(&mut w.db, &env, &w.ctx, true, false).unwrap();
    let g = w.gate();
    assert!(!g.open);
    assert_eq!(g.reasons, vec![GateReason::InterestDebtNoPlan]);
    // Reja bor → ochiq.
    guard::set_debt_declaration(&mut w.db, &env, &w.ctx, true, true).unwrap();
    assert!(w.gate().open);
}

#[test]
fn bypass_needs_confirmation_is_recorded_and_revocable() {
    let mut w = World::new();
    w.three_months();
    let env = env!(w);
    assert!(matches!(
        guard::bypass(&mut w.db, &env, &w.ctx, false),
        Err(ServiceError::Invalid(_))
    ));
    assert!(!w.gate().open);
    guard::bypass(&mut w.db, &env, &w.ctx, true).unwrap();
    guard::bypass(&mut w.db, &env, &w.ctx, true).unwrap(); // takror — yangi qayd yo'q
    let g = w.gate();
    assert!(g.open && g.bypassed && !g.rules_open);
    assert_eq!(
        storage::repo::list::<domain::GateBypass>(w.db.conn(), &w.ctx.household_id)
            .unwrap()
            .len(),
        1
    );
    guard::revoke_bypass(&mut w.db, &env, &w.ctx).unwrap();
    assert!(!w.gate().open);

    // Qoidalar ochiq bo'lsa chetlab o'tish kerak emas.
    w.deposit_guard(9_000_000);
    let env = env!(w);
    assert!(matches!(
        guard::bypass(&mut w.db, &env, &w.ctx, true),
        Err(ServiceError::Invalid(_))
    ));
}

#[test]
fn allocation_fills_guard_first_and_growing_stays_locked_until_gate_opens() {
    let mut w = World::new();
    w.three_months(); // maqsad 9 000 000
    w.earn(10_000_000, 8_000_000);
    // Darvoza yopiq (balans maqsaddan oldin) → hammasi qorovulga.
    assert_eq!(
        vault::guard_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        8_000_000
    );
    assert_eq!(
        vault::growing_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        0
    );

    // 3 000 000 ajratma: 1 000 000 maqsadga yetkazadi → darvoza ochiladi, lekin bu ajratma
    // yopiq darvoza paytida hisoblangani uchun hammasi qorovulga tushadi.
    w.earn(3_000_000, 3_000_000);
    assert_eq!(
        vault::guard_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        11_000_000
    );
    assert!(w.gate().open);

    // Endi maqsad bajarilgan va darvoza ochiq: yangi ajratma o'sadiganga.
    w.earn(2_000_000, 2_000_000);
    assert_eq!(
        vault::guard_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        11_000_000
    );
    assert_eq!(
        vault::growing_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        2_000_000
    );
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        13_000_000
    );
}

#[test]
fn partial_fill_splits_between_guard_and_growing_when_gate_is_bypassed() {
    let mut w = World::new();
    w.three_months(); // maqsad 9 000 000
    w.deposit_guard(8_000_000);
    let env = env!(w);
    guard::bypass(&mut w.db, &env, &w.ctx, true).unwrap();
    w.earn(5_000_000, 3_000_000);
    assert_eq!(
        vault::guard_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        9_000_000
    );
    assert_eq!(
        vault::growing_balance(w.db.conn(), &w.ctx).unwrap().minor(),
        2_000_000
    );
}

#[test]
fn withdrawal_needs_emergency_confirmation_and_only_touches_guard() {
    let mut w = World::new();
    w.deposit_guard(5_000_000);
    let env = env!(w);
    assert!(matches!(
        vault::request_withdrawal(&mut w.db, &env, &w.ctx, uzs(1_000_000), "dori", 10, false),
        Err(ServiceError::Invalid(_))
    ));
    let req = vault::request_withdrawal(&mut w.db, &env, &w.ctx, uzs(1_000_000), "dori", 10, true)
        .unwrap();
    assert_eq!(req.amount.minor(), 1_000_000);
}

#[test]
fn price_book_index_streak_and_validation() {
    let mut w = World::new();
    let env = env!(w);
    let meat = prices::add_item(&mut w.db, &env, &w.ctx, "Go'sht", "kg", 5_000).unwrap();
    let bread = prices::add_item(&mut w.db, &env, &w.ctx, "Non", "dona", 5_000).unwrap();
    assert!(prices::add_item(&mut w.db, &env, &w.ctx, "Go'sht", "kg", 1).is_err());
    assert!(prices::add_item(&mut w.db, &env, &w.ctx, "X", "kg", 10_001).is_err());
    assert!(prices::add_price(&mut w.db, &env, &w.ctx, &meat.meta.id, uzs(0), None, None).is_err());

    assert!(prices::inflation(w.db.conn(), &w.ctx).unwrap().is_none());
    let add = |w: &mut World, id: &str, p: i64, date: &str| {
        let env = env!(w);
        prices::add_price(&mut w.db, &env, &w.ctx, id, uzs(p), Some(d(date)), None).unwrap();
    };
    add(&mut w, &meat.meta.id, 8_000_000, "2023-10-07");
    add(&mut w, &meat.meta.id, 13_000_000, "2026-10-07");
    add(&mut w, &bread.meta.id, 200_000, "2023-10-07");
    add(&mut w, &bread.meta.id, 300_000, "2026-10-07");

    let inf = prices::inflation(w.db.conn(), &w.ctx).unwrap().unwrap();
    assert_eq!(inf.index_bp, 5_625);
    assert_eq!(inf.span_days, 1_096);
    let views = prices::items(w.db.conn(), &w.ctx).unwrap();
    let m = views.iter().find(|v| v.item.name == "Go'sht").unwrap();
    assert_eq!(m.change_bp, Some(6_250));
    assert!(prices::logged_this_week(w.db.conn(), &env!(w), &w.ctx).unwrap());

    // Faolsizlantirilgan mahsulot indeksga kirmaydi.
    prices::set_item(&mut w.db, &env!(w), &w.ctx, &bread.meta.id, 5_000, false).unwrap();
    assert_eq!(
        prices::inflation(w.db.conn(), &w.ctx)
            .unwrap()
            .unwrap()
            .index_bp,
        6_250
    );
    // O'chirilgan mahsulot narxlari bilan yo'qoladi.
    prices::remove_item(&mut w.db, &env!(w), &w.ctx, &meat.meta.id).unwrap();
    assert!(prices::inflation(w.db.conn(), &w.ctx).unwrap().is_none());
}

#[test]
fn purchasing_power_uses_total_vault_and_item_price() {
    let mut w = World::new();
    w.deposit_guard(1_000_000_000);
    let env = env!(w);
    let meat = prices::add_item(&mut w.db, &env, &w.ctx, "Go'sht", "kg", 5_000).unwrap();
    assert!(matches!(
        prices::purchasing(w.db.conn(), &w.ctx, 1_500, 3, Some(&meat.meta.id)),
        Err(ServiceError::Invalid(_))
    ));
    prices::add_price(
        &mut w.db,
        &env,
        &w.ctx,
        &meat.meta.id,
        uzs(13_000_000),
        None,
        None,
    )
    .unwrap();
    let p = prices::purchasing(w.db.conn(), &w.ctx, 1_500, 3, Some(&meat.meta.id)).unwrap();
    assert_eq!(p.nominal.minor(), 1_000_000_000);
    assert_eq!(p.real.minor(), 657_516_232);
    let ex = p.example.unwrap();
    assert!(ex.price_future.minor() > ex.price_today.minor());
    assert!(ex.quantity_future_milli < ex.quantity_now_milli);
    assert!(prices::purchasing(w.db.conn(), &w.ctx, 1_500, 51, None).is_err());
}

#[test]
fn income_source_type_is_stored() {
    let mut w = World::new();
    let r = w.earn(1_000_000, 0);
    let list = income::list_month(
        w.db.conn(),
        &w.ctx,
        services::YearMonth::parse("2026-10").unwrap(),
    )
    .unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].source_type, Some(IncomeSourceType::Ter));
    assert_eq!(r.share.minor(), 0);
}
