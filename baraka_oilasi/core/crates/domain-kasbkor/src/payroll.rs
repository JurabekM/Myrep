//! K6 — xodim bilan oylik hisob va avans (SPEC 7.2). Avans **foizsiz va jarimasiz**: bunday maydon
//! domen modelida umuman yo'q.
//!
//! - Avans `n` ta teng ulushga largest remainder bilan bo'linadi (qoldiq tiyinlar birinchi ulushlarga),
//!   `start_month` dan boshlab har oy haqdan ushlanadi.
//! - Haq yetmasa (masalan, haqsiz ta'til) — ushlanmagan qism keyingi oyga o'tadi, ustama yo'q. Bir nechta
//!   avans — berilgan oy va tartib bo'yicha (eskisi birinchi).
//! - Qoldiq = oldingi qoldiq + (haq − ushlangan) − to'langan; manfiy — ortiq to'langan.
//!
//! Oylar xodim ishlagan birinchi oydan 0 dan sanaladi. Vektorlar: `spec/test-vectors/kk_payroll.json`.
use baraka_money::{allocate, Currency, Money};

use crate::DomainError;

pub const MAX_ADVANCE_INSTALLMENTS: u32 = 24;

/// Bir oy: haq (0 — haqsiz oy) va shu oy to'langan summalar.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PayMonth {
    pub salary: Money,
    pub paid: Vec<Money>,
}

/// Avans shartlari: qachon berildi, qancha, necha oyda, qaysi oydan ushlanadi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Advance {
    pub id: String,
    pub month: u32,
    pub amount: Money,
    pub installments: u32,
    pub start_month: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MonthPay {
    pub salary: Money,
    /// Shu oy ushlanishi kerak bo'lgani (o'tgan oylardan qolgani bilan).
    pub scheduled: Money,
    pub deducted: Money,
    pub net: Money,
    pub paid: Money,
    /// Oy oxiridagi qoldiq: musbat — xodimga qarzmiz, manfiy — ortiq to'langan.
    pub balance: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AdvanceState {
    pub id: String,
    /// `(oy, ulush)`.
    pub schedule: Vec<(u32, Money)>,
    pub deducted: Money,
    pub outstanding: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Payroll {
    pub months: Vec<MonthPay>,
    pub advances: Vec<AdvanceState>,
}

/// Avans shartlarini tekshiradi va ulushlarga bo'ladi.
pub fn advance_parts(a: &Advance) -> Result<Vec<Money>, DomainError> {
    if !a.amount.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
    }
    if !(1..=MAX_ADVANCE_INSTALLMENTS).contains(&a.installments) {
        return Err(DomainError::on("INVALID_INSTALLMENTS", "installments"));
    }
    if a.start_month < a.month {
        return Err(DomainError::on("INVALID_START", "startMonth"));
    }
    let n = usize::try_from(a.installments).map_err(|_| DomainError::new("OVERFLOW"))?;
    Ok(allocate(a.amount, &vec![1; n])?)
}

struct Plan {
    idx: usize,
    month: u32,
    start: u32,
    parts: Vec<Money>,
    due: Money,
    deducted: Money,
}

pub fn payroll(
    currency: Currency,
    months: &[PayMonth],
    advances: &[Advance],
    opening: Money,
) -> Result<Payroll, DomainError> {
    let zero = Money::zero(currency);
    for m in months {
        if m.salary.is_negative() {
            return Err(DomainError::on("AMOUNT_NEGATIVE", "salary"));
        }
        if m.paid.iter().any(|p| !p.is_positive()) {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
    }
    let mut plans = Vec::with_capacity(advances.len());
    for (idx, a) in advances.iter().enumerate() {
        plans.push(Plan {
            idx,
            month: a.month,
            start: a.start_month,
            parts: advance_parts(a)?,
            due: zero,
            deducted: zero,
        });
    }
    let mut order: Vec<usize> = (0..plans.len()).collect();
    order.sort_by_key(|&i| (plans[i].month, plans[i].idx));
    let mut balance = opening;
    let mut rows = Vec::with_capacity(months.len());
    for (i, m) in months.iter().enumerate() {
        let i = u32::try_from(i).map_err(|_| DomainError::new("OVERFLOW"))?;
        let (mut avail, mut scheduled, mut deducted) = (m.salary, zero, zero);
        for &pi in &order {
            let p = &mut plans[pi];
            if let Some(k) = i.checked_sub(p.start) {
                if let Some(part) = usize::try_from(k).ok().and_then(|k| p.parts.get(k)) {
                    p.due = p.due.checked_add(*part)?;
                }
            }
            if p.due.is_positive() {
                scheduled = scheduled.checked_add(p.due)?;
                let d = if p.due.compare(&avail)?.is_le() {
                    p.due
                } else {
                    avail
                };
                p.due = p.due.checked_sub(d)?;
                p.deducted = p.deducted.checked_add(d)?;
                avail = avail.checked_sub(d)?;
                deducted = deducted.checked_add(d)?;
            }
        }
        let paid = m.paid.iter().try_fold(zero, |s, p| s.checked_add(*p))?;
        let net = m.salary.checked_sub(deducted)?;
        balance = balance.checked_add(net)?.checked_sub(paid)?;
        rows.push(MonthPay {
            salary: m.salary,
            scheduled,
            deducted,
            net,
            paid,
            balance,
        });
    }
    let mut states = Vec::with_capacity(plans.len());
    for (p, a) in plans.iter().zip(advances) {
        let mut schedule = Vec::with_capacity(p.parts.len());
        for (k, part) in p.parts.iter().enumerate() {
            let k = u32::try_from(k).map_err(|_| DomainError::new("OVERFLOW"))?;
            schedule.push((p.start + k, *part));
        }
        states.push(AdvanceState {
            id: a.id.clone(),
            schedule,
            deducted: p.deducted,
            outstanding: a.amount.checked_sub(p.deducted)?,
        });
    }
    Ok(Payroll {
        months: rows,
        advances: states,
    })
}
