//! Use-case'lar: domain qoidalari + storage tranzaksiyalari. Tauri'dan mustaqil, to'liq testlanadi.
//! Pul hisobi shu yerda va `domain`/`money` da; frontend faqat tayyor natijani ko'rsatadi.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod env;
mod error;

pub use pdf::{templates_releasable, TEMPLATES_APPROVED};

pub mod agreements;
pub mod audit;
pub mod categories;
pub mod ceremonies;
pub mod contributors;
pub mod council;
pub mod crafts;
pub mod csv_import;
pub mod debts;
pub mod envelopes;
pub mod events;
pub mod expenses;
pub mod goals;
pub mod guard;
pub mod habits;
pub mod havas;
pub mod home;
pub mod income;
pub mod interchange;
pub mod journal;
pub mod learning;
pub mod members;
pub mod obligations;
pub mod onboarding;
pub mod partnerships;
pub mod payoff;
pub mod prices;
pub mod receipts;
pub mod receivables;
pub mod recovery;
pub mod rescue;
pub mod review;
pub mod rules;
pub mod sellables;
pub mod setup;
pub mod subscriptions;
pub mod treats;
pub mod vault;
pub mod ventures;

pub use env::{local_date, sum_money, Ctx, Env, YearMonth, TASHKENT_OFFSET_HOURS};
pub use error::ServiceError;
