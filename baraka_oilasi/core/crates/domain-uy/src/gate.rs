//! 3-qonun: tayyorgarlik darvozasi — «jangga yarador askar yuborilmaydi» (uy/SPEC 2C.4).
use serde::{Deserialize, Serialize};

/// Foizli qarz bo'yicha siyosat. OQ-D4 hal bo'lguncha standart — SPEC dagi qoida.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum InterestDebtPolicy {
    /// SPEC 2C.4: faol foizli qarz bo'lsa ham, chiqish rejasi bo'lsa ochiladi.
    AllowWithPlan,
    /// OQ-D4 taklifi: foizli qarz to'liq yopilmaguncha yopiq.
    BlockUntilPaid,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GatePolicy {
    /// Talab qilinadigan zaxira pul, yuzdan bir oyda (600 = 6 oy).
    pub required_centi_months: i64,
    pub interest_debt: InterestDebtPolicy,
}

impl Default for GatePolicy {
    fn default() -> Self {
        Self {
            required_centi_months: 600,
            interest_debt: InterestDebtPolicy::AllowWithPlan,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GateInput {
    pub coverage_centi_months: i64,
    pub has_interest_debt: bool,
    pub has_payoff_plan: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum GateReason {
    EmergencyFundBelowTarget,
    InterestDebtWithoutPlan,
    InterestDebtActive,
}

impl GateReason {
    pub const fn code(self) -> &'static str {
        match self {
            Self::EmergencyFundBelowTarget => "EMERGENCY_FUND_BELOW_TARGET",
            Self::InterestDebtWithoutPlan => "INTEREST_DEBT_WITHOUT_PLAN",
            Self::InterestDebtActive => "INTEREST_DEBT_ACTIVE",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GateResult {
    pub open: bool,
    /// Ochilish uchun bajarilishi kerak bo'lgan shartlar (bo'sh — darvoza ochiq).
    pub reasons: Vec<GateReason>,
}

pub fn evaluate_gate(input: GateInput, policy: GatePolicy) -> GateResult {
    let mut reasons = Vec::new();
    if input.coverage_centi_months < policy.required_centi_months {
        reasons.push(GateReason::EmergencyFundBelowTarget);
    }
    if input.has_interest_debt {
        match policy.interest_debt {
            InterestDebtPolicy::AllowWithPlan if !input.has_payoff_plan => {
                reasons.push(GateReason::InterestDebtWithoutPlan);
            }
            InterestDebtPolicy::AllowWithPlan => {}
            InterestDebtPolicy::BlockUntilPaid => reasons.push(GateReason::InterestDebtActive),
        }
    }
    GateResult {
        open: reasons.is_empty(),
        reasons,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matrix_default_policy() {
        let p = GatePolicy::default();
        let g = |c, d, plan| {
            evaluate_gate(
                GateInput {
                    coverage_centi_months: c,
                    has_interest_debt: d,
                    has_payoff_plan: plan,
                },
                p,
            )
        };
        assert!(g(600, false, false).open);
        assert!(g(600, true, true).open);
        assert_eq!(
            g(600, true, false).reasons,
            vec![GateReason::InterestDebtWithoutPlan]
        );
        assert_eq!(
            g(599, false, false).reasons,
            vec![GateReason::EmergencyFundBelowTarget]
        );
        assert_eq!(g(140, true, false).reasons.len(), 2);
    }

    #[test]
    fn strict_policy() {
        let p = GatePolicy {
            interest_debt: InterestDebtPolicy::BlockUntilPaid,
            ..GatePolicy::default()
        };
        let r = evaluate_gate(
            GateInput {
                coverage_centi_months: 700,
                has_interest_debt: true,
                has_payoff_plan: true,
            },
            p,
        );
        assert_eq!(r.reasons, vec![GateReason::InterestDebtActive]);
    }
}
