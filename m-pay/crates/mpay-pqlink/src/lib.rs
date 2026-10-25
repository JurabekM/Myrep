//! `mpay-pqlink` — PQ Link v1: post-kvant gibrid kalit kanali (`docs/specs/pqlink.md`).
//!
//! * gibrid KEM: X25519 + ML-KEM-768, `HKDF-SHA256(ss_x25519 ‖ ss_mlkem, salt = th1)`;
//! * gibrid server imzosi: Ed25519 **va** ML-DSA-65;
//! * qurilma autentifikatsiyasi: P-256 kalit + Android Key Attestation zanjiri;
//! * transport: ChaCha20-Poly1305, yo'nalish bo'yicha alohida kalitlar, monoton `seq`, replay himoyasi.
//!
//! [`server::PqLinkServer`] va [`client::ClientHandshake`] — ikki tomon holat mashinalari.
#![forbid(unsafe_code)]

pub mod attestation;
pub mod client;
pub mod crypto;
pub mod device;
pub mod enrollment;
pub mod error;
pub mod identity;
pub mod revocation;
#[cfg(feature = "sandbox-attestation")]
pub mod sandbox;
pub mod server;
pub mod wire;

pub use client::{ClientHandshake, ClientSession};
pub use device::DeviceSigner;
pub use enrollment::EnrollmentGate;
pub use error::PqLinkError;
pub use identity::{KeyStoreServerSigner, MlDsaSeedBlob, ServerIdentity, ServerSigner};
pub use server::{PqLinkServer, ServerConfig, SessionId, SessionInfo};

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
