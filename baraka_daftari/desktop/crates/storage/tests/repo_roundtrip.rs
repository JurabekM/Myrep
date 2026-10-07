#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::*;
use money::{Currency, Money};
use storage::{repo, Database, StorageError};

const KEY: [u8; 32] = [3; 32];

struct Tick(Cell<i64>);
impl Clock for Tick {
    fn now(&self) -> OffsetDateTime {
        let n = self.0.get();
        self.0.set(n + 1);
        OffsetDateTime::from_unix_timestamp(1_800_000_000 + n).unwrap()
    }
}

struct Seq(Cell<u32>);
impl IdGen for Seq {
    fn new_id(&self) -> String {
        let n = self.0.get();
        self.0.set(n + 1);
        format!("00000000-0000-7000-8000-{n:012}")
    }
}

struct Fx {
    clock: Tick,
    ids: Seq,
}

impl Fx {
    fn new() -> Self {
        Self {
            clock: Tick(Cell::new(0)),
            ids: Seq(Cell::new(1)),
        }
    }
    fn meta(&self, household: &str) -> Meta {
        Meta::new(&self.ids, &self.clock, household, "dev-1")
    }
}

fn day() -> Date {
    date_from_str("2026-10-07").unwrap()
}

struct World {
    db: Database,
    fx: Fx,
    household: Household,
    member: Member,
    category: Category,
}

fn world() -> World {
    let db = Database::open_in_memory(&KEY).unwrap();
    let fx = Fx::new();
    let mut hm = fx.meta("");
    hm.household_id = hm.id.clone();
    let household = Household {
        meta: hm,
        name: "Karimovlar".into(),
        base_currency: Currency::Uzs,
    };
    repo::insert(db.conn(), &household).unwrap();
    let hid = household.meta.id.clone();
    let member = Member {
        meta: fx.meta(&hid),
        display_name: "Anvar".into(),
        role: MemberRole::Adult,
    };
    repo::insert(db.conn(), &member).unwrap();
    let category = Category {
        meta: fx.meta(&hid),
        name: "Somsa".into(),
        necessity: Some(Necessity::Havas),
        owner: None,
    };
    repo::insert(db.conn(), &category).unwrap();
    World {
        db,
        fx,
        household,
        member,
        category,
    }
}

#[test]
fn household_member_category_roundtrip() {
    let w = world();
    let c = w.db.conn();
    assert_eq!(
        repo::get::<Household>(c, &w.household.meta.id)
            .unwrap()
            .unwrap(),
        w.household
    );
    assert_eq!(
        repo::list::<Member>(c, &w.household.meta.id).unwrap(),
        vec![w.member.clone()]
    );
    assert_eq!(
        repo::list::<Category>(c, &w.household.meta.id).unwrap(),
        vec![w.category.clone()]
    );
}

#[test]
fn income_and_expense_roundtrip_with_nullable_future_fields() {
    let w = world();
    let hid = &w.household.meta.id;
    let income = Income {
        meta: w.fx.meta(hid),
        member_id: w.member.meta.id.clone(),
        source: "kunlik ish".into(),
        channel: PaymentChannel::Cash,
        amount: Money::new(800_000_000, Currency::Uzs),
        received_on: day(),
    };
    repo::insert(w.db.conn(), &income).unwrap();
    assert_eq!(
        repo::list::<Income>(w.db.conn(), hid).unwrap(),
        vec![income]
    );

    let plain = Expense {
        meta: w.fx.meta(hid),
        member_id: w.member.meta.id.clone(),
        category_id: w.category.meta.id.clone(),
        amount: Money::new(1_500_000, Currency::Uzs),
        spent_on: day(),
        payment_channel: PaymentChannel::Card,
        necessity: None,
        envelope_id: None,
        is_gift: None,
        is_ostentation: None,
        funded_by_debt: None,
        audit_month: None,
    };
    let full = Expense {
        meta: w.fx.meta(hid),
        necessity: Some(Necessity::Zarur),
        envelope_id: Some("env-1".into()),
        is_gift: Some(true),
        is_ostentation: Some(false),
        funded_by_debt: Some(false),
        ..plain.clone()
    };
    repo::insert(w.db.conn(), &plain).unwrap();
    repo::insert(w.db.conn(), &full).unwrap();
    assert_eq!(
        repo::list::<Expense>(w.db.conn(), hid).unwrap(),
        vec![plain, full]
    );
}

#[test]
fn assets_snapshots_vault_and_remaining_tables_roundtrip() {
    let w = world();
    let hid = &w.household.meta.id;
    let c = w.db.conn();
    let asset = Asset {
        meta: w.fx.meta(hid),
        asset_type: AssetType::Vault,
        name: "Kelajagim".into(),
        quantity: 5_000_000,
        unit: "tiyin".into(),
        currency: Some(Currency::Uzs),
        acquired_at: w.fx.clock.now(),
    };
    repo::insert(c, &asset).unwrap();
    let snap = AssetSnapshot {
        meta: w.fx.meta(hid),
        asset_id: asset.meta.id.clone(),
        quantity: 5_000_000,
        taken_at: w.fx.clock.now(),
    };
    repo::insert(c, &snap).unwrap();
    let tx = VaultTransaction {
        meta: w.fx.meta(hid),
        asset_id: asset.meta.id.clone(),
        kind: VaultTxKind::Deposit,
        amount: Money::new(80_000_000, Currency::Uzs),
        occurred_at: w.fx.clock.now(),
        note: Some("ro'molcha".into()),
        source: Some(VaultSource::Opening),
        income_id: None,
    };
    repo::insert(c, &tx).unwrap();
    let rule = AllocationRule {
        meta: w.fx.meta(hid),
        kind: AllocationKind::Percent,
        value: 1000,
        currency: None,
    };
    repo::insert(c, &rule).unwrap();
    let ob = Obligation {
        meta: w.fx.meta(hid),
        name: "Ijara".into(),
        amount: Money::new(300_000_000, Currency::Uzs),
        due_day: 5,
        kind: ObligationKind::Recurring,
        owner: MoneyOwner::Landlord,
        creditor: None,
        remaining: None,
    };
    repo::insert(c, &ob).unwrap();
    let rate = FxRateRecord {
        meta: w.fx.meta(hid),
        from: Currency::Usd,
        to: Currency::Uzs,
        rate_num: 1_265_050,
        rate_den: 100,
        date: day(),
        source: "qo'lda".into(),
    };
    repo::insert(c, &rate).unwrap();

    assert_eq!(repo::list::<Asset>(c, hid).unwrap(), vec![asset]);
    assert_eq!(repo::list::<AssetSnapshot>(c, hid).unwrap(), vec![snap]);
    assert_eq!(repo::list::<VaultTransaction>(c, hid).unwrap(), vec![tx]);
    assert_eq!(repo::list::<AllocationRule>(c, hid).unwrap(), vec![rule]);
    assert_eq!(repo::list::<Obligation>(c, hid).unwrap(), vec![ob]);
    assert_eq!(repo::list::<FxRateRecord>(c, hid).unwrap(), vec![rate]);
}

#[test]
fn update_bumps_version_and_detects_stale_writes() {
    let w = world();
    let c = w.db.conn();
    let mut cat = w.category.clone();
    cat.name = "Choyxona".into();
    repo::update(c, &cat, w.fx.clock.now()).unwrap();

    let stored = repo::get::<Category>(c, &cat.meta.id).unwrap().unwrap();
    assert_eq!((stored.name.as_str(), stored.meta.version), ("Choyxona", 2));
    assert!(stored.meta.updated_at > stored.meta.created_at);

    // Eski versiya (1) bilan qayta yozish rad etiladi.
    assert!(matches!(
        repo::update(c, &cat, w.fx.clock.now()),
        Err(StorageError::NotFound)
    ));
}

#[test]
fn soft_delete_hides_row_keeps_tombstone_and_bumps_version() {
    let w = world();
    let c = w.db.conn();
    repo::soft_delete::<Category>(c, &w.category.meta.id, w.fx.clock.now()).unwrap();
    assert!(repo::get::<Category>(c, &w.category.meta.id)
        .unwrap()
        .is_none());
    assert!(repo::list::<Category>(c, &w.household.meta.id)
        .unwrap()
        .is_empty());

    let (deleted, version): (Option<String>, i64) = c
        .query_row(
            "SELECT deleted_at, version FROM categories WHERE id = ?1",
            [&w.category.meta.id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert!(deleted.is_some());
    assert_eq!(version, 2);
    assert!(matches!(
        repo::soft_delete::<Category>(c, &w.category.meta.id, w.fx.clock.now()),
        Err(StorageError::NotFound)
    ));
}

#[test]
fn data_survives_reopen_on_disk() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("baraka.db");
    let fx = Fx::new();
    let mut hm = fx.meta("");
    hm.household_id = hm.id.clone();
    let h = Household {
        meta: hm,
        name: "Oila".into(),
        base_currency: Currency::Uzs,
    };
    {
        let db = Database::open(&path, &KEY).unwrap();
        repo::insert(db.conn(), &h).unwrap();
    }
    let db = Database::open(&path, &KEY).unwrap();
    assert_eq!(
        repo::get::<Household>(db.conn(), &h.meta.id)
            .unwrap()
            .unwrap(),
        h
    );
}

#[test]
fn transaction_rolls_back_on_error() {
    let mut w = world();
    let hid = w.household.meta.id.clone();
    let before = repo::list::<Category>(w.db.conn(), &hid).unwrap().len();
    let extra = Category {
        meta: w.fx.meta(&hid),
        name: "Yangi".into(),
        necessity: None,
        owner: None,
    };
    let dup = extra.clone(); // bir xil id => ikkinchi insert xato beradi
    let res: Result<(), StorageError> = w.db.transaction(|tx| {
        repo::insert(tx, &extra)?;
        repo::insert(tx, &dup)
    });
    assert!(res.is_err());
    assert_eq!(
        repo::list::<Category>(w.db.conn(), &hid).unwrap().len(),
        before
    );
}

#[test]
fn v2_fields_roundtrip_nasiya_owner_audit_and_withdrawal() {
    let w = world();
    let hid = &w.household.meta.id;
    let c = w.db.conn();

    let fuel = Category {
        meta: w.fx.meta(hid),
        name: "Benzin".into(),
        necessity: None,
        owner: Some(MoneyOwner::Fuel),
    };
    repo::insert(c, &fuel).unwrap();
    assert_eq!(
        repo::get::<Category>(c, &fuel.meta.id).unwrap().unwrap(),
        fuel
    );

    let nasiya = Obligation {
        meta: w.fx.meta(hid),
        name: "Do'kon nasiyasi".into(),
        amount: Money::new(50_000_000, Currency::Uzs),
        due_day: 1,
        kind: ObligationKind::Nasiya,
        owner: MoneyOwner::Shop,
        creditor: Some("Salim aka do'koni".into()),
        remaining: Some(Money::new(30_000_000, Currency::Uzs)),
    };
    repo::insert(c, &nasiya).unwrap();
    assert_eq!(
        repo::get::<Obligation>(c, &nasiya.meta.id)
            .unwrap()
            .unwrap(),
        nasiya
    );

    let audit = Expense {
        meta: w.fx.meta(hid),
        member_id: w.member.meta.id.clone(),
        category_id: fuel.meta.id.clone(),
        amount: Money::new(70_000_000, Currency::Uzs),
        spent_on: day(),
        payment_channel: PaymentChannel::Cash,
        necessity: None,
        envelope_id: None,
        is_gift: None,
        is_ostentation: None,
        funded_by_debt: None,
        audit_month: Some("2026-09".into()),
    };
    repo::insert(c, &audit).unwrap();
    assert_eq!(
        repo::get::<Expense>(c, &audit.meta.id).unwrap().unwrap(),
        audit
    );

    let asset = Asset {
        meta: w.fx.meta(hid),
        asset_type: AssetType::Vault,
        name: "Kelajagim".into(),
        quantity: 0,
        unit: "tiyin".into(),
        currency: Some(Currency::Uzs),
        acquired_at: w.fx.clock.now(),
    };
    repo::insert(c, &asset).unwrap();
    let req = WithdrawalRequest {
        meta: w.fx.meta(hid),
        asset_id: asset.meta.id.clone(),
        amount: Money::new(1_000_000, Currency::Uzs),
        reason: "Dori".into(),
        available_at: w.fx.clock.now(),
        status: WithdrawalStatus::Pending,
    };
    repo::insert(c, &req).unwrap();
    assert_eq!(
        repo::get::<WithdrawalRequest>(c, &req.meta.id)
            .unwrap()
            .unwrap(),
        req
    );
    // CHECK: summa musbat bo'lishi shart.
    let bad = WithdrawalRequest {
        meta: w.fx.meta(hid),
        amount: Money::new(0, Currency::Uzs),
        ..req
    };
    assert!(repo::insert(c, &bad).is_err());
}

#[test]
fn v3_content_tables_roundtrip_and_partial_unique_indexes() {
    let w = world();
    let hid = &w.household.meta.id;
    let c = w.db.conn();

    let done = TaskCompletion {
        meta: w.fx.meta(hid),
        chapter_id: "ch01".into(),
        task_id: "ch01-t1".into(),
        week_start: day(),
        completed_at: w.fx.clock.now(),
    };
    repo::insert(c, &done).unwrap();
    assert_eq!(
        repo::get::<TaskCompletion>(c, &done.meta.id)
            .unwrap()
            .unwrap(),
        done
    );
    // Bir hafta + bir vazifa uchun ikkinchi faol yozuv mumkin emas...
    let dup = TaskCompletion {
        meta: w.fx.meta(hid),
        ..done.clone()
    };
    assert!(repo::insert(c, &dup).is_err());
    // ...lekin o'chirilgandan keyin (tombstone) qayta belgilash mumkin.
    repo::soft_delete::<TaskCompletion>(c, &done.meta.id, w.fx.clock.now()).unwrap();
    repo::insert(c, &dup).unwrap();

    let progress = ChapterProgress {
        meta: w.fx.meta(hid),
        chapter_id: "ch01".into(),
        opened_on: day(),
    };
    repo::insert(c, &progress).unwrap();
    assert_eq!(
        repo::list::<ChapterProgress>(c, hid).unwrap(),
        vec![progress.clone()]
    );
    let dup = ChapterProgress {
        meta: w.fx.meta(hid),
        ..progress
    };
    assert!(repo::insert(c, &dup).is_err());

    let page = DaftarPage {
        meta: w.fx.meta(hid),
        chapter_id: "ch01".into(),
        body: "O'z so'zim bilan".into(),
    };
    repo::insert(c, &page).unwrap();
    assert_eq!(
        repo::get::<DaftarPage>(c, &page.meta.id).unwrap().unwrap(),
        page
    );
    assert!(repo::insert(
        c,
        &DaftarPage {
            meta: w.fx.meta(hid),
            ..page
        }
    )
    .is_err());

    let s = Setting {
        meta: w.fx.meta(hid),
        key: "unlock.window_weeks".into(),
        value: "3".into(),
    };
    repo::insert(c, &s).unwrap();
    assert_eq!(repo::get::<Setting>(c, &s.meta.id).unwrap().unwrap(), s);
    assert!(repo::insert(
        c,
        &Setting {
            meta: w.fx.meta(hid),
            ..s
        }
    )
    .is_err());
}
