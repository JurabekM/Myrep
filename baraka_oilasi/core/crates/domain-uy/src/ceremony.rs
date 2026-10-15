//! 4-qonun: to'y va marosimlarni rejalash (uy/SPEC 2D.8; vektorlar: `ceremony_scenarios`).
//!
//! Qator — bir martalik summa yoki «kishi boshiga × mehmonlar». Har bir qatorning moliyalash
//! manbasi bor. Qarzni to'lash muddati U9 simulyatori (`payoff::payoff_plan`) bilan hisoblanadi:
//! marosim qarzi muddatsiz foizsiz qarz sifatida, faqat oylik ajratma bilan yopiladi.
use baraka_money::{Currency, Money};
use chrono::{Datelike, Months, NaiveDate};

use crate::debt::PlanLine;
use crate::payoff::{payoff_plan, DebtState, PlanDebt, Scheduled, MAX_WINDOWS};
use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum CeremonyKind {
    Toy,
    BeshikToy,
    SunnatToy,
    Maraka,
    Other,
}

impl CeremonyKind {
    pub const ALL: [Self; 5] = [
        Self::Toy,
        Self::BeshikToy,
        Self::SunnatToy,
        Self::Maraka,
        Self::Other,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Toy => "TOY",
            Self::BeshikToy => "BESHIK_TOY",
            Self::SunnatToy => "SUNNAT_TOY",
            Self::Maraka => "MARAKA",
            Self::Other => "OTHER",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum CeremonyStatus {
    Draft,
    /// Qarzsiz o'tkazish yo'llari oilada muhokama qilindi (barcha kattalar belgi qo'ydi).
    Discussed,
    Confirmed,
}

impl CeremonyStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Draft => "DRAFT",
            Self::Discussed => "DISCUSSED",
            Self::Confirmed => "CONFIRMED",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::Draft, Self::Discussed, Self::Confirmed]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum LineKind {
    OneOff,
    PerGuest,
}

impl LineKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::OneOff => "ONE_OFF",
            Self::PerGuest => "PER_GUEST",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::OneOff, Self::PerGuest]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum FundingSource {
    Savings,
    Family,
    /// Kutilayotgan to'yona — aslida kelajakda qaytariladigan ijtimoiy majburiyat (OQ-P1).
    ExpectedGifts,
    Debt,
}

impl FundingSource {
    pub const ALL: [Self; 4] = [Self::Savings, Self::Family, Self::ExpectedGifts, Self::Debt];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Savings => "SAVINGS",
            Self::Family => "FAMILY",
            Self::ExpectedGifts => "EXPECTED_GIFTS",
            Self::Debt => "DEBT",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BudgetLine {
    pub kind: LineKind,
    /// Bir martalik summa yoki kishi boshiga narx.
    pub amount: Money,
    pub source: FundingSource,
}

pub fn line_total(line: &BudgetLine, guests: i64) -> Result<Money, DomainError> {
    if !line.amount.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
    }
    match line.kind {
        LineKind::OneOff => Ok(line.amount),
        LineKind::PerGuest => Ok(line.amount.checked_mul(guests)?),
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ScenarioTotals {
    pub total: Money,
    pub savings: Money,
    pub family: Money,
    pub expected_gifts: Money,
    pub debt: Money,
}

impl ScenarioTotals {
    pub fn by(&self, s: FundingSource) -> Money {
        match s {
            FundingSource::Savings => self.savings,
            FundingSource::Family => self.family,
            FundingSource::ExpectedGifts => self.expected_gifts,
            FundingSource::Debt => self.debt,
        }
    }
}

pub fn scenario_totals(
    lines: &[BudgetLine],
    guests: i64,
    cur: Currency,
) -> Result<ScenarioTotals, DomainError> {
    if guests < 0 {
        return Err(DomainError::on("INVALID_GUESTS", "guests"));
    }
    let zero = Money::zero(cur);
    let mut t = ScenarioTotals {
        total: zero,
        savings: zero,
        family: zero,
        expected_gifts: zero,
        debt: zero,
    };
    for l in lines {
        let v = line_total(l, guests)?;
        let slot = match l.source {
            FundingSource::Savings => &mut t.savings,
            FundingSource::Family => &mut t.family,
            FundingSource::ExpectedGifts => &mut t.expected_gifts,
            FundingSource::Debt => &mut t.debt,
        };
        *slot = slot.checked_add(v)?;
        t.total = t.total.checked_add(v)?;
    }
    Ok(t)
}

/// Marosim qarzini oyiga `monthly` bilan uzish (U9 simulyatori). `Ok(None)` — to'lov 0, qarz
/// hech qachon yopilmaydi; qarz yo'q bo'lsa — `(0, None)`.
pub fn informal_debt_payoff(
    debt: Money,
    start: NaiveDate,
    monthly: Money,
) -> Result<Option<(u32, Option<NaiveDate>)>, DomainError> {
    if !debt.is_positive() {
        return Ok(Some((0, None)));
    }
    if !monthly.is_positive() {
        return Ok(None);
    }
    let first = NaiveDate::from_ymd_opt(start.year(), start.month(), 1)
        .and_then(|d| d.checked_add_months(Months::new(MAX_WINDOWS)))
        .ok_or(DomainError::new("INVALID_DATE"))?;
    let state = Scheduled::new(
        &[PlanLine {
            date: first,
            amount: debt,
        }],
        &[],
    )?;
    let (p, _) = payoff_plan(
        vec![PlanDebt {
            id: String::new(),
            state: DebtState::Scheduled(state),
            fee_bp: 0,
        }],
        start,
        monthly,
    )?;
    Ok(p.into_iter().next().map(|p| (p.months, p.payoff_date)))
}

/// Tasdiqlash qoidasi (uy/SPEC 2D.8): qarz bilan moliyalashtirilgan qator bo'lsa, avval
/// «Buni qarzsiz qanday o'tkazamiz?» oilaviy muhokamasi (`DISCUSSED`) bo'lishi shart.
pub fn check_confirm(status: CeremonyStatus, has_debt: bool) -> Result<(), DomainError> {
    match status {
        CeremonyStatus::Confirmed => Err(DomainError::new("CEREMONY_LOCKED")),
        CeremonyStatus::Draft if has_debt => Err(DomainError::new("DISCUSSION_REQUIRED")),
        _ => Ok(()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn debt_needs_discussion_before_confirm() {
        use CeremonyStatus::*;
        assert_eq!(
            check_confirm(Draft, true).unwrap_err().code,
            "DISCUSSION_REQUIRED"
        );
        assert!(check_confirm(Draft, false).is_ok());
        assert!(check_confirm(Discussed, true).is_ok());
        assert_eq!(
            check_confirm(Confirmed, false).unwrap_err().code,
            "CEREMONY_LOCKED"
        );
    }
}
