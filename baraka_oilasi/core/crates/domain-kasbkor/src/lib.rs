//! Kasb-kor makoni domen qoidalari (`docs/kasbkor/SPEC.md`). Sof funksiyalar: IO, tizim vaqti va
//! tasodifiylik yo'q.
#![deny(clippy::float_arithmetic)]

pub mod cash;
pub mod close;
pub mod credit;
pub mod equipment;
pub mod owner;
pub mod profit;
pub mod quote;
pub mod stock;

pub use baraka_domain_common::DomainError;
