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
    /// Import: noma'lum jadval yoki ustun (boshqa sxema versiyasi).
    #[error("INTERCHANGE_SCHEMA_MISMATCH")]
    SchemaMismatch,
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
            Self::SchemaMismatch => "INTERCHANGE_SCHEMA_MISMATCH",
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
            || msg.contains("GOVERNANCE_IMMUTABLE")
            || msg.contains("KK_CLOSE_IMMUTABLE")
            || msg.contains("KK_CASH_DAY_IMMUTABLE")
            || msg.contains("KK_CREDIT_TERMS_IMMUTABLE")
            || msg.contains("KK_CREDIT_EVENT_IMMUTABLE")
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
