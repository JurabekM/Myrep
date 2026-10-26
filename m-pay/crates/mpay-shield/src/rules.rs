//! Deklarativ qoidalar (TOML). Har qoida — belgilar ustidagi shartlar konyunksiyasi (`all`),
//! ball va ixtiyoriy majburiy harakat. Belgi nomlari yuklashda tekshiriladi.
//!
//! ```toml
//! [[txn_rule]]
//! id = "CARD_VELOCITY_1M"
//! reason = "Karta bo'yicha 1 daqiqada 6+ tranzaksiya"
//! points = 300
//! action = "DECLINE"
//! all = [{ feature = "card_txn_count_1m", op = ">=", value = 6 }]
//! ```

use serde::{Deserialize, Serialize};

use crate::features::{idv_index, txn_index};

/// Taqqoslash operatori.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Op {
    #[serde(rename = ">")]
    Gt,
    #[serde(rename = ">=")]
    Ge,
    #[serde(rename = "<")]
    Lt,
    #[serde(rename = "<=")]
    Le,
    #[serde(rename = "==")]
    Eq,
    #[serde(rename = "!=")]
    Ne,
}

impl Op {
    fn eval(self, a: f32, b: f32) -> bool {
        match self {
            Op::Gt => a > b,
            Op::Ge => a >= b,
            Op::Lt => a < b,
            Op::Le => a <= b,
            Op::Eq => (a - b).abs() < 1e-6,
            Op::Ne => (a - b).abs() >= 1e-6,
        }
    }
}

/// Qoida majburiy harakati.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Action {
    Review,
    Decline,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Condition {
    pub feature: String,
    pub op: Op,
    pub value: f32,
    #[serde(skip)]
    idx: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rule {
    pub id: String,
    pub reason: String,
    pub points: u16,
    #[serde(default)]
    pub action: Option<Action>,
    pub all: Vec<Condition>,
}

impl Rule {
    pub fn matches(&self, f: &[f32]) -> bool {
        self.all.iter().all(|c| c.op.eval(f[c.idx], c.value))
    }
}

/// Chegaralar.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Thresholds {
    /// Tranzaksiya: skor ≥ → REVIEW.
    pub review_at: u16,
    /// Tranzaksiya: skor ≥ → DECLINE.
    pub decline_at: u16,
    /// ID&V: skor ≥ → YELLOW.
    pub idv_yellow_at: u16,
    /// ID&V: skor ≥ → RED.
    pub idv_red_at: u16,
    /// ML ehtimolini ballga aylantirish koeffitsiyenti (`ml_points = p × 1000 × ml_weight`).
    pub ml_weight: f32,
}

/// Merchant toifalari (sandbox: prefiks bo'yicha; production'da MCC).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Merchants {
    #[serde(default)]
    pub p2p_prefixes: Vec<String>,
}

/// Qoidalar to'plami.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuleSet {
    pub version: String,
    pub thresholds: Thresholds,
    #[serde(default)]
    pub merchants: Merchants,
    #[serde(default)]
    pub txn_rule: Vec<Rule>,
    #[serde(default)]
    pub idv_rule: Vec<Rule>,
}

/// Standart qoidalar (binarga joylangan).
pub const DEFAULT_RULES: &str = include_str!("../rules/default.toml");

impl RuleSet {
    /// TOML'dan o'qiydi va belgi nomlarini tekshiradi.
    pub fn parse(text: &str) -> Result<Self, String> {
        let mut rs: RuleSet = toml::from_str(text).map_err(|e| format!("qoidalar TOML: {e}"))?;
        let mut ids = std::collections::HashSet::new();
        for (rules, lookup, kind) in [
            (
                &mut rs.txn_rule,
                txn_index as fn(&str) -> Option<usize>,
                "txn_rule",
            ),
            (
                &mut rs.idv_rule,
                idv_index as fn(&str) -> Option<usize>,
                "idv_rule",
            ),
        ] {
            for r in rules.iter_mut() {
                if !ids.insert(r.id.clone()) {
                    return Err(format!("takroriy qoida ID: {}", r.id));
                }
                if r.all.is_empty() {
                    return Err(format!("{kind} {}: shartlar bo'sh", r.id));
                }
                for c in &mut r.all {
                    c.idx = lookup(&c.feature).ok_or_else(|| {
                        format!("{kind} {}: noma'lum belgi `{}`", r.id, c.feature)
                    })?;
                }
            }
        }
        let t = &rs.thresholds;
        if t.review_at >= t.decline_at
            || t.idv_yellow_at >= t.idv_red_at
            || t.decline_at > 1000
            || t.idv_red_at > 1000
        {
            return Err(
                "chegaralar: review_at < decline_at ≤ 1000, idv_yellow_at < idv_red_at ≤ 1000"
                    .into(),
            );
        }
        Ok(rs)
    }

    pub fn default_rules() -> Result<Self, String> {
        Self::parse(DEFAULT_RULES)
    }

    pub fn is_p2p(&self, merchant: &str) -> bool {
        self.merchants
            .p2p_prefixes
            .iter()
            .any(|p| merchant.starts_with(p.as_str()))
    }
}

/// Qoidalar natijasi.
#[derive(Debug, Clone, Default)]
pub struct RuleHits {
    pub points: u32,
    pub action: Option<Action>,
    pub ids: Vec<String>,
}

pub fn evaluate(rules: &[Rule], f: &[f32]) -> RuleHits {
    let mut h = RuleHits::default();
    for r in rules.iter().filter(|r| r.matches(f)) {
        h.points += u32::from(r.points);
        h.action = h.action.max(r.action);
        h.ids.push(r.id.clone());
    }
    h
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_rules_load() {
        let rs = RuleSet::default_rules().unwrap();
        assert!(!rs.txn_rule.is_empty());
        assert!(!rs.idv_rule.is_empty());
        assert!(rs.is_p2p("P2P0000000001"));
    }

    #[test]
    fn validation() {
        let base = "version='t'\n[thresholds]\nreview_at=500\ndecline_at=800\nidv_yellow_at=400\nidv_red_at=750\nml_weight=1.0\n";
        assert!(RuleSet::parse(&format!("{base}[[txn_rule]]\nid='A'\nreason='r'\npoints=1\nall=[{{feature='nope',op='>',value=1}}]")).is_err());
        assert!(RuleSet::parse(&format!(
            "{base}[[txn_rule]]\nid='A'\nreason='r'\npoints=1\nall=[]"
        ))
        .is_err());
        let rs = RuleSet::parse(&format!(
            "{base}[[txn_rule]]\nid='A'\nreason='r'\npoints=7\naction='REVIEW'\nall=[{{feature='card_txn_count_1m',op='>=',value=3}},{{feature='is_p2p',op='==',value=1}}]"
        ))
        .unwrap();
        let mut f = vec![0.0; crate::features::TXN_FEATURES.len()];
        assert_eq!(evaluate(&rs.txn_rule, &f).points, 0);
        f[txn_index("card_txn_count_1m").unwrap()] = 3.0;
        f[txn_index("is_p2p").unwrap()] = 1.0;
        let h = evaluate(&rs.txn_rule, &f);
        assert_eq!((h.points, h.action), (7, Some(Action::Review)));
        assert!(RuleSet::parse(&base.replace("decline_at=800", "decline_at=400")).is_err());
    }
}
