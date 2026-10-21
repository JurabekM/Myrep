use std::fmt;

use baraka_money::MoneyError;

/// Domen xatosi: barqaror `code` va (ixtiyoriy) maydon nomi. Matnda shaxsiy ma'lumot yo'q.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DomainError {
    pub code: &'static str,
    pub field: Option<&'static str>,
}

impl DomainError {
    pub const fn new(code: &'static str) -> Self {
        Self { code, field: None }
    }

    pub const fn on(code: &'static str, field: &'static str) -> Self {
        Self {
            code,
            field: Some(field),
        }
    }
}

impl fmt::Display for DomainError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.field {
            Some(field) => write!(f, "{} ({field})", self.code),
            None => f.write_str(self.code),
        }
    }
}

impl std::error::Error for DomainError {}

impl From<MoneyError> for DomainError {
    fn from(e: MoneyError) -> Self {
        Self::new(e.code())
    }
}
