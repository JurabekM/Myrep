//! Kasb-kor makoni domen qoidalari (`docs/kasbkor/SPEC.md`). Sof funksiyalar: IO, tizim vaqti va
//! tasodifiylik yo'q.
#![deny(clippy::float_arithmetic)]

pub mod close;
pub mod equipment;
pub mod owner;
pub mod profit;
pub mod quote;

pub use baraka_domain_common::DomainError;
