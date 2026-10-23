//! M1 — qaytish jamg'armasi prognozi (musofir/SPEC 2.2, 4.1).
//!
//! ```text
//! Uy valyutasida   = convert(qoldiq, kurs)                       (kurs yo'q — taxmin yo'q)
//! O'rtacha         = round_half_up(Σ oylik sof jamg'arma / oylar soni)
//! Maqsadgacha      = ⌈qolgan / o'rtacha (uy valyutasida)⌉ oy
//! Qaytishdagi      = max(0, qoldiq + o'rtacha × to'liq oylar)
//! ```
//!
//! Vektorlar: `spec/test-vectors/mf_return_fund.json`.
use baraka_money::{convert, round_half_up, FxRate, Money};
use chrono::{Datelike, NaiveDate};

use crate::{bp_of, DomainError};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FundStatus {
    Reached,
    OnTrack,
    Behind,
    NoSaving,
    NoTarget,
    NoRate,
}

impl FundStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Reached => "REACHED",
            Self::OnTrack => "ON_TRACK",
            Self::Behind => "BEHIND",
            Self::NoSaving => "NO_SAVING",
            Self::NoTarget => "NO_TARGET",
            Self::NoRate => "NO_RATE",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ReturnFund {
    /// Ish valyutasida.
    pub avg_monthly: Option<Money>,
    pub months_until_return: Option<i64>,
    /// Quyidagilar — uy valyutasida.
    pub balance_home: Option<Money>,
    pub avg_monthly_home: Option<Money>,
    pub remaining_home: Option<Money>,
    pub progress_bp: Option<i64>,
    pub months_to_target: Option<i64>,
    pub projected_home: Option<Money>,
    pub shortfall_at_return: Option<Money>,
    pub status: FundStatus,
}

/// `start` dan `end` gacha to'liq oylar soni (o'tib ketgan bo'lsa 0).
pub fn months_between(start: NaiveDate, end: NaiveDate) -> i64 {
    let n = (i64::from(end.year()) - i64::from(start.year())) * 12 + i64::from(end.month())
        - i64::from(start.month())
        - i64::from(end.day() < start.day());
    n.max(0)
}

/// `rate` — ish valyutasidan uy valyutasiga (`from` = `balance` valyutasi); `target` — uy valyutasida;
/// `monthly` — oxirgi to'liq oylarning sof jamg'armasi (ish valyutasida).
pub fn return_fund(
    balance: Money,
    rate: Option<&FxRate>,
    target: Option<Money>,
    monthly: &[Money],
    today: NaiveDate,
    return_on: Option<NaiveDate>,
) -> Result<ReturnFund, DomainError> {
    if balance.is_negative() {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "balance"));
    }
    if target.is_some_and(|t| !t.is_positive()) {
        return Err(DomainError::on("INVALID_TARGET", "target"));
    }
    if let Some(r) = rate {
        if r.rate_num <= 0 || r.rate_den <= 0 {
            return Err(DomainError::on("INVALID_RATE", "rate"));
        }
        if r.from != balance.currency() || target.is_some_and(|t| t.currency() != r.to) {
            return Err(DomainError::new("CURRENCY_MISMATCH"));
        }
    }
    let avg = if monthly.is_empty() {
        None
    } else {
        let sum = Money::sum(monthly.iter().copied(), balance.currency())?;
        let n = i128::try_from(monthly.len()).map_err(|_| DomainError::new("OVERFLOW"))?;
        let m = round_half_up(i128::from(sum.minor()), n)?;
        Some(Money::new(
            i64::try_from(m).map_err(|_| DomainError::new("OVERFLOW"))?,
            balance.currency(),
        ))
    };
    let left = return_on.map(|d| months_between(today, d));
    let mut out = ReturnFund {
        avg_monthly: avg,
        months_until_return: left,
        balance_home: None,
        avg_monthly_home: None,
        remaining_home: None,
        progress_bp: None,
        months_to_target: None,
        projected_home: None,
        shortfall_at_return: None,
        status: FundStatus::NoRate,
    };
    let Some(rate) = rate else {
        return Ok(out);
    };
    let bh = convert(balance, rate)?;
    let ah = avg.map(|a| convert(a, rate)).transpose()?;
    let projected = match left {
        None => None,
        Some(n) => {
            let add = ah.unwrap_or(Money::zero(rate.to)).checked_mul(n)?;
            Some(bh.checked_add(add)?.clamp_non_negative())
        }
    };
    out.balance_home = Some(bh);
    out.avg_monthly_home = ah;
    out.projected_home = projected;
    let Some(target) = target else {
        out.status = FundStatus::NoTarget;
        return Ok(out);
    };
    let remaining = target.checked_sub(bh)?.clamp_non_negative();
    out.remaining_home = Some(remaining);
    out.progress_bp = Some(bp_of(bh.minor(), target.minor())?.min(10_000));
    out.shortfall_at_return = projected
        .map(|p| target.checked_sub(p).map(Money::clamp_non_negative))
        .transpose()?;
    if remaining.is_zero() {
        out.months_to_target = Some(0);
        out.status = FundStatus::Reached;
    } else {
        match ah {
            Some(a) if a.is_positive() => {
                // ⌈qolgan / o'rtacha⌉ — oylar soni (pul emas).
                let (r, a) = (remaining.minor(), a.minor());
                out.months_to_target = Some(r / a + i64::from(r % a != 0));
                out.status = match projected {
                    Some(p) if p.compare(&target)?.is_lt() => FundStatus::Behind,
                    _ => FundStatus::OnTrack,
                };
            }
            _ => out.status = FundStatus::NoSaving,
        }
    }
    Ok(out)
}

/// Ish boshlash summasi (SPEC 6.6) — maqsadning bir qismi: yashash uchun = maqsad − ish boshlash.
/// Vektorlar: `spec/test-vectors/mf_startup.json`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StartupSplit {
    pub startup: Money,
    pub living: Option<Money>,
    pub startup_bp: Option<i64>,
}

pub fn startup_split(target: Option<Money>, startup: Money) -> Result<StartupSplit, DomainError> {
    if !startup.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "startup"));
    }
    let Some(t) = target else {
        return Ok(StartupSplit {
            startup,
            living: None,
            startup_bp: None,
        });
    };
    if !t.is_positive() {
        return Err(DomainError::on("INVALID_TARGET", "target"));
    }
    if startup.compare(&t)?.is_gt() {
        return Err(DomainError::on("STARTUP_EXCEEDS_TARGET", "startup"));
    }
    Ok(StartupSplit {
        startup,
        living: Some(t.checked_sub(startup)?),
        startup_bp: Some(bp_of(startup.minor(), t.minor())?),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    #[test]
    fn months_between_counts_full_months() {
        assert_eq!(months_between(d("2026-10-18"), d("2027-12-01")), 13);
        assert_eq!(months_between(d("2026-10-18"), d("2026-11-18")), 1);
        assert_eq!(months_between(d("2026-10-18"), d("2026-09-01")), 0);
    }

    #[test]
    fn bobur_behind_until_december() {
        let k = |m| Money::new(m, Currency::Krw);
        let rate = FxRate {
            from: Currency::Krw,
            to: Currency::Uzs,
            rate_num: 91,
            rate_den: 10,
        };
        let r = return_fund(
            k(6_000_000),
            Some(&rate),
            Some(Money::new(12_000_000_000, Currency::Uzs)),
            &[k(520_000), k(500_000), k(540_000)],
            d("2026-10-18"),
            Some(d("2027-12-01")),
        )
        .unwrap();
        assert_eq!(r.months_to_target, Some(14));
        assert_eq!(r.status, FundStatus::Behind);
        assert_eq!(
            r.shortfall_at_return,
            Some(Money::new(388_400_000, Currency::Uzs))
        );
    }
}
