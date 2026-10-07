#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{date_from_str, Clock, IdGen, MemberRole, Necessity, OffsetDateTime, PaymentChannel};
use money::{Currency, Money};
use security::KdfParams;
use services::{
    categories::{self, NewCategory},
    council,
    expenses::{self, NewExpense},
    habits, havas, members, setup, treats, Ctx, Env, ServiceError, YearMonth,
};
use storage::Database;
use time::Duration;

const FAST: KdfParams = KdfParams::fast_for_tests();

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
    /// Birinchi a'zo (Adult) PIN: 111111.
    karim: String,
}

fn uzs(v: i64) -> Money {
    Money::new(v, Currency::Uzs)
}

impl World {
    /// 2026-10-07 (chorshanba) 10:00 Toshkent. Bitta kattali a'zo, PIN 111111.
    fn new() -> Self {
        let mut db = Database::open_in_memory(&[8; 32]).unwrap();
        let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-07 05:00 UTC)));
        let ids = Seq(Cell::new(1));
        let env = Env {
            clock: &clock,
            ids: &ids,
            device_id: "dev",
        };
        let ctx = setup::ensure_household(&mut db, &env).unwrap();
        members::set_pin(&mut db, &env, &ctx, &ctx.member_id, "111111", FAST).unwrap();
        let karim = ctx.member_id.clone();
        Self {
            db,
            clock,
            ids,
            ctx,
            karim,
        }
    }

    fn add_adult(&mut self, name: &str, pin: &str) -> String {
        let env = env!(self);
        let m = members::add(&mut self.db, &env, &self.ctx, name, MemberRole::Adult).unwrap();
        members::set_pin(&mut self.db, &env, &self.ctx, &m.meta.id, pin, FAST).unwrap();
        m.meta.id
    }

    fn cat(&self, name: &str) -> String {
        categories::by_name(self.db.conn(), &self.ctx, name)
            .unwrap()
            .unwrap()
            .meta
            .id
    }

    fn spend(&mut self, category: &str, amount: i64, edit: impl FnOnce(&mut NewExpense)) {
        let env = env!(self);
        let mut e = NewExpense {
            date: date_from_str("2026-10-05").unwrap(),
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

    fn set_nec(&mut self, category: &str, nec: Necessity, by: String) {
        let id = self.cat(category);
        let env = env!(self);
        categories::set_necessity(&mut self.db, &env, &self.ctx, &id, nec, &by).unwrap();
    }

    fn propose(
        &mut self,
        by: &str,
        pin: &str,
        amount: i64,
    ) -> Result<domain::HavasLimit, ServiceError> {
        let env = env!(self);
        havas::propose(&mut self.db, &env, &self.ctx, by, pin, uzs(amount))
    }

    fn consent(&mut self, limit: &str, by: &str, pin: &str) -> Result<(), ServiceError> {
        let env = env!(self);
        havas::consent(&mut self.db, &env, &self.ctx, limit, by, pin)
    }

    fn report(&self) -> havas::Report {
        havas::report(
            self.db.conn(),
            &self.ctx,
            YearMonth::parse("2026-10").unwrap(),
        )
        .unwrap()
    }
}

// ----------------------------------------------------------- toifalar

#[test]
fn defaults_have_necessity_and_sadaqa_is_charity() {
    let w = World::new();
    let by = |n: &str| {
        categories::by_name(w.db.conn(), &w.ctx, n)
            .unwrap()
            .unwrap()
    };
    assert_eq!(by("Oziq-ovqat").necessity, Some(Necessity::Zarur));
    assert_eq!(by("Telefon").necessity, Some(Necessity::Kerak));
    assert_eq!(by("Gazak va ichimlik").necessity, Some(Necessity::Havas));
    assert!(by("Sadaqa").is_charity);
    assert_eq!(by("Juma shirinligi").necessity, Some(Necessity::Havas));
    assert!(setup::DEFAULT_CATEGORIES
        .iter()
        .all(|d| by(d.name).necessity.is_some()));
}

#[test]
fn old_databases_get_defaults_without_overriding_user_choices() {
    let mut w = World::new();
    // Eski bazani taqlid: bitta kategoriya toifasiz, bittasini foydalanuvchi o'zgartirgan, bittasi yo'q.
    let kiyim = w.cat("Kiyim");
    let mut c = storage::repo::get::<domain::Category>(w.db.conn(), &kiyim)
        .unwrap()
        .unwrap();
    c.necessity = None;
    storage::repo::update(w.db.conn(), &c, w.clock.0.get()).unwrap();
    w.set_nec("Telefon", Necessity::Havas, w.karim.clone());
    let sadaqa = w.cat("Sadaqa");
    storage::repo::soft_delete::<domain::Category>(w.db.conn(), &sadaqa, w.clock.0.get()).unwrap();

    let ctx = setup::ensure_household(&mut w.db, &env!(w)).unwrap();
    let by = |n: &str| categories::by_name(w.db.conn(), &ctx, n).unwrap().unwrap();
    assert_eq!(
        by("Kiyim").necessity,
        Some(Necessity::Kerak),
        "toifasizga standart qo'yildi"
    );
    assert_eq!(
        by("Telefon").necessity,
        Some(Necessity::Havas),
        "foydalanuvchi tanloviga tegilmadi"
    );
    assert!(
        by("Sadaqa").is_charity,
        "yetishmayotgan kategoriya qaytarildi"
    );
    // Idempotent.
    setup::ensure_household(&mut w.db, &env!(w)).unwrap();
    assert_eq!(
        categories::list(w.db.conn(), &ctx).unwrap().len(),
        setup::DEFAULT_CATEGORIES.len()
    );
}

#[test]
fn necessity_change_records_who_and_when_and_noop_when_same() {
    let mut w = World::new();
    let dilnoza = w.add_adult("Dilnoza", "222222");
    let cat = w.cat("Gazak va ichimlik");
    let env = env!(w);
    categories::set_necessity(&mut w.db, &env, &w.ctx, &cat, Necessity::Havas, &dilnoza).unwrap(); // o'zgarish yo'q
    assert!(categories::history(w.db.conn(), &w.ctx, Some(&cat))
        .unwrap()
        .is_empty());

    categories::set_necessity(&mut w.db, &env, &w.ctx, &cat, Necessity::Kerak, &dilnoza).unwrap();
    w.clock.0.set(w.clock.0.get() + Duration::hours(1));
    let env = env!(w);
    categories::set_necessity(&mut w.db, &env, &w.ctx, &cat, Necessity::Zarur, &w.karim).unwrap();

    let h = categories::history(w.db.conn(), &w.ctx, Some(&cat)).unwrap();
    assert_eq!(h.len(), 2);
    assert_eq!(
        (h[0].from, h[0].to, h[0].changed_by.as_str()),
        (Some(Necessity::Havas), Necessity::Kerak, dilnoza.as_str())
    );
    assert_eq!(
        (h[1].from, h[1].to, h[1].changed_by.as_str()),
        (Some(Necessity::Kerak), Necessity::Zarur, w.karim.as_str())
    );
    assert!(h[1].meta.created_at > h[0].meta.created_at);
    assert!(
        categories::set_necessity(&mut w.db, &env, &w.ctx, &cat, Necessity::Zarur, "yo'q").is_err()
    );
    assert!(
        categories::set_necessity(&mut w.db, &env, &w.ctx, "yo'q", Necessity::Zarur, &w.karim)
            .is_err()
    );
}

#[test]
fn category_add_validation() {
    let mut w = World::new();
    let env = env!(w);
    let new = |name: &str| NewCategory {
        name: name.into(),
        necessity: Some(Necessity::Kerak),
        owner: None,
        is_charity: false,
        is_habit: false,
    };
    assert!(categories::add(&mut w.db, &env, &w.ctx, new("  ")).is_err());
    assert!(
        categories::add(&mut w.db, &env, &w.ctx, new("oziq-OVQAT")).is_err(),
        "katta-kichik harf farqsiz takror"
    );
    categories::add(&mut w.db, &env, &w.ctx, new("Chekish")).unwrap();
}

// ----------------------------------------------------------- PIN

#[test]
fn member_pin_is_verified_and_locked_after_repeated_failures() {
    let mut w = World::new();
    let env = env!(w);
    assert!(members::has_pin(w.db.conn(), &w.ctx, &w.karim).unwrap());
    members::verify(&mut w.db, &env, &w.ctx, &w.karim, "111111").unwrap();
    for _ in 0..3 {
        let env = env!(w);
        assert!(matches!(
            members::verify(&mut w.db, &env, &w.ctx, &w.karim, "000000"),
            Err(ServiceError::WrongPin)
        ));
    }
    let env = env!(w);
    assert!(
        matches!(
            members::verify(&mut w.db, &env, &w.ctx, &w.karim, "111111"),
            Err(ServiceError::PinLocked {
                retry_after_secs: 30
            })
        ),
        "to'g'ri PIN ham kutish vaqtida rad etiladi"
    );
    w.clock.0.set(w.clock.0.get() + Duration::seconds(31));
    let env = env!(w);
    members::verify(&mut w.db, &env, &w.ctx, &w.karim, "111111").unwrap();
}

#[test]
fn member_without_pin_cannot_consent_and_pin_format_is_validated() {
    let mut w = World::new();
    let env = env!(w);
    let m = members::add(&mut w.db, &env, &w.ctx, "Sanjar", MemberRole::Adult).unwrap();
    assert!(matches!(
        members::verify(&mut w.db, &env, &w.ctx, &m.meta.id, "123456"),
        Err(ServiceError::NoPin)
    ));
    for bad in ["12345", "abcdef", ""] {
        assert!(members::set_pin(&mut w.db, &env, &w.ctx, &m.meta.id, bad, FAST).is_err());
    }
    assert!(
        members::add(&mut w.db, &env, &w.ctx, "sanjar", MemberRole::Adult).is_err(),
        "ism takrori"
    );
    assert!(members::set_pin(&mut w.db, &env, &w.ctx, "yo'q", "123456", FAST).is_err());
}

// ----------------------------------------------------------- havas chegarasi

/// Qabul mezoni (D6): rozilik to'liq bo'lmaguncha chegara faol emas.
#[test]
fn limit_is_inactive_until_every_adult_consents_with_own_pin() {
    let mut w = World::new();
    let dilnoza = w.add_adult("Dilnoza", "222222");
    w.spend("Gazak va ichimlik", 900_000, |_| {});

    let limit = w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    let r = w.report();
    assert_eq!(r.limit, None, "bir tomonlama chegara kuchga kirmaydi");
    assert!(
        r.status.is_none(),
        "faol bo'lmagan chegara ogohlantirish bermaydi"
    );
    let p = r.pending.unwrap();
    assert_eq!(p.amount.minor(), 1_000_000);
    assert_eq!(p.consented.len(), 1);
    assert_eq!(
        p.missing
            .iter()
            .map(|m| m.display_name.as_str())
            .collect::<Vec<_>>(),
        ["Dilnoza"]
    );

    // Noto'g'ri PIN (Karimning PIN'i Dilnoza nomidan) — rozilik yozilmaydi.
    assert!(matches!(
        w.consent(&limit.meta.id, &dilnoza, "111111"),
        Err(ServiceError::WrongPin)
    ));
    assert_eq!(w.report().limit, None);

    w.consent(&limit.meta.id, &dilnoza, "222222").unwrap();
    let r = w.report();
    assert_eq!(r.limit, Some(uzs(1_000_000)));
    assert!(r.pending.is_none());
    let st = r.status.unwrap();
    assert_eq!((st.state, st.used_bp), (domain::HavasState::Near, 9000));
}

#[test]
fn single_adult_household_activates_immediately_on_own_pin() {
    let mut w = World::new();
    assert!(matches!(
        w.propose(&w.karim.clone(), "999999", 1_000),
        Err(ServiceError::WrongPin)
    ));
    w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    assert_eq!(w.report().limit, Some(uzs(1_000_000)));
}

#[test]
fn soft_warnings_at_80_and_100_percent_never_block_spending() {
    let mut w = World::new();
    w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    w.spend("Gazak va ichimlik", 700_000, |_| {});
    assert_eq!(w.report().status.unwrap().state, domain::HavasState::Ok);
    w.spend("Gazak va ichimlik", 100_000, |_| {});
    assert_eq!(w.report().status.unwrap().state, domain::HavasState::Near);
    w.spend("Gazak va ichimlik", 400_000, |_| {}); // bloklanmaydi
    let st = w.report().status.unwrap();
    assert_eq!((st.state, st.used_bp), (domain::HavasState::Over, 12_000));
}

#[test]
fn new_proposal_needs_consent_old_limit_stays_in_force_and_stale_consent_is_rejected() {
    let mut w = World::new();
    let dilnoza = w.add_adult("Dilnoza", "222222");
    let first = w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    w.consent(&first.meta.id, &dilnoza, "222222").unwrap();
    assert_eq!(w.report().limit, Some(uzs(1_000_000)));

    let second = w.propose(&dilnoza, "222222", 500_000).unwrap();
    let r = w.report();
    assert_eq!(
        r.limit,
        Some(uzs(1_000_000)),
        "eski chegara kelishilgunga qadar amalda"
    );
    assert_eq!(r.pending.unwrap().amount.minor(), 500_000);
    // Eskirgan taklifga rozilik rad etiladi.
    assert!(matches!(
        w.consent(&first.meta.id, &w.karim.clone(), "111111"),
        Err(ServiceError::Invalid(_))
    ));
    w.consent(&second.meta.id, &w.karim.clone(), "111111")
        .unwrap();
    assert_eq!(w.report().limit, Some(uzs(500_000)));
}

#[test]
fn adding_an_adult_suspends_the_limit_until_they_consent() {
    let mut w = World::new();
    let limit = w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    assert_eq!(w.report().limit, Some(uzs(1_000_000)));
    let sanjar = w.add_adult("Sanjar", "333333");
    let r = w.report();
    assert_eq!(r.limit, None);
    assert_eq!(
        r.pending.as_ref().unwrap().missing[0].display_name,
        "Sanjar"
    );
    w.consent(&limit.meta.id, &sanjar, "333333").unwrap();
    assert_eq!(w.report().limit, Some(uzs(1_000_000)));
}

#[test]
fn children_do_not_block_and_cannot_consent() {
    let mut w = World::new();
    let env = env!(w);
    let child = members::add(&mut w.db, &env, &w.ctx, "Aziza", MemberRole::Child).unwrap();
    members::set_pin(&mut w.db, &env, &w.ctx, &child.meta.id, "444444", FAST).unwrap();
    let limit = w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    assert_eq!(
        w.report().limit,
        Some(uzs(1_000_000)),
        "bola roziligisiz ham faol"
    );
    assert!(matches!(
        w.consent(&limit.meta.id, &child.meta.id, "444444"),
        Err(ServiceError::Invalid(_))
    ));
    assert!(matches!(
        w.propose(&child.meta.id, "444444", 5),
        Err(ServiceError::Invalid(_))
    ));
}

#[test]
fn proposal_validation() {
    let mut w = World::new();
    assert!(w.propose(&w.karim.clone(), "111111", 0).is_err());
    assert!(w.propose(&w.karim.clone(), "111111", -5).is_err());
    assert!(w.propose("yo'q", "111111", 5).is_err());
    let env = env!(w);
    assert!(havas::propose(
        &mut w.db,
        &env,
        &w.ctx,
        &w.karim,
        "111111",
        Money::new(5, Currency::Usd)
    )
    .is_err());
}

// ----------------------------------------------------------- sadaqa, sovg'a, belgilar

/// Qabul mezoni (D6): sadaqa havasga kirmaydi.
#[test]
fn charity_never_counts_as_havas_even_if_marked_havas() {
    let mut w = World::new();
    w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    w.spend("Sadaqa", 300_000, |_| {});
    w.spend("Sadaqa", 100_000, |e| e.necessity = Some(Necessity::Havas)); // baribir havas emas
    w.spend("Sadaqa", 50_000, |e| e.is_ostentation = true);
    let r = w.report();
    assert_eq!(r.spent.minor(), 0);
    assert_eq!(r.charity.minor(), 450_000);
    assert_eq!(r.ostentation.minor(), 0, "sadaqa isrof emas");
    assert_eq!(r.status.unwrap().state, domain::HavasState::Ok);
}

#[test]
fn gifts_are_excluded_and_reported_separately() {
    let mut w = World::new();
    w.spend("Gazak va ichimlik", 100_000, |_| {});
    w.spend("Gazak va ichimlik", 40_000, |e| e.is_gift = true);
    let r = w.report();
    assert_eq!(
        (r.spent.minor(), r.gifts_excluded.minor()),
        (100_000, 40_000)
    );
}

#[test]
fn expense_level_necessity_overrides_category_and_category_change_reclassifies() {
    let mut w = World::new();
    w.spend("Oziq-ovqat", 10_000, |_| {}); // ZARUR — havas emas
    w.spend("Oziq-ovqat", 20_000, |e| {
        e.necessity = Some(Necessity::Havas)
    }); // qimmat restoran
    assert_eq!(w.report().spent.minor(), 20_000);
    w.set_nec("Oziq-ovqat", Necessity::Havas, w.karim.clone());
    assert_eq!(
        w.report().spent.minor(),
        30_000,
        "kategoriya toifasi o'zgarsa, belgilanmagan xarajatlar ham qayta tasniflanadi"
    );
}

#[test]
fn debt_funded_havas_is_flagged_and_ostentation_tracked() {
    let mut w = World::new();
    w.spend("Gazak va ichimlik", 200_000, |e| e.funded_by_debt = true);
    w.spend("Gazak va ichimlik", 100_000, |e| e.is_ostentation = true);
    w.spend("Oziq-ovqat", 50_000, |e| e.funded_by_debt = true); // zarur: qizil bayroq emas
    let r = w.report();
    assert_eq!(r.spent.minor(), 300_000);
    assert_eq!(r.debt_funded.minor(), 200_000);
    assert_eq!(r.ostentation.minor(), 100_000);
}

#[test]
fn other_months_do_not_leak_into_the_report() {
    let mut w = World::new();
    w.spend("Gazak va ichimlik", 100, |e| {
        e.date = date_from_str("2026-09-30").unwrap()
    });
    w.spend("Gazak va ichimlik", 7, |_| {});
    assert_eq!(w.report().spent.minor(), 7);
}

// ----------------------------------------------------------- xarajatlar, hafta varag'i

#[test]
fn batch_is_atomic_and_validated() {
    let mut w = World::new();
    let env = env!(w);
    let good = |w: &World| NewExpense {
        date: date_from_str("2026-10-05").unwrap(),
        category_id: w.cat("Oziq-ovqat"),
        amount: uzs(1_000),
        channel: PaymentChannel::Card,
        note: Some("  non  ".into()),
        necessity: None,
        is_gift: false,
        is_ostentation: false,
        funded_by_debt: false,
        member_id: None,
    };
    let mut bad_amount = good(&w);
    bad_amount.amount = uzs(0);
    let mut future = good(&w);
    future.date = date_from_str("2026-10-08").unwrap();
    let mut ghost_cat = good(&w);
    ghost_cat.category_id = "yo'q".into();
    let mut ghost_member = good(&w);
    ghost_member.member_id = Some("yo'q".into());
    let mut usd = good(&w);
    usd.amount = Money::new(5, Currency::Usd);
    let mut long_note = good(&w);
    long_note.note = Some("x".repeat(121));

    for bad in [bad_amount, future, ghost_cat, ghost_member, usd, long_note] {
        let first = good(&w);
        assert!(expenses::add_many(&mut w.db, &env, &w.ctx, vec![first, bad]).is_err());
    }
    assert!(expenses::add_many(&mut w.db, &env, &w.ctx, vec![]).is_err());
    let all = expenses::list_range(
        w.db.conn(),
        &w.ctx,
        date_from_str("2026-10-01").unwrap(),
        date_from_str("2026-10-31").unwrap(),
    )
    .unwrap();
    assert!(all.is_empty(), "xato bo'lganda hech biri yozilmaydi");

    assert_eq!(
        {
            let batch = vec![good(&w), good(&w)];
            expenses::add_many(&mut w.db, &env, &w.ctx, batch).unwrap()
        },
        2
    );
    let all = expenses::list_range(
        w.db.conn(),
        &w.ctx,
        date_from_str("2026-10-01").unwrap(),
        date_from_str("2026-10-31").unwrap(),
    )
    .unwrap();
    assert_eq!(all.len(), 2);
    assert_eq!(all[0].note.as_deref(), Some("non"));
    expenses::remove(&mut w.db, &env, &w.ctx, &all[0].meta.id).unwrap();
    assert!(expenses::remove(&mut w.db, &env, &w.ctx, &all[0].meta.id).is_err());
}

#[test]
fn category_is_suggested_from_the_last_expense_with_same_note() {
    let mut w = World::new();
    assert_eq!(
        expenses::suggest_category(w.db.conn(), &w.ctx, "somsa").unwrap(),
        None
    );
    w.spend("Oziq-ovqat", 1, |e| e.note = Some("Somsa".into()));
    w.spend("Gazak va ichimlik", 1, |e| {
        e.note = Some("somsa".into());
        e.date = date_from_str("2026-10-06").unwrap();
    });
    let got = expenses::suggest_category(w.db.conn(), &w.ctx, "  SOMSA ").unwrap();
    assert_eq!(
        got,
        Some(w.cat("Gazak va ichimlik")),
        "eng so'nggisi yutadi, harf katta-kichikligi farqsiz"
    );
    assert_eq!(
        expenses::suggest_category(w.db.conn(), &w.ctx, "").unwrap(),
        None
    );
}

// ----------------------------------------------------------- juma shirinligi

#[test]
fn friday_treat_is_due_only_on_its_day_logged_once_and_counts_as_havas() {
    let mut w = World::new();
    let env = env!(w);
    assert!(treats::add(&mut w.db, &env, &w.ctx, " ", uzs(1), 5).is_err());
    assert!(treats::add(&mut w.db, &env, &w.ctx, "Shokolad", uzs(0), 5).is_err());
    assert!(treats::add(&mut w.db, &env, &w.ctx, "Shokolad", uzs(1), 8).is_err());
    let t = treats::add(&mut w.db, &env, &w.ctx, "Shokolad", uzs(30_000), 5).unwrap(); // juma

    // 2026-10-07 chorshanba: juma emas.
    let wed = date_from_str("2026-10-07").unwrap();
    assert!(treats::due_today(w.db.conn(), &w.ctx, wed)
        .unwrap()
        .is_empty());

    w.clock.0.set(w.clock.0.get() + Duration::days(2)); // juma 10-09
    let fri = date_from_str("2026-10-09").unwrap();
    let due = treats::due_today(w.db.conn(), &w.ctx, fri).unwrap();
    assert_eq!(due.len(), 1);
    assert!(!due[0].logged_today);

    let env = env!(w);
    treats::log(&mut w.db, &env, &w.ctx, &t.meta.id).unwrap();
    assert!(treats::due_today(w.db.conn(), &w.ctx, fri).unwrap()[0].logged_today);
    assert!(matches!(
        treats::log(&mut w.db, &env, &w.ctx, &t.meta.id),
        Err(ServiceError::Invalid(_))
    ));

    let r = havas::report(w.db.conn(), &w.ctx, YearMonth::parse("2026-10").unwrap()).unwrap();
    assert_eq!(r.spent.minor(), 30_000, "shirinlik havas hisobiga kiradi");

    treats::set_active(&mut w.db, &env, &w.ctx, &t.meta.id, false).unwrap();
    assert!(treats::due_today(w.db.conn(), &w.ctx, fri)
        .unwrap()
        .is_empty());
    treats::remove(&mut w.db, &env, &w.ctx, &t.meta.id).unwrap();
    assert!(treats::list(w.db.conn(), &w.ctx).unwrap().is_empty());
}

// ----------------------------------------------------------- odatlar

#[test]
fn habit_stats_project_week_month_year_without_judgement() {
    let mut w = World::new();
    let env = env!(w);
    let habit = categories::add(
        &mut w.db,
        &env,
        &w.ctx,
        NewCategory {
            name: "Chekish".into(),
            necessity: Some(Necessity::Havas),
            owner: None,
            is_charity: false,
            is_habit: true,
        },
    )
    .unwrap();
    let today = date_from_str("2026-10-07").unwrap();
    assert_eq!(habits::stats(w.db.conn(), &w.ctx, today).unwrap().len(), 1);
    assert_eq!(
        habits::stats(w.db.conn(), &w.ctx, today).unwrap()[0]
            .window_total
            .minor(),
        0
    );

    // 28 kunlik oynada: 2026-09-10 .. 2026-10-07
    w.spend("Chekish", 28_000_000, |e| {
        e.date = date_from_str("2026-09-10").unwrap()
    });
    w.spend("Chekish", 5_000, |e| {
        e.date = date_from_str("2026-09-09").unwrap()
    }); // oynadan tashqari
    let s = &habits::stats(w.db.conn(), &w.ctx, today).unwrap()[0];
    assert_eq!(s.name, "Chekish");
    assert_eq!(s.window_total.minor(), 28_000_000);
    assert_eq!(
        (
            s.projection.week.minor(),
            s.projection.month.minor(),
            s.projection.year.minor()
        ),
        (7_000_000, 30_000_000, 365_000_000)
    );

    {
        let env = env!(w);
        categories::set_habit(&mut w.db, &env, &w.ctx, &habit.meta.id, false).unwrap();
    }
    assert!(habits::stats(w.db.conn(), &w.ctx, today)
        .unwrap()
        .is_empty());
}

// ----------------------------------------------------------- oila kengashi

#[test]
fn council_minutes_describe_the_agreement_and_render_a_pdf() {
    let mut w = World::new();
    let dilnoza = w.add_adult("Dilnoza", "222222");
    w.set_nec("Telefon", Necessity::Havas, dilnoza.clone());
    w.spend("Gazak va ichimlik", 900_000, |_| {});
    w.spend("Sadaqa", 100_000, |_| {});
    let limit = w.propose(&w.karim.clone(), "111111", 1_000_000).unwrap();
    let ym = YearMonth::parse("2026-10").unwrap();

    // Kelishilmagan: Dilnoza roziligi yo'q.
    let m = council::minutes_data(w.db.conn(), &env!(w), &w.ctx, ym).unwrap();
    assert!(
        m.limit_status.starts_with("Kuchga kirmagan"),
        "{}",
        m.limit_status
    );
    assert!(m.limit_status.contains("Dilnoza"));
    assert_eq!(m.limit_amount.as_deref(), Some("10 000 so'm"));
    let by = |n: &str| m.consents.iter().find(|c| c.name == n).unwrap();
    assert!(by("Men").at.is_some() && by("Dilnoza").at.is_none());
    assert_eq!(m.signers, ["Men", "Dilnoza"]);
    let tel = m.categories.iter().find(|c| c.name == "Telefon").unwrap();
    assert_eq!(tel.necessity, "Havas");
    assert!(tel
        .last_change
        .as_deref()
        .unwrap()
        .starts_with("Dilnoza, 2026-10-07"));
    assert!(m
        .review
        .iter()
        .any(|(k, v)| k == "Havas sarfi" && v == "9 000 so'm"));
    assert!(m.review.iter().any(|(k, _)| k.starts_with("Sadaqa")));

    w.consent(&limit.meta.id, &dilnoza, "222222").unwrap();
    let m = council::minutes_data(w.db.conn(), &env!(w), &w.ctx, ym).unwrap();
    assert_eq!(m.limit_status, "Faol: barcha kattalar rozi");
    assert!(m.consents.iter().all(|c| c.at.is_some()));

    let pdf = council::minutes_pdf(w.db.conn(), &env!(w), &w.ctx, ym).unwrap();
    assert!(pdf.starts_with(b"%PDF-") && pdf.len() > 5_000);
}

#[test]
fn council_minutes_without_any_limit() {
    let w = World::new();
    let m = council::minutes_data(
        w.db.conn(),
        &env!(w),
        &w.ctx,
        YearMonth::parse("2026-10").unwrap(),
    )
    .unwrap();
    assert_eq!(
        (m.limit_amount, m.limit_status.as_str()),
        (None, "Belgilanmagan")
    );
    assert!(m.consents.is_empty());
}

#[test]
fn changing_a_pin_requires_the_old_one() {
    let mut w = World::new();
    let env = env!(w);
    assert!(matches!(
        members::change_pin(
            &mut w.db,
            &env,
            &w.ctx,
            &w.karim,
            Some("000000"),
            "555555",
            FAST
        ),
        Err(ServiceError::WrongPin)
    ));
    assert!(matches!(
        members::change_pin(&mut w.db, &env, &w.ctx, &w.karim, None, "555555", FAST),
        Err(ServiceError::WrongPin)
    ));
    members::change_pin(
        &mut w.db,
        &env,
        &w.ctx,
        &w.karim,
        Some("111111"),
        "555555",
        FAST,
    )
    .unwrap();
    members::verify(&mut w.db, &env, &w.ctx, &w.karim, "555555").unwrap();
    assert!(members::verify(&mut w.db, &env, &w.ctx, &w.karim, "111111").is_err());
    // PIN'i yo'q a'zo eski PIN'siz o'rnata oladi.
    let m = members::add(&mut w.db, &env, &w.ctx, "Sanjar", MemberRole::Adult).unwrap();
    members::change_pin(&mut w.db, &env, &w.ctx, &m.meta.id, None, "666666", FAST).unwrap();
    assert!(members::has_pin(w.db.conn(), &w.ctx, &m.meta.id).unwrap());
}
