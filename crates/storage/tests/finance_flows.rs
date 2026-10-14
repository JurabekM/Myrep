//! D4 saqlash oqimlari: v1 → v2 migratsiya, daromad → «Kelajagim» bog'lanishi, cheklovlar va hisobot.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use domain::calendar::{DateRange, month_of};
use domain::{
    Category, CategoryKey, Channel, DebtPayment, Expense, ExpenseDraft, Household, Income,
    IncomeDraft, LedgerInput, Meta, MonthlyReport, Obligation, ObligationDraft, ObligationKind,
    ShareRule, ShareTarget, ShopDebt, VaultEntry, VaultMovement, build_month_ledger,
};
use money::{Currency, Money};
use rusqlite::Connection;
use rusqlite_migration::{M, Migrations};
use security::SecretKey;
use storage::schema::{self, SCHEMA_V1};
use storage::{
    CategoryRepo, Database, DebtRepo, ExpenseRepo, HouseholdRepo, IncomeRepo, ObligationRepo,
    ReportRepo, RuleRepo, VaultRepo,
};
use time::macros::{date, datetime};
use time::{Date, OffsetDateTime};

const HOUSEHOLD: &str = "0192a000-0000-7000-8000-0000000000a1";
const MEMBER: &str = "0192a000-0000-7000-8000-0000000000b1";
const INCOME: &str = "0192a000-0000-7000-8000-0000000000d1";
const INCOME_2: &str = "0192a000-0000-7000-8000-0000000000d2";
const ASSET: &str = "0192a000-0000-7000-8000-0000000000c1";
const DEVICE: &str = "device-1";
const NOW: OffsetDateTime = datetime!(2026-10-14 06:00 UTC);

fn key() -> SecretKey {
    SecretKey::from_array([9; 32])
}

fn uzs(major: i64) -> Money {
    Money::new(major * 100, Currency::Uzs)
}

fn meta() -> Meta {
    Meta::created(NOW, DEVICE)
}

fn database_with_household() -> Database {
    let db = Database::open_in_memory(&key()).expect("ochilsin");
    let household = Household::create(HOUSEHOLD, "Oila", NOW, DEVICE).expect("xonadon");
    HouseholdRepo::new(db.connection())
        .insert(&household)
        .expect("qo'shilsin");
    let member = domain::Member::create(
        MEMBER,
        HOUSEHOLD,
        "Dilshod",
        domain::MemberRole::Adult,
        NOW,
        DEVICE,
    )
    .expect("a'zo");
    storage::MemberRepo::new(db.connection())
        .insert(&member)
        .expect("a'zo qo'shilsin");
    db
}

fn income(id: &str, major: i64, day: Date) -> Income {
    Income::create(
        id,
        HOUSEHOLD,
        IncomeDraft {
            member_id: MEMBER.to_owned(),
            source: "Kunlik ish".to_owned(),
            channel: Channel::Cash,
            amount: uzs(major),
            occurred_on: day,
            note: None,
        },
        NOW,
        DEVICE,
    )
    .expect("daromad")
}

#[test]
fn v1_dan_v2_ga_otganda_malumot_saqlanadi() {
    let mut conn = Connection::open_in_memory().expect("xotira");
    Migrations::new(vec![M::up(SCHEMA_V1)])
        .to_latest(&mut conn)
        .expect("v1");
    conn.execute(
        "INSERT INTO households (id, name, created_at, updated_at, version, origin_device_id) \
         VALUES (?1, 'Eski oila', '2026-10-01T00:00:00Z', '2026-10-01T00:00:00Z', 1, 'd')",
        [HOUSEHOLD],
    )
    .expect("v1 qator");

    schema::migrations().to_latest(&mut conn).expect("v2");

    let (name, day): (String, i64) = conn
        .query_row(
            "SELECT name, month_start_day FROM households WHERE id = ?1",
            [HOUSEHOLD],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .expect("qator");
    assert_eq!(name, "Eski oila");
    assert_eq!(day, 1);
}

#[test]
fn daromad_ulushi_kelajagimga_boglanadi() {
    let db = database_with_household();
    let conn = db.connection();
    let inc = income(INCOME, 150_000, date!(2026 - 10 - 14));
    IncomeRepo::new(conn).insert(&inc).expect("daromad");

    let vault = VaultRepo::new(conn);
    let asset = vault
        .ensure_asset(ASSET, HOUSEHOLD, Currency::Uzs, NOW, DEVICE)
        .expect("aktiv");
    let again = vault
        .ensure_asset(
            "0192a000-0000-7000-8000-0000000000c2",
            HOUSEHOLD,
            Currency::Uzs,
            NOW,
            DEVICE,
        )
        .expect("aktiv qayta");
    assert_eq!(asset, again, "ikkinchi chaqiruv yangi aktiv yaratmasin");

    vault
        .insert_entry(
            &asset,
            HOUSEHOLD,
            &VaultEntry {
                id: "0192a000-0000-7000-8000-0000000000e1".to_owned(),
                amount: uzs(1_000),
                occurred_on: date!(2026 - 10 - 01),
                movement: VaultMovement::Initial,
                meta: meta(),
            },
        )
        .expect("ro'molcha");
    vault
        .insert_entry(
            &asset,
            HOUSEHOLD,
            &VaultEntry {
                id: "0192a000-0000-7000-8000-0000000000e2".to_owned(),
                amount: uzs(8_000),
                occurred_on: inc.occurred_on,
                movement: VaultMovement::IncomeShare {
                    income_id: INCOME.to_owned(),
                },
                meta: meta(),
            },
        )
        .expect("ulush");

    let entries = vault.list_entries(&asset).expect("yozuvlar");
    assert_eq!(entries.len(), 2);
    let balance = domain::vault::balance(&entries, Currency::Uzs).expect("balans");
    assert_eq!(balance, uzs(9_000));
    assert!(entries.iter().any(|e| matches!(
        &e.movement,
        VaultMovement::IncomeShare { income_id } if income_id == INCOME
    )));
}

#[test]
fn bazada_sababsiz_pul_olish_rad_etiladi() {
    let db = database_with_household();
    let conn = db.connection();
    let vault = VaultRepo::new(conn);
    let asset = vault
        .ensure_asset(ASSET, HOUSEHOLD, Currency::Uzs, NOW, DEVICE)
        .expect("aktiv");
    let result = vault.insert_entry(
        &asset,
        HOUSEHOLD,
        &VaultEntry {
            id: "0192a000-0000-7000-8000-0000000000e3".to_owned(),
            amount: uzs(100),
            occurred_on: date!(2026 - 10 - 14),
            movement: VaultMovement::Withdrawal {
                reason: "   ".to_owned(),
            },
            meta: meta(),
        },
    );
    assert!(result.is_err(), "bo'sh sabab bazada ham rad etilsin");
}

#[test]
fn kategoriya_tizim_kaliti_xonadonda_bir_marta() {
    let db = database_with_household();
    let conn = db.connection();
    let repo = CategoryRepo::new(conn);
    let first = Category::system(
        "0192a000-0000-7000-8000-0000000000f1",
        HOUSEHOLD,
        CategoryKey::Rent,
        NOW,
        DEVICE,
    )
    .expect("kategoriya");
    repo.insert(&first).expect("birinchi");
    let duplicate = Category::system(
        "0192a000-0000-7000-8000-0000000000f2",
        HOUSEHOLD,
        CategoryKey::Rent,
        NOW,
        DEVICE,
    )
    .expect("kategoriya");
    assert!(repo.insert(&duplicate).is_err());

    let listed = repo.list(HOUSEHOLD).expect("ro'yxat");
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0].system_key, Some(CategoryKey::Rent));
    assert_eq!(
        repo.find_system(HOUSEHOLD, CategoryKey::Rent)
            .expect("qidiruv"),
        Some(first.id)
    );
}

#[test]
fn majburiyat_xarajat_va_qoida_saqlanadi() {
    let db = database_with_household();
    let conn = db.connection();
    let category = Category::system(
        "0192a000-0000-7000-8000-0000000000f3",
        HOUSEHOLD,
        CategoryKey::Rent,
        NOW,
        DEVICE,
    )
    .expect("kategoriya");
    CategoryRepo::new(conn)
        .insert(&category)
        .expect("kategoriya");

    let obligation = Obligation::create(
        "0192a000-0000-7000-8000-0000000000f4",
        HOUSEHOLD,
        ObligationDraft {
            title: "Ijara".to_owned(),
            kind: ObligationKind::Rent,
            amount: uzs(1_500_000),
            due_day: Some(5),
            category_id: Some(category.id.clone()),
        },
        NOW,
        DEVICE,
    )
    .expect("majburiyat");
    ObligationRepo::new(conn)
        .insert(&obligation)
        .expect("saqlansin");
    let active = ObligationRepo::new(conn)
        .list_active(HOUSEHOLD)
        .expect("faol");
    assert_eq!(active.len(), 1);
    assert_eq!(active[0].kind, ObligationKind::Rent);
    ObligationRepo::new(conn)
        .set_active(&obligation.id, false, NOW)
        .expect("o'chirilsin");
    assert!(
        ObligationRepo::new(conn)
            .list_active(HOUSEHOLD)
            .expect("faol")
            .is_empty()
    );

    let expense = Expense::create(
        "0192a000-0000-7000-8000-0000000000f5",
        HOUSEHOLD,
        ExpenseDraft {
            member_id: MEMBER.to_owned(),
            category_id: Some(category.id.clone()),
            amount: uzs(1_500_000),
            occurred_on: date!(2026 - 10 - 05),
            note: None,
        },
        NOW,
        DEVICE,
    )
    .expect("xarajat");
    ExpenseRepo::new(conn)
        .insert(&expense)
        .expect("xarajat saqlansin");

    let rules = RuleRepo::new(conn);
    assert!(
        rules
            .find_active(HOUSEHOLD, Currency::Uzs)
            .expect("qoida")
            .is_none()
    );
    let rule = ShareRule {
        target: ShareTarget::Percent(500),
        progressive: true,
        progression_offered_on: Some(date!(2026 - 10 - 01)),
    };
    rules
        .insert(
            "0192a000-0000-7000-8000-0000000000f6",
            HOUSEHOLD,
            &rule,
            NOW,
            DEVICE,
        )
        .expect("qoida");
    let stored = rules
        .find_active(HOUSEHOLD, Currency::Uzs)
        .expect("qoida")
        .expect("bor");
    assert_eq!(stored.rule, rule);
}

#[test]
fn nasiya_va_tolovlar_qoldiqni_beradi() {
    let db = database_with_household();
    let conn = db.connection();
    let debt = ShopDebt::create(
        "0192a000-0000-7000-8000-000000000011",
        HOUSEHOLD,
        "Do'kon Anvar",
        uzs(500_000),
        date!(2026 - 10 - 10),
        NOW,
        DEVICE,
    )
    .expect("nasiya");
    let repo = DebtRepo::new(conn);
    repo.insert_debt(&debt).expect("saqlansin");
    repo.insert_payment(
        HOUSEHOLD,
        &DebtPayment {
            id: "0192a000-0000-7000-8000-000000000012".to_owned(),
            debt_id: debt.id.clone(),
            amount: uzs(200_000),
            paid_on: date!(2026 - 10 - 12),
            meta: meta(),
        },
    )
    .expect("to'lov");
    let payments = repo
        .payment_amounts(&debt.id, Currency::Uzs)
        .expect("to'lovlar");
    let left = domain::debt::outstanding(debt.principal, &payments).expect("qoldiq");
    assert_eq!(left, uzs(300_000));
}

#[test]
fn oylik_hisobot_bir_marta_yoziladi() {
    let db = database_with_household();
    let conn = db.connection();
    let period: DateRange = month_of(date!(2026 - 10 - 14), 1).expect("davr");
    let ledger = build_month_ledger(&LedgerInput {
        period,
        currency: Currency::Uzs,
        incomes: &[income(INCOME_2, 100, date!(2026 - 10 - 03))],
        expenses: &[],
        obligations: &[],
        vault: &[],
    })
    .expect("hisob");
    let report = MonthlyReport::from_ledger(
        "0192a000-0000-7000-8000-000000000021",
        HOUSEHOLD,
        &ledger,
        NOW,
        DEVICE,
    )
    .expect("hisobot");
    let repo = ReportRepo::new(conn);
    assert!(!repo.exists_for(HOUSEHOLD, period.start).expect("tekshiruv"));
    repo.insert(&report).expect("yozilsin");
    assert!(repo.exists_for(HOUSEHOLD, period.start).expect("tekshiruv"));

    let second = MonthlyReport::from_ledger(
        "0192a000-0000-7000-8000-000000000022",
        HOUSEHOLD,
        &ledger,
        NOW,
        DEVICE,
    )
    .expect("hisobot");
    assert!(
        repo.insert(&second).is_err(),
        "bir davrga ikkinchi hisobot yo'q"
    );
}
