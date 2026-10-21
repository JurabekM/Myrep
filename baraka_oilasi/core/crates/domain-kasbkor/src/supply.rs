//! K6 — ta'minotchiga qarz (SPEC 7.1 `SUPPLY`): har yetkazish — summa va to'lov muddati. Kechikish uchun
//! jarima yoki ustama **yo'q**.
//!
//! - To'lovlar sana tartibida eng erta muddatli ochiq yetkazishdan yopiladi (muddat, yetkazilgan sana,
//!   tartib); to'lov shu kungacha yetkazilganlar qoldig'idan oshmaydi (oldindan to'lov — K6 da yo'q).
//! - `due_soon` — 7 kun ichida muddati keladigan qoldiq.
//!
//! Vektorlar: `spec/test-vectors/kk_supplier_balance.json`.
use baraka_money::{Currency, Money};
use chrono::{Duration, NaiveDate};

use crate::credit::InstallmentState;
use crate::DomainError;

pub const MAX_SUPPLY_DAYS: u32 = 365;
pub const DUE_SOON_DAYS: i64 = 7;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Delivery {
    pub id: String,
    pub on: NaiveDate,
    pub amount: Money,
    pub due_days: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SupplyPayment {
    pub on: NaiveDate,
    pub amount: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DeliveryState {
    pub id: String,
    pub due: NaiveDate,
    pub amount: Money,
    pub paid: Money,
    pub outstanding: Money,
    pub state: InstallmentState,
    pub overdue_days: i64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SupplierBalance {
    pub deliveries: Vec<DeliveryState>,
    pub paid: Money,
    pub outstanding: Money,
    pub overdue: Money,
    pub due_soon: Money,
    /// Eng yaqin muddat va undagi qoldiq.
    pub next_due: Option<(NaiveDate, Money)>,
}

/// Yetkazish shartlarini tekshiradi; qaytaradi — to'lov muddati.
pub fn due_date(d: &Delivery) -> Result<NaiveDate, DomainError> {
    if !d.amount.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
    }
    if d.due_days > MAX_SUPPLY_DAYS {
        return Err(DomainError::on("INVALID_DAYS", "dueDays"));
    }
    d.on.checked_add_signed(Duration::days(i64::from(d.due_days)))
        .ok_or(DomainError::on("INVALID_DATE", "deliveredOn"))
}

struct Open {
    due: NaiveDate,
    left: Money,
}

pub fn supplier_balance(
    currency: Currency,
    deliveries: &[Delivery],
    payments: &[SupplyPayment],
    today: NaiveDate,
) -> Result<SupplierBalance, DomainError> {
    let zero = Money::zero(currency);
    let mut open = Vec::with_capacity(deliveries.len());
    for d in deliveries {
        open.push(Open {
            due: due_date(d)?,
            left: d.amount,
        });
    }
    // Yopish tartibi: muddat, yetkazilgan sana, kiritilgan tartib.
    let mut order: Vec<usize> = (0..deliveries.len()).collect();
    order.sort_by_key(|&i| (open[i].due, deliveries[i].on, i));
    let mut prev: Option<NaiveDate> = None;
    let mut paid_total = zero;
    for p in payments {
        if prev.is_some_and(|d| p.on < d) {
            return Err(DomainError::on("INVALID_DATE", "paidOn"));
        }
        prev = Some(p.on);
        if !p.amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        let mut avail = zero;
        for &i in &order {
            if deliveries[i].on <= p.on {
                avail = avail.checked_add(open[i].left)?;
            }
        }
        if p.amount.compare(&avail)?.is_gt() {
            return Err(DomainError::on("EXCEEDS_OUTSTANDING", "amount"));
        }
        paid_total = paid_total.checked_add(p.amount)?;
        let mut a = p.amount;
        for &i in &order {
            if !a.is_positive() {
                break;
            }
            if deliveries[i].on > p.on || !open[i].left.is_positive() {
                continue;
            }
            let x = if a.compare(&open[i].left)?.is_le() {
                a
            } else {
                open[i].left
            };
            open[i].left = open[i].left.checked_sub(x)?;
            a = a.checked_sub(x)?;
        }
    }
    let (mut outstanding, mut overdue, mut soon) = (zero, zero, zero);
    let mut rows = Vec::with_capacity(deliveries.len());
    for (d, o) in deliveries.iter().zip(&open) {
        outstanding = outstanding.checked_add(o.left)?;
        let (state, days) = if !o.left.is_positive() {
            (InstallmentState::Paid, 0)
        } else if o.due < today {
            overdue = overdue.checked_add(o.left)?;
            (InstallmentState::Overdue, (today - o.due).num_days())
        } else {
            if (o.due - today).num_days() <= DUE_SOON_DAYS {
                soon = soon.checked_add(o.left)?;
            }
            (InstallmentState::Due, 0)
        };
        rows.push(DeliveryState {
            id: d.id.clone(),
            due: o.due,
            amount: d.amount,
            paid: d.amount.checked_sub(o.left)?,
            outstanding: o.left,
            state,
            overdue_days: days,
        });
    }
    let next_due = order
        .iter()
        .find(|&&i| open[i].left.is_positive())
        .map(|&i| (open[i].due, open[i].left));
    Ok(SupplierBalance {
        deliveries: rows,
        paid: paid_total,
        outstanding,
        overdue,
        due_soon: soon,
        next_due,
    })
}
