//! «Baraka oilasi» use-case qatlami (`docs/BARAKA_OILASI.md`, 4.2–4.4).
//!
//! Android (`flutter_rust_bridge`) va desktop (`tauri-specta`) adapterlari **faqat** shu
//! crate'ni chaqiradi. Shu sababli ikkala platformaning xulqi bir xil bo'ladi.
//! Kirishdagi summalar string, chiqishdagi pul — `MoneyDto { minor, currency, formatted }`.
#![deny(clippy::float_arithmetic)]

mod app;
mod catalog;
mod ceremony;
mod debts;
mod dto;
mod error;
mod events;
mod governance;
mod partnership;
mod receipt;
mod recovery;
pub mod session;
mod settings;
mod sync;
mod text;
mod uy;
mod venture;

pub use app::App;
pub use dto::*;
pub use error::AppError;
pub use events::{ChangeEvent, Topic};
pub use session::{Session, SessionStatus, SetupResult};

pub use baraka_domain_common::{Clock, FixedClock, IdGen, SequentialIdGen, SystemClock, UuidV7Gen};
pub use baraka_security::{DbKey, KdfParams, PlatformSecret};

/// Yadro versiyasi (Y1: ikkala adapter shu funksiyadan bir xil javob oladi).
pub fn core_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
