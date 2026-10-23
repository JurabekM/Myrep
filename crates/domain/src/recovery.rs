//! «Qarz tiklash» taqsimoti 70/20/10 (SPEC 2D, DESKTOP_PROMPT D10): daromad uch qismga — ehtiyoj, qarz, jamg'arma.
//!
//! Ulushlar bazis punktlarda, yig'indisi 10 000 (100%). Jamg'arma ulushi kamida 100 bp (1%) — nolga tushirib
//! bo'lmaydi. Qismlar [`money::allocate`] bo'yicha (eng katta qoldiq usuli), yig'indisi daromadga teng.

use money::{Money, allocate};

use crate::DomainError;

/// Jamg'arma ulushining minimumi: 1% (100 bp).
pub const SAVINGS_MIN_BP: u64 = 100;
/// To'liq taqsimot: 100% (10 000 bp).
pub const SPLIT_TOTAL_BP: u64 = 10_000;

/// Daromadni `[ehtiyoj, qarz, jamg'arma]` ulushlari bo'yicha bo'ladi.
/// Yig'indisi 10 000 bo'lmasa — `SPLIT_NOT_100_PERCENT`; jamg'arma < 100 bp bo'lsa — `SAVINGS_BELOW_MINIMUM`.
pub fn recovery_split(income: Money, split_bp: [u64; 3]) -> Result<[Money; 3], DomainError> {
    let total = split_bp
        .iter()
        .fold(0_u64, |acc, part| acc.saturating_add(*part));
    if total != SPLIT_TOTAL_BP {
        return Err(DomainError::SplitNotHundred);
    }
    if split_bp[2] < SAVINGS_MIN_BP {
        return Err(DomainError::SavingsBelowMinimum);
    }
    let parts = allocate(income, &split_bp)?;
    match parts.as_slice() {
        [needs, debt, savings] => Ok([*needs, *debt, *savings]),
        _ => Err(DomainError::InvalidRule),
    }
}
