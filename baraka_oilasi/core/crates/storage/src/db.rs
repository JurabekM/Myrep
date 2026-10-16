use std::path::Path;
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

fn prepare(mut conn: Connection, key: &DbKey, wal: bool) -> Result<Database, StorageError> {
    apply_key(&conn, key)?;
    conn.execute_batch("PRAGMA foreign_keys = ON; PRAGMA secure_delete = ON;")?;
    if wal {
        conn.pragma_update(None, "journal_mode", "WAL")?;
    }
    MIGRATIONS.to_latest(&mut conn)?;
    Ok(Database {
        conn: Mutex::new(conn),
    })
}

impl Database {
    pub fn open(path: &Path, key: &DbKey) -> Result<Self, StorageError> {
        prepare(Connection::open(path)?, key, true)
    }

    pub fn open_in_memory(key: &DbKey) -> Result<Self, StorageError> {
        prepare(Connection::open_in_memory()?, key, false)
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

    /// Barcha yozuvlar tranzaksiyada: `f` xato qaytarsa, hech narsa saqlanmaydi.
    pub fn write<T>(
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn migrations_are_valid() {
        assert!(MIGRATIONS.validate().is_ok());
    }

    #[test]
    fn file_cannot_be_opened_without_the_key() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("baraka.db");
        let key = DbKey::from_bytes([1; 32]);
        {
            let db = Database::open(&path, &key).unwrap();
            assert_eq!(db.schema_version().unwrap(), 8);
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
