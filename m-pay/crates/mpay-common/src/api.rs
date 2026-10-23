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
    },
    Declined {
        idv: IdvAssessment,
    },
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
