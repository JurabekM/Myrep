//! D7 saqlash oqimlari: obunalar (ishlatilgan/bekor qilingan holat), konvertlar, «Qutqarilgan pul» yozuvlari
//! va xonadon sozlamalari (sxema v6).
#![allow(clippy::expect_used, clippy::unwrap_used)]

use domain::rescue::{RescueKind, SavingsRescue};
use domain::{Envelope, Household, Subscription};
use money::{Currency, Money};
use security::SecretKey;
use storage::{Database, EnvelopeRepo, HouseholdRepo, RescueRepo, SubscriptionRepo};
use time::OffsetDateTime;
use time::macros::{date, datetime};

const HOUSEHOLD: &str = "0192e000-0000-7000-8000-0000000000a1";
const SUB: &str = "0192e000-0000-7000-8000-0000000000b1";
const SUB_2: &str = "0192e000-0000-7000-8000-0000000000b2";
const ENVELOPE: &str = "0192e000-0000-7000-8000-0000000000c1";
const RESCUE: &str = "0192e000-0000-7000-8000-0000000000d1";
const RESCUE_2: &str = "0192e000-0000-7000-8000-0000000000d2";
const DEVICE: &str = "device-1";
const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

fn database() -> Database {
    let db = Database::open_in_memory(&SecretKey::from_array([7; 32])).expect("ochilsin");
    let household = Household::create(HOUSEHOLD, "Oila", NOW, DEVICE).expect("xonadon");
    HouseholdRepo::new(db.connection())
        .insert(&household)
        .expect("qo'shilsin");
    db
}

fn uzs(major: i64) -> Money {
    Money::new(major * 100, Currency::Uzs)
}

#[test]
fn sxema_v11_qollanadi() {
    let db = database();
    assert_eq!(db.schema_version().expect("versiya"), 11);
}

#[test]
fn obuna_saqlanadi_va_holati_yangilanadi() {
    let db = database();
    let repo = SubscriptionRepo::new(db.connection());
    let sub = Subscription::create(
        SUB,
        HOUSEHOLD,
        "Telegram Premium",
        uzs(30_000),
        Some(uzs(300_000)),
        NOW,
        DEVICE,
    )
    .expect("obuna");
    repo.insert(&sub).expect("qo'shilsin");

    let loaded = repo.find(SUB).expect("o'qilsin").expect("bor");
    assert_eq!(loaded.monthly, uzs(30_000));
    assert_eq!(loaded.yearly, Some(uzs(300_000)));
    assert_eq!(loaded.cancelled_on, None);

    let cancelled = loaded
        .cancel(date!(2026 - 10 - 01))
        .expect("bekor qilinsin");
    repo.update(&cancelled).expect("yangilansin");

    let after = repo.find(SUB).expect("o'qilsin").expect("bor");
    assert_eq!(after.cancelled_on, Some(date!(2026 - 10 - 01)));
    assert_eq!(after.meta.version, 1);
}

#[test]
fn obuna_ruyxati_va_yoq_yangilash_xato() {
    let db = database();
    let repo = SubscriptionRepo::new(db.connection());
    let first =
        Subscription::create(SUB, HOUSEHOLD, "Zoom", uzs(5_000), None, NOW, DEVICE).expect("obuna");
    let second = Subscription::create(SUB_2, HOUSEHOLD, "Spotify", uzs(3_000), None, NOW, DEVICE)
        .expect("obuna");
    repo.insert(&first).expect("qo'shilsin");
    repo.insert(&second).expect("qo'shilsin");
    assert_eq!(repo.list(HOUSEHOLD).expect("ro'yxat").len(), 2);

    let ghost = Subscription::create(
        "0192e000-0000-7000-8000-0000000000ff",
        HOUSEHOLD,
        "Yo'q",
        uzs(1),
        None,
        NOW,
        DEVICE,
    )
    .expect("obuna");
    assert!(repo.update(&ghost).is_err());
}

#[test]
fn konvert_saqlanadi() {
    let db = database();
    let repo = EnvelopeRepo::new(db.connection());
    let envelope = Envelope::create(
        ENVELOPE,
        HOUSEHOLD,
        "Bozor",
        uzs(500_000),
        None,
        NOW,
        DEVICE,
    )
    .expect("konvert");
    repo.insert(&envelope).expect("qo'shilsin");

    let loaded = repo.find(ENVELOPE).expect("o'qilsin").expect("bor");
    assert_eq!(loaded.name, "Bozor");
    assert_eq!(loaded.weekly_limit, uzs(500_000));
    assert_eq!(repo.list(HOUSEHOLD).expect("ro'yxat").len(), 1);
}

#[test]
fn qutqarilgan_pul_yozuvlari_sana_boyicha_qaytadi() {
    let db = database();
    let repo = RescueRepo::new(db.connection());
    let later = SavingsRescue::create(
        RESCUE,
        HOUSEHOLD,
        RescueKind::Subscription,
        uzs(12),
        date!(2026 - 10 - 20),
        NOW,
        DEVICE,
    )
    .expect("yozuv")
    .with_source(Some(SUB.to_owned()));
    let earlier = SavingsRescue::create(
        RESCUE_2,
        HOUSEHOLD,
        RescueKind::Transfer,
        uzs(7),
        date!(2026 - 10 - 02),
        NOW,
        DEVICE,
    )
    .expect("yozuv");
    repo.insert(&later).expect("qo'shilsin");
    repo.insert(&earlier).expect("qo'shilsin");

    let listed = repo.list(HOUSEHOLD).expect("ro'yxat");
    assert_eq!(listed.len(), 2);
    assert_eq!(listed[0].id, RESCUE_2);
    assert_eq!(listed[0].kind, RescueKind::Transfer);
    assert_eq!(listed[1].source_id.as_deref(), Some(SUB));
    assert_eq!(listed[1].amount, uzs(12));
}

#[test]
fn xonadon_sozlamasi_yoziladi_va_almashtiriladi() {
    let db = database();
    let repo = RescueRepo::new(db.connection());
    assert_eq!(
        repo.setting(HOUSEHOLD, "baseline_month").expect("o'qilsin"),
        None
    );

    repo.set_setting(HOUSEHOLD, "baseline_month", "2026-09")
        .expect("yozilsin");
    repo.set_setting(HOUSEHOLD, "baseline_month", "2026-08")
        .expect("almashsin");
    assert_eq!(
        repo.setting(HOUSEHOLD, "baseline_month")
            .expect("o'qilsin")
            .as_deref(),
        Some("2026-08")
    );
}
