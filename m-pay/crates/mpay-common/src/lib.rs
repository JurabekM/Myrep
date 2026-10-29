//! `mpay-common` — M-Pay umumiy tiplari.
//!
//! * [`pan`] — test PAN, Luhn, maskalash, amal qilish muddati;
//! * [`tlv`] — BER-TLV parser/encoder va DOL;
//! * [`iso8583`] — ISO 8583 subset packer;
//! * [`clearing`] — kliring fayli va emitent tasdig'i (M-Pay Test Scheme v1, ADR-0025);
//! * [`emv`] — M-Pay Test Scheme profili (teglar, PDOL/CDOL, IAD, Track 2);
//! * [`phone`] — telefon raqami (E.164 tekshiruvi, maskalash);
//! * [`ports`] — modullararo port trait'lari (ADR-0002);
//! * [`ids`], [`clock`], [`config`] — identifikatorlar, vaqt manbai, konfiguratsiya.
#![forbid(unsafe_code)]

pub mod api;
pub mod clearing;
pub mod clock;
pub mod config;
pub mod emv;
pub mod ids;
pub mod iso8583;
pub mod pan;
pub mod phone;
pub mod ports;
pub mod tlv;

pub use ids::{DeviceId, PanFingerprint, TokenId};
pub use pan::{CardExpiry, Pan, PanKind};

/// Crate versiyasi (diagnostika va `/healthz` uchun).
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
