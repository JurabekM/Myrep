//! Havas chegarasi holati va odat prognozi (SPEC 2B.3, 2B.9). Bloklash yo'q: faqat yumshoq ogohlantirish.
use money::{round_half_up, Money, MoneyError};

use crate::{share_bp, Necessity};

/// Shu foizdan (bazis punkt) boshlab «yaqinlashdi» ogohlantirishi (80%).
pub const NEAR_BP: i64 = 8_000;
/// 100% va undan ortiq — chegara oshdi.
pub const OVER_BP: i64 = 10_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HavasState {
    Ok,
    Near,
    Over,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HavasStatus {
    pub state: HavasState,
    /// Chegaraning necha foizi sarflangan (bazis punkt, half-up).
    pub used_bp: i64,
}

/// # Errors
/// `limit <= 0`, `spent < 0` yoki valyuta mos kelmasa.
pub fn havas_status(spent: Money, limit: Money) -> Result<HavasStatus, HavasError> {
    if spent.currency() != limit.currency() {
        return Err(HavasError::Money(MoneyError::CurrencyMismatch {
            left: spent.currency(),
            right: limit.currency(),
        }));
    }
    if limit.minor() <= 0 {
        return Err(HavasError::InvalidLimit);
    }
    if spent.minor() < 0 {
        return Err(HavasError::InvalidAmount);
    }
    // Chegaralar aniq (yaxlitlashsiz) solishtiriladi: 79,996% hali «yaqinlashdi» emas.
    let (s, l) = (i128::from(spent.minor()), i128::from(limit.minor()));
    let state = if s * 10_000 >= l * i128::from(OVER_BP) {
        HavasState::Over
    } else if s * 10_000 >= l * i128::from(NEAR_BP) {
        HavasState::Near
    } else {
        HavasState::Ok
    };
    Ok(HavasStatus {
        state,
        used_bp: share_bp(spent, limit)?,
    })
}

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum HavasError {
    #[error("chegara musbat bo'lishi kerak")]
    InvalidLimit,
    #[error("sarflangan summa manfiy bo'lmasligi kerak")]
    InvalidAmount,
    #[error(transparent)]
    Money(#[from] MoneyError),
}

/// Xarajatning amaldagi toifasi: xarajatning o'zida belgilangan bo'lsa shu, aks holda kategoriyaniki.
#[must_use]
pub const fn effective_necessity(
    expense: Option<Necessity>,
    category: Option<Necessity>,
) -> Option<Necessity> {
    match expense {
        Some(n) => Some(n),
        None => category,
    }
}

/// Havas hisobiga kiradimi: amaldagi toifa `Havas`, sovg'a (`gift`) emas va sadaqa emas.
/// Sadaqa — isrof emas, shuning uchun toifasi qanday belgilangan bo'lishidan qat'i nazar kirmaydi.
#[must_use]
pub fn counts_as_havas(
    necessity: Option<Necessity>,
    is_gift: bool,
    category_is_charity: bool,
) -> bool {
    necessity == Some(Necessity::Havas) && !is_gift && !category_is_charity
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HabitProjection {
    pub week: Money,
    pub month: Money,
    pub year: Money,
}

/// Oxirgi `window_days` kunlik jamidan haftalik, oylik (30 kun) va yillik (365 kun) prognoz.
/// Faqat statistika: ayblash yoki majburlash yo'q.
///
/// # Errors
/// `window_days == 0`, manfiy jami yoki overflow bo'lsa.
pub fn habit_projection(total: Money, window_days: u32) -> Result<HabitProjection, HavasError> {
    if window_days == 0 {
        return Err(HavasError::InvalidLimit);
    }
    if total.minor() < 0 {
        return Err(HavasError::InvalidAmount);
    }
    let scale = |days: i128| -> Result<Money, MoneyError> {
        let num = i128::from(total.minor())
            .checked_mul(days)
            .ok_or(MoneyError::Overflow)?;
        Ok(Money::new(
            round_half_up(num, i128::from(window_days))?,
            total.currency(),
        ))
    };
    Ok(HabitProjection {
        week: scale(7)?,
        month: scale(30)?,
        year: scale(365)?,
    })
}

#[cfg(test)]
mod tests {
    use money::Currency;

    use super::*;

    fn m(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn thresholds_are_exact_not_rounded() {
        // 79,996% — yaxlitlanganda 8000 bp ko'rinadi, lekin holat hali OK.
        let s = havas_status(m(79_996), m(100_000)).unwrap();
        assert_eq!((s.state, s.used_bp), (HavasState::Ok, 8000));
        assert_eq!(
            havas_status(m(80_000), m(100_000)).unwrap().state,
            HavasState::Near
        );
        assert_eq!(
            havas_status(m(99_999), m(100_000)).unwrap().state,
            HavasState::Near
        );
        assert_eq!(
            havas_status(m(100_000), m(100_000)).unwrap().state,
            HavasState::Over
        );
    }

    #[test]
    fn invalid_inputs() {
        assert_eq!(havas_status(m(1), m(0)), Err(HavasError::InvalidLimit));
        assert_eq!(havas_status(m(-1), m(10)), Err(HavasError::InvalidAmount));
        assert!(matches!(
            havas_status(Money::new(1, Currency::Usd), m(10)),
            Err(HavasError::Money(_))
        ));
    }

    #[test]
    fn huge_amounts_do_not_overflow() {
        let s = havas_status(m(i64::MAX), m(i64::MAX)).unwrap();
        assert_eq!(s.state, HavasState::Over);
    }

    #[test]
    fn expense_necessity_overrides_category() {
        assert_eq!(
            effective_necessity(Some(Necessity::Havas), Some(Necessity::Zarur)),
            Some(Necessity::Havas)
        );
        assert_eq!(
            effective_necessity(None, Some(Necessity::Kerak)),
            Some(Necessity::Kerak)
        );
        assert_eq!(effective_necessity(None, None), None);
    }

    #[test]
    fn charity_and_gifts_never_count_as_havas() {
        let h = Some(Necessity::Havas);
        assert!(counts_as_havas(h, false, false));
        assert!(!counts_as_havas(h, true, false), "sovg'a");
        assert!(!counts_as_havas(h, false, true), "sadaqa");
        assert!(!counts_as_havas(Some(Necessity::Zarur), false, false));
        assert!(!counts_as_havas(None, false, false));
    }

    #[test]
    fn projection_and_errors() {
        let p = habit_projection(m(28_000_000), 28).unwrap();
        assert_eq!(
            (p.week.minor(), p.month.minor(), p.year.minor()),
            (7_000_000, 30_000_000, 365_000_000)
        );
        assert_eq!(habit_projection(m(1), 0), Err(HavasError::InvalidLimit));
        assert_eq!(habit_projection(m(-1), 7), Err(HavasError::InvalidAmount));
        assert!(matches!(
            habit_projection(m(i64::MAX), 1),
            Err(HavasError::Money(MoneyError::Overflow))
        ));
    }
}
