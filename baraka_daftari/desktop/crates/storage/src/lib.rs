//! SQLCipher bazasi, migratsiyalar va repository'lar (D3).
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod db;
mod error;
mod migrations;
mod row;

pub mod repo;

pub use db::{Database, DB_KEY_LEN};
pub use error::StorageError;
pub use migrations::{migrations, SCHEMA_VERSION};
pub use rusqlite::Connection;
