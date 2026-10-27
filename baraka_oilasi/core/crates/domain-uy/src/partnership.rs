//! 5-qonun: mudoraba va musharaka bo'yicha foyda/zarar taqsimoti (uy/SPEC 2E.1).
//!
//! Ochiq savollar: OQ-D1 (zararni keyingi foydadan qoplash) ulamo qaroridan keyin qo'shiladi;
//! OQ-D2 (Hanafiy: ishlamaydigan sherik ulushi) hozircha faqat ogohlantirish
//! (`SILENT_PARTNER_SHARE_ABOVE_CAPITAL`). Vektorlar: `profit_distribution`, `partnership_rules`,
//! `buyout_schedule`.
use std::collections::BTreeSet;

use baraka_money::{allocate, allocate_minor, percent_of, round_half_up, Currency, Money, BP_ONE};
use chrono::{Months, NaiveDate};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PartnershipKind {
    Mudaraba,
    Musharaka,
}

impl PartnershipKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Mudaraba => "MUDARABA",
            Self::Musharaka => "MUSHARAKA",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::Mudaraba, Self::Musharaka]
            .into_iter()
            .find(|k| k.as_str() == s)
    }

    /// Tur bo'yicha zarar qoidasi (2E.1) — ustada avtomatik qo'yiladi.
    pub const fn loss_rule(self) -> LossRule {
        match self {
            Self::Mudaraba => LossRule::CapitalProviderBears,
            Self::Musharaka => LossRule::ProportionalToCapital,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PartnerRole {
    CapitalProvider,
    Worker,
    Both,
}

impl PartnerRole {
    pub const fn provides_capital(self) -> bool {
        matches!(self, Self::CapitalProvider | Self::Both)
    }

    pub const fn works(self) -> bool {
        matches!(self, Self::Worker | Self::Both)
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CapitalProvider => "CAPITAL_PROVIDER",
            Self::Worker => "WORKER",
            Self::Both => "BOTH",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::CapitalProvider, Self::Worker, Self::Both]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

/// Zarar qoidasi (kelishuvning 5-savoli). Satr ko'rinishi `baraka_agreements::LossRuleKind` bilan bir xil.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum LossRule {
    CapitalProviderBears,
    ProportionalToCapital,
    Other,
}

impl LossRule {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CapitalProviderBears => "CAPITAL_PROVIDER_BEARS",
            Self::ProportionalToCapital => "PROPORTIONAL_TO_CAPITAL",
            Self::Other => "OTHER",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [
            Self::CapitalProviderBears,
            Self::ProportionalToCapital,
            Self::Other,
        ]
        .into_iter()
        .find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Partner {
    pub id: String,
    pub role: PartnerRole,
    pub profit_share_bp: i64,
    pub capital: Money,
}

/// Mudorabada ishchining beparvoligi yoki shart buzilishi — izoh majburiy.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Negligence {
    pub partner_id: String,
    pub note: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DistributionInput {
    pub kind: PartnershipKind,
    /// Davr natijasi: musbat — foyda, manfiy — zarar.
    pub result: Money,
    pub partners: Vec<Partner>,
    pub negligence: Option<Negligence>,
    /// Kafolatli (qat'iy) daromad urinishini ifodalaydi — har doim rad etiladi.
    pub fixed_return: Option<Money>,
}

fn by_capital(
    total: Money,
    partners: &[Partner],
    eligible: impl Fn(&Partner) -> bool,
) -> Result<Vec<Money>, DomainError> {
    let ratios: Vec<i64> = partners
        .iter()
        .map(|p| {
            if eligible(p) {
                p.capital.minor().max(0)
            } else {
                0
            }
        })
        .collect();
    if ratios.iter().all(|r| *r == 0) {
        return Err(DomainError::on("NO_CAPITAL", "capital"));
    }
    Ok(allocate(total, &ratios)?)
}

/// Har bir sherikka tushadigan ulush (zararda — manfiy), `partners` tartibida.
pub fn distribute(input: &DistributionInput) -> Result<Vec<Money>, DomainError> {
    if input.fixed_return.is_some() {
        return Err(DomainError::on(
            "GUARANTEED_RETURN_FORBIDDEN",
            "fixed_return",
        ));
    }
    if input.partners.len() < 2 {
        return Err(DomainError::on("MIN_TWO_PARTNERS", "partners"));
    }
    for p in &input.partners {
        input.result.compare(&p.capital)?;
        if p.capital.is_negative() {
            return Err(DomainError::on("CAPITAL_NEGATIVE", "capital"));
        }
    }
    let shares: Vec<i64> = input.partners.iter().map(|p| p.profit_share_bp).collect();
    if shares.iter().any(|s| *s < 0) || shares.iter().sum::<i64>() != BP_ONE {
        return Err(DomainError::on("PROFIT_SHARES_NOT_100", "profit_share_bp"));
    }
    if !input.result.is_negative() {
        return Ok(allocate(input.result, &shares)?);
    }
    match input.kind {
        PartnershipKind::Musharaka => by_capital(input.result, &input.partners, |_| true),
        PartnershipKind::Mudaraba => match &input.negligence {
            Some(n) => {
                if n.note.trim().is_empty() {
                    return Err(DomainError::on("NEGLIGENCE_NOTE_REQUIRED", "negligence"));
                }
                let found = input
                    .partners
                    .iter()
                    .any(|p| p.id == n.partner_id && p.role == PartnerRole::Worker);
                if !found {
                    return Err(DomainError::on("NEGLIGENCE_PARTY_NOT_WORKER", "negligence"));
                }
                let ratios: Vec<i64> = input
                    .partners
                    .iter()
                    .map(|p| i64::from(p.id == n.partner_id))
                    .collect();
                Ok(allocate(input.result, &ratios)?)
            }
            None => by_capital(input.result, &input.partners, |p| p.role.provides_capital()),
        },
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum CapitalKind {
    Money,
    /// Narxlangan uskuna (tikuv mashinasi, asbob) — narxi tomonlar kelishgan qiymat.
    Equipment,
}

impl CapitalKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Money => "MONEY",
            Self::Equipment => "EQUIPMENT",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::Money, Self::Equipment]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CapitalItem {
    pub kind: CapitalKind,
    pub description: String,
    pub amount: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PartnerTerms {
    pub role: PartnerRole,
    pub profit_share_bp: i64,
    pub capital_items: Vec<CapitalItem>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RulesInput {
    pub kind: PartnershipKind,
    pub currency: Currency,
    pub partners: Vec<PartnerTerms>,
    /// Kafolatli (qat'iy) daromad urinishi — har doim xato.
    pub fixed_return: Option<Money>,
    pub loss_rule: LossRule,
    pub duration_months: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RulesResult {
    /// Kod bo'yicha tartiblangan; bo'sh bo'lmasa shartnomani imzolab bo'lmaydi.
    pub errors: Vec<&'static str>,
    pub warnings: Vec<&'static str>,
    /// Har bir sherikning kapitali (musbat bandlar yig'indisi).
    pub capital: Vec<Money>,
    /// Zarar ulushlari (bp); xato bo'lsa — `None`.
    pub loss_share_bp: Option<Vec<i64>>,
}

/// Sheriklik shartlari (uy/SPEC 2E.1). Usta barcha xatolarni birdan ko'rsatishi uchun birinchi
/// xatoda to'xtamaydi. Vektor: `partnership_rules`.
pub fn check_rules(input: &RulesInput) -> Result<RulesResult, DomainError> {
    use PartnerRole::{Both, CapitalProvider, Worker};
    let mut errors = BTreeSet::new();
    let mut warnings = BTreeSet::new();
    let zero = Money::zero(input.currency);
    let mut caps = Vec::with_capacity(input.partners.len());
    for p in &input.partners {
        let mut cap = zero;
        for item in &p.capital_items {
            if item.amount.is_positive() {
                cap = cap.checked_add(item.amount)?;
            } else {
                zero.compare(&item.amount)?;
                errors.insert("CAPITAL_ITEM_NOT_POSITIVE");
            }
        }
        caps.push(cap);
    }
    if input.partners.len() < 2 {
        errors.insert("MIN_TWO_PARTNERS");
    }
    let shares: Vec<i64> = input.partners.iter().map(|p| p.profit_share_bp).collect();
    if shares.iter().any(|s| *s < 0) || shares.iter().sum::<i64>() != BP_ONE {
        errors.insert("PROFIT_SHARES_NOT_100");
    }
    if let Some(f) = input.fixed_return {
        zero.compare(&f)?;
        errors.insert("GUARANTEED_RETURN_FORBIDDEN");
    }
    let rc: Vec<(PartnerRole, i64)> = input
        .partners
        .iter()
        .zip(&caps)
        .map(|(p, c)| (p.role, c.minor()))
        .collect();
    if rc.iter().any(|(r, c)| *r != Worker && *c == 0) {
        errors.insert("CAPITAL_PROVIDER_WITHOUT_CAPITAL");
    }
    match input.kind {
        PartnershipKind::Mudaraba => {
            if !rc.iter().any(|(r, c)| *r == CapitalProvider && *c > 0) {
                errors.insert("MUDARABA_CAPITAL_PROVIDER_REQUIRED");
            }
            if !rc.iter().any(|(r, _)| *r == Worker) {
                errors.insert("MUDARABA_WORKER_REQUIRED");
            }
            if rc.iter().any(|(r, _)| *r == Both) {
                errors.insert("MUDARABA_BOTH_ROLE");
            }
            if rc.iter().any(|(r, c)| *r == Worker && *c > 0) {
                errors.insert("MUDARABA_WORKER_CAPITAL");
            }
        }
        PartnershipKind::Musharaka => {
            if rc.iter().filter(|(_, c)| *c > 0).count() < 2 {
                errors.insert("MUSHARAKA_TWO_CAPITALS_REQUIRED");
            }
            let total: i128 = rc.iter().map(|(_, c)| i128::from(*c)).sum();
            let silent_above = rc.iter().zip(&shares).any(|((r, c), s)| {
                *r == CapitalProvider
                    && i128::from(*s) * total > i128::from(*c) * i128::from(BP_ONE)
            });
            if total > 0 && silent_above {
                warnings.insert("SILENT_PARTNER_SHARE_ABOVE_CAPITAL");
            }
        }
    }
    if input.loss_rule != input.kind.loss_rule() {
        errors.insert("LOSS_RULE_MISMATCH");
    }
    if !input
        .duration_months
        .is_some_and(|m| (1..=600).contains(&m))
    {
        errors.insert("TERM_REQUIRED");
    }
    let loss_share_bp = if errors.is_empty() {
        let ratios: Vec<i64> = rc
            .iter()
            .map(|(r, c)| match input.kind {
                PartnershipKind::Musharaka => *c,
                PartnershipKind::Mudaraba if *r == CapitalProvider => *c,
                PartnershipKind::Mudaraba => 0,
            })
            .collect();
        Some(allocate_minor(BP_ONE, &ratios)?)
    } else {
        None
    };
    Ok(RulesResult {
        errors: errors.into_iter().collect(),
        warnings: warnings.into_iter().collect(),
        capital: caps,
        loss_share_bp,
    })
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BuyoutInput {
    /// Sotuvchining butun ulushi (kapitali).
    pub stake: Money,
    pub total_capital: Money,
    pub buyer_capital: Money,
    pub units: u32,
    pub units_per_period: u32,
    pub start: NaiveDate,
    pub period_months: u32,
    /// Davr uchun taxminiy sof foyda — to'lov xaridor ulushidan oshadimi, shuni ko'rsatish uchun.
    pub expected_profit: Option<Money>,
    pub buyer_share_bp: i64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BuyoutRow {
    pub period: u32,
    pub date: NaiveDate,
    pub units: u32,
    pub payment: Money,
    pub remaining_stake: Money,
    pub seller_bp: i64,
    pub buyer_bp: i64,
    pub exceeds_share: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BuyoutSchedule {
    pub rows: Vec<BuyoutRow>,
    pub buyer_profit: Option<Money>,
}

impl BuyoutSchedule {
    pub fn end_date(&self) -> Option<NaiveDate> {
        self.rows.last().map(|r| r.date)
    }
}

pub const MAX_BUYOUT_UNITS: u32 = 600;

fn bp_of(part: i64, total: i64) -> Result<i64, DomainError> {
    let v = round_half_up(i128::from(part) * i128::from(BP_ONE), i128::from(total))?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

/// Kamayib boruvchi musharaka (uy/SPEC 2E.2): sotuvchi ulushi `units` ta teng birlikka bo'linadi
/// (largest remainder), xaridor har `period_months` oyda `units_per_period` birlik oladi.
/// Narx — taxminiy: har birlik sotilgan kuni baholanadi (kapitalga kafolat yo'q, OQ-D6).
pub fn buyout_schedule(input: &BuyoutInput) -> Result<BuyoutSchedule, DomainError> {
    let BuyoutInput {
        stake,
        total_capital,
        buyer_capital,
        ..
    } = *input;
    stake.compare(&total_capital)?;
    stake.compare(&buyer_capital)?;
    if !stake.is_positive() {
        return Err(DomainError::on("STAKE_NOT_POSITIVE", "stake"));
    }
    if buyer_capital.is_negative()
        || stake.checked_add(buyer_capital)?.minor() > total_capital.minor()
    {
        return Err(DomainError::on("STAKE_EXCEEDS_CAPITAL", "stake"));
    }
    if !(1..=MAX_BUYOUT_UNITS).contains(&input.units) {
        return Err(DomainError::on("INVALID_UNITS", "units"));
    }
    if !(1..=input.units).contains(&input.units_per_period) {
        return Err(DomainError::on(
            "INVALID_UNITS_PER_PERIOD",
            "unitsPerPeriod",
        ));
    }
    if !(1..=12).contains(&input.period_months) {
        return Err(DomainError::on("INVALID_PERIOD", "periodMonths"));
    }
    let buyer_profit = match input.expected_profit {
        None => None,
        Some(p) => {
            stake.compare(&p)?;
            if p.is_negative() {
                return Err(DomainError::on("INVALID_PROFIT", "expectedProfit"));
            }
            Some(percent_of(p, input.buyer_share_bp)?)
        }
    };
    let n = usize::try_from(input.units).map_err(|_| DomainError::new("OVERFLOW"))?;
    let prices = allocate(stake, &vec![1; n])?;
    let total = total_capital.minor();
    let mut rows = Vec::new();
    let mut bought = Money::zero(stake.currency());
    let mut taken = 0_usize;
    let per = usize::try_from(input.units_per_period).map_err(|_| DomainError::new("OVERFLOW"))?;
    while taken < n {
        let k = per.min(n - taken);
        let payment = Money::sum(prices[taken..taken + k].iter().copied(), stake.currency())?;
        taken += k;
        bought = bought.checked_add(payment)?;
        let period = u32::try_from(rows.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
        let date = input
            .start
            .checked_add_months(Months::new(period * input.period_months))
            .ok_or(DomainError::new("INVALID_DATE"))?;
        let remaining = stake.checked_sub(bought)?;
        rows.push(BuyoutRow {
            period: period + 1,
            date,
            units: u32::try_from(k).map_err(|_| DomainError::new("OVERFLOW"))?,
            payment,
            remaining_stake: remaining,
            seller_bp: bp_of(remaining.minor(), total)?,
            buyer_bp: bp_of(buyer_capital.checked_add(bought)?.minor(), total)?,
            exceeds_share: buyer_profit.is_some_and(|b| payment.minor() > b.minor()),
        });
    }
    Ok(BuyoutSchedule { rows, buyer_profit })
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    fn mudaraba(result: i64) -> DistributionInput {
        DistributionInput {
            kind: PartnershipKind::Mudaraba,
            result: uzs(result),
            partners: vec![
                Partner {
                    id: "dilshod".into(),
                    role: PartnerRole::CapitalProvider,
                    profit_share_bp: 5000,
                    capital: uzs(800_000_000),
                },
                Partner {
                    id: "feruza".into(),
                    role: PartnerRole::Worker,
                    profit_share_bp: 5000,
                    capital: uzs(0),
                },
            ],
            negligence: None,
            fixed_return: None,
        }
    }

    #[test]
    fn documented_vectors() {
        assert_eq!(
            distribute(&mudaraba(300_000_000)),
            Ok(vec![uzs(150_000_000), uzs(150_000_000)])
        );
        assert_eq!(
            distribute(&mudaraba(-200_000_000)),
            Ok(vec![uzs(-200_000_000), uzs(0)])
        );
        let mush = DistributionInput {
            kind: PartnershipKind::Musharaka,
            result: uzs(-300_000_000),
            partners: vec![
                Partner {
                    id: "a".into(),
                    role: PartnerRole::Both,
                    profit_share_bp: 6000,
                    capital: uzs(600_000_000),
                },
                Partner {
                    id: "b".into(),
                    role: PartnerRole::Both,
                    profit_share_bp: 4000,
                    capital: uzs(200_000_000),
                },
            ],
            negligence: None,
            fixed_return: None,
        };
        assert_eq!(
            distribute(&mush),
            Ok(vec![uzs(-225_000_000), uzs(-75_000_000)])
        );
        let mut fixed = mudaraba(300_000_000);
        fixed.fixed_return = Some(uzs(50_000_000));
        assert_eq!(
            distribute(&fixed).map_err(|e| e.code),
            Err("GUARANTEED_RETURN_FORBIDDEN")
        );
    }

    #[test]
    fn negligence_rules() {
        let mut i = mudaraba(-200_000_000);
        i.negligence = Some(Negligence {
            partner_id: "feruza".into(),
            note: " ".into(),
        });
        assert_eq!(
            distribute(&i).map_err(|e| e.code),
            Err("NEGLIGENCE_NOTE_REQUIRED")
        );
        i.negligence = Some(Negligence {
            partner_id: "feruza".into(),
            note: "shart buzildi".into(),
        });
        assert_eq!(distribute(&i), Ok(vec![uzs(0), uzs(-200_000_000)]));
        i.negligence = Some(Negligence {
            partner_id: "dilshod".into(),
            note: "x".into(),
        });
        assert_eq!(
            distribute(&i).map_err(|e| e.code),
            Err("NEGLIGENCE_PARTY_NOT_WORKER")
        );
    }

    #[test]
    fn shares_must_sum_to_100() {
        let mut i = mudaraba(100);
        i.partners[0].profit_share_bp = 6000;
        assert_eq!(
            distribute(&i).map_err(|e| e.code),
            Err("PROFIT_SHARES_NOT_100")
        );
    }
}
