//! Shield roli uchun ichki protokol (2-faza P2.4, ADR-0019): ko'p instansiyada belgilar ombori
//! bitta Shield instansiyasida, API instansiyalari unga shu DTO'lar bilan murojaat qiladi.
//!
//! DTO'larda **ochiq PAN yo'q**: karta — HMAC barmoq izi, qurilma — ID (hex). Dvigatel aynan shu
//! maydonlarni ishlatadi (`ProvisionEvent`, `TxnEvent`).

use mpay_common::ports::{IdvRequest, RiskRequest};
use serde::{Deserialize, Serialize};

use crate::engine::Shield;
use crate::features::{ProvisionEvent, TxnEvent};

/// `POST /internal/shield/idv`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdvEventDto {
    pub at: i64,
    /// Qurilma ID (hex, 32 bayt).
    pub device: String,
    /// Karta barmoq izi (hex, 32 bayt).
    pub card: String,
    pub attestation_level: u8,
    pub existing_tokens_for_pan: u32,
    pub existing_tokens_for_device: u32,
}

/// `POST /internal/shield/txn`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TxnEventDto {
    pub at: i64,
    pub device: String,
    pub card: String,
    pub merchant: String,
    pub country: u16,
    pub amount_minor: u64,
    pub cdcvm: bool,
}

fn hex32(s: &str) -> Result<[u8; 32], String> {
    let mut b = [0u8; 32];
    hex::decode_to_slice(s, &mut b).map_err(|_| "32 baytli hex kutilgan".to_string())?;
    Ok(b)
}

impl IdvEventDto {
    pub fn from_request(r: &IdvRequest) -> Self {
        Self {
            at: r.at.unix_timestamp(),
            device: hex::encode(r.device_id.0),
            card: hex::encode(r.pan_fingerprint.0),
            attestation_level: r.attestation_level as u8,
            existing_tokens_for_pan: r.existing_tokens_for_pan,
            existing_tokens_for_device: r.existing_tokens_for_device,
        }
    }

    pub fn to_event(&self) -> Result<ProvisionEvent, String> {
        Ok(ProvisionEvent {
            at: self.at,
            device: hex32(&self.device)?,
            card: hex32(&self.card)?,
            attestation_level: self.attestation_level,
            existing_tokens_for_pan: self.existing_tokens_for_pan,
            existing_tokens_for_device: self.existing_tokens_for_device,
        })
    }
}

impl TxnEventDto {
    pub fn from_request(r: &RiskRequest) -> Self {
        Self {
            at: r.at.unix_timestamp(),
            device: hex::encode(r.device_id.0),
            card: hex::encode(r.pan_fingerprint.0),
            merchant: r.merchant_id.clone(),
            country: r.country,
            amount_minor: r.amount_minor,
            cdcvm: r.cdcvm_performed,
        }
    }

    /// Dvigatel hodisasi (`is_p2p` — Shield instansiyasining qoidalari bo'yicha).
    pub fn to_event(&self, shield: &Shield) -> Result<TxnEvent, String> {
        Ok(TxnEvent {
            at: self.at,
            device: hex32(&self.device)?,
            card: hex32(&self.card)?,
            merchant: self.merchant.clone(),
            country: self.country,
            amount_minor: self.amount_minor,
            cdcvm: self.cdcvm,
            is_p2p: shield.rules().is_p2p(&self.merchant),
        })
    }
}
