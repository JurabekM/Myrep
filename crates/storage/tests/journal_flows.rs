//! D8A saqlash oqimlari: kelishuv versiyasi, append-only jurnal (UPDATE/DELETE triggerlari), xesh zanjiri.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use domain::Household;
use domain::agreement::{AgreementStatus, AgreementType};
use domain::journal::{GENESIS_HASH, JournalEntry, JournalKind};
use money::{Currency, Money};
use security::SecretKey;
use storage::{AgreementRepo, AgreementRow, Database, HouseholdRepo, JournalRepo, StorageError};
use time::OffsetDateTime;
use time::macros::{date, datetime};

const HOUSEHOLD: &str = "0192f200-0000-7000-8000-0000000000a1";
const AGREEMENT: &str = "0192f200-0000-7000-8000-0000000000b1";
const E1: &str = "0192f200-0000-7000-8000-0000000000c1";
const E2: &str = "0192f200-0000-7000-8000-0000000000c2";
const DEVICE: &str = "device-1";
const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

fn database() -> Database {
    let db = Database::open_in_memory(&SecretKey::from_array([12; 32])).expect("ochilsin");
    let household = Household::create(HOUSEHOLD, "Oila", NOW, DEVICE).expect("xonadon");
    HouseholdRepo::new(db.connection())
        .insert(&household)
        .expect("qo'shilsin");
    AgreementRepo::new(db.connection())
        .insert(&AgreementRow {
            id: AGREEMENT.to_owned(),
            household_id: HOUSEHOLD.to_owned(),
            kind: AgreementType::Partnership,
            title: "Musharaka".to_owned(),
            status: AgreementStatus::Draft,
            version: 1,
            answers_json: "{}".to_owned(),
            effective_from: None,
            created_at: NOW,
            updated_at: NOW,
            origin_device_id: DEVICE.to_owned(),
        })
        .expect("kelishuv");
    db
}

fn entry(id: &str, party: &str, minor: i64, kind: JournalKind) -> JournalEntry {
    JournalEntry {
        id: id.to_owned(),
        agreement_id: AGREEMENT.to_owned(),
        kind,
        party_id: party.to_owned(),
        amount: Money::new(minor, Currency::Uzs),
        date: date!(2026 - 10 - 01),
        note: None,
    }
}

#[test]
fn zanjir_yoziladi_va_tekshiriladi() {
    let db = database();
    let journal = JournalRepo::new(db.connection());
    journal
        .append(
            HOUSEHOLD,
            &entry(E1, "P1", 300, JournalKind::Contribution),
            NOW,
            DEVICE,
        )
        .expect("birinchi");
    journal
        .append(
            HOUSEHOLD,
            &entry(E2, "P2", 300, JournalKind::Contribution),
            NOW,
            DEVICE,
        )
        .expect("ikkinchi");

    let stored = journal.list(AGREEMENT).expect("o'qilsin");
    assert_eq!(stored.len(), 2);
    assert_eq!(stored[0].prev_hash, GENESIS_HASH);
    assert_eq!(stored[1].prev_hash, stored[0].hash);
    assert_eq!(journal.verify(AGREEMENT).expect("tekshiruv"), Ok(()));
}

#[test]
fn yozuvni_ozgartirish_va_ochirish_db_darajasida_rad_etiladi() {
    let db = database();
    let journal = JournalRepo::new(db.connection());
    journal
        .append(
            HOUSEHOLD,
            &entry(E1, "P1", 300, JournalKind::Contribution),
            NOW,
            DEVICE,
        )
        .expect("yozildi");
    let conn = db.connection();

    let update = conn.execute(
        "UPDATE journal_entries SET amount_minor = 1 WHERE id = ?1",
        [E1],
    );
    let update_error = update.expect_err("UPDATE rad etilsin").to_string();
    assert!(update_error.contains("append-only"), "{update_error}");

    let delete = conn.execute("DELETE FROM journal_entries WHERE id = ?1", [E1]);
    let delete_error = delete.expect_err("DELETE rad etilsin").to_string();
    assert!(delete_error.contains("append-only"), "{delete_error}");

    // Rad etilgan urinishlardan keyin yozuv o'zgarmagan va zanjir to'g'ri.
    let stored = journal.list(AGREEMENT).expect("o'qilsin");
    assert_eq!(stored[0].entry.amount.minor(), 300);
    assert_eq!(journal.verify(AGREEMENT).expect("tekshiruv"), Ok(()));
}

#[test]
fn tuzatish_yangi_yozuv_bilan_qilinadi() {
    let db = database();
    let journal = JournalRepo::new(db.connection());
    journal
        .append(
            HOUSEHOLD,
            &entry(E1, "P1", 300, JournalKind::Contribution),
            NOW,
            DEVICE,
        )
        .expect("yozildi");
    journal
        .append(
            HOUSEHOLD,
            &entry(E2, "P1", 20, JournalKind::Correction),
            NOW,
            DEVICE,
        )
        .expect("tuzatish");

    let stored = journal.list(AGREEMENT).expect("o'qilsin");
    assert_eq!(stored.len(), 2);
    assert_eq!(
        stored[0].entry.amount.minor(),
        300,
        "eski yozuv o'zgarmagan"
    );
    assert_eq!(stored[1].entry.kind, JournalKind::Correction);
    assert_eq!(journal.verify(AGREEMENT).expect("tekshiruv"), Ok(()));
}

#[test]
fn kelishuv_versiyasi_nomuvofiqlikda_rad_etiladi() {
    let db = database();
    let agreements = AgreementRepo::new(db.connection());
    let version = agreements
        .update_answers(AGREEMENT, 1, AgreementStatus::Draft, "{\"a\":1}", NOW)
        .expect("yangilansin");
    assert_eq!(version, 2);
    assert!(matches!(
        agreements.update_answers(AGREEMENT, 1, AgreementStatus::Draft, "{}", NOW),
        Err(StorageError::VersionConflict)
    ));
    let found = agreements.find(AGREEMENT).expect("o'qilsin").expect("bor");
    assert_eq!(found.version, 2);
    assert_eq!(found.answers_json, "{\"a\":1}");
}
