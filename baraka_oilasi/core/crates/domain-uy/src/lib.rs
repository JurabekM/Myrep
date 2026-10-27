//! Uy makoni domen qoidalari. Sof funksiyalar: IO, tizim vaqti va
//! tasodifiylik yo'q. Spetsifikatsiya: `docs/uy/SPEC.md`, algoritmlar: `docs/BARAKA_OILASI.md` 5.
#![deny(clippy::float_arithmetic)]

pub mod allocation;
pub mod amortization;
pub mod audit;
pub mod ceremony;
pub mod debt;
pub mod emergency;
pub mod gate;
pub mod inflation;
pub mod learning;
pub mod nudge;
pub mod partnership;
pub mod payoff;
pub mod recovery;
pub mod rescue;
pub mod review;
pub mod spike;
pub mod streak;
pub mod venture;

pub use baraka_domain_common::DomainError;
