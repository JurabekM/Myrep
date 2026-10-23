//! `mpay-shield` — risk engine va ID&V.
//!
//! M5 gacha faqat [`stub::StubShield`]: deterministik, test PAN va merchant ID bo'yicha
//! boshqariladigan qarorlar (`docs/test-data.md`). Haqiqiy qoidalar, graf belgilar va ML skor —
//! M5 da shu port trait'lari (`IdvDecider`, `RiskScorer`) ortida.
#![forbid(unsafe_code)]

pub mod stub;

pub use stub::{StubShield, StubShieldConfig};

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
