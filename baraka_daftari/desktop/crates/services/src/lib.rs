//! Use-case'lar: domain qoidalari + storage tranzaksiyalari. Tauri'dan mustaqil, to'liq testlanadi.
//! Pul hisobi shu yerda va `domain`/`money` da; frontend faqat tayyor natijani ko'rsatadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod env;
mod error;

pub mod audit;
pub mod home;
pub mod income;
pub mod learning;
pub mod obligations;
pub mod rules;
pub mod setup;
pub mod vault;

pub use env::{local_date, sum_money, Ctx, Env, YearMonth, TASHKENT_OFFSET_HOURS};
pub use error::ServiceError;
