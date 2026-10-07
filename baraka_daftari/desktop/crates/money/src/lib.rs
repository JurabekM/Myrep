//! Pul modeli (DESKTOP_PROMPT 4-bo'lim). `f32`/`f64` taqiqlangan.
//!
//! Bu crate mobil ilova (Dart) bilan bitma-bit mos bo'lishi shart:
//! `spec/test-vectors/` dagi oltin vektorlar ikkala tomonda ham yashil bo'lishi kerak.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod allocate;
mod currency;
mod error;
mod format;
mod fx;
mod money;
mod rounding;

pub use allocate::{allocate, percent_of};
pub use currency::Currency;
pub use error::MoneyError;
pub use format::{format_money, Locale};
pub use fx::FxRate;
pub use money::Money;
pub use rounding::round_half_up;
