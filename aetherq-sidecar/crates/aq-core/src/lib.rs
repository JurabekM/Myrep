//! AETHER-Q v5.1 protokol yadrosi (Rust).
//!
//! Python referens (`aether_q_v3/aether_q_v51`) bilan bayt-mos: KDF/KMAC, KEM combiner,
//! ML-KEM-768 / ML-DSA-65 (FIPS 203/204), handshake (to'liq, resumption, PoW, 0-RTT), transport.
//! Testlar `kat/aq51_wire_kat.json` (Python generatori: `kat/gen_wire_kat.py`) bilan tekshiradi.

pub mod dos;
pub mod early;
pub mod error;
pub mod handshake;
pub mod identity;
pub mod kdf;
pub mod kem;
pub mod net;
pub mod sig;
pub mod ticket;
pub mod transport;
pub mod wire;

pub use error::{AqError, Result};
pub use identity::Identity;
pub use transport::{Receiver, Role, Sender, Session};

/// AETHER-Q versiyasi wire formatda (handshake sarlavhasi).
pub const PROTOCOL_VERSION: u16 = wire::AQ_VERSION;
