//! Pul hisobi: butun sonli minor birliklar (tiyin, sent) va aniq arifmetika.
//!
//! Qoidalar (DESKTOP_PROMPT.md 4-bo'lim):
//! * `f32`/`f64` pul uchun ishlatilmaydi — kasrlar butun sonlar nisbati sifatida hisoblanadi;
//! * yaxlitlash faqat [`round_half_up_div`] orqali bajariladi;
//! * har xil valyutalarni qo'shish [`MoneyError::CurrencyMismatch`] xatosini beradi.

mod allocate;
mod currency;
mod error;
mod format;
mod fx;
mod rounding;
mod value;

pub use allocate::{BASIS_POINTS_WHOLE, allocate, percent_of};
pub use currency::Currency;
pub use error::MoneyError;
pub use format::{Locale, format_money};
pub use fx::{FxRate, convert};
pub use rounding::round_half_up_div;
pub use value::Money;
