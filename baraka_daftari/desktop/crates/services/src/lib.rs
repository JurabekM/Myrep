//! Use-case'lar: domain qoidalari + storage tranzaksiyalari. Tauri'dan mustaqil, to'liq testlanadi.
//! Pul hisobi shu yerda va `domain`/`money` da; frontend faqat tayyor natijani ko'rsatadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod env;
mod error;

pub mod audit;
pub mod categories;
pub mod council;
pub mod csv_import;
pub mod envelopes;
pub mod expenses;
pub mod guard;
pub mod habits;
pub mod havas;
pub mod home;
pub mod income;
pub mod learning;
pub mod members;
pub mod obligations;
pub mod prices;
pub mod rescue;
pub mod rules;
pub mod setup;
pub mod subscriptions;
pub mod treats;
pub mod vault;

pub use env::{local_date, sum_money, Ctx, Env, YearMonth, TASHKENT_OFFSET_HOURS};
pub use error::ServiceError;
