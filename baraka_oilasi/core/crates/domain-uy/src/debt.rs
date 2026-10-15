//! 4-qonun: qarz inventari, to'lov rejasi, haqiqiy narx, oylik yuk va «to'xta va o'yla»
//! (uy/SPEC 2C.7, 2D.3, 2D.5, 2D.6; vektorlar: `debt_plan`, `debt_status`, `debt_load`).
//!
//! Har bir qarzning to'lov rejasi bo'ladi: rejasiz qarz yo'q. Reja to'rt xil tuziladi
//! (`ANNUITY | DIFFERENTIATED | FIXED_MARKUP | MANUAL`), haqiqiy narx esa hamma turda bitta
//! formula: jami narx = ilovagacha to'langan + reja yig'indisi.
use baraka_money::{allocate_minor, round_half_up, Currency, Money};
use chrono::{Months, NaiveDate};

use crate::amortization::{simulate, LoanTerms, ScheduleKind};
use crate::DomainError;

/// Muddati shuncha kun ichida kelsa — xushmuomala eslatma.
pub const DUE_SOON_DAYS: i64 = 3;
/// «To'xta va o'yla»: oylik qarz yuki shundan oshsa — ogohlantirish (30%, OQ-P8).
pub const LOAD_HIGH_BP: i64 = 3_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum CreditorType {
    Bank,
    /// Nasiya daftari.
    Shop,
    Relative,
    Friend,
    Other,
}

impl CreditorType {
    pub const ALL: [Self; 5] = [
        Self::Bank,
        Self::Shop,
        Self::Relative,
        Self::Friend,
        Self::Other,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Bank => "BANK",
            Self::Shop => "SHOP",
            Self::Relative => "RELATIVE",
            Self::Friend => "FRIEND",
            Self::Other => "OTHER",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PlanKind {
    Annuity,
    Differentiated,
    FixedMarkup,
    Manual,
}

impl PlanKind {
    pub const ALL: [Self; 4] = [
        Self::Annuity,
        Self::Differentiated,
        Self::FixedMarkup,
        Self::Manual,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Annuity => "ANNUITY",
            Self::Differentiated => "DIFFERENTIATED",
            Self::FixedMarkup => "FIXED_MARKUP",
            Self::Manual => "MANUAL",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PlanLine {
    pub date: NaiveDate,
    pub amount: Money,
}

/// Reja tuzish uchun kirish. `first_date`: bank turlarida — birinchi to'lov sanasi,
/// `MANUAL` da — qarz boshlangan sana (qatorlar undan oldin bo'lmaydi).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanSpec {
    pub kind: PlanKind,
    pub principal: Money,
    /// `FIXED_MARKUP` va `MANUAL` dagi ustama (jami). Bank turlarida 0 bo'lishi shart.
    pub markup: Money,
    pub annual_bp: i64,
    pub months: u32,
    pub first_date: NaiveDate,
    pub lines: Vec<PlanLine>,
}

impl PlanSpec {
    /// Foizli (ribo) qarzmi: qizil bayroq (uy/SPEC 2D.5).
    pub fn is_ribo(&self) -> bool {
        match self.kind {
            PlanKind::Annuity | PlanKind::Differentiated => self.annual_bp > 0,
            PlanKind::FixedMarkup | PlanKind::Manual => self.markup.is_positive(),
        }
    }
}

fn plus_months(d: NaiveDate, k: u32) -> Result<NaiveDate, DomainError> {
    d.checked_add_months(Months::new(k))
        .ok_or(DomainError::on("INVALID_DATE", "firstDate"))
}

/// To'lov rejasi qatorlari. Rejasiz qarz saqlanmaydi — bo'sh reja xato.
pub fn build_plan(spec: &PlanSpec) -> Result<Vec<PlanLine>, DomainError> {
    let cur = spec.principal.currency();
    if !spec.principal.is_positive() {
        return Err(DomainError::on("PRINCIPAL_NOT_POSITIVE", "principal"));
    }
    if spec.markup.currency() != cur {
        return Err(DomainError::on("CURRENCY_MISMATCH", "markup"));
    }
    if spec.markup.is_negative() {
        return Err(DomainError::on("MARKUP_NEGATIVE", "markup"));
    }
    if spec.kind == PlanKind::Manual {
        if spec.lines.is_empty() {
            return Err(DomainError::on("SCHEDULE_REQUIRED", "schedule"));
        }
        let mut prev = spec.first_date;
        let mut total = Money::zero(cur);
        for l in &spec.lines {
            if l.amount.currency() != cur {
                return Err(DomainError::on("CURRENCY_MISMATCH", "schedule"));
            }
            if !l.amount.is_positive() {
                return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "schedule"));
            }
            if l.date < prev {
                return Err(DomainError::on("SCHEDULE_DATES_ORDER", "schedule"));
            }
            prev = l.date;
            total = total.checked_add(l.amount)?;
        }
        if total != spec.principal.checked_add(spec.markup)? {
            return Err(DomainError::on("SCHEDULE_SUM_MISMATCH", "schedule"));
        }
        return Ok(spec.lines.clone());
    }
    if spec.months == 0 || spec.months > 600 {
        return Err(DomainError::on("INVALID_TERM", "months"));
    }
    let amounts: Vec<i64> = match spec.kind {
        PlanKind::Annuity | PlanKind::Differentiated => {
            if !spec.markup.is_zero() {
                return Err(DomainError::on("MARKUP_NOT_ALLOWED", "markup"));
            }
            let kind = if spec.kind == PlanKind::Annuity {
                ScheduleKind::Annuity
            } else {
                ScheduleKind::Differentiated
            };
            let terms = LoanTerms {
                principal: spec.principal,
                annual_bp: spec.annual_bp,
                months: spec.months,
                kind,
            };
            simulate(&terms, Money::zero(cur))?
                .rows
                .iter()
                .map(|r| r.interest.minor() + r.principal.minor())
                .collect()
        }
        PlanKind::FixedMarkup => {
            if spec.markup.is_zero() {
                return Err(DomainError::on("MARKUP_REQUIRED", "markup"));
            }
            let total = spec.principal.checked_add(spec.markup)?;
            allocate_minor(total.minor(), &vec![1; spec.months as usize])?
        }
        PlanKind::Manual => return Err(DomainError::new("INVALID_PLAN_KIND")),
    };
    amounts
        .into_iter()
        .zip(0u32..)
        .map(|(a, k)| {
            Ok(PlanLine {
                date: plus_months(spec.first_date, k)?,
                amount: Money::new(a, cur),
            })
        })
        .collect()
}

pub fn plan_total(lines: &[PlanLine], currency: Currency) -> Result<Money, DomainError> {
    Ok(Money::sum(lines.iter().map(|l| l.amount), currency)?)
}

fn bp_of(part: Money, whole: Money) -> Result<i64, DomainError> {
    let v = round_half_up(i128::from(part.minor()) * 10_000, i128::from(whole.minor()))?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TrueCostInput {
    /// Reja tuzilgan summa (ilovaga kiritilgan paytdagi qoldiq).
    pub principal: Money,
    /// Dastlab olingan summa; bo'lmasa — `principal`.
    pub original_principal: Option<Money>,
    /// Ilovaga kiritilgunga qadar to'langan.
    pub paid_before: Money,
    pub plan_total: Money,
    /// Ilovada yozilgan to'lovlar.
    pub paid_since: Money,
}

/// «Asosiy summa → Jami to'langan → Ortiqcha to'lov» (uy/SPEC 2D.3).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TrueCost {
    pub original_principal: Money,
    pub total_cost: Money,
    pub overpay: Money,
    /// Ortiqcha to'lovning jami narxdagi ulushi.
    pub overpay_bp: i64,
    pub paid_total: Money,
    pub remaining: Money,
}

pub fn true_cost(i: &TrueCostInput) -> Result<TrueCost, DomainError> {
    let original = i.original_principal.unwrap_or(i.principal);
    if original.compare(&i.principal)?.is_lt() {
        return Err(DomainError::on(
            "ORIGINAL_BELOW_PRINCIPAL",
            "originalPrincipal",
        ));
    }
    if i.paid_before.is_negative() || i.paid_since.is_negative() {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    if i.paid_since.compare(&i.plan_total)?.is_gt() {
        return Err(DomainError::on("PAYMENT_EXCEEDS_REMAINING", "amount"));
    }
    let total_cost = i.paid_before.checked_add(i.plan_total)?;
    let overpay = total_cost.checked_sub(original)?;
    if overpay.is_negative() {
        return Err(DomainError::on("COST_BELOW_PRINCIPAL", "paidBefore"));
    }
    Ok(TrueCost {
        original_principal: original,
        total_cost,
        overpay,
        overpay_bp: bp_of(overpay, total_cost)?,
        paid_total: i.paid_before.checked_add(i.paid_since)?,
        remaining: i.plan_total.checked_sub(i.paid_since)?,
    })
}

/// Imkoniyat narxi: ortiqcha to'lov maqsad summasining necha bp'iga teng (10 000 = 1 marta).
pub fn goal_coverage_bp(overpay: Money, goal_target: Money) -> Result<i64, DomainError> {
    if !goal_target.is_positive() {
        return Err(DomainError::on("INVALID_GOAL", "target"));
    }
    overpay.compare(&goal_target)?;
    bp_of(overpay, goal_target)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reminder {
    DueSoon,
    Overdue,
}

impl Reminder {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::DueSoon => "DUE_SOON",
            Self::Overdue => "OVERDUE",
        }
    }
}

/// To'lovlar reja qatorlariga ketma-ket yoziladi (avval eng erta qator).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PlanStatus {
    pub remaining: Money,
    pub next: Option<PlanLine>,
    pub overdue: Money,
    pub payoff_date: Option<NaiveDate>,
    pub reminder: Option<Reminder>,
}

/// Rejaning hali to'lanmagan qatorlari: odatiy to'lovlar boshidan, muddatidan oldingi
/// to'lovlar oxiridan yopiladi («muddatni qisqartirish» — «Qarzsiz kun» oldinga siljiydi).
pub fn remaining_lines(
    lines: &[PlanLine],
    regular: Money,
    prepaid: Money,
) -> Result<Vec<PlanLine>, DomainError> {
    let cur = regular.currency();
    let total = plan_total(lines, cur)?;
    if regular.is_negative()
        || prepaid.is_negative()
        || regular.checked_add(prepaid)?.compare(&total)?.is_gt()
    {
        return Err(DomainError::on("PAYMENT_EXCEEDS_REMAINING", "amount"));
    }
    let mut out: Vec<PlanLine> = lines.to_vec();
    let mut r = regular.minor();
    for l in out.iter_mut() {
        let take = r.min(l.amount.minor());
        l.amount = Money::new(l.amount.minor() - take, cur);
        r -= take;
    }
    let mut p = prepaid.minor();
    for l in out.iter_mut().rev() {
        let take = p.min(l.amount.minor());
        l.amount = Money::new(l.amount.minor() - take, cur);
        p -= take;
    }
    out.retain(|l| l.amount.is_positive());
    Ok(out)
}

pub fn plan_status(
    lines: &[PlanLine],
    paid: Money,
    prepaid: Money,
    today: NaiveDate,
) -> Result<PlanStatus, DomainError> {
    let cur = paid.currency();
    let rest = remaining_lines(lines, paid, prepaid)?;
    status_of(&rest, today, cur)
}

/// Qolgan qatorlar bo'yicha holat (bank qarzlarida qatorlar prognozdan olinadi).
pub fn status_of(
    rest: &[PlanLine],
    today: NaiveDate,
    cur: Currency,
) -> Result<PlanStatus, DomainError> {
    let next = rest.first().copied();
    let overdue = Money::sum(
        rest.iter().filter(|l| l.date < today).map(|l| l.amount),
        cur,
    )?;
    let remaining = plan_total(rest, cur)?;
    let reminder = if overdue.is_positive() {
        Some(Reminder::Overdue)
    } else {
        next.filter(|n| (n.date - today).num_days() <= DUE_SOON_DAYS)
            .map(|_| Reminder::DueSoon)
    };
    Ok(PlanStatus {
        remaining,
        next,
        overdue,
        payoff_date: rest.last().map(|l| l.date),
        reminder,
    })
}

/// `[from, to)` oralig'idagi reja to'lovlari (oylik qarz yuki uchun).
pub fn due_between(
    lines: &[PlanLine],
    from: NaiveDate,
    to: NaiveDate,
    currency: Currency,
) -> Result<Money, DomainError> {
    Ok(Money::sum(
        lines
            .iter()
            .filter(|l| l.date >= from && l.date < to)
            .map(|l| l.amount),
        currency,
    )?)
}

/// Oylik qarz yuki, bp. Daromad bo'lmasa — `None` (noma'lum).
pub fn debt_load_bp(payments: Money, income: Money) -> Result<Option<i64>, DomainError> {
    payments.compare(&income)?;
    if !income.is_positive() {
        return Ok(None);
    }
    bp_of(payments, income).map(Some)
}

/// «Zaruratmi yoki hashamatmi».
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BorrowNeed {
    Necessity,
    Luxury,
}

impl BorrowNeed {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Necessity => "NECESSITY",
            Self::Luxury => "LUXURY",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::Necessity, Self::Luxury]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

/// Foizsiz muqobillar (uy/SPEC 2D.6).
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Alternative {
    Qorovul,
    Relative,
    SellItem,
}

impl Alternative {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Qorovul => "QOROVUL",
            Self::Relative => "RELATIVE",
            Self::SellItem => "SELL_ITEM",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::Qorovul, Self::Relative, Self::SellItem]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum BorrowWarning {
    /// Foizli qarz — qizil ogohlantirish.
    Ribo,
    Luxury,
    AlternativeAvailable,
    LoadHigh,
    LoadUnknown,
}

impl BorrowWarning {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Ribo => "RIBO",
            Self::Luxury => "LUXURY",
            Self::AlternativeAvailable => "ALTERNATIVE_AVAILABLE",
            Self::LoadHigh => "LOAD_HIGH",
            Self::LoadUnknown => "LOAD_UNKNOWN",
        }
    }
}

/// «To'xta va o'yla»: taqiqlamaydi, faqat ogohlantirishlar ro'yxatini beradi.
pub fn evaluate_borrow(
    need: BorrowNeed,
    alternatives: &[Alternative],
    is_ribo: bool,
    projected_load_bp: Option<i64>,
) -> Vec<BorrowWarning> {
    let mut w = Vec::new();
    if is_ribo {
        w.push(BorrowWarning::Ribo);
    }
    if need == BorrowNeed::Luxury {
        w.push(BorrowWarning::Luxury);
    }
    if !alternatives.is_empty() {
        w.push(BorrowWarning::AlternativeAvailable);
    }
    match projected_load_bp {
        None => w.push(BorrowWarning::LoadUnknown),
        Some(bp) if bp > LOAD_HIGH_BP => w.push(BorrowWarning::LoadHigh),
        Some(_) => {}
    }
    w
}

/// Foydalanuvchi bergan qarz. **Foiz yoki ustama maydoni yo'q** (uy/SPEC 2D.5):
/// `tests::receivable_has_no_interest_field` struktura to'liq ochilganda shuni tekshiradi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Receivable {
    pub debtor: String,
    pub amount: Money,
    pub lent_on: NaiveDate,
    pub lines: Vec<PlanLine>,
}

impl Receivable {
    /// Qaytarish rejasi majburiy va yig'indisi aynan berilgan summaga teng.
    pub fn validate(&self) -> Result<(), DomainError> {
        build_plan(&PlanSpec {
            kind: PlanKind::Manual,
            principal: self.amount,
            markup: Money::zero(self.amount.currency()),
            annual_bp: 0,
            months: 0,
            first_date: self.lent_on,
            lines: self.lines.clone(),
        })
        .map(|_| ())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    #[test]
    fn receivable_has_no_interest_field() {
        let r = Receivable {
            debtor: "Qoʻshni".into(),
            amount: uzs(20_000_000),
            lent_on: d("2026-10-01"),
            lines: vec![PlanLine {
                date: d("2026-10-31"),
                amount: uzs(20_000_000),
            }],
        };
        // To'liq ochish: strukturaga yangi (masalan, foiz) maydon qo'shilsa, bu test kompilyatsiya
        // bo'lmaydi va qaror qayta ko'rib chiqiladi.
        let Receivable {
            debtor: _,
            amount: _,
            lent_on: _,
            lines: _,
        } = r.clone();
        assert!(r.validate().is_ok());
        let more = Receivable {
            lines: vec![PlanLine {
                date: d("2026-10-31"),
                amount: uzs(21_000_000),
            }],
            ..r
        };
        assert_eq!(more.validate().unwrap_err().code, "SCHEDULE_SUM_MISMATCH");
    }

    #[test]
    fn ribo_flag_and_friction() {
        let spec = |kind, bp, markup| PlanSpec {
            kind,
            principal: uzs(100),
            markup: uzs(markup),
            annual_bp: bp,
            months: 2,
            first_date: d("2026-11-01"),
            lines: vec![],
        };
        assert!(spec(PlanKind::Annuity, 2400, 0).is_ribo());
        assert!(!spec(PlanKind::Annuity, 0, 0).is_ribo());
        assert!(spec(PlanKind::FixedMarkup, 0, 10).is_ribo());
        assert!(!spec(PlanKind::Manual, 0, 0).is_ribo());
        assert_eq!(
            evaluate_borrow(
                BorrowNeed::Luxury,
                &[Alternative::Qorovul],
                true,
                Some(3_001)
            ),
            vec![
                BorrowWarning::Ribo,
                BorrowWarning::Luxury,
                BorrowWarning::AlternativeAvailable,
                BorrowWarning::LoadHigh
            ]
        );
        assert!(evaluate_borrow(BorrowNeed::Necessity, &[], false, Some(3_000)).is_empty());
        assert_eq!(
            evaluate_borrow(BorrowNeed::Necessity, &[], false, None),
            vec![BorrowWarning::LoadUnknown]
        );
    }

    #[test]
    fn due_between_and_currency_guard() {
        let lines = [
            PlanLine {
                date: d("2026-10-31"),
                amount: uzs(5),
            },
            PlanLine {
                date: d("2026-11-01"),
                amount: uzs(7),
            },
        ];
        assert_eq!(
            due_between(&lines, d("2026-10-01"), d("2026-11-01"), Currency::Uzs).unwrap(),
            uzs(5)
        );
        assert!(debt_load_bp(uzs(1), Money::new(1, Currency::Usd)).is_err());
        assert!(goal_coverage_bp(uzs(1), uzs(0)).is_err());
    }
}
