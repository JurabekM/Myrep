use std::path::Path;
use std::sync::{Mutex, MutexGuard, PoisonError};

use rusqlite::Connection;
use security::SecretKey;
use zeroize::Zeroizing;

use crate::{StorageError, schema};

/// Ochish navbatga qo'yiladi: SQLCipher jarayon bo'yicha birinchi marta ishga tushganda parallel ochish
/// kalitni bo'sh deb o'qiydi («sqlcipher not initialized»). Qulf faqat ochish paytida ushlanadi.
static OPEN_LOCK: Mutex<()> = Mutex::new(());

fn open_guard() -> MutexGuard<'static, ()> {
    OPEN_LOCK.lock().unwrap_or_else(PoisonError::into_inner)
}

/// Ochilgan shifrlangan ma'lumotlar bazasi. Kalit bazani ochish paytida ishlatiladi va bu yerda saqlanmaydi.
pub struct Database {
    conn: Connection,
}

impl Database {
    /// Fayldan ochadi (yo'q bo'lsa yaratadi). Kalit noto'g'ri bo'lsa — [`StorageError::WrongKeyOrNotDatabase`].
    /// Ochilgach migratsiyalar avtomatik qo'llanadi.
    pub fn open(path: &Path, key: &SecretKey) -> Result<Self, StorageError> {
        let _guard = open_guard();
        Self::initialize(Connection::open(path)?, key)
    }

    /// Xotirada ochadi (testlar uchun). Yozuvlar jarayon tugagach yo'qoladi.
    pub fn open_in_memory(key: &SecretKey) -> Result<Self, StorageError> {
        let _guard = open_guard();
        Self::initialize(Connection::open_in_memory()?, key)
    }

    fn initialize(conn: Connection, key: &SecretKey) -> Result<Self, StorageError> {
        apply_key(&conn, key)?;
        conn.execute_batch("PRAGMA foreign_keys = ON;")?;
        verify_readable(&conn)?;
        let mut database = Self { conn };
        schema::migrations().to_latest(&mut database.conn)?;
        Ok(database)
    }

    /// Asosiy SQLite ulanishi (repo'lar uchun).
    pub fn connection(&self) -> &Connection {
        &self.conn
    }

    /// Joriy sxema versiyasi (`PRAGMA user_version`).
    pub fn schema_version(&self) -> Result<i64, StorageError> {
        Ok(self
            .conn
            .query_row("PRAGMA user_version", [], |row| row.get(0))?)
    }
}

/// SQLCipher'ga 256-bitli xom kalitni beradi: `PRAGMA key = "x'<64 hex>'"`.
/// Hex satr va SQL matni tozalanadi (`Zeroizing`).
fn apply_key(conn: &Connection, key: &SecretKey) -> Result<(), StorageError> {
    let hex = Zeroizing::new(hex_encode(key.as_bytes()));
    let statement = Zeroizing::new(format!("PRAGMA key = \"x'{}'\";", hex.as_str()));
    conn.execute_batch(statement.as_str())?;
    Ok(())
}

/// Kalit to'g'ri bo'lsa, sqlite_master o'qiladi. Noto'g'ri bo'lsa SQLCipher xato beradi.
fn verify_readable(conn: &Connection) -> Result<(), StorageError> {
    conn.query_row("SELECT count(*) FROM sqlite_master", [], |_| Ok(()))
        .map_err(|_| StorageError::WrongKeyOrNotDatabase)
}

fn hex_encode(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(char::from(DIGITS[usize::from(byte >> 4)]));
        out.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    out
}
