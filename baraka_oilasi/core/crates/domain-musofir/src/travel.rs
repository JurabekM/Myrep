//! M3 — yo'l qarzi rejasi (musofir/SPEC 6.1), uy valyutasida.
//!
//! ```text
//! Qolgan          = max(0, qarz qoldig'i − max(0, «Qarz to'lovi» maqsadidagi pul))
//! Oylik o'rtacha  = round_half_up(Σ oxirgi oylarda shu maqsadga kelgan / oylar soni)
//! Necha oyda      = ⌈qolgan / o'rtacha⌉;   oyiga kerak = round_half_up(qolgan / maqsadli muddat)
//! ```
//!
//! Vektorlar: `spec/test-vectors/mf_travel_debt.json`.
use baraka_money::{round_half_up, Money};
use chrono::{Months, NaiveDate};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TravelDebtStatus {
    Cleared,
    OnTrack,
    Behind,
    NoPayments,
}

impl TravelDebtStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Cleared => "CLEARED",
            Self::OnTrack => "ON_TRACK",
            Self::Behind => "BEHIND",
            Self::NoPayments => "NO_PAYMENTS",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TravelDebtPlan {
    pub remaining: Money,
    pub avg_monthly: Option<Money>,
    pub months_to_clear: Option<i64>,
    pub clear_on: Option<NaiveDate>,
    pub required_monthly: Money,
    pub status: TravelDebtStatus,
}

fn ratio(num: i64, den: i64) -> Result<i64, DomainError> {
    let v = round_half_up(i128::from(num), i128::from(den))?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

/// `outstanding` — U8 qarzining qoldig'i; `available` — «Qarz to'lovi» maqsadi qoldig'i (manfiy bo'lishi
/// mumkin); `monthly` — oxirgi to'liq oylarda shu maqsadga kelgan summalar.
pub fn travel_debt_plan(
    outstanding: Money,
    available: Money,
    monthly: &[Money],
    target_months: i64,
    today: NaiveDate,
) -> Result<TravelDebtPlan, DomainError> {
    if outstanding.is_negative() {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "outstanding"));
    }
    if !(1..=60).contains(&target_months) {
        return Err(DomainError::on("INVALID_MONTHS", "targetMonths"));
    }
    let c = outstanding.currency();
    let remaining = outstanding
        .checked_sub(available.clamp_non_negative())?
        .clamp_non_negative();
    let avg = if monthly.is_empty() {
        None
    } else {
        let sum = Money::sum(monthly.iter().copied(), c)?;
        let n = i64::try_from(monthly.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
        Some(Money::new(ratio(sum.minor(), n)?, c))
    };
    let required_monthly = Money::new(ratio(remaining.minor(), target_months)?, c);
    let mut plan = TravelDebtPlan {
        remaining,
        avg_monthly: avg,
        months_to_clear: None,
        clear_on: None,
        required_monthly,
        status: TravelDebtStatus::NoPayments,
    };
    if remaining.is_zero() {
        plan.months_to_clear = Some(0);
        plan.clear_on = Some(today);
        plan.status = TravelDebtStatus::Cleared;
    } else if let Some(a) = avg.filter(Money::is_positive) {
        // ⌈qolgan / o'rtacha⌉ — oylar soni (pul emas).
        let (r, a) = (remaining.minor(), a.minor());
        let n = r / a + i64::from(r % a != 0);
        plan.months_to_clear = Some(n);
        plan.clear_on = u32::try_from(n)
            .ok()
            .and_then(|m| today.checked_add_months(Months::new(m)));
        plan.status = if n <= target_months {
            TravelDebtStatus::OnTrack
        } else {
            TravelDebtStatus::Behind
        };
    }
    Ok(plan)
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    #[test]
    fn four_months_from_first_salaries() {
        let u = |m| Money::new(m, Currency::Uzs);
        let d = NaiveDate::from_ymd_opt(2026, 10, 19).unwrap();
        let p = travel_debt_plan(
            u(1_500_000_000),
            u(327_000_000),
            &[u(327_000_000), u(300_000_000), u(280_000_000)],
            6,
            d,
        )
        .unwrap();
        assert_eq!(p.months_to_clear, Some(4));
        assert_eq!(p.clear_on, NaiveDate::from_ymd_opt(2027, 2, 19));
        assert_eq!(p.status, TravelDebtStatus::OnTrack);
    }
}
