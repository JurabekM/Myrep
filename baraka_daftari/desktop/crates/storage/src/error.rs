#[derive(Debug, thiserror::Error)]
pub enum StorageError {
    #[error("baza kaliti noto'g'ri yoki fayl shifrlangan bazaga o'xshamaydi")]
    WrongKey,
    #[error("SQLCipher ulanmagan (oddiy SQLite aniqlandi)")]
    CipherUnavailable,
    #[error("sqlite xatosi: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("migratsiya xatosi: {0}")]
    Migration(#[from] rusqlite_migration::Error),
    #[error("ma'lumot buzilgan: {0}")]
    Corrupt(String),
    #[error("yozuv topilmadi yoki allaqachon o'chirilgan")]
    NotFound,
}
