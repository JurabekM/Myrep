use thiserror::Error;

/// Saqlash qatlamining xatolari. Xabarlarda ma'lumot qiymati (summa, ism, izoh) bo'lmaydi.
#[derive(Debug, Error)]
pub enum StorageError {
    /// Kalit noto'g'ri, yoki fayl shifrlangan ma'lumotlar bazasi emas.
    #[error("kalit noto'g'ri yoki fayl shifrlangan ma'lumotlar bazasi emas")]
    WrongKeyOrNotDatabase,
    /// SQLite xatosi (cheklov buzilishi va boshqalar).
    #[error("ma'lumotlar bazasi xatosi: {0}")]
    Sqlite(#[from] rusqlite::Error),
    /// Migratsiya xatosi.
    #[error("migratsiya xatosi: {0}")]
    Migration(#[from] rusqlite_migration::Error),
    /// Yozuv topilmadi (yoki o'chirilgan).
    #[error("yozuv topilmadi")]
    NotFound,
    /// Yozuv boshqa joyda o'zgartirilgan: versiya mos kelmaydi.
    #[error("yozuv boshqa joyda o'zgartirilgan: qayta yuklang")]
    VersionConflict,
    /// Bazadagi qiymat yaroqsiz (masalan, vaqt formati).
    #[error("ma'lumot yaroqsiz: {0}")]
    InvalidData(String),
    /// Domen qoidasi buzildi.
    #[error("domen qoidasi buzildi: {0}")]
    Domain(#[from] domain::DomainError),
}
