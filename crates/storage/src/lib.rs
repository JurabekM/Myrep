//! Shifrlangan ma'lumotlar bazasi: SQLCipher, migratsiyalar (sxema v1, v2) va repo'lar.
//!
//! Baza fayli kalitsiz ochilmaydi (SQLCipher). Kalit `security` crate'idan keladi; bu crate uni
//! faqat ochish paytida ishlatadi va saqlamaydi (DESKTOP_PROMPT.md 6.2).

mod db;
mod error;
mod family;
mod finance;
mod progress;
mod repo;
pub mod schema;

pub use db::Database;
pub use error::StorageError;
pub use family::{LimitRepo, PinRepo, PinState, TreatRepo};
pub use finance::{
    CategoryRepo, DebtRepo, ExpenseRepo, IncomeRepo, ObligationRepo, ReportRepo, RuleRepo,
    StoredRule, VaultRepo,
};
pub use progress::{DaftarPageRepo, TaskCompletionRepo};
pub use repo::{HouseholdRepo, MemberRepo};
