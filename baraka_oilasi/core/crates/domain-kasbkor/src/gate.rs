//! K7 — kengayish darvozasi (SPEC 6.1): beshala shart bajarilsa ochiq; yopiq bo'lsa — sabablar.
//!
//! 1. Biznes zaxirasi ≥ `required_months` × oxirgi to'liq oylar operatsion xarajati o'rtachasi
//!    (`round_half_up`; xarajat 0 — bajarilgan, tarix yo'q — bajarilmagan).
//! 2. Oxirgi 3 «Hisob kuni»da haqiqiy foyda > 0 (3 tadan kam — bajarilmagan).
//! 3. 90+ kunlik nasiya ≤ `max_bad_bp` × jami nasiya.
//! 4. Foizli qarz yo'q yoki qarzdan chiqish rejasi bor (Uy darvozasi qoidasi).
//! 5. Kengayish rejasi yozilgan (CAPEX, uch stsenariy — «Hunardan ishga»).
//!
//! Chegaralar sozlanadi (OQ-K6). Vektorlar: `spec/test-vectors/kk_expansion_gate.json`.
use baraka_money::{round_half_up, Money};

use crate::DomainError;

pub const DEFAULT_RESERVE_MONTHS: u32 = 3;
pub const DEFAULT_MAX_BAD_BP: i64 = 1000;
pub const PROFIT_CLOSES: usize = 3;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum GateCondition {
    Reserve,
    Profit,
    Receivables,
    InterestDebt,
    Plan,
}

impl GateCondition {
    pub const ALL: [Self; 5] = [
        Self::Reserve,
        Self::Profit,
        Self::Receivables,
        Self::InterestDebt,
        Self::Plan,
    ];

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Reserve => "RESERVE",
            Self::Profit => "PROFIT",
            Self::Receivables => "RECEIVABLES",
            Self::InterestDebt => "INTEREST_DEBT",
            Self::Plan => "PLAN",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GateInput {
    pub reserve: Money,
    pub opex_months: Vec<Money>,
    pub required_months: u32,
    /// «Hisob kuni» haqiqiy foydalari, eskisidan yangisiga.
    pub true_profits: Vec<Money>,
    pub receivables: Money,
    pub receivables_90: Money,
    pub max_bad_bp: i64,
    pub has_interest_debt: bool,
    pub has_payoff_plan: bool,
    pub has_plan: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GateResult {
    pub open: bool,
    pub conditions: Vec<(GateCondition, bool)>,
    pub average_opex: Option<Money>,
    pub required_reserve: Option<Money>,
    pub coverage_centi_months: Option<i64>,
    pub bad_debt_bp: i64,
}

impl GateResult {
    pub fn reasons(&self) -> Vec<GateCondition> {
        self.conditions
            .iter()
            .filter(|(_, ok)| !ok)
            .map(|(c, _)| *c)
            .collect()
    }
}

fn ratio(num: i128, den: i128) -> Result<i64, DomainError> {
    i64::try_from(round_half_up(num, den)?).map_err(|_| DomainError::new("OVERFLOW"))
}

pub fn expansion_gate(input: &GateInput) -> Result<GateResult, DomainError> {
    let cur = input.reserve.currency();
    let negative = input.reserve.is_negative()
        || input.receivables.is_negative()
        || input.receivables_90.is_negative()
        || input.opex_months.iter().any(Money::is_negative);
    if negative {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "amount"));
    }
    if !(1..=24).contains(&input.required_months) {
        return Err(DomainError::on("INVALID_MONTHS", "requiredMonths"));
    }
    if !(0..=10_000).contains(&input.max_bad_bp) {
        return Err(DomainError::on("INVALID_BP", "maxBadBp"));
    }
    if input.receivables_90.compare(&input.receivables)?.is_gt() {
        return Err(DomainError::on("INVALID_RECEIVABLES", "receivables90"));
    }
    let (average_opex, required_reserve, coverage, reserve_ok) = if input.opex_months.is_empty() {
        (None, None, None, false)
    } else {
        let total = Money::sum(input.opex_months.iter().copied(), cur)?;
        let n =
            i128::try_from(input.opex_months.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
        let avg = Money::new(ratio(i128::from(total.minor()), n)?, cur);
        let required = Money::new(
            avg.minor()
                .checked_mul(i64::from(input.required_months))
                .ok_or(DomainError::new("OVERFLOW"))?,
            cur,
        );
        if avg.is_zero() {
            (Some(avg), Some(required), None, true)
        } else {
            let coverage = ratio(
                i128::from(input.reserve.minor()) * 100,
                i128::from(avg.minor()),
            )?;
            let ok = !input.reserve.compare(&required)?.is_lt();
            (Some(avg), Some(required), Some(coverage), ok)
        }
    };
    let profit_ok = input.true_profits.len() >= PROFIT_CLOSES
        && input.true_profits[input.true_profits.len() - PROFIT_CLOSES..]
            .iter()
            .all(Money::is_positive);
    let bad_debt_bp = if input.receivables.is_positive() {
        ratio(
            i128::from(input.receivables_90.minor()) * 10_000,
            i128::from(input.receivables.minor()),
        )?
    } else {
        0
    };
    let receivables_ok = i128::from(input.receivables_90.minor()) * 10_000
        <= i128::from(input.max_bad_bp) * i128::from(input.receivables.minor());
    let debt_ok = !input.has_interest_debt || input.has_payoff_plan;
    let conditions = vec![
        (GateCondition::Reserve, reserve_ok),
        (GateCondition::Profit, profit_ok),
        (GateCondition::Receivables, receivables_ok),
        (GateCondition::InterestDebt, debt_ok),
        (GateCondition::Plan, input.has_plan),
    ];
    Ok(GateResult {
        open: conditions.iter().all(|(_, ok)| *ok),
        conditions,
        average_opex,
        required_reserve,
        coverage_centi_months: coverage,
        bad_debt_bp,
    })
}
