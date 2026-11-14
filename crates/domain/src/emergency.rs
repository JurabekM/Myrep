//! Favqiyat zaxirasi («Qorovul», SPEC 2C.1): maqsadli summa.
//!
//! Maqsad = oylik `ZARUR + KERAK` xarajatlarining o'rtachasi × N oy. O'rtacha — so'nggi
//! [`AVERAGE_MONTHS`] ta ma'lumotli oy bo'yicha (xarajati nolga teng oy hisobga olinmaydi).
//! Ma'lumotli oy uchtadan kam bo'lsa, maqsad hisoblanmaydi (`None`).

use money::{Currency, Money, round_half_up_div};

use crate::DomainError;

/// O'rtacha olinadigan oylar soni (birinchi milestone: 3 oy).
pub const AVERAGE_MONTHS: usize = 3;

/// Zaxira maqsadi. `monthly_spend` — har oyning `ZARUR + KERAK` jami, eng eskidan yangigacha.
/// `target_months` — 3 (birinchi milestone) yoki 6 (to'liq maqsad, standart). Yarim tiyin yuqoriga.
pub fn emergency_target(
    currency: Currency,
    monthly_spend: &[Money],
    target_months: i64,
) -> Result<Option<Money>, DomainError> {
    if target_months <= 0 {
        return Err(DomainError::InvalidRule);
    }
    let recent: Vec<Money> = monthly_spend
        .iter()
        .rev()
        .filter(|month| month.minor() > 0)
        .take(AVERAGE_MONTHS)
        .copied()
        .collect();
    if recent.len() < AVERAGE_MONTHS {
        return Ok(None);
    }
    let mut sum = Money::zero(currency);
    for month in &recent {
        sum = sum.checked_add(*month)?;
    }
    let scaled = round_half_up_div(
        i128::from(sum.minor()) * i128::from(target_months),
        AVERAGE_MONTHS as i128,
    )?;
    Ok(Some(Money::new(
        i64::try_from(scaled).unwrap_or(i64::MAX),
        currency,
    )))
}
