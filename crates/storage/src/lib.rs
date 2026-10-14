//! Shifrlangan ma'lumotlar bazasi: SQLCipher, migratsiyalar (sxema v1) va repo'lar.
//!
//! Baza fayli kalitsiz ochilmaydi (SQLCipher). Kalit `security` crate'idan keladi; bu crate uni
//! faqat ochish paytida ishlatadi va saqlamaydi (DESKTOP_PROMPT.md 6.2).

mod db;
mod error;
mod repo;
pub mod schema;

pub use db::Database;
pub use error::StorageError;
pub use repo::{HouseholdRepo, MemberRepo};
