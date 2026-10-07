#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{date_from_str, Clock, IdGen, MoneyOwner, OffsetDateTime, PaymentChannel, ShareRule};
use money::{Currency, Money};
use services::{
    audit, home, income, obligations, rules, setup, vault, Ctx, Env, ServiceError, YearMonth,
};
use storage::Database;
use time::Duration;

const KEY: [u8; 32] = [5; 32];

struct TestClock(Cell<OffsetDateTime>);
impl Clock for TestClock {
    fn now(&self) -> OffsetDateTime {
        self.0.get()
    }
}
impl TestClock {
    fn advance(&self, d: Duration) {
        self.0.set(self.0.get() + d);
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

/// `Env` faqat `clock` va `ids` maydonlarini oladi, shuning uchun `w.db` bilan birga ishlatsa bo'ladi.
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

impl World {
    /// 2026-10-07 (chorshanba) 10:00 Toshkent vaqti.
    fn new() -> Self {
        let mut db = Database::open_in_memory(&KEY).unwrap();
        let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-07 05:00 UTC)));
        let ids = Seq(Cell::new(1));
        let ctx = {
            let env = Env {
                clock: &clock,
                ids: &ids,
                device_id: "dev",
            };
            setup::ensure_household(&mut db, &env).unwrap()
        };
        Self {
            db,
            clock,
            ids,
            ctx,
        }
    }
}

fn uzs(v: i64) -> Money {
    Money::new(v, Currency::Uzs)
}

fn new_income(amount: i64, share: Option<i64>) -> income::NewIncome {
    income::NewIncome {
        amount: uzs(amount),
        source: "DAILY_WORK".into(),
        channel: PaymentChannel::Cash,
        received_on: None,
        share: share.map(uzs),
        member_id: None,
        source_type: None,
    }
}

#[test]
fn setup_is_idempotent_and_seeds_defaults() {
    let mut w = World::new();
    let again = {
        let env = env!(w);
        setup::ensure_household(&mut w.db, &env).unwrap()
    };
    assert_eq!(again.household_id, w.ctx.household_id);
    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap().minor(), 0);
    let rule = rules::current(w.db.conn(), &w.ctx).unwrap().rule;
    assert_eq!(rule, ShareRule::Percent { bp: 500 });
    let cats = domain_categories(&w);
    assert!(cats
        .iter()
        .any(|c| c.name == "Benzin" && c.owner == Some(MoneyOwner::Fuel)));
    assert_eq!(cats.len(), setup::DEFAULT_CATEGORIES.len());
}

fn domain_categories(w: &World) -> Vec<domain::Category> {
    storage::repo::list::<domain::Category>(w.db.conn(), &w.ctx.household_id).unwrap()
}

/// E2E (servis darajasida): daromad → taklif → ajratma → balans → bosh sahifa.
#[test]
fn income_to_vault_to_home() {
    let mut w = World::new();
    let env = env!(w);

    let s = income::suggest(w.db.conn(), &env, &w.ctx, uzs(800_000_000)).unwrap();
    assert_eq!(s.share.minor(), 40_000_000); // 5%

    let rec = income::record(&mut w.db, &env, &w.ctx, new_income(800_000_000, None)).unwrap();
    assert_eq!(rec.share.minor(), 40_000_000);
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        40_000_000
    );

    let h = home::summary(w.db.conn(), &env, &w.ctx).unwrap();
    assert_eq!(h.self_paid.minor(), 40_000_000);
    assert_eq!(h.self_paid_bp, 500);
    assert_eq!(h.income.minor(), 800_000_000);
    assert_eq!(h.vault_balance.minor(), 40_000_000);
    assert_eq!((h.streak.current_weeks, h.streak.saved_days), (1, 1));
    assert_eq!(h.rate_suggestion, None);
}

#[test]
fn user_can_override_share_including_zero_and_bounds_are_enforced() {
    let mut w = World::new();
    let env = env!(w);
    let r = income::record(&mut w.db, &env, &w.ctx, new_income(1_000_000, Some(0))).unwrap();
    assert_eq!(r.share.minor(), 0);
    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap().minor(), 0);
    assert!(
        home::summary(w.db.conn(), &env, &w.ctx)
            .unwrap()
            .streak
            .current_weeks
            == 0
    );

    assert!(matches!(
        income::record(&mut w.db, &env, &w.ctx, new_income(1_000, Some(1_001))),
        Err(ServiceError::Invalid(_))
    ));
    assert!(income::record(&mut w.db, &env, &w.ctx, new_income(1_000, Some(-1))).is_err());
    assert!(income::record(&mut w.db, &env, &w.ctx, new_income(0, None)).is_err());
    let mut bad = new_income(1_000, None);
    bad.source = "  ".into();
    assert!(income::record(&mut w.db, &env, &w.ctx, bad).is_err());
    let mut usd = new_income(1_000, None);
    usd.amount = Money::new(1_000, Currency::Usd);
    assert!(income::record(&mut w.db, &env, &w.ctx, usd).is_err());
    let mut ghost = new_income(1_000, None);
    ghost.member_id = Some("yo'q".into());
    assert!(matches!(
        income::record(&mut w.db, &env, &w.ctx, ghost),
        Err(ServiceError::NotFound)
    ));
}

#[test]
fn failed_record_leaves_no_partial_state() {
    let mut w = World::new();
    let env = env!(w);
    let before = income::list_month(w.db.conn(), &w.ctx, YearMonth::parse("2026-10").unwrap())
        .unwrap()
        .len();
    let _ = income::record(&mut w.db, &env, &w.ctx, new_income(1_000, Some(5_000)));
    let after = income::list_month(w.db.conn(), &w.ctx, YearMonth::parse("2026-10").unwrap())
        .unwrap()
        .len();
    assert_eq!(before, after);
}

#[test]
fn fixed_monthly_rule_stops_at_target() {
    let mut w = World::new();
    let env = env!(w);
    rules::set(
        &mut w.db,
        &env,
        &w.ctx,
        ShareRule::MonthlyFixed {
            target: uzs(300_000),
        },
    )
    .unwrap();
    income::record(&mut w.db, &env, &w.ctx, new_income(200_000, None)).unwrap(); // 200k
    let r = income::record(&mut w.db, &env, &w.ctx, new_income(500_000, None)).unwrap(); // faqat 100k
    assert_eq!(r.share.minor(), 100_000);
    let r = income::record(&mut w.db, &env, &w.ctx, new_income(500_000, None)).unwrap();
    assert_eq!(r.share.minor(), 0);
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        300_000
    );
}

#[test]
fn rule_validation_and_history() {
    let mut w = World::new();
    let env = env!(w);
    for bad in [
        ShareRule::Percent { bp: 0 },
        ShareRule::Percent { bp: 10_001 },
        ShareRule::MonthlyFixed { target: uzs(0) },
        ShareRule::MonthlyFixed {
            target: Money::new(5, Currency::Usd),
        },
    ] {
        assert!(rules::set(&mut w.db, &env, &w.ctx, bad).is_err());
    }
    rules::set(&mut w.db, &env, &w.ctx, ShareRule::Percent { bp: 1000 }).unwrap();
    assert_eq!(
        rules::current(w.db.conn(), &w.ctx).unwrap().rule,
        ShareRule::Percent { bp: 1000 }
    );
}

#[test]
fn progressive_suggestion_after_four_weeks_of_streak() {
    let mut w = World::new();
    for _ in 0..4 {
        let env = env!(w);
        income::record(&mut w.db, &env, &w.ctx, new_income(1_000_000, None)).unwrap();
        w.clock.advance(Duration::days(7));
    }
    let env = env!(w);
    let h = home::summary(w.db.conn(), &env, &w.ctx).unwrap();
    assert_eq!(h.streak.current_weeks, 4);
    assert_eq!(h.rate_suggestion, Some(600));
    // Qabul qilinsa stavka o'zgaradi va hisoblagich qayta boshlanadi.
    rules::set(&mut w.db, &env, &w.ctx, ShareRule::Percent { bp: 600 }).unwrap();
    assert_eq!(
        home::summary(w.db.conn(), &env, &w.ctx)
            .unwrap()
            .rate_suggestion,
        None
    );
}

#[test]
fn opening_balance_once_only_and_not_counted_as_paid() {
    let mut w = World::new();
    let env = env!(w);
    vault::set_opening_balance(&mut w.db, &env, &w.ctx, uzs(500_000_000)).unwrap();
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        500_000_000
    );
    assert!(matches!(
        vault::set_opening_balance(&mut w.db, &env, &w.ctx, uzs(1)),
        Err(ServiceError::OpeningBalanceExists)
    ));
    let h = home::summary(w.db.conn(), &env, &w.ctx).unwrap();
    assert_eq!(h.self_paid.minor(), 0);
    assert_eq!(h.streak.current_weeks, 0);
    assert_eq!(h.vault_balance.minor(), 500_000_000);
}

#[test]
fn withdrawal_requires_cooldown_and_enough_money() {
    let mut w = World::new();
    let env = env!(w);
    income::record(
        &mut w.db,
        &env,
        &w.ctx,
        new_income(10_000_000, Some(10_000_000)),
    )
    .unwrap();

    assert!(matches!(
        vault::request_withdrawal(
            &mut w.db,
            &env,
            &w.ctx,
            uzs(10_000_001),
            "dori",
            86_400,
            true
        ),
        Err(ServiceError::InsufficientFunds)
    ));
    assert!(
        vault::request_withdrawal(&mut w.db, &env, &w.ctx, uzs(1), "  ", 86_400, true).is_err()
    );

    let req = vault::request_withdrawal(
        &mut w.db,
        &env,
        &w.ctx,
        uzs(4_000_000),
        "Dori",
        86_400,
        true,
    )
    .unwrap();
    // So'rov pulni ushlamaydi va darrov chiqarmaydi.
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        10_000_000
    );
    assert_eq!(
        home::summary(w.db.conn(), &env, &w.ctx)
            .unwrap()
            .pending_withdrawals,
        1
    );
    assert!(matches!(
        vault::confirm_withdrawal(&mut w.db, &env, &w.ctx, &req.meta.id),
        Err(ServiceError::Cooling {
            remaining_secs: 86_400
        })
    ));

    w.clock.advance(Duration::hours(23));
    assert!(matches!(
        vault::confirm_withdrawal(&mut w.db, &env!(w), &w.ctx, &req.meta.id),
        Err(ServiceError::Cooling { .. })
    ));
    w.clock.advance(Duration::hours(1));
    vault::confirm_withdrawal(&mut w.db, &env!(w), &w.ctx, &req.meta.id).unwrap();
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        6_000_000
    );
    // Ikkinchi marta tasdiqlab bo'lmaydi.
    assert!(vault::confirm_withdrawal(&mut w.db, &env!(w), &w.ctx, &req.meta.id).is_err());
    // Pul olish "o'zingizga to'langan"ni kamaytirmaydi, streakni buzmaydi.
    let h = home::summary(w.db.conn(), &env!(w), &w.ctx).unwrap();
    assert_eq!(h.self_paid.minor(), 10_000_000);
}

#[test]
fn withdrawal_can_be_cancelled_and_balance_is_rechecked_at_confirm() {
    let mut w = World::new();
    let env = env!(w);
    income::record(
        &mut w.db,
        &env,
        &w.ctx,
        new_income(10_000_000, Some(10_000_000)),
    )
    .unwrap();
    let a =
        vault::request_withdrawal(&mut w.db, &env, &w.ctx, uzs(8_000_000), "A", 10, true).unwrap();
    let b =
        vault::request_withdrawal(&mut w.db, &env, &w.ctx, uzs(8_000_000), "B", 10, true).unwrap();
    vault::cancel_withdrawal(&mut w.db, &env, &w.ctx, &b.meta.id).unwrap();
    assert!(vault::cancel_withdrawal(&mut w.db, &env, &w.ctx, &b.meta.id).is_err());
    w.clock.advance(Duration::seconds(11));
    vault::confirm_withdrawal(&mut w.db, &env!(w), &w.ctx, &a.meta.id).unwrap();
    assert!(vault::confirm_withdrawal(&mut w.db, &env!(w), &w.ctx, &b.meta.id).is_err());
    assert_eq!(
        vault::balance(w.db.conn(), &w.ctx).unwrap().minor(),
        2_000_000
    );
}

#[test]
fn audit_overview_matches_the_story_numbers() {
    let mut w = World::new();
    let env = env!(w);
    let sep = YearMonth::parse("2026-09").unwrap();
    let mut inc = new_income(800_000_000, Some(0));
    inc.received_on = Some(date_from_str("2026-09-10").unwrap());
    income::record(&mut w.db, &env, &w.ctx, inc).unwrap();

    obligations::add_recurring(
        &mut w.db,
        &env,
        &w.ctx,
        "Ijara",
        uzs(300_000_000),
        5,
        MoneyOwner::Landlord,
    )
    .unwrap();
    obligations::add_recurring(
        &mut w.db,
        &env,
        &w.ctx,
        "Avtokredit",
        uzs(235_000_000),
        15,
        MoneyOwner::Bank,
    )
    .unwrap();

    let cats = domain_categories(&w);
    let by = |n: &str| cats.iter().find(|c| c.name == n).unwrap().meta.id.clone();
    audit::set_category_total(
        &mut w.db,
        &env,
        &w.ctx,
        sep,
        &by("Benzin"),
        uzs(100_000_000),
    )
    .unwrap();
    audit::set_category_total(
        &mut w.db,
        &env,
        &w.ctx,
        sep,
        &by("Oziq-ovqat"),
        uzs(65_000_000),
    )
    .unwrap();

    let o = audit::overview(w.db.conn(), &w.ctx, sep).unwrap();
    assert_eq!(o.income.minor(), 800_000_000);
    assert_eq!(o.obligations.minor(), 535_000_000);
    assert_eq!(o.expenses.minor(), 165_000_000);
    assert_eq!(o.month_result.minor(), 100_000_000);
    assert_eq!(o.unexplained.minor(), 100_000_000); // "somsaga bir million"
    let owner = |ow: MoneyOwner| {
        o.whose
            .shares
            .iter()
            .find(|s| s.owner == Some(ow))
            .map(|s| (s.amount.minor(), s.bp))
    };
    assert_eq!(owner(MoneyOwner::Landlord), Some((300_000_000, 3750)));
    assert_eq!(owner(MoneyOwner::Bank), Some((235_000_000, 2938))); // 29.375% → half-up
    assert_eq!(owner(MoneyOwner::Fuel), Some((100_000_000, 1250)));
    assert_eq!(owner(MoneyOwner::Other), Some((65_000_000, 813)));
    assert_eq!(o.whose.unexplained.minor(), 100_000_000);
}

#[test]
fn audit_entry_is_replaced_not_duplicated_and_zero_clears() {
    let mut w = World::new();
    let env = env!(w);
    let sep = YearMonth::parse("2026-09").unwrap();
    let cat = domain_categories(&w)[0].meta.id.clone();
    for v in [10, 25] {
        audit::set_category_total(&mut w.db, &env, &w.ctx, sep, &cat, uzs(v)).unwrap();
    }
    assert_eq!(
        audit::overview(w.db.conn(), &w.ctx, sep)
            .unwrap()
            .expenses
            .minor(),
        25
    );
    audit::set_category_total(&mut w.db, &env, &w.ctx, sep, &cat, uzs(0)).unwrap();
    assert_eq!(
        audit::overview(w.db.conn(), &w.ctx, sep)
            .unwrap()
            .expenses
            .minor(),
        0
    );
    // Boshqa oyga ta'sir qilmaydi.
    audit::set_category_total(&mut w.db, &env, &w.ctx, sep, &cat, uzs(7)).unwrap();
    let oct = YearMonth::parse("2026-10").unwrap();
    assert_eq!(
        audit::overview(w.db.conn(), &w.ctx, oct)
            .unwrap()
            .expenses
            .minor(),
        0
    );
    assert!(audit::set_category_total(&mut w.db, &env, &w.ctx, sep, &cat, uzs(-1)).is_err());
    assert!(matches!(
        audit::set_category_total(&mut w.db, &env, &w.ctx, sep, "yo'q", uzs(1)),
        Err(ServiceError::NotFound)
    ));
}

#[test]
fn savings_reduce_unexplained_but_not_month_result() {
    let mut w = World::new();
    let env = env!(w);
    income::record(&mut w.db, &env, &w.ctx, new_income(1_000_000, None)).unwrap(); // 5% = 50_000
    let o = audit::overview(w.db.conn(), &w.ctx, YearMonth::parse("2026-10").unwrap()).unwrap();
    assert_eq!(o.month_result.minor(), 1_000_000);
    assert_eq!(o.savings.minor(), 50_000);
    assert_eq!(o.unexplained.minor(), 950_000);
    assert_eq!(o.whose.self_paid_bp, 500);
}

#[test]
fn nasiya_payments_reduce_balance_and_become_shop_expenses() {
    let mut w = World::new();
    let env = env!(w);
    let n = obligations::add_nasiya(
        &mut w.db,
        &env,
        &w.ctx,
        "Salim aka do'koni",
        uzs(50_000_000),
    )
    .unwrap();
    assert!(obligations::add_nasiya(&mut w.db, &env, &w.ctx, " ", uzs(1)).is_err());

    let left = obligations::pay_nasiya(&mut w.db, &env, &w.ctx, &n.meta.id, uzs(20_000_000), None)
        .unwrap();
    assert_eq!(left.minor(), 30_000_000);
    assert!(
        obligations::pay_nasiya(&mut w.db, &env, &w.ctx, &n.meta.id, uzs(30_000_001), None)
            .is_err()
    );
    let left = obligations::pay_nasiya(&mut w.db, &env, &w.ctx, &n.meta.id, uzs(30_000_000), None)
        .unwrap();
    assert_eq!(left.minor(), 0);

    let o = audit::overview(w.db.conn(), &w.ctx, YearMonth::parse("2026-10").unwrap()).unwrap();
    assert_eq!(o.expenses.minor(), 50_000_000);
    assert_eq!(
        o.obligations.minor(),
        0,
        "nasiya qarzi doimiy majburiyat emas"
    );
    let shop = o
        .whose
        .shares
        .iter()
        .find(|s| s.owner == Some(MoneyOwner::Shop))
        .unwrap();
    assert_eq!(shop.amount.minor(), 50_000_000);
}

#[test]
fn recurring_obligation_validation_and_removal() {
    let mut w = World::new();
    let env = env!(w);
    for (name, amount, day) in [
        ("", 1, 5),
        ("Ijara", 0, 5),
        ("Ijara", 1, 0),
        ("Ijara", 1, 32),
    ] {
        assert!(obligations::add_recurring(
            &mut w.db,
            &env,
            &w.ctx,
            name,
            uzs(amount),
            day,
            MoneyOwner::Landlord
        )
        .is_err());
    }
    let o = obligations::add_recurring(
        &mut w.db,
        &env,
        &w.ctx,
        "Ijara",
        uzs(100),
        5,
        MoneyOwner::Landlord,
    )
    .unwrap();
    assert_eq!(
        obligations::monthly_total(w.db.conn(), &w.ctx)
            .unwrap()
            .minor(),
        100
    );
    obligations::remove(&mut w.db, &env, &w.ctx, &o.meta.id).unwrap();
    assert_eq!(
        obligations::monthly_total(w.db.conn(), &w.ctx)
            .unwrap()
            .minor(),
        0
    );
    assert!(obligations::remove(&mut w.db, &env, &w.ctx, &o.meta.id).is_err());
}

#[test]
fn streak_follows_friday_weeks_across_months() {
    let mut w = World::new();
    // 2026-10-07 chorshanba. Oldingi haftalar: 10-02 dan boshlanadigan hafta joriy.
    for _ in 0..3 {
        let env = env!(w);
        income::record(&mut w.db, &env, &w.ctx, new_income(1_000, None)).unwrap();
        w.clock.advance(Duration::days(-7));
    }
    w.clock.advance(Duration::days(21)); // yana bugunga
    let env = env!(w);
    let h = home::summary(w.db.conn(), &env, &w.ctx).unwrap();
    assert_eq!(
        (
            h.streak.current_weeks,
            h.streak.best_weeks,
            h.streak.saved_days
        ),
        (3, 3, 3)
    );
}
