use std::fmt;

use serde::Serialize;

/// Adapterlarga uzatiladigan yagona xato: barqaror `code` va ixtiyoriy `field`.
/// Matnda summa, ism yoki boshqa shaxsiy ma'lumot bo'lmaydi.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct AppError {
    pub code: String,
    pub field: Option<String>,
}

impl AppError {
    pub fn new(code: &str) -> Self {
        Self {
            code: code.to_string(),
            field: None,
        }
    }

    pub fn on(code: &str, field: &str) -> Self {
        Self {
            code: code.to_string(),
            field: Some(field.to_string()),
        }
    }
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.field {
            Some(field) => write!(f, "{} ({field})", self.code),
            None => f.write_str(&self.code),
        }
    }
}

impl std::error::Error for AppError {}

impl From<baraka_storage::StorageError> for AppError {
    fn from(e: baraka_storage::StorageError) -> Self {
        Self::new(e.code())
    }
}

impl From<baraka_money::MoneyError> for AppError {
    fn from(e: baraka_money::MoneyError) -> Self {
        Self::new(e.code())
    }
}

impl From<baraka_domain_common::DomainError> for AppError {
    fn from(e: baraka_domain_common::DomainError) -> Self {
        Self {
            code: e.code.to_string(),
            field: e.field.map(str::to_string),
        }
    }
}

impl From<baraka_security::SecurityError> for AppError {
    fn from(e: baraka_security::SecurityError) -> Self {
        Self::new(e.code())
    }
}

impl From<baraka_journal::EntryError> for AppError {
    fn from(e: baraka_journal::EntryError) -> Self {
        Self::new(e.code())
    }
}

impl From<baraka_journal::ChainError> for AppError {
    fn from(e: baraka_journal::ChainError) -> Self {
        Self::new(e.code())
    }
}

impl From<baraka_interchange::InterchangeError> for AppError {
    fn from(e: baraka_interchange::InterchangeError) -> Self {
        Self::new(e.code())
    }
}
