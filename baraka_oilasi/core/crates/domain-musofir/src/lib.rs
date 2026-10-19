//! Musofir makoni domen qoidalari (`docs/musofir/SPEC.md`). Sof funksiyalar: IO, tizim vaqti va
//! tasodifiylik yo'q.
#![deny(clippy::float_arithmetic)]

pub mod cooling;
pub mod fund;
pub mod month;
pub mod rate;
pub mod remittance;
pub mod travel;

pub use baraka_domain_common::DomainError;

use baraka_money::round_half_up;

/// Ulush basis points'da: `round_half_up(part × 10000 / whole)`, `whole > 0`.
pub(crate) fn bp_of(part: i64, whole: i64) -> Result<i64, DomainError> {
    let v = round_half_up(i128::from(part) * 10_000, i128::from(whole))?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}
