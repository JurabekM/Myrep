//! D14 testlari: eksport → yangi baza → import 1:1 (round-trip), fork, ziddiyat, inkremental.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use domain::journal::{JournalEntry, JournalKind};
use domain::{Household, IdGen, Member, MemberRole};
use domain::agreement::{AgreementStatus, AgreementType};
use money::{Currency, Money};
use security::SecretKey;
use storage::interchange::{export_json, import_json};
use storage::schema::TABLES;
use storage::{AgreementRepo, AgreementRow, Database, HouseholdRepo, JournalRepo, MemberRepo};
use time::macros::{date, datetime};
use time::OffsetDateTime;

const NOW: OffsetDateTime = datetime!(2026-12-01 06:00 UTC);
const HOUSEHOLD: &str = "0192e000-0000-7000-8000-00000000aa01";
const OWNER: &str = "0192e000-0000-7000-8000-00000000aa02";
const AGREEMENT: &str = "0192e000-0000-7000-8000-00000000aa03";

struct Seq(std::sync::atomic::AtomicU32);

impl IdGen for Seq {
    fn next_id(&self) -> String {
        let n = self.0.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
        format!("0192e000-0000-7000-8000-0000000000{n:02x}")
    }
}

fn database(seed: u8) -> Database {
    Database::open_in_memory(&SecretKey::from_array([seed; 32])).expect("xotirada baza")
}

fn seed(db: &Database) {
    let conn = db.connection();
    let household = Household::create(HOUSEHOLD, "Asosiy daftar", NOW, "desktop").expect("xonadon");
    HouseholdRepo::new(conn).insert(&household).expect("xonadon");
    let owner = Member::create(OWNER, HOUSEHOLD, "O'zim", MemberRole::Adult, NOW, "desktop").expect("a'zo");
    MemberRepo::new(conn).insert(&owner).expect("a'zo");
    AgreementRepo::new(conn)
        .insert(&AgreementRow {
            id: AGREEMENT.into(),
            household_id: HOUSEHOLD.into(),
            kind: AgreementType::Partnership,
            title: "Non sexi".into(),
            status: AgreementStatus::Signed,
            version: 1,
            answers_json: "{}".into(),
            effective_from: Some(date!(2026 - 11 - 01)),
            created_at: NOW,
            updated_at: NOW,
            origin_device_id: "desktop".into(),
        })
        .expect("kelishuv");
}

fn entry(id: &str, minor: i64) -> JournalEntry {
    JournalEntry {
        id: id.into(),
        agreement_id: AGREEMENT.into(),
        kind: JournalKind::Contribution,
        party_id: "P1".into(),
        amount: Money::new(minor, Currency::Uzs),
        date: date!(2026 - 11 - 05),
        note: None,
    }
}

fn count(db: &Database, table: &str) -> i64 {
    db.connection()
        .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| row.get(0))
        .expect("count")
}

#[test]
fn round_trip_eksport_import_1_ga_1() {
    let source = database(1);
    seed(&source);
    let journal = JournalRepo::new(source.connection());
    let ids = Seq(std::sync::atomic::AtomicU32::new(0));
    journal.append(HOUSEHOLD, &entry(&ids.next_id(), 300), NOW, "desktop").expect("yozuv");
    journal.append(HOUSEHOLD, &entry(&ids.next_id(), 200), NOW, "desktop").expect("yozuv");

    let payload = export_json(&source, HOUSEHOLD, "desktop", "2026-12-01T06:00:00Z", None).expect("eksport");
    assert_eq!(payload["format"], "baraka-interchange");
    assert_eq!(payload["tables"]["journal_entries"].as_array().unwrap().len(), 2);

    let target = database(2);
    let preview = import_json(&target, &payload, true).expect("dry-run");
    assert!(!preview.blocked);
    assert_eq!(preview.journal_appended, 2);
    assert_eq!(count(&target, "households"), 0, "dry-run hech narsa yozmaydi");

    let report = import_json(&target, &payload, false).expect("import");
    assert_eq!(report.inserted.get("households"), Some(&1));
    assert_eq!(report.inserted.get("agreements"), Some(&1));
    assert_eq!(report.journal_appended, 2);
    assert!(report.conflicts.is_empty());
    for table in TABLES {
        assert_eq!(count(&source, table), count(&target, table), "{table} 1:1 emas");
    }
    // Telefondan kelgan xeshlar desktopda qayta hisoblanganda mos keladi.
    assert!(JournalRepo::new(target.connection()).verify(AGREEMENT).expect("tekshiruv").is_ok());
    // Qayta import — idempotent.
    let again = import_json(&target, &payload, false).expect("qayta");
    assert_eq!(again.journal_appended, 0);
    assert!(again.inserted.is_empty() && again.updated.is_empty());
}

#[test]
fn fork_importni_toxtatadi() {
    let local = database(3);
    seed(&local);
    let ids = Seq(std::sync::atomic::AtomicU32::new(0));
    let first = ids.next_id();
    JournalRepo::new(local.connection())
        .append(HOUSEHOLD, &entry(&first, 300), NOW, "desktop")
        .expect("yozuv");
    JournalRepo::new(local.connection())
        .append(HOUSEHOLD, &entry(&ids.next_id(), 200), NOW, "desktop")
        .expect("yozuv");

    let other = database(4);
    seed(&other);
    JournalRepo::new(other.connection())
        .append(HOUSEHOLD, &entry(&first, 300), NOW, "phone")
        .expect("yozuv");
    JournalRepo::new(other.connection())
        .append(HOUSEHOLD, &entry(&ids.next_id(), 999), NOW, "phone")
        .expect("boshqa yozuv");
    let payload = export_json(&other, HOUSEHOLD, "phone", "2026-12-01T07:00:00Z", None).expect("eksport");

    let report = import_json(&local, &payload, false).expect("hisobot");
    assert!(report.blocked);
    assert_eq!(report.forks.len(), 1);
    assert_eq!(report.forks[0].first_broken, 2);
    assert_eq!(count(&local, "journal_entries"), 2, "hech narsa yozilmadi");

    // Xeshi buzilgan kiruvchi zanjir ham to'xtatadi.
    let mut tampered = payload.clone();
    tampered["tables"]["journal_entries"][1]["amount_minor"] = serde_json::json!(1);
    let report = import_json(&local, &tampered, false).expect("hisobot");
    assert!(report.blocked);
    assert_eq!(report.forks[0].first_broken, 0);
}

#[test]
fn versiya_katta_yutadi_eski_ziddiyatga_tushadi_inkremental_filtr() {
    let local = database(5);
    seed(&local);
    let other = database(6);
    seed(&other);
    // Boshqa qurilmada kelishuv 2-versiyaga chiqdi.
    AgreementRepo::new(other.connection())
        .update_answers(AGREEMENT, 1, AgreementStatus::Draft, "{\"v\":2}", NOW)
        .expect("yangilandi");
    let payload = export_json(&other, HOUSEHOLD, "phone", "2026-12-01T07:00:00Z", None).expect("eksport");
    let report = import_json(&local, &payload, false).expect("import");
    assert_eq!(report.updated.get("agreements"), Some(&1));
    let row = AgreementRepo::new(local.connection()).find(AGREEMENT).expect("so'rov").expect("bor");
    assert_eq!(row.version, 2);
    assert_eq!(row.answers_json, "{\"v\":2}");

    // Mahalliy yangiroq (3-versiya) — kiruvchi 2-versiya ziddiyatga tushadi.
    AgreementRepo::new(local.connection())
        .update_answers(AGREEMENT, 2, AgreementStatus::Draft, "{\"v\":3}", NOW)
        .expect("yangilandi");
    let report = import_json(&local, &payload, false).expect("import");
    assert_eq!(report.updated.get("agreements"), None);
    assert_eq!(report.conflicts.len(), 1);
    assert_eq!(report.conflicts[0].reason, "LOCAL_NEWER");

    // Inkremental: `since` kelajakda — hech narsa chiqmaydi (updated_at/created_at bo'lgan jadvallarda).
    let empty = export_json(&local, HOUSEHOLD, "desktop", "x", Some("2099-01-01T00:00:00Z")).expect("eksport");
    assert_eq!(empty["tables"]["agreements"].as_array().unwrap().len(), 0);
    assert_eq!(empty["tables"]["households"].as_array().unwrap().len(), 0);
}
