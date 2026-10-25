//! HTTP API DTO'lari (`docs/specs/api.md`) — server va client (soft-wallet, terminal) uchun
//! yagona JSON shakli.
//!
//! Maxfiy maydonlar (`pan`, `dpan`, LUK `key`) `Zeroizing<String>` da va `Debug` da yashirilgan.
//! Bu DTO'lar **faqat PQ Link muhrlangan** tanalarda uzatiladi.

use core::fmt;

use serde::{Deserialize, Serialize};
use zeroize::Zeroizing;

use crate::ports::IdvAssessment;
use crate::TokenId;

/// Muhrlangan javob konverti.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope<T> {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<T>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ErrorBody>,
}

impl<T> Envelope<T> {
    pub fn ok(data: T) -> Self {
        Self {
            ok: true,
            data: Some(data),
            error: None,
        }
    }

    pub fn err(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            ok: false,
            data: None,
            error: Some(ErrorBody {
                code: code.into(),
                message: message.into(),
            }),
        }
    }
}

/// Xato tanasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ErrorBody {
    pub code: String,
    pub message: String,
}

/// Ochiq (muhrlanmagan) xato javobi: `{"error": {...}}`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorResponse {
    pub error: ErrorBody,
}

/// `GET /v1/pqlink/identity`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerIdentityDto {
    pub suite: String,
    /// Hex.
    pub ed25519: String,
    /// Hex.
    pub mldsa65: String,
    /// `SHA-256(ed25519 ‖ mldsa65)`, hex.
    pub fingerprint: String,
    /// Kalit almashtirish (P1.6): e'lon qilingan keyingi identifikator va joriy kalitlar tasdig'i.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub next: Option<NextIdentityDto>,
}

/// `POST /v1/devices/rekey` (sealed, ADR-0015): yangi qurilma kaliti attestatsiya zanjiri (DER, hex;
/// challenge = `/v1/pqlink/enroll` nonce'i) va yangi kalit imzosi
/// `"MPAY-PQLINK-V1 device-rekey" ‖ session_id ‖ eski device_id` ustidan (ECDSA P-256, DER, hex).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RekeyRequest {
    pub cert_chain: Vec<String>,
    pub signature: String,
}

/// `POST /v1/devices/rekey` javobi.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RekeyResponse {
    pub device_id: String,
    pub tokens_moved: u64,
}

/// `GET /v1/pqlink/revocations` — oflayn ildiz kaliti imzolagan bekor qilingan identifikatorlar
/// (ADR-0014). Hamma qiymatlar hex.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RevocationsDto {
    /// `mpay-pqlink-revocations/1`.
    pub format: String,
    pub version: u64,
    pub revoked: Vec<String>,
    pub root_ed25519: String,
    pub root_mldsa65: String,
    pub sig_ed25519: String,
    pub sig_mldsa65: String,
}

/// Keyingi server identifikatori: `endorsement_*` — joriy identifikatorning
/// `ROTATION_LABEL ‖ fingerprint` ustidan gibrid imzosi (hex).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NextIdentityDto {
    pub ed25519: String,
    pub mldsa65: String,
    pub fingerprint: String,
    pub endorsement_ed25519: String,
    pub endorsement_mldsa65: String,
}

/// `POST /v1/tokens` so'rovi.
#[derive(Clone, Serialize, Deserialize)]
pub struct ProvisionRequest {
    pub pan: Zeroizing<String>,
    /// YYMM.
    pub expiry: String,
}

impl fmt::Debug for ProvisionRequest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ProvisionRequest")
            .field("expiry", &self.expiry)
            .finish_non_exhaustive()
    }
}

/// LUK.
#[derive(Clone, Serialize, Deserialize)]
pub struct LukDto {
    pub seq: u32,
    /// 16 bayt, hex.
    pub key: Zeroizing<String>,
    pub issued_at: i64,
    pub expires_at: i64,
    pub max_uses: u32,
}

impl fmt::Debug for LukDto {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "LukDto(seq={}, <maxfiy>)", self.seq)
    }
}

/// Token profili (qurilma uchun).
#[derive(Clone, Serialize, Deserialize)]
pub struct TokenProfileDto {
    pub token_id: TokenId,
    pub dpan: Zeroizing<String>,
    pub dpan_expiry: String,
    pub psn: u8,
    pub aid: String,
    pub scheme: String,
    pub luks: Vec<LukDto>,
}

impl fmt::Debug for TokenProfileDto {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("TokenProfileDto")
            .field("token_id", &self.token_id)
            .field("luks", &self.luks.len())
            .finish_non_exhaustive()
    }
}

/// `POST /v1/tokens` javobi.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ProvisionResponse {
    Active {
        #[serde(flatten)]
        profile: TokenProfileDto,
        idv: IdvAssessment,
    },
    PendingIdv {
        token_id: TokenId,
        challenge_id: String,
        otp_expires_at: i64,
        idv: IdvAssessment,
        /// OTP SMS yuborilgan telefon (maskalangan); sandbox kanalida yoki yuborilmasa yo'q.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        otp_sent_to: Option<String>,
    },
    Declined {
        idv: IdvAssessment,
    },
}

/// `POST /v1/tokens/{id}/idv/resend` (sealed) so'rovi va javobi (2-faza P2.1).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OtpResendRequest {
    pub challenge_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OtpResendResponse {
    pub otp_sent_to: String,
}

/// `POST /v1/tokens/{id}/idv/verify` so'rovi.
#[derive(Clone, Serialize, Deserialize)]
pub struct OtpVerifyRequest {
    pub challenge_id: String,
    pub otp: Zeroizing<String>,
}

impl fmt::Debug for OtpVerifyRequest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("OtpVerifyRequest")
            .field("challenge_id", &self.challenge_id)
            .finish_non_exhaustive()
    }
}

/// `POST /v1/tokens/{id}/luks` javobi.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LuksResponse {
    pub luks: Vec<LukDto>,
}

/// Bo'sh so'rov tanasi.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Empty {}

/// `GET /v1/sandbox/otp/{challenge_id}` javobi.
#[derive(Clone, Serialize, Deserialize)]
pub struct SandboxOtp {
    pub challenge_id: String,
    pub otp: Zeroizing<String>,
}

impl fmt::Debug for SandboxOtp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "SandboxOtp({})", self.challenge_id)
    }
}

/// `POST /v1/authorizations` so'rovi (terminal → acquirer shlyuzi).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorizationRequest {
    /// ISO 8583 maydon 41 (≤ 8 belgi).
    pub terminal_id: String,
    /// ISO 8583 maydon 42 (≤ 15 belgi).
    pub merchant_id: String,
    /// System Trace Audit Number (0–999999).
    pub stan: u32,
    /// Karta va terminal ICC teglari (BER-TLV, hex): GPO javobi (`82`, `57`, `5F34`, `5F24`,
    /// `9F36`, `9F26`, `9F27`, `9F10`) + PDOL ma'lumotlari.
    pub icc_data: String,
}

/// `POST /v1/authorizations` javobi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthorizationResponse {
    pub approved: bool,
    /// ISO 8583 maydon 39 (`00`, `05`, `51`, `59`, `91`, `Q1`).
    pub response_code: String,
    /// Ichki sabab kodi (`APPROVED`, `ARQC_MISMATCH`, ...).
    pub reason: String,
    pub stan: u32,
    pub rrn: String,
    pub dpan_masked: String,
    pub amount_minor: u64,
    pub currency: u16,
    /// Emitent autentifikatsiya ma'lumoti `91` = ARPC ‖ ARC (hex) — ARQC to'g'ri bo'lganda.
    pub issuer_auth_data: Option<String>,
    pub risk_score: Option<u16>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ports::IdvDecision;

    #[test]
    fn provision_response_roundtrip_and_redaction() {
        let r = ProvisionResponse::Active {
            profile: TokenProfileDto {
                token_id: TokenId::from_random([1; 16]),
                dpan: Zeroizing::new("9900770000001230".into()),
                dpan_expiry: "2912".into(),
                psn: 0,
                aid: "F04D50415901".into(),
                scheme: "MPAY-AES128-CMAC-V1".into(),
                luks: vec![LukDto {
                    seq: 1,
                    key: Zeroizing::new("00112233445566778899aabbccddeeff".into()),
                    issued_at: 1,
                    expires_at: 2,
                    max_uses: 10,
                }],
            },
            idv: IdvAssessment {
                decision: IdvDecision::Green,
                score: 10,
                reasons: vec![],
            },
        };
        let json = serde_json::to_string(&r).unwrap();
        assert!(json.contains("\"status\":\"ACTIVE\""));
        let back: ProvisionResponse = serde_json::from_str(&json).unwrap();
        let dbg = format!("{back:?}");
        assert!(!dbg.contains("9900770000001230"));
        assert!(!dbg.contains("00112233"));
        let ProvisionResponse::Active { profile, .. } = back else {
            panic!()
        };
        assert_eq!(
            profile.luks[0].key.as_str(),
            "00112233445566778899aabbccddeeff"
        );

        let d: ProvisionResponse = serde_json::from_str(
            r#"{"status":"DECLINED","idv":{"decision":"RED","score":900,"reasons":["X"]}}"#,
        )
        .unwrap();
        assert!(matches!(d, ProvisionResponse::Declined { .. }));
    }
}
