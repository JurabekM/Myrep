use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum AgreementType {
    Partnership,
    Loan,
    Rent,
    Service,
    Family,
    Other,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum AgreementStatus {
    Draft,
    Signed,
    Active,
    InDispute,
    Closed,
}

/// Savolga javob holati: javob berilgan, asosli ravishda «tegishli emas» yoki hali javobsiz.
#[derive(Clone, Debug, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Answer<T> {
    #[default]
    Unanswered,
    Answered { value: T },
    NotApplicable { reason: String },
}

impl<T> Answer<T> {
    pub fn value(&self) -> Option<&T> {
        match self {
            Self::Answered { value } => Some(value),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Party {
    pub id: String,
    pub full_name: String,
    #[serde(default)]
    pub role: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ContributionKind {
    Money,
    Goods,
    Labor,
    Network,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Contribution {
    pub party_id: String,
    pub kind: ContributionKind,
    pub description: String,
    /// Minor birlikda, string (pul qoidasi).
    #[serde(default)]
    pub amount_minor: Option<String>,
    #[serde(default)]
    pub currency: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Duty {
    pub id: String,
    pub title: String,
    /// Yagona mas'ul tomon. `None` yoki «hamma» qabul qilinmaydi.
    #[serde(default)]
    pub owner_party_id: Option<String>,
    /// «Bajarilmasa» bandi: masalan, «1 kun ichida xabar beradi va o'rniga yechim topadi».
    #[serde(default)]
    pub breach_clause: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfitShare {
    pub party_id: String,
    pub share_bp: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfitRule {
    pub shares: Vec<ProfitShare>,
    /// Qat'iy summa urinishi (so'mda). Sheriklikda taqiqlanadi.
    #[serde(default)]
    pub fixed_amount_minor: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum LossRuleKind {
    /// Mudoraba: moliyaviy zarar kapital egasida (beparvolikdan tashqari).
    CapitalProviderBears,
    /// Musharaka: kapitalga mutanosib.
    ProportionalToCapital,
    Other,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LossRule {
    pub kind: LossRuleKind,
    #[serde(default)]
    pub note: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Custody {
    /// Pul qayerda turadi.
    pub location: String,
    /// Hisobni kim yuritadi.
    pub keeper_party_id: String,
    /// Ikkinchi tomon necha kunda bir ko'radi (standart — 30).
    pub review_every_days: u32,
    /// Jurnalga yozadigan qurilma (6.6).
    #[serde(default)]
    pub keeper_device_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ExitClause {
    pub notice_days: u32,
    pub valuation_method: String,
    pub payout_terms: String,
    #[serde(default)]
    pub asset_split: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Arbiter {
    pub full_name: String,
    #[serde(default)]
    pub role: Option<String>,
    /// Agar hakam tomonlardan birining yozuvi bilan bog'langan bo'lsa — xato.
    #[serde(default)]
    pub party_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Term {
    /// `YYYY-MM-DD`; o'tmishda bo'lishi mumkin (og'zaki kelishuvni yozish).
    pub effective_from: String,
    #[serde(default)]
    pub duration_months: Option<u32>,
    /// Yillik yangilash sanasi.
    pub review_date: String,
}

/// 9 savol bo'yicha kelishuv qoralamasi.
#[derive(Clone, Debug, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgreementDraft {
    pub parties: Answer<Vec<Party>>,
    pub contributions: Answer<Vec<Contribution>>,
    pub duties: Answer<Vec<Duty>>,
    pub profit_rule: Answer<ProfitRule>,
    pub loss_rule: Answer<LossRule>,
    pub custody: Answer<Custody>,
    pub exit_clause: Answer<ExitClause>,
    pub arbiter: Answer<Arbiter>,
    pub term: Answer<Term>,
}
