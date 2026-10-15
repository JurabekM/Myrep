//! «Baraka oilasi» pul modeli (`docs/BARAKA_OILASI.md`, 5-bo'lim).
//!
//! Barcha hisoblar butun sonlarda: summa `i64` minor birlikda, oraliq hisob `i128` da.
//! Suzuvchi nuqtali sonlar bu crate'da taqiqlangan.
#![no_std]
#![deny(clippy::float_arithmetic)]

extern crate alloc;

mod allocate;
mod currency;
mod error;
mod format;
mod fx;
mod money;
mod parse;
mod rounding;

pub use allocate::{allocate, allocate_minor, percent_of, BP_ONE};
pub use currency::Currency;
pub use error::{MoneyError, ParseError};
pub use format::{format, format_minor, Locale};
pub use fx::{convert, FxRate};
pub use money::Money;
pub use parse::parse_amount;
pub use rounding::round_half_up;
