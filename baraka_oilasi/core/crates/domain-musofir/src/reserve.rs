//! M4 — qorovul pul (musofir/SPEC 6.4, OQ-MF3), ish valyutasida.
//!
//! ```text
//! Maqsad        = round_half_up(Σ oylik chet el xarajati × N / oylar soni)   (N = 1–3)
//! Yetmagani     = max(0, maqsad − qoldiq)
//! Ulushdan      qorovulga = min(ulush, yetmagani);  jamg'armaga = ulush − qorovulga
//! ```
//! Tarix (yozuvi bor to'liq oy) bo'lmasa — maqsad yo'q (`NO_HISTORY`), ulush jamg'armaga.
//!
//! Vektorlar: `spec/test-vectors/mf_reserve.json`.
use baraka_money::{round_half_up, Money};

use crate::{bp_of, DomainError};

pub const MIN_MONTHS: i64 = 1;
pub const MAX_MONTHS: i64 = 3;
pub const DEFAULT_MONTHS: i64 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReserveStatus {
    Full,
    Partial,
    Empty,
    NoHistory,
}

impl ReserveStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Full => "FULL",
            Self::Partial => "PARTIAL",
            Self::Empty => "EMPTY",
            Self::NoHistory => "NO_HISTORY",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Reserve {
    pub avg_monthly: Option<Money>,
    pub target: Option<Money>,
    pub gap: Option<Money>,
    pub progress_bp: Option<i64>,
    pub status: ReserveStatus,
    /// O'z ulushi berilgan bo'lsa: qorovul pulga va jamg'armaga.
    pub to_reserve: Option<Money>,
    pub to_fund: Option<Money>,
}

fn ratio(num: i128, den: i128) -> Result<i64, DomainError> {
    let v = round_half_up(num, den)?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

/// `monthly` — oxirgi to'liq oylardagi chet el xarajatlari; `share` — shu maoshdan o'z ulushi (ixtiyoriy).
pub fn reserve_plan(
    balance: Money,
    monthly: &[Money],
    months: i64,
    share: Option<Money>,
) -> Result<Reserve, DomainError> {
    if !(MIN_MONTHS..=MAX_MONTHS).contains(&months) {
        return Err(DomainError::on("INVALID_MONTHS", "reserveMonths"));
    }
    if balance.is_negative()
        || share.is_some_and(|s| s.is_negative())
        || monthly.iter().any(Money::is_negative)
    {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    let c = balance.currency();
    let mut r = Reserve {
        avg_monthly: None,
        target: None,
        gap: None,
        progress_bp: None,
        status: ReserveStatus::NoHistory,
        to_reserve: share.map(|_| Money::zero(c)),
        to_fund: share,
    };
    if monthly.is_empty() {
        return Ok(r);
    }
    let sum = Money::sum(monthly.iter().copied(), c)?;
    let n = i128::try_from(monthly.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
    let target = Money::new(ratio(i128::from(sum.minor()) * i128::from(months), n)?, c);
    let gap = target.checked_sub(balance)?.clamp_non_negative();
    r.avg_monthly = Some(Money::new(ratio(i128::from(sum.minor()), n)?, c));
    r.target = Some(target);
    r.gap = Some(gap);
    r.progress_bp = Some(if target.is_positive() {
        bp_of(balance.minor(), target.minor())?.min(10_000)
    } else {
        10_000
    });
    r.status = if gap.is_zero() {
        ReserveStatus::Full
    } else if balance.is_zero() {
        ReserveStatus::Empty
    } else {
        ReserveStatus::Partial
    };
    if let Some(s) = share {
        let to_reserve = if s.compare(&gap)?.is_lt() { s } else { gap };
        r.to_reserve = Some(to_reserve);
        r.to_fund = Some(s.checked_sub(to_reserve)?);
    }
    Ok(r)
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    #[test]
    fn share_goes_to_reserve_first() {
        let k = |m| Money::new(m, Currency::Krw);
        let r = reserve_plan(
            k(300_000),
            &[k(810_000), k(790_000), k(815_000)],
            1,
            Some(k(520_000)),
        )
        .unwrap();
        assert_eq!(r.target, Some(k(805_000)));
        assert_eq!(r.to_reserve, Some(k(505_000)));
        assert_eq!(r.to_fund, Some(k(15_000)));
        assert_eq!(r.status, ReserveStatus::Partial);
    }
}
