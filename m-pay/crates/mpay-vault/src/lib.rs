//! `mpay-vault` — Token Vault.
//!
//! * provisioning: FPAN → Shield ID&V (GREEN / YELLOW / RED) → DPAN + LUK'lar;
//! * YELLOW: OTP-simulyatsiya bosqichi;
//! * lifecycle: `ACTIVE`, `SUSPENDED`, `DELETED`, LUK to'ldirish;
//! * detokenizatsiya — faqat ichki [`VaultDetokenizer`] porti orqali (issuer uchun);
//! * PAN/DPAN — faqat envelope-shifrlangan (KEK → DEK → AES-256-GCM), qidiruv HMAC indeks bo'yicha;
//! * har bir o'zgarish — append-only xesh-zanjirli audit log.
#![forbid(unsafe_code)]

pub mod audit;
pub mod db;
pub mod error;
pub mod model;
pub mod vault;

use std::sync::Arc;

use async_trait::async_trait;
use mpay_common::ports::{ConsumeOutcome, Detokenizer, PortError, TokenView};
use mpay_common::{Pan, TokenId};

pub use error::VaultError;
pub use model::{
    DeviceContext, LukGrant, ProvisionOutcome, ProvisionRequest, TokenProfile, TokenSummary,
    VaultConfig,
};
pub use vault::Vault;

/// Detokenizatsiya porti — faqat `mpay-issuer` ga beriladi (ADR-0002); HTTP'da ochilmaydi.
/// Har chaqiruv audit log'ga `actor` nomi bilan yoziladi.
pub struct VaultDetokenizer {
    vault: Arc<Vault>,
    actor: &'static str,
}

impl VaultDetokenizer {
    pub fn new(vault: Arc<Vault>, actor: &'static str) -> Self {
        Self { vault, actor }
    }
}

fn port(e: VaultError) -> PortError {
    PortError::Internal(e.code().to_owned())
}

#[async_trait]
impl Detokenizer for VaultDetokenizer {
    async fn lookup(&self, dpan: &Pan, luk_seq: u32) -> Result<Option<TokenView>, PortError> {
        self.vault
            .detok_lookup(dpan, luk_seq, self.actor)
            .await
            .map_err(port)
    }

    async fn consume(
        &self,
        token_id: &TokenId,
        luk_seq: u32,
        atc: u16,
    ) -> Result<ConsumeOutcome, PortError> {
        self.vault
            .detok_consume(token_id, luk_seq, atc, self.actor)
            .await
            .map_err(port)
    }
}

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
