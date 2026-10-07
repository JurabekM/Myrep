use std::path::Path;

use rusqlite::Connection;

use crate::{migrations, StorageError};

pub const DB_KEY_LEN: usize = 32;

/// Shifrlangan baza (SQLCipher). Kalit — xom 256-bit (KDF `security` crate'ida).
pub struct Database {
    conn: Connection,
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

impl Database {
    /// Bazani ochadi (yo'q bo'lsa yaratadi) va migratsiyalarni qo'llaydi.
    ///
    /// # Errors
    /// Kalit noto'g'ri bo'lsa [`StorageError::WrongKey`]; SQLCipher bo'lmasa
    /// [`StorageError::CipherUnavailable`].
    pub fn open(path: &Path, key: &[u8; DB_KEY_LEN]) -> Result<Self, StorageError> {
        Self::init(Connection::open(path)?, key)
    }

    /// Xotiradagi shifrlangan baza (testlar uchun).
    ///
    /// # Errors
    /// [`Database::open`] bilan bir xil.
    pub fn open_in_memory(key: &[u8; DB_KEY_LEN]) -> Result<Self, StorageError> {
        Self::init(Connection::open_in_memory()?, key)
    }

    fn init(mut conn: Connection, key: &[u8; DB_KEY_LEN]) -> Result<Self, StorageError> {
        // Xom kalit sintaksisi: PRAGMA key = "x'<64 hex>'". Matn SQL tarixiga tushmasligi uchun
        // `execute_batch` ishlatiladi va loglanmaydi.
        let mut pragma = format!("PRAGMA key = \"x'{}'\";", hex(key));
        let res = conn.execute_batch(&pragma);
        zeroize::Zeroize::zeroize(&mut pragma);
        res?;

        let cipher: String = conn
            .query_row("PRAGMA cipher_version", [], |r| r.get(0))
            .unwrap_or_default();
        if cipher.is_empty() {
            return Err(StorageError::CipherUnavailable);
        }
        // Noto'g'ri kalit birinchi o'qishda `NotADatabase` beradi.
        if let Err(e) = conn.query_row("SELECT count(*) FROM sqlite_master", [], |r| {
            r.get::<_, i64>(0)
        }) {
            return Err(match e {
                rusqlite::Error::SqliteFailure(f, _)
                    if f.code == rusqlite::ErrorCode::NotADatabase =>
                {
                    StorageError::WrongKey
                }
                other => other.into(),
            });
        }
        conn.pragma_update(None, "foreign_keys", true)?;
        migrations().to_latest(&mut conn)?;
        Ok(Self { conn })
    }

    #[must_use]
    pub const fn conn(&self) -> &Connection {
        &self.conn
    }

    /// Yozuvlar guruhini bitta tranzaksiyada bajaradi; xato bo'lsa hammasi bekor qilinadi.
    /// Xato turi chaqiruvchida (`E: From<StorageError>`), shuning uchun servis xatolari yo'qolmaydi.
    ///
    /// # Errors
    /// Closure xatosi yoki tranzaksiya boshlash/commit xatosi.
    pub fn transaction<T, E: From<StorageError>>(
        &mut self,
        f: impl FnOnce(&rusqlite::Transaction<'_>) -> Result<T, E>,
    ) -> Result<T, E> {
        let tx = self.conn.transaction().map_err(StorageError::from)?;
        let out = f(&tx)?;
        tx.commit().map_err(StorageError::from)?;
        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const KEY: [u8; 32] = [7; 32];
    const OTHER: [u8; 32] = [9; 32];

    #[test]
    fn file_is_not_plain_sqlite_and_needs_the_key() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("baraka.db");
        drop(Database::open(&path, &KEY).unwrap());

        let head = std::fs::read(&path).unwrap();
        assert_ne!(
            &head[..15],
            b"SQLite format 3",
            "fayl ochiq SQLite sarlavhasiga ega"
        );

        assert!(matches!(
            Database::open(&path, &OTHER),
            Err(StorageError::WrongKey)
        ));
        // Kalitsiz (oddiy SQLite sifatida) ochib bo'lmaydi.
        let plain = Connection::open(&path).unwrap();
        assert!(plain
            .query_row("SELECT count(*) FROM sqlite_master", [], |r| r
                .get::<_, i64>(0))
            .is_err());
        // To'g'ri kalit bilan qayta ochiladi.
        assert!(Database::open(&path, &KEY).is_ok());
    }

    #[test]
    fn foreign_keys_are_enforced() {
        let db = Database::open_in_memory(&KEY).unwrap();
        let err = db.conn().execute(
            "INSERT INTO members (id, household_id, created_at, updated_at, version, origin_device_id, display_name, role)
             VALUES ('m','nope','t','t',1,'d','x','ADULT')",
            [],
        );
        assert!(err.is_err());
    }
}
