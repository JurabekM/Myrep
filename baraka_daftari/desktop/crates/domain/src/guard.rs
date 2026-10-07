//! 3-qonun (SPEC 2C): qorovul pul maqsadi, shaxsiy inflyatsiya, tayyorgarlik darvozasi,
//! ajratma ustuvorligi va «sichqon kemirgani». Sof hisoblar; vektorlar `spec/test-vectors/` da.
use money::{round_half_up, Currency, Money, MoneyError};

/// Qorovul pulning to'liq maqsadi (oy) — standart.
pub const GUARD_FULL_MONTHS: u32 = 6;
/// Birinchi bosqich (milestone).
pub const GUARD_MILESTONE_MONTHS: u32 = 3;
/// Darvoza uchun talab: 6,00 oy (x100).
pub const GATE_REQUIRED_X100: u32 = GUARD_FULL_MONTHS * 100;

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum GuardError {
    #[error("og'irliklar yig'indisi musbat bo'lishi kerak")]
    NoWeights,
    #[error("narx noto'g'ri")]
    InvalidPrice,
    #[error("summa noto'g'ri")]
    InvalidAmount,
    #[error(transparent)]
    Money(#[from] MoneyError),
}

/// Qorovul maqsadi = `round_half_up(Σ oylik (ZARUR+KERAK) × N / k)`. Ma'lumot bo'lmasa — `0`.
///
/// # Errors
/// Valyuta mos kelmasa yoki hisob sig'masa.
pub fn emergency_target(
    months: &[Money],
    target_months: u32,
    currency: Currency,
) -> Result<Money, GuardError> {
    if months.is_empty() {
        return Ok(Money::new(0, currency));
    }
    let mut sum: i128 = 0;
    for m in months {
        if m.currency() != currency {
            return Err(MoneyError::CurrencyMismatch {
                left: currency,
                right: m.currency(),
            }
            .into());
        }
        if m.minor() < 0 {
            return Err(GuardError::InvalidAmount);
        }
        sum += i128::from(m.minor());
    }
    let k = i128::try_from(months.len()).map_err(|_| MoneyError::Overflow)?;
    let minor = round_half_up(sum * i128::from(target_months), k)?;
    Ok(Money::new(minor, currency))
}

/// Qorovul necha oylik zaxirani qoplaydi (×100, quyiga yaxlitlanadi). Maqsad `0` bo'lsa — `0`.
///
/// # Errors
/// Valyuta mos kelmasa yoki hisob sig'masa.
pub fn guard_months_x100(
    balance: Money,
    target: Money,
    target_months: u32,
) -> Result<u32, GuardError> {
    if balance.currency() != target.currency() {
        return Err(MoneyError::CurrencyMismatch {
            left: balance.currency(),
            right: target.currency(),
        }
        .into());
    }
    if target.minor() <= 0 || balance.minor() <= 0 {
        return Ok(0);
    }
    let v =
        i128::from(balance.minor()) * i128::from(target_months) * 100 / i128::from(target.minor());
    Ok(u32::try_from(v).unwrap_or(u32::MAX))
}

/// Savatdagi bitta mahsulot: og'irlik (bp) va birinchi/oxirgi narx.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BasketLine {
    pub weight_bp: u32,
    pub first: Money,
    pub last: Money,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InflationIndex {
    pub per_item_bp: Vec<i64>,
    pub index_bp: i64,
}

/// Shaxsiy inflyatsiya: mahsulot o'zgarishi `round_half_up((oxirgi−birinchi)×10000/birinchi)`,
/// indeks — og'irlik bo'yicha o'rtacha (half-up).
///
/// # Errors
/// Og'irliklar yig'indisi 0, narx ≤ 0 (birinchi) yoki < 0 (oxirgi), valyuta mos kelmasa.
pub fn personal_inflation(lines: &[BasketLine]) -> Result<InflationIndex, GuardError> {
    let total_weight: i128 = lines.iter().map(|l| i128::from(l.weight_bp)).sum();
    if total_weight == 0 {
        return Err(GuardError::NoWeights);
    }
    let mut per = Vec::with_capacity(lines.len());
    let mut weighted: i128 = 0;
    for l in lines {
        if l.first.currency() != l.last.currency() {
            return Err(MoneyError::CurrencyMismatch {
                left: l.first.currency(),
                right: l.last.currency(),
            }
            .into());
        }
        if l.first.minor() <= 0 || l.last.minor() < 0 {
            return Err(GuardError::InvalidPrice);
        }
        let change = (i128::from(l.last.minor()) - i128::from(l.first.minor())) * 10_000;
        let bp = round_half_up(change, i128::from(l.first.minor()))?;
        weighted += i128::from(l.weight_bp) * i128::from(bp);
        per.push(bp);
    }
    Ok(InflationIndex {
        per_item_bp: per,
        index_bp: round_half_up(weighted, total_weight)?,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateReason {
    GuardBelowTarget,
    InterestDebtNoPlan,
}

impl GateReason {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::GuardBelowTarget => "GUARD_BELOW_TARGET",
            Self::InterestDebtNoPlan => "INTEREST_DEBT_NO_PLAN",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateStatus {
    pub open: bool,
    pub reasons: Vec<GateReason>,
}

/// «Jangga yarador askar yuborilmaydi»: qorovul ≥ talab **va** (foizli qarz yo'q **yoki** qarzdan
/// chiqish rejasi bor).
#[must_use]
pub fn readiness_gate(
    guard_months_x100: u32,
    has_interest_debt: bool,
    has_debt_plan: bool,
    required_x100: u32,
) -> GateStatus {
    let mut reasons = Vec::new();
    if guard_months_x100 < required_x100 {
        reasons.push(GateReason::GuardBelowTarget);
    }
    if has_interest_debt && !has_debt_plan {
        reasons.push(GateReason::InterestDebtNoPlan);
    }
    GateStatus {
        open: reasons.is_empty(),
        reasons,
    }
}

/// Ajratmani bo'lish: avval qorovul maqsadigacha, ortig'i «o'sadigan»ga — faqat darvoza ochiq bo'lsa.
/// Yopiq bo'lsa hammasi qorovulga (o'sadigan bo'lim qulflangan).
///
/// # Errors
/// Manfiy summa yoki valyuta mos kelmasa.
pub fn split_allocation(
    share: Money,
    guard_balance: Money,
    guard_target: Money,
    gate_open: bool,
) -> Result<(Money, Money), GuardError> {
    if share.minor() < 0 {
        return Err(GuardError::InvalidAmount);
    }
    let gap = guard_target.checked_sub(guard_balance)?;
    if !gate_open {
        return Ok((share, Money::new(0, share.currency())));
    }
    let to_guard = share.minor().min(gap.minor().max(0));
    let rest = share.checked_sub(Money::new(to_guard, share.currency()))?;
    Ok((Money::new(to_guard, share.currency()), rest))
}

/// «Sichqon kemirgani»: bugungi narxlarda `years` yildan keyingi qiymat — yil-yilga half-up.
///
/// # Errors
/// Manfiy summa yoki sig'masa.
pub fn real_value(amount: Money, annual_bp: u32, years: u32) -> Result<Money, GuardError> {
    if amount.minor() < 0 {
        return Err(GuardError::InvalidAmount);
    }
    let mut v = i128::from(amount.minor());
    for _ in 0..years {
        v = i128::from(round_half_up(v * 10_000, 10_000 + i128::from(annual_bp))?);
    }
    Ok(Money::new(
        i64::try_from(v).map_err(|_| MoneyError::Overflow)?,
        amount.currency(),
    ))
}

/// Mahsulot narxi `years` yildan keyin (yil-yilga half-up).
///
/// # Errors
/// Manfiy narx yoki sig'masa.
pub fn future_price(price: Money, annual_bp: u32, years: u32) -> Result<Money, GuardError> {
    if price.minor() < 0 {
        return Err(GuardError::InvalidAmount);
    }
    let mut p = i128::from(price.minor());
    for _ in 0..years {
        p = i128::from(round_half_up(p * (10_000 + i128::from(annual_bp)), 10_000)?);
    }
    Ok(Money::new(
        i64::try_from(p).map_err(|_| MoneyError::Overflow)?,
        price.currency(),
    ))
}

/// Summaga necha birlik (1/1000 aniqlikda: kg uchun gramm) olinadi.
///
/// # Errors
/// Narx ≤ 0 yoki summa manfiy bo'lsa.
pub fn quantity_milli(amount: Money, unit_price: Money) -> Result<i64, GuardError> {
    if unit_price.minor() <= 0 || amount.minor() < 0 {
        return Err(GuardError::InvalidAmount);
    }
    if amount.currency() != unit_price.currency() {
        return Err(MoneyError::CurrencyMismatch {
            left: amount.currency(),
            right: unit_price.currency(),
        }
        .into());
    }
    Ok(round_half_up(
        i128::from(amount.minor()) * 1000,
        i128::from(unit_price.minor()),
    )?)
}
