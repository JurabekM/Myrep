//! D5 saqlash oqimlari: haftalik vazifa bajarilishi, birinchi bajarilish tarixi va «Daftar sahifasi».
#![allow(clippy::expect_used, clippy::unwrap_used)]

use domain::{DaftarPage, Household, TaskCompletion};
use security::SecretKey;
use storage::{DaftarPageRepo, Database, HouseholdRepo, TaskCompletionRepo};
use time::OffsetDateTime;
use time::macros::{date, datetime};

const HOUSEHOLD: &str = "0192b000-0000-7000-8000-0000000000a1";
const OTHER_HOUSEHOLD: &str = "0192b000-0000-7000-8000-0000000000a2";
const COMPLETION_1: &str = "0192b000-0000-7000-8000-0000000000c1";
const COMPLETION_2: &str = "0192b000-0000-7000-8000-0000000000c2";
const COMPLETION_3: &str = "0192b000-0000-7000-8000-0000000000c3";
const PAGE: &str = "0192b000-0000-7000-8000-0000000000d1";
const PAGE_2: &str = "0192b000-0000-7000-8000-0000000000d2";
const DEVICE: &str = "device-1";
const NOW: OffsetDateTime = datetime!(2026-10-14 06:00 UTC);

fn database() -> Database {
    let db = Database::open_in_memory(&SecretKey::from_array([5; 32])).expect("ochilsin");
    let household = Household::create(HOUSEHOLD, "Oila", NOW, DEVICE).expect("xonadon");
    HouseholdRepo::new(db.connection())
        .insert(&household)
        .expect("qo'shilsin");
    db
}

fn completion(id: &str, task: &str, week: time::Date, at: OffsetDateTime) -> TaskCompletion {
    TaskCompletion::create(id, HOUSEHOLD, task, week, true, at, DEVICE).expect("bajarilish")
}

#[test]
fn bajarilishlar_hafta_boyicha_royxatlanadi() {
    let db = database();
    let repo = TaskCompletionRepo::new(db.connection());
    let this_week = date!(2026 - 10 - 09);
    repo.insert(&completion(COMPLETION_1, "ch01.t1", this_week, NOW))
        .expect("qo'shilsin");
    repo.insert(&completion(COMPLETION_2, "ch01.t2", this_week, NOW))
        .expect("qo'shilsin");
    repo.insert(&completion(
        COMPLETION_3,
        "ch01.t3",
        date!(2026 - 10 - 16),
        NOW,
    ))
    .expect("qo'shilsin");

    let listed = repo.list_for_week(HOUSEHOLD, this_week).expect("o'qilsin");
    assert_eq!(listed.len(), 2);
    assert!(
        listed
            .iter()
            .all(|c| c.week_start == this_week && c.is_auto)
    );
}

#[test]
fn ochirilgan_bajarilish_birinchi_vaqtni_saqlaydi() {
    let db = database();
    let repo = TaskCompletionRepo::new(db.connection());
    let week = date!(2026 - 10 - 09);
    repo.insert(&completion(COMPLETION_1, "ch01.t1", week, NOW))
        .expect("qo'shilsin");
    // Belgi olib tashlandi — yozuv mantiqiy o'chdi.
    repo.soft_delete(COMPLETION_1, NOW + time::Duration::hours(1))
        .expect("o'chirilsin");
    // Keyinroq qayta belgilandi.
    repo.insert(&completion(
        COMPLETION_2,
        "ch01.t1",
        week,
        NOW + time::Duration::days(3),
    ))
    .expect("qo'shilsin");

    assert_eq!(
        repo.list_for_week(HOUSEHOLD, week).expect("o'qilsin").len(),
        1
    );
    let first = repo.first_completed_at(HOUSEHOLD).expect("o'qilsin");
    assert_eq!(first.get("ch01.t1"), Some(&NOW));
}

#[test]
fn ochirish_mavjud_bolmagan_yozuvda_xato_beradi() {
    let db = database();
    let repo = TaskCompletionRepo::new(db.connection());
    assert!(repo.soft_delete(COMPLETION_3, NOW).is_err());
}

#[test]
fn daftar_sahifasi_bob_uchun_bitta_va_yangilanadi() {
    let db = database();
    let repo = DaftarPageRepo::new(db.connection());
    let page =
        DaftarPage::create(PAGE, HOUSEHOLD, "ch05", 5, "Birinchi", NOW, DEVICE).expect("sahifa");
    repo.insert(&page).expect("qo'shilsin");

    let found = repo
        .find_for_chapter(HOUSEHOLD, "ch05")
        .expect("o'qilsin")
        .expect("sahifa bor");
    assert_eq!(found.body, "Birinchi");
    assert_eq!(found.law_number, 5);

    let later = datetime!(2026-10-15 06:00 UTC);
    let edited = found.with_body("Ikkinchi", later).expect("yangilansin");
    repo.update_body(&edited).expect("saqlansin");
    let reread = repo
        .find_for_chapter(HOUSEHOLD, "ch05")
        .expect("o'qilsin")
        .expect("sahifa bor");
    assert_eq!(reread.body, "Ikkinchi");
    assert_eq!(reread.meta.version, 2);

    // Shu bob uchun ikkinchi sahifa qo'shib bo'lmaydi.
    let second =
        DaftarPage::create(PAGE_2, HOUSEHOLD, "ch05", 5, "Boshqa", NOW, DEVICE).expect("sahifa");
    assert!(repo.insert(&second).is_err());
}

#[test]
fn boshqa_xonadon_sahifasini_kormaydi() {
    let db = database();
    let repo = DaftarPageRepo::new(db.connection());
    let page = DaftarPage::create(PAGE, HOUSEHOLD, "ch01", 1, "Matn", NOW, DEVICE).expect("sahifa");
    repo.insert(&page).expect("qo'shilsin");
    assert!(
        repo.find_for_chapter(OTHER_HOUSEHOLD, "ch01")
            .expect("o'qilsin")
            .is_none()
    );
}
