//! Saqlash oqimlari: shifrlash, kalit tekshiruvi, migratsiyalar, repo'lar va DB cheklovlari.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use domain::{Household, Member, MemberRole};
use rusqlite::Connection;
use security::SecretKey;
use storage::{Database, HouseholdRepo, MemberRepo, StorageError, schema};
use time::{Duration, OffsetDateTime};

const HOUSEHOLD: &str = "0192a000-0000-7000-8000-0000000000a1";
const MEMBER: &str = "0192a000-0000-7000-8000-0000000000b1";
const ASSET: &str = "0192a000-0000-7000-8000-0000000000c1";
const DEVICE: &str = "device-1";

fn key(byte: u8) -> SecretKey {
    SecretKey::from_array([byte; 32])
}

fn at(offset_secs: i64) -> OffsetDateTime {
    OffsetDateTime::from_unix_timestamp(1_800_000_000).expect("vaqt")
        + Duration::seconds(offset_secs)
}

/// Test papkasi: test tugagach o'chiriladi (fayl ochiq bo'lmasligi uchun avval baza yopiladi).
struct TempDb {
    dir: PathBuf,
}

impl TempDb {
    fn new(name: &str) -> Self {
        let dir = std::env::temp_dir().join(format!(
            "baraka-storage-{name}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|elapsed| elapsed.as_nanos())
                .unwrap_or(0)
        ));
        std::fs::create_dir_all(&dir).expect("papka");
        Self { dir }
    }

    fn path(&self) -> PathBuf {
        self.dir.join("daftar.db")
    }
}

impl Drop for TempDb {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}

fn household() -> Household {
    Household::create(HOUSEHOLD, "Oila", at(0), DEVICE).expect("to'g'ri xonadon")
}

#[test]
fn shifrlangan_fayl_kalitsiz_oqilmaydi_va_kalit_bilan_qayta_ochiladi() {
    let temp = TempDb::new("encrypted");
    let path = temp.path();
    {
        let db = Database::open(&path, &key(7)).expect("ochilsin");
        HouseholdRepo::new(db.connection())
            .insert(&household())
            .expect("qo'shilsin");
    }

    // Fayl SQLite sarlavhasi bilan boshlanmaydi: u shifrlangan.
    let bytes = std::fs::read(&path).expect("fayl");
    assert_ne!(bytes.get(..16), Some(&b"SQLite format 3\0"[..]));

    // Kalitsiz (oddiy SQLite sifatida) o'qib bo'lmaydi.
    let plain = Connection::open(&path).expect("ochiladi, lekin...");
    assert!(
        plain
            .query_row("SELECT count(*) FROM sqlite_master", [], |_| Ok(()))
            .is_err()
    );

    // To'g'ri kalit bilan ma'lumot saqlanib qolgan.
    let db = Database::open(&path, &key(7)).expect("qayta ochilsin");
    let found = HouseholdRepo::new(db.connection())
        .find(HOUSEHOLD)
        .expect("o'qilsin")
        .expect("xonadon bor");
    assert_eq!(found.name, "Oila");
}

#[test]
fn notogri_kalit_rad_etiladi() {
    let temp = TempDb::new("wrong-key");
    let path = temp.path();
    drop(Database::open(&path, &key(7)).expect("yaratilsin"));
    assert!(matches!(
        Database::open(&path, &key(8)),
        Err(StorageError::WrongKeyOrNotDatabase)
    ));
}

#[test]
fn migratsiya_sxema_v1_ni_qollaydi() {
    let db = Database::open_in_memory(&key(1)).expect("ochilsin");
    assert_eq!(db.schema_version().expect("versiya"), 1);

    let mut statement = db
        .connection()
        .prepare("SELECT name FROM sqlite_master WHERE type = 'table'")
        .expect("so'rov");
    let names: Vec<String> = statement
        .query_map([], |row| row.get(0))
        .expect("qatorlar")
        .map(Result::unwrap)
        .collect();
    for table in schema::TABLES {
        assert!(names.iter().any(|name| name == table), "{table} yo'q");
    }
}

#[test]
fn migratsiyalar_tekshiruvdan_otadi() {
    schema::migrations()
        .validate()
        .expect("migratsiyalar to'g'ri");
}

#[test]
fn xonadon_hayot_sikli_versiya_bilan() {
    let db = Database::open_in_memory(&key(1)).expect("ochilsin");
    let repo = HouseholdRepo::new(db.connection());
    repo.insert(&household()).expect("qo'shilsin");

    let found = repo.find(HOUSEHOLD).expect("o'qilsin").expect("bor");
    assert_eq!(found.name, "Oila");
    assert_eq!(found.meta.version, 1);

    let renamed = repo
        .rename(HOUSEHOLD, "Yangi oila", 1, at(60))
        .expect("o'zgarsin");
    assert_eq!(renamed.name, "Yangi oila");
    assert_eq!(renamed.meta.version, 2);

    // Eski versiya bilan o'zgartirish rad etiladi.
    assert!(matches!(
        repo.rename(HOUSEHOLD, "Boshqa", 1, at(120)),
        Err(StorageError::VersionConflict)
    ));

    repo.soft_delete(HOUSEHOLD, 2, at(180))
        .expect("o'chirilsin");
    assert!(repo.find(HOUSEHOLD).expect("o'qilsin").is_none());
    assert!(repo.list().expect("ro'yxat").is_empty());
    // O'chirilgan yozuv qayta o'chirilmaydi: u endi topilmaydi.
    assert!(matches!(
        repo.soft_delete(HOUSEHOLD, 3, at(240)),
        Err(StorageError::NotFound)
    ));
}

#[test]
fn azo_faqat_mavjud_xonadonda_bolishi_mumkin() {
    let db = Database::open_in_memory(&key(1)).expect("ochilsin");
    let member = Member::create(
        MEMBER,
        HOUSEHOLD,
        "Dilshod",
        MemberRole::Adult,
        at(0),
        DEVICE,
    )
    .expect("to'g'ri a'zo");
    // Xonadon yo'q: tashqi kalit buziladi.
    assert!(matches!(
        MemberRepo::new(db.connection()).insert(&member),
        Err(StorageError::Sqlite(_))
    ));

    HouseholdRepo::new(db.connection())
        .insert(&household())
        .expect("xonadon qo'shilsin");
    MemberRepo::new(db.connection())
        .insert(&member)
        .expect("endi qo'shiladi");
    let members = MemberRepo::new(db.connection())
        .list_for_household(HOUSEHOLD)
        .expect("ro'yxat");
    assert_eq!(members.len(), 1);
    assert_eq!(members[0].role, MemberRole::Adult);
}

#[test]
fn rol_cheklovi_bazada_ham_ishlaydi() {
    let db = Database::open_in_memory(&key(1)).expect("ochilsin");
    HouseholdRepo::new(db.connection())
        .insert(&household())
        .expect("xonadon");
    let result = db.connection().execute(
        "INSERT INTO members (id, household_id, name, role, created_at, updated_at, version, origin_device_id) \
         VALUES (?1, ?2, 'X', 'ADMIN', '2026-10-14T00:00:00Z', '2026-10-14T00:00:00Z', 1, 'd')",
        [MEMBER, HOUSEHOLD],
    );
    assert!(result.is_err());
}

#[test]
fn chiqim_sababsiz_qaytarilmaydi() {
    // Sxemadagi qoida: `WITHDRAWAL` (pul olish) uchun sabab majburiy (SPEC 2D.6, friction).
    let db = Database::open_in_memory(&key(1)).expect("ochilsin");
    HouseholdRepo::new(db.connection())
        .insert(&household())
        .expect("xonadon");
    db.connection()
        .execute(
            "INSERT INTO assets (id, household_id, type, name, quantity, unit, acquired_at, created_at, updated_at, version, origin_device_id) \
             VALUES (?1, ?2, 'VAULT', 'Qorovul', 0, 'minor', '2026-10-14', '2026-10-14T00:00:00Z', '2026-10-14T00:00:00Z', 1, 'd')",
            [ASSET, HOUSEHOLD],
        )
        .expect("aktiv");

    let insert = |reason: Option<&str>| {
        db.connection().execute(
            "INSERT INTO vault_transactions (id, household_id, asset_id, kind, amount_minor, currency, occurred_on, reason, created_at, updated_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, 'WITHDRAWAL', 1000, 'UZS', '2026-10-14', ?4, '2026-10-14T00:00:00Z', '2026-10-14T00:00:00Z', 1, 'd')",
            rusqlite::params![
                "0192a000-0000-7000-8000-0000000000d1",
                HOUSEHOLD,
                ASSET,
                reason
            ],
        )
    };
    assert!(insert(None).is_err());
    assert!(insert(Some("   ")).is_err());
    assert!(insert(Some("Favqulodda holat")).is_ok());
}
