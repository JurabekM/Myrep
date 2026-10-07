use crate::MoneyError;

/// Yagona markazlashgan yaxlitlash: `num / den` ni **half-up** (+∞ tomon) yaxlitlaydi.
/// `den > 0` bo'lishi shart. Boshqa joyda yaxlitlash taqiqlanadi.
///
/// Musbat qiymatlarda 0,5 → 1; manfiylarda -0,5 → 0 (ya'ni `floor(x + 1/2)`).
///
/// # Errors
/// `den <= 0` yoki natija `i64` ga sig'masa [`MoneyError`].
pub fn round_half_up(num: i128, den: i128) -> Result<i64, MoneyError> {
    if den <= 0 {
        return Err(MoneyError::InvalidRate);
    }
    let two_num = num.checked_mul(2).ok_or(MoneyError::Overflow)?;
    let two_den = den.checked_mul(2).ok_or(MoneyError::Overflow)?;
    let shifted = two_num.checked_add(den).ok_or(MoneyError::Overflow)?;
    i64::try_from(shifted.div_euclid(two_den)).map_err(|_| MoneyError::Overflow)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn half_goes_up() {
        assert_eq!(round_half_up(1, 2).unwrap(), 1);
        assert_eq!(round_half_up(3, 2).unwrap(), 2);
        assert_eq!(round_half_up(4, 3).unwrap(), 1);
        assert_eq!(round_half_up(5, 3).unwrap(), 2);
        assert_eq!(round_half_up(-1, 2).unwrap(), 0);
        assert_eq!(round_half_up(-3, 2).unwrap(), -1);
    }

    #[test]
    fn rejects_bad_denominator() {
        assert!(round_half_up(1, 0).is_err());
        assert!(round_half_up(1, -2).is_err());
    }

    #[test]
    fn detects_overflow() {
        assert_eq!(round_half_up(i128::MAX, 1), Err(MoneyError::Overflow));
        assert_eq!(
            round_half_up(i128::from(i64::MAX) + 1, 1),
            Err(MoneyError::Overflow)
        );
    }
}
