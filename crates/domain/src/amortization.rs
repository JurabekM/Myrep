//! Amortizatsiya simulyatori (SPEC 2D, DESKTOP_PROMPT D10): annuitet, «muddatni qisqartirish» rejimi.
//!
//! * Oylik annuitet to'lovi: `P · r · g / (g − 1)`, bu yerda `r = annual_bp / 120 000`, `g = (1 + r)^N`.
//!   Yarim tiyin yuqoriga. `(1 + r)^N` i128 ustida qo'zg'aladigan-nuqta (10^18 masshtab) bilan hisoblanadi —
//!   pul uchun `f64` ishlatilmaydi.
//! * Har oy foiz yaxlitlanadi (yarim tiyin yuqoriga). Oxirgi to'lov qolgan qoldiqdan oshmaydi.
//! * Qo'shimcha to'lov (`extra`) qoldiqni kamaytiradi: to'lov o'zgarmaydi, muddat qisqaradi.

use money::{Money, round_half_up_div};

use crate::DomainError;

/// Qo'zg'aladigan nuqta masshtabi (10^18).
const ONE: i128 = 1_000_000_000_000_000_000;
/// 12 oy × 10 000 bp: yillik bp'dan oylik foiz bo'linmasi.
const MONTHLY_DIVISOR: i128 = 120_000;
/// Himoya: bu chegaradan uzun jadval — xato (kirish noto'g'ri yoki hisoblash cheksiz).
const MAX_MONTHS: u32 = 1_200;

/// Jadvalning bir oyi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmortRow {
    /// Oy tartibi (1 dan).
    pub month: u32,
    /// Foiz qismi.
    pub interest: Money,
    /// Asosiy qarz qismi.
    pub principal: Money,
    /// Qo'shimcha to'lov.
    pub extra: Money,
    /// Oydan keyingi qoldiq.
    pub balance: Money,
}

/// To'liq jadval.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Schedule {
    /// Standart oylik to'lov.
    pub payment: Money,
    /// Jadval uzunligi (oylar).
    pub months: u32,
    /// Jami foiz.
    pub total_interest: Money,
    /// Oylar bo'yicha qatorlar.
    pub rows: Vec<AmortRow>,
}

/// `a × b / ONE`, oraliq ko'paytmalar i128 chegarasidan oshmaydi.
fn mul_fixed(a: i128, b: i128) -> Result<i128, DomainError> {
    let high = (a / ONE).checked_mul(b).ok_or(DomainError::InvalidRule)?;
    let low = (a % ONE).checked_mul(b).ok_or(DomainError::InvalidRule)? / ONE;
    high.checked_add(low).ok_or(DomainError::InvalidRule)
}

/// `base^exponent` qo'zg'aladigan-nuqtada (ikkilik daraja).
fn fixed_pow(base: i128, exponent: u32) -> Result<i128, DomainError> {
    let mut result = ONE;
    let mut square = base;
    let mut remaining = exponent;
    while remaining > 0 {
        if remaining & 1 == 1 {
            result = mul_fixed(result, square)?;
        }
        remaining >>= 1;
        if remaining > 0 {
            square = mul_fixed(square, square)?;
        }
    }
    Ok(result)
}

/// Oylik annuitet to'lovi (minor birlikda, yarim tiyin yuqoriga).
pub fn annuity_payment(
    principal: Money,
    annual_bp: i64,
    term_months: i64,
) -> Result<Money, DomainError> {
    let term = u32::try_from(term_months).map_err(|_| DomainError::InvalidRule)?;
    if principal.minor() <= 0 || annual_bp <= 0 || term == 0 || term > MAX_MONTHS {
        return Err(DomainError::InvalidRule);
    }
    let rate = i128::from(annual_bp) * ONE / MONTHLY_DIVISOR;
    let growth = fixed_pow(ONE + rate, term)?;
    // r · g (qo'zg'aladigan-nuqtada), so'ng P · r · g / (g − 1).
    let rate_growth = mul_fixed(rate, growth)?;
    let numerator = i128::from(principal.minor())
        .checked_mul(rate_growth)
        .ok_or(DomainError::InvalidRule)?;
    let payment = round_half_up_div(numerator, growth - ONE)?;
    Ok(Money::new(
        i64::try_from(payment).map_err(|_| DomainError::InvalidRule)?,
        principal.currency(),
    ))
}

/// Annuitet jadvali. `extra_per_month` — har oy qo'shimcha to'lov (0 bo'lishi mumkin).
pub fn annuity_schedule(
    principal: Money,
    annual_bp: i64,
    term_months: i64,
    extra_per_month: Money,
) -> Result<Schedule, DomainError> {
    if extra_per_month.minor() < 0 || extra_per_month.currency() != principal.currency() {
        return Err(DomainError::InvalidRule);
    }
    let payment = annuity_payment(principal, annual_bp, term_months)?;
    let currency = principal.currency();
    let mut balance = principal.minor();
    let mut total_interest: i64 = 0;
    let mut rows = Vec::new();
    while balance > 0 {
        let month = u32::try_from(rows.len() + 1).map_err(|_| DomainError::InvalidRule)?;
        if month > MAX_MONTHS {
            return Err(DomainError::InvalidRule);
        }
        let interest = i64::try_from(round_half_up_div(
            i128::from(balance) * i128::from(annual_bp),
            MONTHLY_DIVISOR,
        )?)
        .map_err(|_| DomainError::InvalidRule)?;
        // To'lov foizdan kichik bo'lsa, qarz o'smoqda: bunday jadval hisoblanmaydi.
        let scheduled = payment.minor() - interest;
        if scheduled <= 0 {
            return Err(DomainError::InvalidRule);
        }
        let principal_part = scheduled.min(balance);
        balance -= principal_part;
        let extra = extra_per_month.minor().min(balance);
        balance -= extra;
        total_interest = total_interest
            .checked_add(interest)
            .ok_or(DomainError::InvalidRule)?;
        rows.push(AmortRow {
            month,
            interest: Money::new(interest, currency),
            principal: Money::new(principal_part, currency),
            extra: Money::new(extra, currency),
            balance: Money::new(balance, currency),
        });
    }
    Ok(Schedule {
        payment,
        months: u32::try_from(rows.len()).map_err(|_| DomainError::InvalidRule)?,
        total_interest: Money::new(total_interest, currency),
        rows,
    })
}
