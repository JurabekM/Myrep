//! Barcha makonlar uchun umumiy domen tiplari (`docs/BARAKA_OILASI.md`, 4.5, 8.1).
#![deny(clippy::float_arithmetic)]

mod enums;
mod error;
mod ids;
mod time;

pub use enums::*;
pub use error::DomainError;
pub use ids::{IdGen, SequentialIdGen, UuidV7Gen};
pub use time::{
    local_date, month_period, week_start, Clock, FixedClock, SystemClock, DEFAULT_TZ, WEEK_ANCHOR,
};

pub use baraka_money as money;
