//! 8-tamoyil «O'zingizga sarmoya qiling» (`docs/uy/SPEC.md` 2G): «Bir soatim qancha?», natijani
//! o'lchash, «Sarmoya» ulushi va bilim rejasi qoidalari. Pul — valyutadan mustaqil minor birliklarda
//! (Musofir ish valyutasida ham shu formula).

use baraka_money::round_half_up;
use chrono::{Months, NaiveDate};

use crate::DomainError;

/// Kuniga 600 daqiqadan (10 soat) ko'p — soat chegarasi eslatmasi.
pub const CEIL_DAY_MINUTES: u32 = 600;
/// Oyiga 15 600 daqiqadan (260 soat) ko'p — soat chegarasi eslatmasi.
pub const CEIL_MONTH_MINUTES: u32 = 15_600;
/// Bir a'zoda bir vaqtda faol rejalar chegarasi (2G.2).
pub const MAX_ACTIVE_PLANS: usize = 2;
/// Ko'rik sanasi standarti: boshlanishdan 3 oy keyin.
pub const DEFAULT_REVIEW_MONTHS: u32 = 3;
/// Daromad o'rtachasi uchun ko'pi bilan oxirgi 3 to'liq oy.
pub const AVG_MONTHS: usize = 3;
const SKILL_MAX_CHARS: usize = 120;

fn bp_of(part: i64, whole: i64) -> Result<i64, DomainError> {
    let v = round_half_up(i128::from(part) * 10_000, i128::from(whole))?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

fn to_i64(v: i128) -> Result<i64, DomainError> {
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

// --- 2G.1 «Bir soatim qancha?» ------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum IncomeSource {
    /// Oxirgi to'liq oylar o'rtachasi (ilova taklifi).
    Auto,
    /// Foydalanuvchi kiritgan.
    Manual,
}

impl IncomeSource {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Auto => "AUTO",
            Self::Manual => "MANUAL",
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct HourInput<'a> {
    /// Qo'lda kiritilgan oylik daromad; `None` — `month_totals` o'rtachasi.
    pub income: Option<i64>,
    /// Oxirgi to'liq oylardan yozuvi borlarining jami (ko'pi bilan 3 ta).
    pub month_totals: &'a [i64],
    pub minutes_per_day: u32,
    pub days: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HourValue {
    pub income: i64,
    pub source: IncomeSource,
    pub monthly_minutes: u32,
    pub hour_value: i64,
    pub double_target: i64,
    pub over_ceiling: bool,
}

/// 1 soat qiymati = `round_half_up(daromad × 60 / oylik daqiqalar)`; «ikki barobar maqsad» — 2 ×.
pub fn hour_value(i: &HourInput<'_>) -> Result<HourValue, DomainError> {
    if i.month_totals.len() > AVG_MONTHS {
        return Err(DomainError::new("TOO_MANY_MONTHS"));
    }
    if i.month_totals.iter().any(|t| *t < 0) || i.income.is_some_and(|v| v < 0) {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    if !(1..=1440).contains(&i.minutes_per_day) {
        return Err(DomainError::on("INVALID_TIME", "minutesPerDay"));
    }
    if !(1..=31).contains(&i.days) {
        return Err(DomainError::on("INVALID_DAYS", "days"));
    }
    let (income, source) = match i.income {
        Some(v) => (v, IncomeSource::Manual),
        None if i.month_totals.is_empty() => return Err(DomainError::new("NO_INCOME")),
        None => {
            let sum: i128 = i.month_totals.iter().map(|t| i128::from(*t)).sum();
            let n =
                i128::try_from(i.month_totals.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
            (to_i64(round_half_up(sum, n)?)?, IncomeSource::Auto)
        }
    };
    if income == 0 {
        return Err(DomainError::new("NO_INCOME"));
    }
    let minutes = i.minutes_per_day * i.days;
    let hv = to_i64(round_half_up(i128::from(income) * 60, i128::from(minutes))?)?;
    Ok(HourValue {
        income,
        source,
        monthly_minutes: minutes,
        hour_value: hv,
        double_target: hv.checked_mul(2).ok_or(DomainError::new("OVERFLOW"))?,
        over_ceiling: i.minutes_per_day > CEIL_DAY_MINUTES || minutes > CEIL_MONTH_MINUTES,
    })
}

// --- 2G.5 Natijani o'lchash -----------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HourChange {
    pub diff: i64,
    /// Boshlang'ich 0 bo'lsa — `None`.
    pub change_bp: Option<i64>,
}

pub fn hour_value_change(base: i64, new: i64) -> Result<HourChange, DomainError> {
    if base < 0 || new < 0 {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    let diff = new - base;
    Ok(HourChange {
        diff,
        change_bp: if base == 0 {
            None
        } else {
            Some(bp_of(diff, base)?)
        },
    })
}

// --- 2G.3 «Sarmoya» ulushi ------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InvestShare {
    pub total: i64,
    /// Oy daromadi 0 bo'lsa — `None`.
    pub share_bp: Option<i64>,
}

pub fn self_invest_share(income: i64, amounts: &[i64]) -> Result<InvestShare, DomainError> {
    if income < 0 {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    if amounts.iter().any(|a| *a <= 0) {
        return Err(DomainError::new("AMOUNT_NOT_POSITIVE"));
    }
    let total = amounts
        .iter()
        .try_fold(0i64, |acc, a| acc.checked_add(*a))
        .ok_or(DomainError::new("OVERFLOW"))?;
    Ok(InvestShare {
        total,
        share_bp: if income == 0 {
            None
        } else {
            Some(bp_of(total, income)?)
        },
    })
}

// --- 2G.2 Bilim rejasi ------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PlanStatus {
    Active,
    Paused,
    Done,
    Dropped,
}

impl PlanStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Active => "ACTIVE",
            Self::Paused => "PAUSED",
            Self::Done => "DONE",
            Self::Dropped => "DROPPED",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "ACTIVE" => Some(Self::Active),
            "PAUSED" => Some(Self::Paused),
            "DONE" => Some(Self::Done),
            "DROPPED" => Some(Self::Dropped),
            _ => None,
        }
    }

    /// Yopilgan reja (`DONE`, `DROPPED`) qayta ochilmaydi.
    pub const fn can_become(self, to: Self) -> bool {
        matches!(
            (self, to),
            (Self::Active, Self::Paused | Self::Done | Self::Dropped)
                | (Self::Paused, Self::Active | Self::Done | Self::Dropped)
        )
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum PathKind {
    Book,
    Mentor,
    Course,
    Practice,
}

impl PathKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Book => "BOOK",
            Self::Mentor => "MENTOR",
            Self::Course => "COURSE",
            Self::Practice => "PRACTICE",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "BOOK" => Some(Self::Book),
            "MENTOR" => Some(Self::Mentor),
            "COURSE" => Some(Self::Course),
            "PRACTICE" => Some(Self::Practice),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanDraft {
    pub skill: String,
    pub paths: Vec<PathKind>,
    /// Byudjet (minor birlik); ixtiyoriy.
    pub budget: Option<i64>,
    pub weekly_minutes: u32,
    pub start: NaiveDate,
    /// `None` — boshlanishdan 3 oy keyin.
    pub review: Option<NaiveDate>,
}

/// Tekshirilgan reja: yo'llar tartiblangan va takrorsiz, ko'rik sanasi aniqlangan.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ValidPlan {
    pub skill: String,
    pub paths: Vec<PathKind>,
    pub budget: Option<i64>,
    pub weekly_minutes: u32,
    pub start: NaiveDate,
    pub review: NaiveDate,
}

pub fn validate_plan(d: &PlanDraft) -> Result<ValidPlan, DomainError> {
    let skill = d.skill.trim();
    if skill.is_empty() {
        return Err(DomainError::on("SKILL_REQUIRED", "skill"));
    }
    if skill.chars().count() > SKILL_MAX_CHARS {
        return Err(DomainError::on("SKILL_TOO_LONG", "skill"));
    }
    let mut paths = d.paths.clone();
    paths.sort_unstable();
    paths.dedup();
    if paths.is_empty() {
        return Err(DomainError::on("PATH_REQUIRED", "paths"));
    }
    if d.budget.is_some_and(|b| b < 0) {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "budget"));
    }
    if !(1..=10_080).contains(&d.weekly_minutes) {
        return Err(DomainError::on("INVALID_TIME", "weeklyMinutes"));
    }
    let review = match d.review {
        Some(r) => r,
        None => d
            .start
            .checked_add_months(Months::new(DEFAULT_REVIEW_MONTHS))
            .ok_or(DomainError::on("INVALID_DATE", "start"))?,
    };
    if review <= d.start {
        return Err(DomainError::on("INVALID_REVIEW_DATE", "review"));
    }
    Ok(ValidPlan {
        skill: skill.to_owned(),
        paths,
        budget: d.budget,
        weekly_minutes: d.weekly_minutes,
        start: d.start,
        review,
    })
}

/// Yangi reja ochish yoki `PAUSED → ACTIVE`: a'zoning boshqa faol rejalari soni chegarada bo'lsa — rad.
pub fn check_activation(other_active: usize) -> Result<(), DomainError> {
    if other_active >= MAX_ACTIVE_PLANS {
        Err(DomainError::new("ACTIVE_PLAN_LIMIT"))
    } else {
        Ok(())
    }
}

/// Holat o'tishi: ruxsat etilmagan o'tish — `INVALID_TRANSITION`; faollashtirishda chegara tekshiriladi.
pub fn transition(
    from: PlanStatus,
    to: PlanStatus,
    other_active: usize,
) -> Result<PlanStatus, DomainError> {
    if !from.can_become(to) {
        return Err(DomainError::new("INVALID_TRANSITION"));
    }
    if to == PlanStatus::Active {
        check_activation(other_active)?;
    }
    Ok(to)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    fn draft() -> PlanDraft {
        PlanDraft {
            skill: "  Buxgalteriya dasturi  ".into(),
            paths: vec![PathKind::Course, PathKind::Book, PathKind::Course],
            budget: Some(150_000_000),
            weekly_minutes: 240,
            start: d("2026-11-30"),
            review: None,
        }
    }

    #[test]
    fn hour_value_manual() {
        let h = hour_value(&HourInput {
            income: Some(720_000_000),
            month_totals: &[],
            minutes_per_day: 600,
            days: 26,
        })
        .unwrap();
        assert_eq!((h.hour_value, h.double_target), (2_769_231, 5_538_462));
        assert_eq!(h.source, IncomeSource::Manual);
        assert!(!h.over_ceiling);
    }

    #[test]
    fn hour_value_auto_and_errors() {
        let h = hour_value(&HourInput {
            income: None,
            month_totals: &[600_000_000, 750_000_000, 900_000_000],
            minutes_per_day: 480,
            days: 22,
        })
        .unwrap();
        assert_eq!((h.income, h.source), (750_000_000, IncomeSource::Auto));
        let none = HourInput {
            income: None,
            month_totals: &[],
            minutes_per_day: 480,
            days: 22,
        };
        assert_eq!(hour_value(&none).unwrap_err().code, "NO_INCOME");
        let zero_time = HourInput {
            income: Some(1),
            minutes_per_day: 0,
            ..none
        };
        assert_eq!(hour_value(&zero_time).unwrap_err().code, "INVALID_TIME");
    }

    #[test]
    fn change_and_share() {
        assert_eq!(
            hour_value_change(3_076_923, 6_153_846).unwrap().change_bp,
            Some(10_000)
        );
        assert_eq!(hour_value_change(0, 5).unwrap().change_bp, None);
        assert_eq!(
            hour_value_change(3_076_923, 2_800_000).unwrap().diff,
            -276_923
        );
        let s = self_invest_share(720_000_000, &[12_000_000, 45_000_000]).unwrap();
        assert_eq!((s.total, s.share_bp), (57_000_000, Some(792)));
        assert_eq!(self_invest_share(0, &[1]).unwrap().share_bp, None);
        assert_eq!(
            self_invest_share(1, &[0]).unwrap_err().code,
            "AMOUNT_NOT_POSITIVE"
        );
    }

    #[test]
    fn plan_validation_defaults_review_and_dedups_paths() {
        let p = validate_plan(&draft()).unwrap();
        assert_eq!(p.skill, "Buxgalteriya dasturi");
        assert_eq!(p.paths, vec![PathKind::Book, PathKind::Course]);
        // 30-noyabr + 3 oy — fevral oxiri.
        assert_eq!(p.review, d("2027-02-28"));
    }

    #[test]
    fn plan_validation_errors() {
        let mut x = draft();
        x.skill = "   ".into();
        assert_eq!(validate_plan(&x).unwrap_err().code, "SKILL_REQUIRED");
        let mut x = draft();
        x.paths.clear();
        assert_eq!(validate_plan(&x).unwrap_err().code, "PATH_REQUIRED");
        let mut x = draft();
        x.budget = Some(-1);
        assert_eq!(validate_plan(&x).unwrap_err().code, "AMOUNT_NEGATIVE");
        let mut x = draft();
        x.weekly_minutes = 0;
        assert_eq!(validate_plan(&x).unwrap_err().code, "INVALID_TIME");
        let mut x = draft();
        x.review = Some(x.start);
        assert_eq!(validate_plan(&x).unwrap_err().code, "INVALID_REVIEW_DATE");
        let mut x = draft();
        x.skill = "a".repeat(121);
        assert_eq!(validate_plan(&x).unwrap_err().code, "SKILL_TOO_LONG");
    }

    #[test]
    fn active_limit_applies_to_open_and_resume() {
        assert!(check_activation(1).is_ok());
        assert_eq!(check_activation(2).unwrap_err().code, "ACTIVE_PLAN_LIMIT");
        // Ikkita faol reja bor: to'xtatilganini qayta faollashtirib bo'lmaydi.
        assert_eq!(
            transition(PlanStatus::Paused, PlanStatus::Active, 2)
                .unwrap_err()
                .code,
            "ACTIVE_PLAN_LIMIT"
        );
        assert_eq!(
            transition(PlanStatus::Paused, PlanStatus::Active, 1),
            Ok(PlanStatus::Active)
        );
        // To'xtatish chegarani tekshirmaydi.
        assert_eq!(
            transition(PlanStatus::Active, PlanStatus::Paused, 5),
            Ok(PlanStatus::Paused)
        );
    }

    #[test]
    fn closed_plans_stay_closed() {
        for from in [PlanStatus::Done, PlanStatus::Dropped] {
            for to in [
                PlanStatus::Active,
                PlanStatus::Paused,
                PlanStatus::Done,
                PlanStatus::Dropped,
            ] {
                assert_eq!(
                    transition(from, to, 0).unwrap_err().code,
                    "INVALID_TRANSITION"
                );
            }
        }
        assert!(!PlanStatus::Active.can_become(PlanStatus::Active));
    }
}
