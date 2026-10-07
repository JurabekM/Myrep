//! 4-qonun (SPEC 2D.3, 2D.5): to'lov jadvali, qarzning haqiqiy narxi va oylik yuk.
//! Sof hisoblar; vektorlar: `debt_schedule`, `debt_cost`, `debt_burden`.
use money::{allocate, round_half_up, Money, MoneyError};
use time::{Date, Month};

/// Jadvaldagi eng ko'p oy (10 yil).
pub const MAX_SCHEDULE_MONTHS: u32 = 120;

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ScheduleError {
    #[error("to'lov rejasi bo'sh")]
    Empty,
    #[error("to'lov summasi musbat bo'lishi kerak")]
    NonPositive,
    #[error("jadval jami asosiy summadan kam")]
    BelowPrincipal,
    #[error("oylar soni 1 dan 120 gacha")]
    InvalidMonths,
    #[error("summa noto'g'ri")]
    InvalidAmount,
    #[error(transparent)]
    Money(#[from] MoneyError),
}

impl ScheduleError {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::Empty => "EMPTY_SCHEDULE",
            Self::NonPositive => "NON_POSITIVE",
            Self::BelowPrincipal => "BELOW_PRINCIPAL",
            Self::InvalidMonths => "INVALID_MONTHS",
            Self::InvalidAmount => "INVALID_AMOUNT",
            Self::Money(_) => "MONEY",
        }
    }
}

/// `d` dan `n` oy keyin: kun saqlanadi, oyda yetmasa oy oxiriga qisqartiriladi (31-yanvar + 1 = 28/29-fevral).
#[must_use]
pub fn add_months(d: Date, n: u32) -> Date {
    let total = i64::from(d.year()) * 12 + i64::from(u8::from(d.month())) - 1 + i64::from(n);
    let year = i32::try_from(total.div_euclid(12)).unwrap_or(d.year());
    let month_n = u8::try_from(total.rem_euclid(12) + 1).unwrap_or(1);
    let month = Month::try_from(month_n).unwrap_or(Month::January);
    let day = d.day().min(month.length(year));
    Date::from_calendar_date(year, month, day).unwrap_or(d)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ScheduleSummary {
    pub total: Money,
    /// Ustama = jami − asosiy. `0` — ustamasiz (qarzi hasana).
    pub markup: Money,
}

/// To'lov jadvalining jami va ustamasi. Rejasiz yoki asosiy summadan kam jadval qabul qilinmaydi.
///
/// # Errors
/// Bo'sh jadval, musbat bo'lmagan summa, asosiydan kam jami yoki valyuta mos kelmasa.
pub fn schedule_summary(
    principal: Money,
    rows: &[Money],
) -> Result<ScheduleSummary, ScheduleError> {
    if rows.is_empty() {
        return Err(ScheduleError::Empty);
    }
    if principal.minor() <= 0 {
        return Err(ScheduleError::InvalidAmount);
    }
    let mut total = Money::new(0, principal.currency());
    for r in rows {
        if r.minor() <= 0 {
            return Err(ScheduleError::NonPositive);
        }
        total = total.checked_add(*r)?;
    }
    if total.minor() < principal.minor() {
        return Err(ScheduleError::BelowPrincipal);
    }
    Ok(ScheduleSummary {
        total,
        markup: total.checked_sub(principal)?,
    })
}

/// Teng bo'laklarga bo'lingan jadval (`FIXED_MARKUP`): `(asosiy + ustama)` `months` ga bo'linadi,
/// qoldiq birinchi to'lovlarga qo'shiladi; sanalar `first_due` dan oyma-oy.
///
/// # Errors
/// Oylar 1..=120 emas, asosiy ≤ 0 yoki ustama < 0 bo'lsa.
pub fn fixed_markup_schedule(
    principal: Money,
    markup: Money,
    months: u32,
    first_due: Date,
) -> Result<Vec<(Date, Money)>, ScheduleError> {
    if months == 0 || months > MAX_SCHEDULE_MONTHS {
        return Err(ScheduleError::InvalidMonths);
    }
    if principal.minor() <= 0 || markup.minor() < 0 {
        return Err(ScheduleError::InvalidAmount);
    }
    let total = principal.checked_add(markup)?;
    let ratios = vec![1_u64; months as usize];
    let parts = allocate(total, &ratios)?;
    Ok(parts
        .into_iter()
        .enumerate()
        .map(|(i, m)| (add_months(first_due, u32::try_from(i).unwrap_or(0)), m))
        .collect())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DebtCost {
    /// To'langan + jadvaldagi qoldiq.
    pub total: Money,
    /// Asosiy summadan ortiqcha (kamida 0).
    pub excess: Money,
    /// Ortiqcha ulushi jamiga nisbatan, bp (half-up).
    pub excess_bp: u32,
}

/// Qarzning haqiqiy narxi (SPEC 2D.3).
///
/// # Errors
/// Asosiy ≤ 0, manfiy summa yoki valyuta mos kelmasa.
pub fn debt_cost(
    principal: Money,
    paid: Money,
    remaining_scheduled: Money,
) -> Result<DebtCost, ScheduleError> {
    if principal.minor() <= 0 || paid.minor() < 0 || remaining_scheduled.minor() < 0 {
        return Err(ScheduleError::InvalidAmount);
    }
    let total = paid.checked_add(remaining_scheduled)?;
    let excess = Money::new(
        total.checked_sub(principal)?.minor().max(0),
        principal.currency(),
    );
    let bp = if total.minor() > 0 {
        round_half_up(
            i128::from(excess.minor()) * 10_000,
            i128::from(total.minor()),
        )?
    } else {
        0
    };
    Ok(DebtCost {
        total,
        excess,
        excess_bp: u32::try_from(bp).unwrap_or(u32::MAX),
    })
}

/// Oylik qarz yuki daromadga nisbatan (bp, half-up).
///
/// # Errors
/// Daromad ≤ 0 yoki oylik to'lov < 0 bo'lsa.
pub fn burden_bp(monthly: Money, income: Money) -> Result<u32, ScheduleError> {
    if income.minor() <= 0 || monthly.minor() < 0 {
        return Err(ScheduleError::InvalidAmount);
    }
    if monthly.currency() != income.currency() {
        return Err(MoneyError::CurrencyMismatch {
            left: monthly.currency(),
            right: income.currency(),
        }
        .into());
    }
    let v = round_half_up(
        i128::from(monthly.minor()) * 10_000,
        i128::from(income.minor()),
    )?;
    Ok(u32::try_from(v).unwrap_or(u32::MAX))
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::date;

    #[test]
    fn month_arithmetic_clamps_to_month_end() {
        assert_eq!(add_months(date!(2026 - 01 - 31), 1), date!(2026 - 02 - 28));
        assert_eq!(add_months(date!(2028 - 01 - 31), 1), date!(2028 - 02 - 29));
        assert_eq!(add_months(date!(2026 - 11 - 15), 3), date!(2027 - 02 - 15));
        assert_eq!(add_months(date!(2026 - 12 - 31), 12), date!(2027 - 12 - 31));
    }

    #[test]
    fn currency_mismatch_is_rejected() {
        let a = Money::new(10, Currency::Uzs);
        let b = Money::new(10, Currency::Usd);
        assert!(burden_bp(a, b).is_err());
    }
}
