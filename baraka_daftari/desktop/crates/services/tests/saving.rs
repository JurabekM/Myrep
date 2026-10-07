#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, BillingPeriod, Clock, Date, IdGen, Necessity, OffsetDateTime, PaymentChannel,
    RescueKind,
};
use money::{Currency, Money};
use services::{
    categories,
    csv_import::{self, DateFormat, Mapping, SignRule},
    envelopes,
    expenses::{self, NewExpense},
    home, rescue, setup, subscriptions, vault, Ctx, Env, ServiceError,
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
}

fn uzs(v: i64) -> Money {
    Money::new(v, Currency::Uzs)
}

fn d(s: &str) -> Date {
    date_from_str(s).unwrap()
}

impl World {
    /// 2026-10-07 (chorshanba); joriy hafta 2026-10-02 (juma) dan.
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

    fn cat(&self, name: &str) -> String {
        categories::by_name(self.db.conn(), &self.ctx, name)
            .unwrap()
            .unwrap()
            .meta
            .id
    }

    fn add_env(
        &mut self,
        name: &str,
        limit: i64,
        category: Option<&str>,
        nec: Option<Necessity>,
    ) -> domain::Envelope {
        let cat = category.map(|c| self.cat(c));
        let env = env!(self);
        envelopes::add(&mut self.db, &env, &self.ctx, name, uzs(limit), cat, nec).unwrap()
    }

    fn import(
        &mut self,
        parsed: csv_import::Parsed,
        default_category: &str,
    ) -> Result<csv_import::ImportOutcome, ServiceError> {
        let cat = self.cat(default_category);
        self.import_raw(parsed, &cat)
    }

    fn import_raw(
        &mut self,
        parsed: csv_import::Parsed,
        category_id: &str,
    ) -> Result<csv_import::ImportOutcome, ServiceError> {
        let env = env!(self);
        csv_import::import(&mut self.db, &env, &self.ctx, parsed, category_id)
    }

    fn days(&self, n: i64) {
        self.clock.0.set(self.clock.0.get() + Duration::days(n));
    }

    fn spend(
        &mut self,
        category: &str,
        amount: i64,
        date: &str,
        edit: impl FnOnce(&mut NewExpense),
    ) {
        let env = env!(self);
        let mut e = NewExpense {
            date: d(date),
            category_id: self.cat(category),
            amount: uzs(amount),
            channel: PaymentChannel::Cash,
            note: None,
            necessity: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            member_id: None,
        };
        edit(&mut e);
        expenses::add_many(&mut self.db, &env, &self.ctx, vec![e]).unwrap();
    }
}

// ------------------------------------------------------------ obunalar

#[test]
fn subscription_costs_and_validation() {
    let mut w = World::new();
    let add = |w: &mut World, name: &str, a: Money, p: BillingPeriod, s: Option<Date>| {
        let env = env!(w);
        subscriptions::add(&mut w.db, &env, &w.ctx, name, a, p, s)
    };
    let m = BillingPeriod::Monthly;
    assert!(add(&mut w, " ", uzs(1), m, None).is_err());
    assert!(add(&mut w, "X", uzs(-1), m, None).is_err());
    assert!(add(&mut w, "X", uzs(1), m, Some(d("2026-10-08"))).is_err());
    assert!(add(&mut w, "X", Money::new(5, Currency::Usd), m, None).is_err());

    add(&mut w, "Netflix", uzs(9_000_000), m, None).unwrap();
    add(
        &mut w,
        "iCloud",
        uzs(1_000_000),
        BillingPeriod::Weekly,
        None,
    )
    .unwrap();
    add(
        &mut w,
        "Antivirus",
        uzs(1_200_005),
        BillingPeriod::Yearly,
        None,
    )
    .unwrap();
    let t = subscriptions::totals(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap();
    assert_eq!(t.monthly.minor(), 9_000_000 + 4_333_333 + 100_000);
    assert_eq!(t.yearly.minor(), 108_000_000 + 52_000_000 + 1_200_005);
}

#[test]
fn forgotten_detector_mark_used_and_needed_flag() {
    let mut w = World::new();
    let env = env!(w);
    let s = subscriptions::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Spotify",
        uzs(5_000_000),
        BillingPeriod::Monthly,
        Some(d("2026-08-08")),
    )
    .unwrap();
    // 2026-08-08 .. 2026-10-07 = 60 kun
    let v = &subscriptions::list(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap()[0];
    assert!(v.forgotten && v.active);
    assert!(
        !subscriptions::list(w.db.conn(), &w.ctx, d("2026-10-06")).unwrap()[0].forgotten,
        "59 kun: hali emas"
    );

    subscriptions::mark_used(&mut w.db, &env, &w.ctx, &s.meta.id).unwrap();
    assert!(!subscriptions::list(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap()[0].forgotten);
    w.days(60);
    assert!(subscriptions::list(w.db.conn(), &w.ctx, d("2026-12-06")).unwrap()[0].forgotten);

    subscriptions::set_needed(&mut w.db, &env!(w), &w.ctx, &s.meta.id, Some(false)).unwrap();
    assert_eq!(
        subscriptions::list(w.db.conn(), &w.ctx, d("2026-12-06")).unwrap()[0]
            .sub
            .needed,
        Some(false)
    );
    subscriptions::set_needed(&mut w.db, &env!(w), &w.ctx, &s.meta.id, None).unwrap();
    assert_eq!(
        subscriptions::list(w.db.conn(), &w.ctx, d("2026-12-06")).unwrap()[0]
            .sub
            .needed,
        None
    );
    assert!(subscriptions::mark_used(&mut w.db, &env!(w), &w.ctx, "yo'q").is_err());
}

#[test]
fn cancelling_records_one_month_as_rescued_money_and_is_not_repeatable() {
    let mut w = World::new();
    let env = env!(w);
    let weekly = subscriptions::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Kuryer",
        uzs(1_000_000),
        BillingPeriod::Weekly,
        None,
    )
    .unwrap();
    let free = subscriptions::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Bepul",
        uzs(0),
        BillingPeriod::Monthly,
        None,
    )
    .unwrap();

    let r = subscriptions::cancel(&mut w.db, &env, &w.ctx, &weekly.meta.id)
        .unwrap()
        .unwrap();
    assert_eq!(
        (r.kind, r.amount.minor(), r.note.as_deref()),
        (RescueKind::Subscription, 4_333_333, Some("Kuryer"))
    );
    assert!(subscriptions::cancel(&mut w.db, &env, &w.ctx, &weekly.meta.id).is_err());
    assert!(
        subscriptions::cancel(&mut w.db, &env, &w.ctx, &free.meta.id)
            .unwrap()
            .is_none(),
        "bepul obuna: qutqarilgan pul yo'q"
    );
    assert!(subscriptions::mark_used(&mut w.db, &env, &w.ctx, &weekly.meta.id).is_err());

    let views = subscriptions::list(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap();
    assert!(views.iter().all(|v| !v.active && !v.forgotten));
    assert_eq!(
        subscriptions::totals(w.db.conn(), &w.ctx, d("2026-10-07"))
            .unwrap()
            .monthly
            .minor(),
        0
    );
    assert_eq!(
        rescue::available(w.db.conn(), &w.ctx).unwrap().minor(),
        4_333_333
    );
}

#[test]
fn removing_a_subscription_does_not_credit_rescue() {
    let mut w = World::new();
    let env = env!(w);
    let s = subscriptions::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Xato kiritilgan",
        uzs(100),
        BillingPeriod::Monthly,
        None,
    )
    .unwrap();
    subscriptions::remove(&mut w.db, &env, &w.ctx, &s.meta.id).unwrap();
    assert!(subscriptions::list(w.db.conn(), &w.ctx, d("2026-10-07"))
        .unwrap()
        .is_empty());
    assert_eq!(rescue::available(w.db.conn(), &w.ctx).unwrap().minor(), 0);
}

// ------------------------------------------------------------ konvertlar

#[test]
fn envelope_counts_cash_and_card_and_reports_cash_to_fill() {
    let mut w = World::new();
    let bozor = w.add_env("Bozor", 100_000, Some("Oziq-ovqat"), None);
    w.spend("Oziq-ovqat", 30_000, "2026-10-03", |_| {});
    w.spend("Oziq-ovqat", 50_000, "2026-10-05", |e| {
        e.channel = PaymentChannel::Card
    }); // karta ham ayriladi
    w.spend("Yo'lkira", 99_000, "2026-10-05", |_| {}); // boshqa kategoriya
    let v = &envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap()[0];
    assert_eq!(v.week_start, d("2026-10-02"));
    assert_eq!(
        (
            v.spent.minor(),
            v.status.remaining.minor(),
            v.cash_to_fill.minor()
        ),
        (80_000, 20_000, 20_000)
    );
    assert_eq!(v.status.state, domain::HavasState::Near);
    assert_eq!(v.envelope.meta.id, bozor.meta.id);

    w.spend("Oziq-ovqat", 50_000, "2026-10-06", |_| {});
    let v = &envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap()[0];
    assert_eq!(
        (
            v.status.remaining.minor(),
            v.cash_to_fill.minor(),
            v.status.state
        ),
        (-30_000, 0, domain::HavasState::Over)
    );
}

#[test]
fn week_boundaries_follow_friday() {
    let mut w = World::new();
    w.add_env("Bozor", 100_000, Some("Oziq-ovqat"), None);
    w.spend("Oziq-ovqat", 1_000, "2026-10-01", |_| {}); // payshanba — oldingi hafta
    w.spend("Oziq-ovqat", 2_000, "2026-10-02", |_| {}); // juma — shu hafta
    let this = envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap();
    let prev = envelopes::status(w.db.conn(), &w.ctx, d("2026-09-30")).unwrap();
    assert_eq!(this[0].spent.minor(), 2_000);
    assert_eq!(prev[0].spent.minor(), 1_000);
}

#[test]
fn havas_envelope_uses_havas_rule_charity_and_gifts_excluded() {
    let mut w = World::new();
    let env = env!(w);
    envelopes::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Havas",
        uzs(100_000),
        None,
        Some(Necessity::Havas),
    )
    .unwrap();
    w.spend("Gazak va ichimlik", 10_000, "2026-10-05", |_| {});
    w.spend("Gazak va ichimlik", 7_000, "2026-10-05", |e| {
        e.is_gift = true
    });
    w.spend("Sadaqa", 50_000, "2026-10-05", |e| {
        e.necessity = Some(Necessity::Havas)
    });
    w.spend("Oziq-ovqat", 3_000, "2026-10-05", |e| {
        e.necessity = Some(Necessity::Havas)
    }); // xarajat darajasida havas
    assert_eq!(
        envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap()[0]
            .spent
            .minor(),
        13_000
    );
}

#[test]
fn explicit_envelope_id_wins_over_category_matching() {
    let mut w = World::new();
    let bozor = w.add_env("Bozor", 100_000, Some("Oziq-ovqat"), None);
    let other = w.add_env("Boshqa", 100_000, None, None);
    w.spend("Oziq-ovqat", 5_000, "2026-10-05", |_| {});
    // Xarajatni qo'lda boshqa konvertga biriktiramiz.
    let list = expenses::list_range(w.db.conn(), &w.ctx, d("2026-10-05"), d("2026-10-05")).unwrap();
    let mut e = list[0].clone();
    e.envelope_id = Some(other.meta.id.clone());
    storage::repo::update(w.db.conn(), &e, w.clock.0.get()).unwrap();
    let by_name = |n: &str| {
        envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07"))
            .unwrap()
            .into_iter()
            .find(|v| v.envelope.name == n)
            .unwrap()
    };
    assert_eq!(by_name("Bozor").spent.minor(), 0);
    assert_eq!(by_name("Boshqa").spent.minor(), 5_000);
    let _ = bozor;
}

#[test]
fn closing_a_week_stores_difference_and_can_be_redone() {
    let mut w = World::new();
    let bozor = w.add_env("Bozor", 100_000, Some("Oziq-ovqat"), None);
    w.spend("Oziq-ovqat", 80_000, "2026-10-04", |_| {});

    let p = envelopes::close_week(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &bozor.meta.id,
        d("2026-10-07"),
        uzs(15_000),
    )
    .unwrap();
    assert_eq!(
        (
            p.spent.minor(),
            p.leftover_cash.minor(),
            p.difference.minor()
        ),
        (80_000, 15_000, 5_000)
    );
    assert!(
        envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap()[0]
            .closed
            .is_some()
    );

    let p2 = envelopes::close_week(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &bozor.meta.id,
        d("2026-10-07"),
        uzs(25_000),
    )
    .unwrap();
    assert_eq!(p2.meta.id, p.meta.id, "qayta yopish yozuvni yangilaydi");
    assert_eq!(p2.difference.minor(), -5_000);

    assert!(
        envelopes::close_week(
            &mut w.db,
            &env!(w),
            &w.ctx,
            &bozor.meta.id,
            d("2026-10-14"),
            uzs(0)
        )
        .is_err(),
        "kelajak haftasi"
    );
    assert!(envelopes::close_week(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &bozor.meta.id,
        d("2026-10-07"),
        uzs(-1)
    )
    .is_err());
    assert!(
        envelopes::close_week(&mut w.db, &env!(w), &w.ctx, "yo'q", d("2026-10-07"), uzs(0))
            .is_err()
    );
}

#[test]
fn envelope_validation_and_deactivation() {
    let mut w = World::new();
    let env = env!(w);
    assert!(envelopes::add(&mut w.db, &env, &w.ctx, " ", uzs(1), None, None).is_err());
    assert!(envelopes::add(&mut w.db, &env, &w.ctx, "X", uzs(0), None, None).is_err());
    assert!(matches!(
        envelopes::add(
            &mut w.db,
            &env,
            &w.ctx,
            "X",
            uzs(1),
            Some("yo'q".into()),
            None
        ),
        Err(ServiceError::NotFound)
    ));
    let e = w.add_env("X", 1, None, None);
    let env = env!(w);
    envelopes::set_active(&mut w.db, &env, &w.ctx, &e.meta.id, false).unwrap();
    assert!(envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07"))
        .unwrap()
        .is_empty());
    envelopes::set_active(&mut w.db, &env, &w.ctx, &e.meta.id, true).unwrap();
    envelopes::remove(&mut w.db, &env, &w.ctx, &e.meta.id).unwrap();
    assert!(envelopes::status(w.db.conn(), &w.ctx, d("2026-10-07"))
        .unwrap()
        .is_empty());
}

// ------------------------------------------------------------ qutqarilgan pul

/// Tugagan hafta 2026-09-25..10-01, undan oldingi 09-18..09-24.
fn havas_weeks(w: &mut World, before: i64, after: i64) {
    w.spend("Gazak va ichimlik", before, "2026-09-20", |_| {});
    w.spend("Gazak va ichimlik", after, "2026-09-27", |_| {});
}

/// Qabul mezoni (D7): qutqarilgan pul — havas kamaygan miqdor; manfiy holat → 0.
#[test]
fn rescued_money_is_the_drop_in_havas_and_never_negative() {
    let mut w = World::new();
    havas_weeks(&mut w, 50_000, 30_000);
    let r = rescue::weekly_report(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap();
    assert_eq!(
        (r.week, r.baseline_week),
        (d("2026-09-25"), d("2026-09-18"))
    );
    assert_eq!(
        (r.baseline.minor(), r.current.minor(), r.rescued.minor()),
        (50_000, 30_000, 20_000)
    );

    let mut w = World::new();
    havas_weeks(&mut w, 30_000, 50_000); // havas ko'paydi
    let r = rescue::weekly_report(w.db.conn(), &w.ctx, d("2026-10-07")).unwrap();
    assert_eq!(r.rescued.minor(), 0);
    assert!(
        rescue::claim_week(&mut w.db, &env!(w), &w.ctx)
            .unwrap()
            .is_none(),
        "0 bo'lsa yozilmaydi"
    );
    assert!(rescue::list(w.db.conn(), &w.ctx).unwrap().is_empty());
}

#[test]
fn first_week_without_history_rescues_nothing() {
    let mut w = World::new();
    w.spend("Gazak va ichimlik", 1_000, "2026-09-27", |_| {});
    assert_eq!(
        rescue::weekly_report(w.db.conn(), &w.ctx, d("2026-10-07"))
            .unwrap()
            .rescued
            .minor(),
        0
    );
}

#[test]
fn only_havas_counts_charity_and_necessities_are_not_a_win() {
    let mut w = World::new();
    // Oldingi hafta: katta sadaqa va zarur xarajat; shu hafta ular kamaygan — bu «yutuq» emas.
    w.spend("Sadaqa", 500_000, "2026-09-20", |_| {});
    w.spend("Oziq-ovqat", 300_000, "2026-09-20", |_| {});
    w.spend("Gazak va ichimlik", 40_000, "2026-09-20", |e| {
        e.is_gift = true
    });
    w.spend("Gazak va ichimlik", 10_000, "2026-09-20", |_| {});
    w.spend("Gazak va ichimlik", 4_000, "2026-09-27", |_| {});
    assert_eq!(
        rescue::weekly_report(w.db.conn(), &w.ctx, d("2026-10-07"))
            .unwrap()
            .rescued
            .minor(),
        6_000
    );
}

#[test]
fn claim_is_idempotent_and_transfer_moves_money_to_the_vault() {
    let mut w = World::new();
    havas_weeks(&mut w, 50_000, 30_000);
    let env = env!(w);
    let r = rescue::claim_week(&mut w.db, &env, &w.ctx)
        .unwrap()
        .unwrap();
    assert_eq!(
        (r.kind, r.amount.minor(), r.week_start),
        (RescueKind::HavasDrop, 20_000, Some(d("2026-09-25")))
    );
    let again = rescue::claim_week(&mut w.db, &env, &w.ctx)
        .unwrap()
        .unwrap();
    assert_eq!(again.meta.id, r.meta.id);
    assert_eq!(rescue::list(w.db.conn(), &w.ctx).unwrap().len(), 1);
    assert_eq!(
        rescue::available(w.db.conn(), &w.ctx).unwrap().minor(),
        20_000
    );

    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap().minor(), 0);
    rescue::transfer(&mut w.db, &env, &w.ctx, &r.meta.id).unwrap();
    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap().minor(), 20_000);
    assert_eq!(rescue::available(w.db.conn(), &w.ctx).unwrap().minor(), 0);
    assert!(
        rescue::transfer(&mut w.db, &env, &w.ctx, &r.meta.id).is_err(),
        "ikki marta o'tkazib bo'lmaydi"
    );
    assert!(rescue::transfer(&mut w.db, &env, &w.ctx, "yo'q").is_err());
    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap().minor(), 20_000);

    // O'tkazma «o'zingizga to'langan» va ketma-ketlikka qo'shiladi.
    let h = home::summary(w.db.conn(), &env, &w.ctx).unwrap();
    assert_eq!(h.self_paid.minor(), 20_000);
    assert_eq!(h.streak.current_weeks, 1);
}

#[test]
fn transfer_all_combines_havas_drop_and_cancelled_subscriptions() {
    let mut w = World::new();
    havas_weeks(&mut w, 50_000, 30_000);
    let env = env!(w);
    rescue::claim_week(&mut w.db, &env, &w.ctx).unwrap();
    let sub = subscriptions::add(
        &mut w.db,
        &env,
        &w.ctx,
        "Netflix",
        uzs(9_000),
        BillingPeriod::Monthly,
        None,
    )
    .unwrap();
    subscriptions::cancel(&mut w.db, &env, &w.ctx, &sub.meta.id).unwrap();

    assert_eq!(
        rescue::available(w.db.conn(), &w.ctx).unwrap().minor(),
        29_000
    );
    assert_eq!(
        rescue::transfer_all(&mut w.db, &env, &w.ctx)
            .unwrap()
            .minor(),
        29_000
    );
    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap().minor(), 29_000);
    assert_eq!(rescue::available(w.db.conn(), &w.ctx).unwrap().minor(), 0);
    assert_eq!(
        rescue::transfer_all(&mut w.db, &env, &w.ctx)
            .unwrap()
            .minor(),
        0
    );
}

// ------------------------------------------------------------ CSV import

fn mapping() -> Mapping {
    Mapping {
        date_col: 0,
        amount_col: 1,
        note_col: Some(2),
        date_format: DateFormat::DayMonthYearDots,
        sign: SignRule::NegativeAreExpenses,
    }
}

const CSV: &str = "Sana;Summa;Izoh\n\
    05.10.2026;-15 000;Somsa\n\
    06.10.2026;+8 000 000;Oylik\n\
    06.10.2026;-250 000;Benzin\n\
    xx;-1;Xato\n";

fn parsed(csv: &str) -> csv_import::Parsed {
    let t = csv_import::parse_table(csv.as_bytes()).unwrap();
    csv_import::parse_rows(&t, &mapping(), Currency::Uzs, d("2026-10-07"))
}

#[test]
fn import_creates_expenses_uses_note_history_and_skips_income_and_bad_rows() {
    let mut w = World::new();
    w.spend("Gazak va ichimlik", 1, "2026-10-01", |e| {
        e.note = Some("somsa".into())
    });
    let p = parsed(CSV);
    let out = w.import(p, "Boshqa").unwrap();
    assert_eq!(
        (
            out.imported,
            out.duplicates,
            out.skipped_sign,
            out.errors.len()
        ),
        (2, 0, 1, 1)
    );

    let all = expenses::list_range(w.db.conn(), &w.ctx, d("2026-10-05"), d("2026-10-06")).unwrap();
    assert_eq!(all.len(), 2);
    let somsa = all
        .iter()
        .find(|e| e.note.as_deref() == Some("Somsa"))
        .unwrap();
    assert_eq!(
        somsa.category_id,
        w.cat("Gazak va ichimlik"),
        "izohdan kategoriya topildi"
    );
    assert_eq!(somsa.amount.minor(), 1_500_000);
    assert_eq!(somsa.payment_channel, PaymentChannel::Card);
    let benzin = all
        .iter()
        .find(|e| e.note.as_deref() == Some("Benzin"))
        .unwrap();
    assert_eq!(
        benzin.category_id,
        w.cat("Boshqa"),
        "noma'lum izoh: standart kategoriya"
    );
}

#[test]
fn importing_the_same_file_twice_does_not_duplicate() {
    let mut w = World::new();
    let first = w.import(parsed(CSV), "Boshqa").unwrap();
    assert_eq!(first.imported, 2);
    let second = w.import(parsed(CSV), "Boshqa").unwrap();
    assert_eq!((second.imported, second.duplicates), (0, 2));
    assert_eq!(
        expenses::list_range(w.db.conn(), &w.ctx, d("2026-10-01"), d("2026-10-31"))
            .unwrap()
            .len(),
        2
    );
}

#[test]
fn duplicate_rows_inside_one_file_are_collapsed_and_unknown_category_fails_cleanly() {
    let mut w = World::new();
    let two = "Sana;Summa;Izoh\n05.10.2026;-1 000;Non\n05.10.2026;-1 000;Non\n";
    let out = w.import(parsed(two), "Boshqa").unwrap();
    assert_eq!((out.imported, out.duplicates), (1, 1));
    assert!(matches!(
        csv_import::import(&mut w.db, &env!(w), &w.ctx, parsed(CSV), "yo'q"),
        Err(ServiceError::NotFound)
    ));
}
