//! SQLite ulanish hovuzi va migratsiyalar.

use std::str::FromStr;
use std::time::Duration;

use sqlx::sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions, SqliteSynchronous};
use sqlx::{Sqlite, SqlitePool, Transaction};

use crate::VaultError;

/// Commit chidamliligi (SQLite `synchronous`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Durability {
    /// Har commit diskka `fsync` (standart; to'lov ma'lumoti uchun tavsiya etiladi).
    #[default]
    Full,
    /// WAL + `NORMAL`: jarayon yiqilsa ma'lumot yo'qolmaydi, lekin elektr uzilsa oxirgi
    /// commit'lar yo'qolishi mumkin (fayl buzilmaydi). Faqat sandbox / o'lchov uchun.
    Normal,
}

/// Standart hovuz hajmi. SQLite'da bir vaqtda bitta yozuvchi: ko'p ulanish yozish qulfi uchun
/// SQLite busy-handler'ida uxlab kutadi (Windows'da ~15 ms donadorlik). Bitta ulanishda navbat
/// jarayon ichida (tokio) — yuk sinovida p99 1045 ms → 156 ms, o'tkazuvchanlik 83 → 235 so'rov/s
/// (`docs/load-report.md`).
pub const DEFAULT_MAX_CONNECTIONS: u32 = 1;

/// SQLite hovuzini ochadi: WAL, `foreign_keys = ON`, `busy_timeout`, `synchronous = FULL`.
pub async fn open_pool(url: &str) -> Result<SqlitePool, VaultError> {
    open_pool_with(url, Durability::Full, DEFAULT_MAX_CONNECTIONS).await
}

/// [`open_pool`], chidamlilik va hovuz hajmi tanlanadi.
///
/// Muhim: tranzaksiya ochiq turganda hovuzdan boshqa so'rov qilinmaydi (aks holda bitta ulanishda
/// o'z-o'zini kutish) — tayyorgarlik tranzaksiyadan oldin, ichida faqat `&mut tx`.
pub async fn open_pool_with(
    url: &str,
    durability: Durability,
    max_connections: u32,
) -> Result<SqlitePool, VaultError> {
    let opts = SqliteConnectOptions::from_str(url)?
        .create_if_missing(true)
        .journal_mode(SqliteJournalMode::Wal)
        .synchronous(match durability {
            Durability::Full => SqliteSynchronous::Full,
            Durability::Normal => SqliteSynchronous::Normal,
        })
        .foreign_keys(true)
        .busy_timeout(Duration::from_secs(5));
    Ok(SqlitePoolOptions::new()
        .max_connections(max_connections.max(1))
        .connect_with(opts)
        .await?)
}

/// Yozuvchi tranzaksiya: `BEGIN IMMEDIATE`. WAL rejimida oddiy (deferred) tranzaksiya avval o'qib,
/// keyin yozishga o'tganda boshqa yozuvchi bo'lsa `busy_timeout` ni kutmasdan `SQLITE_BUSY` qaytaradi
/// (yuk sinovida `DB_ERROR` → `91`). `IMMEDIATE` yozish qulfini boshida oladi va navbatda kutadi.
pub async fn begin_write(pool: &SqlitePool) -> Result<Transaction<'static, Sqlite>, sqlx::Error> {
    pool.begin_with("BEGIN IMMEDIATE").await
}

/// Vault migratsiyalarini qo'llaydi. Boshqa modullar (issuer) ham shu DB'da o'z
/// migratsiyalariga ega, shuning uchun "noma'lum" migratsiyalar e'tiborsiz qoldiriladi.
pub async fn migrate(pool: &SqlitePool) -> Result<(), VaultError> {
    let mut m = sqlx::migrate!("./migrations");
    m.set_ignore_missing(true);
    m.run(pool).await?;
    Ok(())
}
