//! SQLite ulanish hovuzi va migratsiyalar.

use std::str::FromStr;
use std::time::Duration;

use sqlx::sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions, SqliteSynchronous};
use sqlx::SqlitePool;

use crate::VaultError;

/// SQLite hovuzini ochadi: WAL, `foreign_keys = ON`, `busy_timeout`.
pub async fn open_pool(url: &str) -> Result<SqlitePool, VaultError> {
    let opts = SqliteConnectOptions::from_str(url)?
        .create_if_missing(true)
        .journal_mode(SqliteJournalMode::Wal)
        .synchronous(SqliteSynchronous::Full)
        .foreign_keys(true)
        .busy_timeout(Duration::from_secs(5));
    Ok(SqlitePoolOptions::new()
        .max_connections(8)
        .connect_with(opts)
        .await?)
}

/// Vault migratsiyalarini qo'llaydi. Boshqa modullar (issuer) ham shu DB'da o'z
/// migratsiyalariga ega, shuning uchun "noma'lum" migratsiyalar e'tiborsiz qoldiriladi.
pub async fn migrate(pool: &SqlitePool) -> Result<(), VaultError> {
    let mut m = sqlx::migrate!("./migrations");
    m.set_ignore_missing(true);
    m.run(pool).await?;
    Ok(())
}
