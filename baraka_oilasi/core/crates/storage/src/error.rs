use thiserror::Error;

#[derive(Debug, Error)]
pub enum StorageError {
    #[error("WRONG_KEY_OR_CORRUPT")]
    WrongKey,
    #[error("JOURNAL_IMMUTABLE")]
    JournalImmutable,
    /// Shartnoma versiyasi yoki imzo — dalil, o'zgarmaydi.
    #[error("EVIDENCE_IMMUTABLE")]
    EvidenceImmutable,
    /// Yopilgan davr ichidagi sanaga daftar yozuvi qo'shishga urinish.
    #[error("PERIOD_CLOSED")]
    PeriodClosed,
    #[error("NOT_FOUND")]
    NotFound,
    #[error("SCOPE_MISMATCH")]
    ScopeMismatch,
    #[error("MIGRATION_FAILED")]
    Migration(#[from] rusqlite_migration::Error),
    #[error("DB_ERROR")]
    Sqlite(rusqlite::Error),
    #[error("CORRUPT_ROW")]
    CorruptRow,
    #[error("LOCK_POISONED")]
    LockPoisoned,
}

impl StorageError {
    pub fn code(&self) -> &'static str {
        match self {
            Self::WrongKey => "WRONG_KEY_OR_CORRUPT",
            Self::JournalImmutable => "JOURNAL_IMMUTABLE",
            Self::EvidenceImmutable => "EVIDENCE_IMMUTABLE",
            Self::PeriodClosed => "PERIOD_CLOSED",
            Self::NotFound => "NOT_FOUND",
            Self::ScopeMismatch => "SCOPE_MISMATCH",
            Self::Migration(_) => "MIGRATION_FAILED",
            Self::Sqlite(_) => "DB_ERROR",
            Self::CorruptRow => "CORRUPT_ROW",
            Self::LockPoisoned => "LOCK_POISONED",
        }
    }
}

impl From<rusqlite::Error> for StorageError {
    fn from(e: rusqlite::Error) -> Self {
        let msg = e.to_string();
        if msg.contains("JOURNAL_IMMUTABLE") {
            Self::JournalImmutable
        } else if msg.contains("VENTURE_PERIOD_CLOSED") {
            Self::PeriodClosed
        } else if msg.contains("AGREEMENT_VERSION_IMMUTABLE")
            || msg.contains("SIGNATURE_IMMUTABLE")
            || msg.contains("VENTURE_IMMUTABLE")
        {
            Self::EvidenceImmutable
        } else if msg.contains("file is not a database") {
            Self::WrongKey
        } else if matches!(e, rusqlite::Error::QueryReturnedNoRows) {
            Self::NotFound
        } else {
            Self::Sqlite(e)
        }
    }
}
