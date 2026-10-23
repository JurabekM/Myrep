//! D6 saqlash oqimlari: toifa tarixi, a'zo PIN urinishlari, havas chegarasi va rozilik, Juma shirinligi,
//! sxema v3 → v4 (toifa standart qiymatlari tiklanadi).
#![allow(clippy::expect_used, clippy::unwrap_used)]

use domain::{
    Category, CategoryKey, HavasLimit, Household, LimitConsent, Member, MemberRole, Necessity,
    ScheduledTreat,
};
use money::{Currency, Money};
use rusqlite::{Connection, params};
use rusqlite_migration::{M, Migrations};
use security::SecretKey;
use storage::schema::{self, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3};
use storage::{CategoryRepo, Database, HouseholdRepo, LimitRepo, MemberRepo, PinRepo, TreatRepo};
use time::macros::datetime;
use time::{OffsetDateTime, Weekday};

const HOUSEHOLD: &str = "0192d000-0000-7000-8000-0000000000a1";
const ADULT: &str = "0192d000-0000-7000-8000-0000000000b1";
const CATEGORY: &str = "0192d000-0000-7000-8000-0000000000c1";
const CHANGE: &str = "0192d000-0000-7000-8000-0000000000c2";
const LIMIT: &str = "0192d000-0000-7000-8000-0000000000d1";
const CONSENT: &str = "0192d000-0000-7000-8000-0000000000d2";
const CONSENT_2: &str = "0192d000-0000-7000-8000-0000000000d3";
const TREAT: &str = "0192d000-0000-7000-8000-0000000000e1";
const DEVICE: &str = "device-1";
const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

fn database() -> Database {
    let db = Database::open_in_memory(&SecretKey::from_array([6; 32])).expect("ochilsin");
    let household = Household::create(HOUSEHOLD, "Oila", NOW, DEVICE).expect("xonadon");
    HouseholdRepo::new(db.connection())
        .insert(&household)
        .expect("qo'shilsin");
    let adult =
        Member::create(ADULT, HOUSEHOLD, "Jasur", MemberRole::Adult, NOW, DEVICE).expect("a'zo");
    MemberRepo::new(db.connection())
        .insert(&adult)
        .expect("a'zo qo'shilsin");
    db
}

fn uzs(major: i64) -> Money {
    Money::new(major * 100, Currency::Uzs)
}

#[test]
fn toifa_saqlanadi_va_ozgarish_tarixi_yoziladi() {
    let db = database();
    let conn = db.connection();
    let categories = CategoryRepo::new(conn);
    let category = Category::system(CATEGORY, HOUSEHOLD, CategoryKey::Snacks, NOW, DEVICE)
        .expect("kategoriya");
    categories.insert(&category).expect("qo'shilsin");

    let listed = categories.list(HOUSEHOLD).expect("o'qilsin");
    assert_eq!(listed[0].necessity, Necessity::Havas);

    let (changed, change) = listed[0]
        .clone()
        .change_necessity(Necessity::Kerak, ADULT, CHANGE, NOW, DEVICE)
        .expect("o'zgarsin");
    categories.update_necessity(&changed).expect("saqlansin");
    categories.insert_necessity_change(&change).expect("tarix");

    let reread = categories.list(HOUSEHOLD).expect("o'qilsin");
    assert_eq!(reread[0].necessity, Necessity::Kerak);
    let history = categories.list_necessity_changes(CATEGORY).expect("tarix");
    assert_eq!(
        history,
        vec![(Necessity::Havas, Necessity::Kerak, ADULT.to_owned())]
    );
}

#[test]
fn pin_urinishlari_hisoblanadi_va_nolga_tushadi() {
    let db = database();
    let pins = PinRepo::new(db.connection());
    let verifier = vec![7_u8; 48];

    let fresh = pins.find(ADULT).expect("o'qilsin").expect("a'zo bor");
    assert!(fresh.verifier.is_none());
    assert_eq!(fresh.failed_attempts, 0);

    pins.set_verifier(ADULT, &verifier).expect("o'rnatilsin");
    pins.record_failure(ADULT, NOW).expect("qayd");
    let attempts = pins.record_failure(ADULT, NOW).expect("qayd");
    assert_eq!(attempts, 2);
    let stored = pins.find(ADULT).expect("o'qilsin").expect("a'zo bor");
    assert_eq!(stored.verifier.as_deref(), Some(verifier.as_slice()));
    assert_eq!(stored.failed_at, Some(NOW));

    pins.reset_failures(ADULT).expect("nolga");
    assert_eq!(
        pins.find(ADULT)
            .expect("o'qilsin")
            .expect("a'zo")
            .failed_attempts,
        0
    );
}

#[test]
fn havas_chegarasi_va_rozilik_bir_marta_yoziladi() {
    let db = database();
    let limits = LimitRepo::new(db.connection());
    let limit = HavasLimit::create(LIMIT, HOUSEHOLD, uzs(1_000_000), NOW, DEVICE).expect("chegara");
    limits.insert_limit(&limit).expect("qo'shilsin");

    let latest = limits
        .latest(HOUSEHOLD)
        .expect("o'qilsin")
        .expect("chegara bor");
    assert_eq!(latest.monthly, uzs(1_000_000));

    let consent =
        LimitConsent::create(CONSENT, HOUSEHOLD, LIMIT, ADULT, NOW, DEVICE).expect("rozilik");
    limits.insert_consent(&consent).expect("qo'shilsin");
    assert_eq!(
        limits.consented_members(LIMIT).expect("o'qilsin"),
        vec![ADULT.to_owned()]
    );

    // Bir kattaning ikkinchi roziligi UNIQUE bilan rad etiladi.
    let again =
        LimitConsent::create(CONSENT_2, HOUSEHOLD, LIMIT, ADULT, NOW, DEVICE).expect("rozilik");
    assert!(limits.insert_consent(&again).is_err());
}

#[test]
fn juma_shirinligi_royxatda_korinadi() {
    let db = database();
    let treats = TreatRepo::new(db.connection());
    let treat = ScheduledTreat::create(
        TREAT,
        HOUSEHOLD,
        "Juma shirinligi",
        uzs(50),
        Weekday::Friday,
        NOW,
        DEVICE,
    )
    .expect("ritual");
    treats.insert_treat(&treat).expect("qo'shilsin");

    let listed = treats.list_treats(HOUSEHOLD).expect("o'qilsin");
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0].weekday, Weekday::Friday);
    assert_eq!(listed[0].amount, uzs(50));
}

#[test]
fn v3_dan_v4_ga_otganda_toifa_standart_qiymatdan_tiklanadi() {
    // Eski (v3) bazada toifasiz tizim kategoriyasi va xarajat bor; v4 ularni standart qiymat bilan to'ldiradi.
    let mut conn = Connection::open_in_memory().expect("xotira");
    Migrations::new(vec![M::up(SCHEMA_V1), M::up(SCHEMA_V2), M::up(SCHEMA_V3)])
        .to_latest(&mut conn)
        .expect("v3 gacha");
    conn.execute(
        "INSERT INTO households (id, name, created_at, updated_at, version, origin_device_id) VALUES (?1, 'Oila', '2026-10-15T01:00:00Z', '2026-10-15T01:00:00Z', 1, 'device-1')",
        [HOUSEHOLD],
    )
    .expect("xonadon");
    for (id, key) in [
        ("0192d000-0000-7000-8000-0000000000f1", Some("SNACKS")),
        ("0192d000-0000-7000-8000-0000000000f2", Some("RENT")),
        ("0192d000-0000-7000-8000-0000000000f3", None),
    ] {
        conn.execute(
            "INSERT INTO categories (id, household_id, name, system_key, created_at, updated_at, version, origin_device_id) \
             VALUES (?1, ?2, 'Kategoriya', ?3, '2026-10-15T01:00:00Z', '2026-10-15T01:00:00Z', 1, 'device-1')",
            params![id, HOUSEHOLD, key],
        )
        .expect("kategoriya");
    }

    schema::migrations().to_latest(&mut conn).expect("v4 gacha");

    let level = |id: &str| -> String {
        conn.query_row(
            "SELECT default_necessity FROM categories WHERE id = ?1",
            [id],
            |row| row.get(0),
        )
        .expect("toifa")
    };
    assert_eq!(level("0192d000-0000-7000-8000-0000000000f1"), "HAVAS");
    assert_eq!(level("0192d000-0000-7000-8000-0000000000f2"), "ZARUR");
    assert_eq!(level("0192d000-0000-7000-8000-0000000000f3"), "KERAK");

    let tables: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name IN ('havas_limits', 'limit_consents', 'scheduled_treats', 'necessity_changes')",
            [],
            |row| row.get(0),
        )
        .expect("jadvallar");
    assert_eq!(tables, 4);
}
