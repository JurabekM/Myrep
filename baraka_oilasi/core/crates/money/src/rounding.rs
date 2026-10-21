use crate::MoneyError;

/// Yagona yaxlitlash funksiyasi: `num / den` ni **yarimni noldan uzoqqa** yaxlitlaydi (5.3).
///
/// `round_half_up(5, 2) = 3`, `round_half_up(-5, 2) = -3`, `round_half_up(-12, 5) = -2`.
pub fn round_half_up(num: i128, den: i128) -> Result<i128, MoneyError> {
    if den == 0 {
        return Err(MoneyError::DivisionByZero);
    }
    let negative = (num < 0) != (den < 0);
    let n = num.unsigned_abs();
    let d = den.unsigned_abs();
    let mut q = n / d;
    let r = n % d;
    // r >= d - r  <=>  2r >= d, overflow'siz
    if r >= d - r {
        q += 1;
    }
    let q = i128::try_from(q).map_err(|_| MoneyError::Overflow)?;
    Ok(if negative { -q } else { q })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn half_away_from_zero() {
        assert_eq!(round_half_up(5, 2), Ok(3));
        assert_eq!(round_half_up(-5, 2), Ok(-3));
        assert_eq!(round_half_up(-12, 5), Ok(-2));
        assert_eq!(round_half_up(7, 2), Ok(4));
        assert_eq!(round_half_up(5, -2), Ok(-3));
        assert_eq!(round_half_up(1, 3), Ok(0));
        assert_eq!(round_half_up(0, 7), Ok(0));
        assert_eq!(round_half_up(1, 0), Err(MoneyError::DivisionByZero));
    }

    #[test]
    fn extreme_values_do_not_overflow() {
        assert_eq!(round_half_up(i128::MAX, i128::MAX), Ok(1));
        assert_eq!(round_half_up(i128::MAX, 1), Ok(i128::MAX));
        assert_eq!(round_half_up(i128::MIN, 1), Err(MoneyError::Overflow));
    }
}
