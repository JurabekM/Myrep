//! Deterministik Shield stub (M3–M4). **Haqiqiy risk baholash emas** — e2e testlar va demo
//! har bir qaror shoxobchasini boshqara olishi uchun.
//!
//! ID&V (provisioning) — FPAN'ning 7–8-raqamlari "stsenariy kodi":
//!
//! | Kod | Qaror |
//! |---|---|
//! | `00`–`79` | GREEN |
//! | `80`–`89` | YELLOW (OTP) |
//! | `90`–`99` | RED |
//!
//! Qo'shimcha: attestatsiya StrongBox'dan past bo'lsa — kamida YELLOW.
//!
//! Avtorizatsiya risk skori — merchant ID prefiksi va summa:
//!
//! | Shart | Qaror |
//! |---|---|
//! | merchant ID `RISKY` bilan boshlanadi | DECLINE (skor 950) |
//! | merchant ID `REVIEW` bilan boshlanadi yoki summa ≥ `review_amount_minor` | REVIEW (skor 600) |
//! | boshqa | APPROVE (skor 50) |

use async_trait::async_trait;
use mpay_common::ports::{
    IdvAssessment, IdvDecider, IdvDecision, IdvRequest, PortError, RiskAssessment, RiskDecision,
    RiskRequest, RiskScorer, SecurityLevel,
};
use serde::{Deserialize, Serialize};

/// Stub sozlamalari.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct StubShieldConfig {
    /// Shu summadan (minor birlik, tiyin) boshlab REVIEW.
    pub review_amount_minor: u64,
}

impl Default for StubShieldConfig {
    fn default() -> Self {
        Self {
            // 50 000 000,00 UZS
            review_amount_minor: 5_000_000_000,
        }
    }
}

/// Deterministik stub.
#[derive(Debug, Clone, Default)]
pub struct StubShield {
    cfg: StubShieldConfig,
}

impl StubShield {
    pub fn new(cfg: StubShieldConfig) -> Self {
        Self { cfg }
    }
}

#[async_trait]
impl IdvDecider for StubShield {
    async fn decide(&self, req: &IdvRequest) -> Result<IdvAssessment, PortError> {
        let digits = req.fpan.expose_digits();
        let scenario: u8 = digits[6..8]
            .parse()
            .map_err(|_| PortError::Internal("PAN".into()))?;
        let mut reasons = vec![format!("STUB_SCENARIO_{scenario:02}")];
        let (mut decision, mut score) = match scenario {
            0..=79 => (IdvDecision::Green, 100),
            80..=89 => (IdvDecision::Yellow, 550),
            _ => (IdvDecision::Red, 950),
        };
        if req.attestation_level < SecurityLevel::StrongBox && decision == IdvDecision::Green {
            decision = IdvDecision::Yellow;
            score = 500;
            reasons.push("ATTESTATION_BELOW_STRONGBOX".into());
        }
        tracing::debug!(decision = ?decision, score, "shield-stub: ID&V");
        Ok(IdvAssessment {
            decision,
            score,
            reasons,
        })
    }
}

#[async_trait]
impl RiskScorer for StubShield {
    async fn score(&self, req: &RiskRequest) -> Result<RiskAssessment, PortError> {
        let (decision, score, reason) = if req.merchant_id.starts_with("RISKY") {
            (RiskDecision::Decline, 950, "STUB_RISKY_MERCHANT")
        } else if req.merchant_id.starts_with("REVIEW")
            || req.amount_minor >= self.cfg.review_amount_minor
        {
            (RiskDecision::Review, 600, "STUB_REVIEW")
        } else {
            (RiskDecision::Approve, 50, "STUB_OK")
        };
        Ok(RiskAssessment {
            score,
            decision,
            reasons: vec![reason.into()],
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use mpay_common::{DeviceId, Pan, PanFingerprint, TokenId};
    use time::OffsetDateTime;

    fn idv_req(prefix: &str, level: SecurityLevel) -> IdvRequest {
        IdvRequest {
            fpan: Pan::from_prefix(prefix).unwrap(),
            pan_fingerprint: PanFingerprint([0; 32]),
            device_id: DeviceId([0; 32]),
            attestation_level: level,
            existing_tokens_for_pan: 0,
            existing_tokens_for_device: 0,
            integrity: None,
            at: OffsetDateTime::UNIX_EPOCH,
        }
    }

    #[tokio::test]
    async fn idv_scenarios() {
        let s = StubShield::default();
        let d = |p: &str| idv_req(p, SecurityLevel::StrongBox);
        assert_eq!(
            s.decide(&d("990001000000001")).await.unwrap().decision,
            IdvDecision::Green
        );
        assert_eq!(
            s.decide(&d("990001800000001")).await.unwrap().decision,
            IdvDecision::Yellow
        );
        assert_eq!(
            s.decide(&d("990001950000001")).await.unwrap().decision,
            IdvDecision::Red
        );
        let tee = idv_req("990001000000001", SecurityLevel::TrustedEnvironment);
        assert_eq!(s.decide(&tee).await.unwrap().decision, IdvDecision::Yellow);
    }

    #[tokio::test]
    async fn risk_rules() {
        let s = StubShield::default();
        let r = |m: &str, amount| RiskRequest {
            token_id: TokenId::from_random([0; 16]),
            device_id: DeviceId([0; 32]),
            pan_fingerprint: PanFingerprint([0; 32]),
            amount_minor: amount,
            currency: 860,
            merchant_id: m.into(),
            terminal_id: "T".into(),
            country: 860,
            atc: 1,
            cdcvm_performed: true,
            at: OffsetDateTime::UNIX_EPOCH,
        };
        assert_eq!(
            s.score(&r("SHOP", 100)).await.unwrap().decision,
            RiskDecision::Approve
        );
        assert_eq!(
            s.score(&r("RISKY01", 100)).await.unwrap().decision,
            RiskDecision::Decline
        );
        assert_eq!(
            s.score(&r("REVIEW1", 100)).await.unwrap().decision,
            RiskDecision::Review
        );
        assert_eq!(
            s.score(&r("SHOP", 5_000_000_000)).await.unwrap().decision,
            RiskDecision::Review
        );
    }
}
