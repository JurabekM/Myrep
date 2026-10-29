//! Ma'lumotlar bazasi qatlami — `mpay-db` (ADR-0018) qayta eksporti va Vault migratsiyalari.

pub use mpay_db::*;

use crate::VaultError;

/// Vault migratsiyalarini qo'llaydi (`migrations/sqlite` yoki `migrations/postgres`).
pub async fn migrate(db: &Db) -> Result<(), VaultError> {
    db.migrate_with(
        sqlx::migrate!("./migrations/sqlite"),
        sqlx::migrate!("./migrations/postgres"),
    )
    .await?;
    Ok(())
}
