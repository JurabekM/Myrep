//! Shield dvigateli: belgilar → qoidalar → ML → skor (0–1000) va qaror.
//!
//! ```text
//! skor = min(1000, round(p_ml × 1000 × ml_weight + Σ qoida ballari))
//! qaror = max(qoida harakati, chegara bo'yicha qaror)
//! ```

use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use mpay_common::ports::{
    IdvAssessment, IdvDecider, IdvDecision, IdvRequest, PortError, RiskAssessment, RiskDecision,
    RiskRequest, RiskScorer,
};

use crate::features::{FeatureStore, ProvisionEvent, TxnEvent, IDV_FEATURES, TXN_FEATURES};
use crate::model::MlScorer;
use crate::rules::{self, Action, RuleSet};

/// To'liq tranzaksiya bahosi (baholash va diagnostika uchun).
#[derive(Debug, Clone)]
pub struct TxnAssessment {
    pub features: [f32; TXN_FEATURES.len()],
    pub ml_probability: Option<f32>,
    pub rule_points: u32,
    pub score: u16,
    pub decision: RiskDecision,
    pub reasons: Vec<String>,
}

/// To'liq ID&V bahosi.
#[derive(Debug, Clone)]
pub struct IdvDetail {
    pub features: [f32; IDV_FEATURES.len()],
    pub assessment: IdvAssessment,
}

/// Shield dvigateli.
pub struct Shield {
    store: Mutex<FeatureStore>,
    rules: RuleSet,
    ml: Option<Arc<dyn MlScorer>>,
}

impl std::fmt::Debug for Shield {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Shield")
            .field("rules", &self.rules.version)
            .field("ml", &self.ml.as_ref().map(|m| m.version().to_owned()))
            .finish()
    }
}

impl Shield {
    pub fn new(rules: RuleSet, ml: Option<Arc<dyn MlScorer>>) -> Self {
        Self {
            store: Mutex::new(FeatureStore::new()),
            rules,
            ml,
        }
    }

    /// Standart qoidalar va joylangan model bilan.
    pub fn with_defaults() -> Result<Self, String> {
        let ml: Arc<dyn MlScorer> = Arc::new(crate::model::TractScorer::default_model()?);
        Ok(Self::new(RuleSet::default_rules()?, Some(ml)))
    }

    pub fn rules(&self) -> &RuleSet {
        &self.rules
    }

    fn store(&self) -> std::sync::MutexGuard<'_, FeatureStore> {
        self.store
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }

    /// Faqat belgilar (o'qitish uchun replay; omborni yangilaydi).
    pub fn featurize_txn(&self, e: &TxnEvent) -> [f32; TXN_FEATURES.len()] {
        self.store().txn(e)
    }

    /// Tranzaksiyani baholaydi (omborni yangilaydi).
    pub fn assess_txn(&self, e: &TxnEvent) -> TxnAssessment {
        let features = self.store().txn(e);
        let hits = rules::evaluate(&self.rules.txn_rule, &features);
        let ml_probability = self.ml.as_ref().and_then(|m| match m.predict(&features) {
            Ok(p) => Some(p),
            Err(err) => {
                tracing::error!(error = %err, "shield: ML skor xatosi — faqat qoidalar");
                None
            }
        });
        let t = &self.rules.thresholds;
        let ml_points = ml_probability.map_or(0.0, |p| p * 1000.0 * t.ml_weight);
        let score = (ml_points + hits.points as f32).round().clamp(0.0, 1000.0) as u16;
        let by_score = if score >= t.decline_at {
            Some(Action::Decline)
        } else if score >= t.review_at {
            Some(Action::Review)
        } else {
            None
        };
        let decision = match by_score.max(hits.action) {
            Some(Action::Decline) => RiskDecision::Decline,
            Some(Action::Review) => RiskDecision::Review,
            None => RiskDecision::Approve,
        };
        let mut reasons = hits.ids;
        if ml_points >= f32::from(t.review_at) {
            reasons.push("ML_HIGH_RISK".into());
        }
        TxnAssessment {
            features,
            ml_probability,
            rule_points: hits.points,
            score,
            decision,
            reasons,
        }
    }

    /// Provisioning'ni baholaydi (qurilma–karta qirrasini qo'shadi).
    pub fn assess_provision(&self, e: &ProvisionEvent) -> IdvDetail {
        let features = self.store().provision(e);
        let hits = rules::evaluate(&self.rules.idv_rule, &features);
        let t = &self.rules.thresholds;
        let score = hits.points.min(1000) as u16;
        let decision = if score >= t.idv_red_at || hits.action == Some(Action::Decline) {
            IdvDecision::Red
        } else if score >= t.idv_yellow_at || hits.action == Some(Action::Review) {
            IdvDecision::Yellow
        } else {
            IdvDecision::Green
        };
        IdvDetail {
            features,
            assessment: IdvAssessment {
                decision,
                score,
                reasons: hits.ids,
            },
        }
    }

    /// Port so'rovini hodisaga aylantiradi.
    pub fn txn_event(&self, r: &RiskRequest) -> TxnEvent {
        TxnEvent {
            at: r.at.unix_timestamp(),
            device: r.device_id.0,
            card: r.pan_fingerprint.0,
            merchant: r.merchant_id.clone(),
            country: r.country,
            amount_minor: r.amount_minor,
            cdcvm: r.cdcvm_performed,
            is_p2p: self.rules.is_p2p(&r.merchant_id),
        }
    }
}

#[async_trait]
impl RiskScorer for Shield {
    async fn score(&self, req: &RiskRequest) -> Result<RiskAssessment, PortError> {
        let a = self.assess_txn(&self.txn_event(req));
        tracing::info!(
            score = a.score,
            decision = ?a.decision,
            ml = ?a.ml_probability,
            reasons = ?a.reasons,
            "shield: tranzaksiya"
        );
        Ok(RiskAssessment {
            score: a.score,
            decision: a.decision,
            reasons: a.reasons,
        })
    }
}

#[async_trait]
impl IdvDecider for Shield {
    async fn decide(&self, req: &IdvRequest) -> Result<IdvAssessment, PortError> {
        let d = self.assess_provision(&ProvisionEvent {
            at: req.at.unix_timestamp(),
            device: req.device_id.0,
            card: req.pan_fingerprint.0,
            attestation_level: req.attestation_level as u8,
            existing_tokens_for_pan: req.existing_tokens_for_pan,
            existing_tokens_for_device: req.existing_tokens_for_device,
        });
        tracing::info!(score = d.assessment.score, decision = ?d.assessment.decision, reasons = ?d.assessment.reasons, "shield: ID&V");
        Ok(d.assessment)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rules_only() -> Shield {
        Shield::new(RuleSet::default_rules().unwrap(), None)
    }

    fn tx(at: i64, card: u8, dev: u8, merchant: &str, amount: u64) -> TxnEvent {
        TxnEvent {
            at,
            device: [dev; 32],
            card: [card; 32],
            merchant: merchant.into(),
            country: 860,
            amount_minor: amount,
            cdcvm: false,
            is_p2p: false,
        }
    }

    #[test]
    fn velocity_declines() {
        let s = rules_only();
        let t0 = 1_800_000_000;
        let mut last = None;
        for i in 0..7 {
            last = Some(s.assess_txn(&tx(t0 + i * 5, 1, 1, "SHOP", 5_000_000)));
        }
        let a = last.unwrap();
        assert_eq!(a.decision, RiskDecision::Decline);
        assert!(a.reasons.iter().any(|r| r == "CARD_VELOCITY_1M"));
    }

    #[test]
    fn normal_txn_approved() {
        let s = rules_only();
        let a = s.assess_txn(&tx(1_800_000_000, 1, 1, "SHOP", 5_000_000));
        assert_eq!(a.decision, RiskDecision::Approve);
        assert_eq!(a.score, 0);
    }

    #[test]
    fn idv_device_farm_escalates() {
        let s = rules_only();
        let ev = |c: u8, lvl: u8| ProvisionEvent {
            at: 1_800_000_000 + i64::from(c) * 60,
            device: [9; 32],
            card: [c; 32],
            attestation_level: lvl,
            existing_tokens_for_pan: 0,
            existing_tokens_for_device: u32::from(c),
        };
        let d: Vec<_> = (0..6)
            .map(|c| s.assess_provision(&ev(c, 2)).assessment.decision)
            .collect();
        assert_eq!(&d[..3], &[IdvDecision::Green; 3]);
        assert_eq!(d[3], IdvDecision::Yellow);
        assert_eq!(d[5], IdvDecision::Red);
        let s2 = rules_only();
        assert_eq!(
            s2.assess_provision(&ev(0, 1)).assessment.decision,
            IdvDecision::Yellow
        );
    }
}
