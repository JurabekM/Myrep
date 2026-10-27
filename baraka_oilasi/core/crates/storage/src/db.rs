use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use baraka_security::DbKey;
use rusqlite::{Connection, Transaction};
use rusqlite_migration::{Migrations, M};

use crate::StorageError;

const MIGRATIONS_SLICE: &[M<'_>] = &[
    M::up(include_str!("../migrations/001_init.sql")),
    M::up(include_str!("../migrations/002_debts.sql")),
    M::up(include_str!("../migrations/003_recovery.sql")),
    M::up(include_str!("../migrations/004_ceremonies.sql")),
    M::up(include_str!("../migrations/005_partnerships.sql")),
    M::up(include_str!("../migrations/006_ventures.sql")),
    M::up(include_str!("../migrations/007_governance.sql")),
    M::up(include_str!("../migrations/008_sync.sql")),
    M::up(include_str!("../migrations/009_onboarding.sql")),
    M::up(include_str!("../migrations/010_kasbkor.sql")),
    M::up(include_str!("../migrations/011_kasbkor_profit.sql")),
    M::up(include_str!("../migrations/012_kasbkor_close.sql")),
    M::up(include_str!("../migrations/013_kasbkor_cash_credit.sql")),
    M::up(include_str!("../migrations/014_kasbkor_stock.sql")),
    M::up(include_str!("../migrations/015_kasbkor_staff_supply.sql")),
    M::up(include_str!("../migrations/016_kasbkor_growth.sql")),
    M::up(include_str!("../migrations/017_device_roles.sql")),
    M::up(include_str!("../migrations/018_musofir.sql")),
    M::up(include_str!("../migrations/019_musofir_remittance.sql")),
    M::up(include_str!("../migrations/020_musofir_return.sql")),
    M::up(include_str!("../migrations/021_musofir_reserve.sql")),
    M::up(include_str!("../migrations/022_musofir_story.sql")),
    M::up(include_str!("../migrations/023_learning.sql")),
    M::up(include_str!("../migrations/024_kasbkor_learning.sql")),
    M::up(include_str!("../migrations/025_musofir_learning.sql")),
];
const MIGRATIONS: Migrations<'_> = Migrations::from_slice(MIGRATIONS_SLICE);

/// Yozuv metama'lumoti: vaqt (UTC, RFC 3339) va yozayotgan qurilma.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Meta {
    pub now: String,
    pub device_id: String,
}

pub struct Database {
    conn: Mutex<Connection>,
    /// Hisobchi qurilmasi: oddiy yozuvlar rad etiladi, faqat sinxronlash importi (`write_sync`).
    read_only: AtomicBool,
}

fn apply_key(conn: &Connection, key: &DbKey) -> Result<(), StorageError> {
    let pragma = key.sqlcipher_pragma_value();
    conn.execute_batch(&format!("PRAGMA key = \"{}\";", pragma.as_str()))?;
    // Kalitni darhol tekshirish: noto'g'ri kalit bilan birinchi o'qish xato beradi.
    conn.query_row("SELECT count(*) FROM sqlite_master", [], |r| {
        r.get::<_, i64>(0)
    })
    .map_err(|_| StorageError::WrongKey)?;
    Ok(())
}

/// Kalit, PRAGMA'lar va migratsiyalar. `version` — `None`: oxirgisigacha (odatdagi ochish);
/// `Some(n)`: faqat dastlabki `n` ta (eski reliz sxemasi, `test-support`).
fn prepare(
    mut conn: Connection,
    key: &DbKey,
    wal: bool,
    version: Option<usize>,
) -> Result<Database, StorageError> {
    apply_key(&conn, key)?;
    conn.execute_batch("PRAGMA foreign_keys = ON; PRAGMA secure_delete = ON;")?;
    if wal {
        conn.pragma_update(None, "journal_mode", "WAL")?;
    }
    match version {
        None => MIGRATIONS.to_latest(&mut conn)?,
        Some(v) => MIGRATIONS.to_version(&mut conn, v)?,
    }
    Ok(Database {
        conn: Mutex::new(conn),
        read_only: AtomicBool::new(false),
    })
}

impl Database {
    pub fn open(path: &Path, key: &DbKey) -> Result<Self, StorageError> {
        prepare(Connection::open(path)?, key, true, None)
    }

    pub fn open_in_memory(key: &DbKey) -> Result<Self, StorageError> {
        prepare(Connection::open_in_memory()?, key, false, None)
    }

    /// Joriy sxema versiyasi (`user_version`).
    pub fn schema_version(&self) -> Result<i64, StorageError> {
        self.read(|c| Ok(c.query_row("PRAGMA user_version", [], |r| r.get(0))?))
    }

    pub fn read<T>(
        &self,
        f: impl FnOnce(&Connection) -> Result<T, StorageError>,
    ) -> Result<T, StorageError> {
        let conn = self.conn.lock().map_err(|_| StorageError::LockPoisoned)?;
        f(&conn)
    }

    pub fn set_read_only(&self, on: bool) {
        self.read_only.store(on, Ordering::SeqCst);
    }

    pub fn is_read_only(&self) -> bool {
        self.read_only.load(Ordering::SeqCst)
    }

    /// Barcha yozuvlar tranzaksiyada: `f` xato qaytarsa, hech narsa saqlanmaydi.
    pub fn write<T>(
        &self,
        f: impl FnOnce(&Transaction<'_>) -> Result<T, StorageError>,
    ) -> Result<T, StorageError> {
        if self.is_read_only() {
            return Err(StorageError::ReadOnly);
        }
        self.write_sync(f)
    }

    /// Faqat o'qish rejimida ham ishlaydi: sinxronlash importi va qurilmaning o'z sozlamalari.
    pub fn write_sync<T>(
        &self,
        f: impl FnOnce(&Transaction<'_>) -> Result<T, StorageError>,
    ) -> Result<T, StorageError> {
        let mut conn = self.conn.lock().map_err(|_| StorageError::LockPoisoned)?;
        let tx = conn.transaction()?;
        let out = f(&tx)?;
        tx.commit()?;
        Ok(out)
    }
}

/// Faqat testlar uchun (`test-support`, R6): eski reliz bazasini yasash — relizlararo yangilanish
/// testi (masalan, 1.1.0 → 1.2.0) shu bilan haqiqiy eski sxemada boshlanadi.
#[cfg(any(test, feature = "test-support"))]
impl Database {
    /// Yangi bazani faqat dastlabki `version` ta migratsiya bilan yaratadi (1.1.0 — 22). Keyingi
    /// `Database::open` qolgan migratsiyalarni odatdagidek qo'llaydi.
    pub fn create_at_version(
        path: &Path,
        key: &DbKey,
        version: usize,
    ) -> Result<Self, StorageError> {
        prepare(Connection::open(path)?, key, true, Some(version))
    }

    /// `src` dagi barcha yozuvlarni shu bazaga ko'chiradi — **shu bazaning** (eski) sxemasidagi jadval
    /// va ustunlar bilan: keyingi migratsiyalarda qo'shilgan jadval va ustunlar tashlab ketiladi.
    /// `map` har yozuvni yozishdan oldin o'zgartira oladi (masalan, eski reliz formatiga qaytarish).
    /// Tashqi kalitlar tranzaksiya oxirida tekshiriladi. Qaytaradi: ko'chirilgan yozuvlar soni.
    pub fn copy_rows_from(
        &self,
        src: &Database,
        mut map: impl FnMut(&str, &mut baraka_interchange::canon::Row),
    ) -> Result<usize, StorageError> {
        use crate::repo::sync::{quoted, table_columns, to_json, to_sql};
        assert!(
            !std::ptr::eq(self, src),
            "copy_rows_from: manba va maqsad bitta baza bo'lmasligi kerak"
        );
        let from = src.conn.lock().map_err(|_| StorageError::LockPoisoned)?;
        let mut to = self.conn.lock().map_err(|_| StorageError::LockPoisoned)?;
        let tx = to.transaction()?;
        tx.execute_batch("PRAGMA defer_foreign_keys = ON;")?;
        let tables: Vec<String> = {
            let mut st = tx.prepare(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                 ORDER BY rowid",
            )?;
            let names = st.query_map([], |r| r.get(0))?;
            names.collect::<Result<_, _>>()?
        };
        let mut copied = 0;
        for t in &tables {
            let cols = table_columns(&tx, t)?;
            let list = cols
                .iter()
                .map(|c| quoted(c))
                .collect::<Vec<_>>()
                .join(", ");
            let table = quoted(t);
            let mut read = from.prepare(&format!("SELECT {list} FROM {table} ORDER BY rowid"))?;
            let marks: Vec<String> = (1..=cols.len()).map(|i| format!("?{i}")).collect();
            let mut write = tx.prepare(&format!(
                "INSERT INTO {table} ({list}) VALUES ({})",
                marks.join(", ")
            ))?;
            let mut rows = read.query([])?;
            while let Some(r) = rows.next()? {
                let mut row = baraka_interchange::canon::Row::new();
                for (i, c) in cols.iter().enumerate() {
                    row.insert(c.clone(), to_json(r.get_ref(i)?)?);
                }
                map(t, &mut row);
                let values = cols
                    .iter()
                    .map(|c| row.get(c).map_or(Ok(rusqlite::types::Value::Null), to_sql))
                    .collect::<Result<Vec<_>, _>>()?;
                write.execute(rusqlite::params_from_iter(values))?;
                copied += 1;
            }
        }
        tx.commit()?;
        Ok(copied)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn migrations_are_valid() {
        assert!(MIGRATIONS.validate().is_ok());
    }

    /// v19 rol jadvallarini qayta quradi: mavjud rollar, ulash takliflari va kutilayotgan eksport
    /// yozuvlari (`sync_pending` → `sync_exports`) saqlanib qolishi kerak.
    #[test]
    fn v19_keeps_roles_and_pending_rows() {
        let mut conn = Connection::open_in_memory().unwrap();
        conn.execute_batch("PRAGMA foreign_keys = ON;").unwrap();
        MIGRATIONS.to_version(&mut conn, 18).unwrap();
        conn.execute_batch(
            "INSERT INTO households (id, household_id, name, base_currency, locale, tz, month_start_day, created_at,
                updated_at, origin_device_id, updated_by_device_id)
                VALUES ('h', 'h', 'x', 'UZS', 'uz', 'Asia/Tashkent', 1, 't', 't', 'd1', 'd1');
             INSERT INTO devices (id, household_id, name, platform, paired_at, created_at, updated_at,
                origin_device_id, updated_by_device_id)
                VALUES ('d2', 'h', 'Telefon', 'android', 't', 't', 't', 'd1', 'd1');
             INSERT INTO spaces (id, household_id, kind, name, created_at, updated_at, origin_device_id,
                updated_by_device_id) VALUES ('kk', 'h', 'KASBKOR', 'KASBKOR', 't', 't', 'd1', 'd1');
             INSERT INTO device_access (id, household_id, device_id, role, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id) VALUES ('d2', 'h', 'd2', 'SELLER', 'kk', 't', 't', 'd1', 'd1');
             INSERT INTO sync_exports (export_id, household_id, peer_device_id, mode, row_count, created_at,
                role, role_space_id) VALUES ('e1', 'h', NULL, 'PAIRING', 3, 't', 'SELLER', 'kk');
             INSERT INTO sync_pending (export_id, tbl, row_id, hash) VALUES ('e1', 'spaces', 'kk', 'abc');",
        )
        .unwrap();
        MIGRATIONS.to_latest(&mut conn).unwrap();
        let count = |sql: &str| conn.query_row(sql, [], |r| r.get::<_, i64>(0)).unwrap();
        assert_eq!(
            count("SELECT count(*) FROM device_access WHERE role = 'SELLER'"),
            1
        );
        assert_eq!(
            count("SELECT count(*) FROM sync_exports WHERE role = 'SELLER'"),
            1
        );
        assert_eq!(
            count("SELECT count(*) FROM sync_pending WHERE export_id = 'e1'"),
            1
        );
        assert_eq!(count("SELECT count(*) FROM pragma_foreign_key_check"), 0);
        // Tashqi kalit yangi `sync_exports` ga qaraydi; yangi rol qabul qilinadi.
        assert!(conn
            .execute("INSERT INTO sync_pending (export_id, tbl, row_id, hash) VALUES ('e9', 'x', 'y', 'z')", [])
            .is_err());
        conn.execute("UPDATE device_access SET role = 'HOME' WHERE id = 'd2'", [])
            .unwrap();
    }

    #[test]
    fn file_cannot_be_opened_without_the_key() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("baraka.db");
        let key = DbKey::from_bytes([1; 32]);
        {
            let db = Database::open(&path, &key).unwrap();
            assert_eq!(db.schema_version().unwrap(), 25);
        }
        let wrong = DbKey::from_bytes([2; 32]);
        assert!(matches!(
            Database::open(&path, &wrong),
            Err(StorageError::WrongKey)
        ));
        // Kalitsiz oddiy SQLite sifatida ham o'qib bo'lmaydi.
        let plain = Connection::open(&path).unwrap();
        assert!(plain
            .query_row("SELECT count(*) FROM sqlite_master", [], |r| r
                .get::<_, i64>(0))
            .is_err());
        // Fayl boshida «SQLite format 3» sarlavhasi yo'q (shifrlangan).
        let bytes = std::fs::read(&path).unwrap();
        assert!(!bytes.starts_with(b"SQLite format 3"));
        assert!(Database::open(&path, &key).is_ok());
    }
}
