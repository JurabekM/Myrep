//! K4 — nasiya (SPEC 5.2): narx savdo paytida qotiriladi; kechikish uchun ustama, jarima yoki foiz
//! **yo'q** — bu turdagi maydon domen modelida umuman yo'q, qoldiq sanaga bog'liq emas.
//!
//! - Nasiya narxi `n` ta oylik to'lovga largest remainder bilan bo'linadi (qoldiq tiyinlar birinchi
//!   to'lovlarga); birinchisi `first_due` da, keyingilari har oy.
//! - Hodisalar sana tartibida: to'lov, kechirish (to'liq yoki qisman), muddatni uzaytirish (yopilmagan
//!   to'lovlar `m` oyga suriladi, summa o'zgarmaydi).
//! - Kechikkan kunlar — eng birinchi yopilmagan va muddati o'tgan to'lov sanasidan; guruhlar
//!   1–30, 31–60, 61–90, 90+ kun.
//!
//! Vektorlar: `spec/test-vectors/kk_credit_sale.json`.
use baraka_money::{allocate, Money};
use chrono::{Months, NaiveDate};

use crate::DomainError;

pub const MAX_INSTALLMENTS: u32 = 120;
pub const MAX_EXTENSION_MONTHS: u32 = 24;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CreditEvent {
    Payment { on: NaiveDate, amount: Money },
    Forgive { on: NaiveDate, amount: Money },
    Extend { on: NaiveDate, months: u32 },
}

impl CreditEvent {
    pub fn on(&self) -> NaiveDate {
        match *self {
            Self::Payment { on, .. } | Self::Forgive { on, .. } | Self::Extend { on, .. } => on,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CreditTerms {
    pub credit_price: Money,
    /// Naqd narx — faqat ma'lumot uchun (farqi — OQ-D5).
    pub cash_price: Option<Money>,
    pub installments: u32,
    pub first_due: NaiveDate,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InstallmentState {
    Paid,
    Overdue,
    Due,
}

impl InstallmentState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Paid => "PAID",
            Self::Overdue => "OVERDUE",
            Self::Due => "DUE",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Installment {
    pub due: NaiveDate,
    pub amount: Money,
    pub covered: Money,
    pub state: InstallmentState,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CreditStatus {
    Settled,
    Current,
    Overdue,
}

impl CreditStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Settled => "SETTLED",
            Self::Current => "CURRENT",
            Self::Overdue => "OVERDUE",
        }
    }
}

/// Kechikish yoshi guruhi (SPEC 5.2).
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum AgingBucket {
    D1To30,
    D31To60,
    D61To90,
    /// «Umidsiz bo'lishi mumkin» (zakot va kengayish darvozasida hisobga olinadi).
    D90Plus,
}

impl AgingBucket {
    pub fn of_days(days: i64) -> Option<Self> {
        Some(match days {
            ..=0 => return None,
            1..=30 => Self::D1To30,
            31..=60 => Self::D31To60,
            61..=90 => Self::D61To90,
            _ => Self::D90Plus,
        })
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::D1To30 => "D1_30",
            Self::D31To60 => "D31_60",
            Self::D61To90 => "D61_90",
            Self::D90Plus => "D90_PLUS",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CreditState {
    pub schedule: Vec<Installment>,
    pub paid: Money,
    pub forgiven: Money,
    pub outstanding: Money,
    pub status: CreditStatus,
    pub overdue_days: i64,
    pub bucket: Option<AgingBucket>,
    /// Navbatdagi yopilmagan to'lov (sana va qolgan summa).
    pub next_due: Option<(NaiveDate, Money)>,
    /// Nasiya narxi − naqd narx (naqd narx berilgan bo'lsa).
    pub credit_markup: Option<Money>,
}

fn add_months(d: NaiveDate, m: u32) -> Result<NaiveDate, DomainError> {
    d.checked_add_months(Months::new(m))
        .ok_or(DomainError::new("INVALID_DATE"))
}

impl CreditTerms {
    pub fn validate(&self) -> Result<(), DomainError> {
        if !self.credit_price.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "creditPrice"));
        }
        if self.cash_price.is_some_and(|c| !c.is_positive()) {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "cashPrice"));
        }
        if !(1..=MAX_INSTALLMENTS).contains(&self.installments) {
            return Err(DomainError::on("INVALID_INSTALLMENTS", "installments"));
        }
        Ok(())
    }

    /// Dastlabki jadval: `(sana, summa)`.
    pub fn schedule(&self) -> Result<Vec<(NaiveDate, Money)>, DomainError> {
        self.validate()?;
        let n = usize::try_from(self.installments)
            .map_err(|_| DomainError::on("INVALID_INSTALLMENTS", "installments"))?;
        let amounts = allocate(self.credit_price, &vec![1; n])?;
        let mut out = Vec::with_capacity(n);
        for (k, a) in (0u32..).zip(amounts) {
            out.push((add_months(self.first_due, k)?, a));
        }
        Ok(out)
    }

    /// `today` dagi holat. Hodisalar sana bo'yicha o'smaydigan tartibda bo'lishi shart.
    pub fn state(
        &self,
        events: &[CreditEvent],
        today: NaiveDate,
    ) -> Result<CreditState, DomainError> {
        let mut rows = self.schedule()?;
        let cur = self.credit_price.currency();
        let (mut paid, mut forgiven) = (Money::zero(cur), Money::zero(cur));
        let mut prev: Option<NaiveDate> = None;
        for e in events {
            if prev.is_some_and(|p| e.on() < p) {
                return Err(DomainError::on("INVALID_DATE", "date"));
            }
            prev = Some(e.on());
            let outstanding = self.credit_price.checked_sub(paid)?.checked_sub(forgiven)?;
            match *e {
                CreditEvent::Payment { amount, .. } | CreditEvent::Forgive { amount, .. } => {
                    if !amount.is_positive() {
                        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
                    }
                    if amount.compare(&outstanding)?.is_gt() {
                        return Err(DomainError::on("EXCEEDS_OUTSTANDING", "amount"));
                    }
                    if matches!(e, CreditEvent::Payment { .. }) {
                        paid = paid.checked_add(amount)?;
                    } else {
                        forgiven = forgiven.checked_add(amount)?;
                    }
                }
                CreditEvent::Extend { months, .. } => {
                    if !(1..=MAX_EXTENSION_MONTHS).contains(&months) {
                        return Err(DomainError::on("INVALID_EXTENSION", "months"));
                    }
                    if outstanding.is_zero() {
                        return Err(DomainError::new("ALREADY_SETTLED"));
                    }
                    let covered = paid.checked_add(forgiven)?;
                    let mut cum = Money::zero(cur);
                    for row in &mut rows {
                        cum = cum.checked_add(row.1)?;
                        if cum.compare(&covered)?.is_gt() {
                            row.0 = add_months(row.0, months)?;
                        }
                    }
                }
            }
        }
        let covered = paid.checked_add(forgiven)?;
        let mut cum = Money::zero(cur);
        let mut schedule = Vec::with_capacity(rows.len());
        let (mut earliest, mut next_due) = (None, None);
        for (due, amount) in rows {
            let c = amount.min(covered.checked_sub(cum)?.clamp_non_negative())?;
            cum = cum.checked_add(amount)?;
            let state = if c == amount {
                InstallmentState::Paid
            } else if due < today {
                earliest = earliest.or(Some(due));
                InstallmentState::Overdue
            } else {
                InstallmentState::Due
            };
            if c != amount && next_due.is_none() {
                next_due = Some((due, amount.checked_sub(c)?));
            }
            schedule.push(Installment {
                due,
                amount,
                covered: c,
                state,
            });
        }
        let outstanding = self.credit_price.checked_sub(covered)?;
        let overdue_days = earliest.map_or(0, |d| (today - d).num_days());
        let status = if outstanding.is_zero() {
            CreditStatus::Settled
        } else if overdue_days == 0 {
            CreditStatus::Current
        } else {
            CreditStatus::Overdue
        };
        Ok(CreditState {
            schedule,
            paid,
            forgiven,
            outstanding,
            status,
            overdue_days,
            bucket: if status == CreditStatus::Overdue {
                AgingBucket::of_days(overdue_days)
            } else {
                None
            },
            next_due,
            credit_markup: self
                .cash_price
                .map(|c| self.credit_price.checked_sub(c))
                .transpose()?,
        })
    }
}

/// Mijozlardagi pul yoshi bo'yicha (SPEC 5.2): muddati o'tmagan va 4 ta guruh.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Aging {
    pub current: Money,
    /// `D1To30`, `D31To60`, `D61To90`, `D90Plus` tartibida.
    pub overdue: [Money; 4],
    pub total: Money,
}

pub fn aging(
    currency: baraka_money::Currency,
    states: &[&CreditState],
) -> Result<Aging, DomainError> {
    let zero = Money::zero(currency);
    let mut a = Aging {
        current: zero,
        overdue: [zero; 4],
        total: zero,
    };
    for s in states {
        let slot = match s.bucket {
            None => &mut a.current,
            Some(AgingBucket::D1To30) => &mut a.overdue[0],
            Some(AgingBucket::D31To60) => &mut a.overdue[1],
            Some(AgingBucket::D61To90) => &mut a.overdue[2],
            Some(AgingBucket::D90Plus) => &mut a.overdue[3],
        };
        *slot = slot.checked_add(s.outstanding)?;
        a.total = a.total.checked_add(s.outstanding)?;
    }
    Ok(a)
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    /// Ustama yo'q: qancha kechiksa ham qoldiq o'zgarmaydi.
    #[test]
    fn lateness_never_changes_outstanding() {
        let t = CreditTerms {
            credit_price: Money::from_major(660_000, Currency::Uzs).unwrap(),
            cash_price: None,
            installments: 3,
            first_due: d("2026-11-10"),
        };
        let ev = [CreditEvent::Payment {
            on: d("2026-11-10"),
            amount: Money::from_major(220_000, Currency::Uzs).unwrap(),
        }];
        let a = t.state(&ev, d("2026-12-30")).unwrap();
        let b = t.state(&ev, d("2036-12-30")).unwrap();
        assert_eq!(a.outstanding, b.outstanding);
        let ag = aging(Currency::Uzs, &[&a, &b]).unwrap();
        assert_eq!(ag.overdue[0], a.outstanding);
        assert_eq!(ag.overdue[3], b.outstanding);
        assert_eq!(ag.total, a.outstanding.checked_add(b.outstanding).unwrap());
    }
}
