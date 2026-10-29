//! `mpay-shield` — risk engine va ID&V.
//!
//! M5 gacha faqat [`stub::StubShield`]: deterministik, test PAN va merchant ID bo'yicha
//! boshqariladigan qarorlar (`docs/test-data.md`). Haqiqiy qoidalar, graf belgilar va ML skor —
//! M5 da shu port trait'lari (`IdvDecider`, `RiskScorer`) ortida.
#![forbid(unsafe_code)]

pub mod engine;
pub mod features;
pub mod graph;
pub mod model;
pub mod remote;
pub mod replay;
pub mod rules;
pub mod snapshot;
pub mod stub;

pub use engine::Shield;
pub use snapshot::SnapshotError;
pub use stub::{StubShield, StubShieldConfig};

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
