use crate::{Money, MoneyError};

/// `amount` ni `step_minor` karraligacha **yuqoriga** yaxlitlaydi (ceiling). Qadam musbat bo'lishi shart.
///
/// Ulush taklifi uchun: 7 500 so'm → 1 000 so'mgacha → 8 000 so'm. Yuqoriga yaxlitlash
/// [`round_half_up_div`] dan boshqa qoida, shuning uchun u ham shu modulda turadi.
pub fn ceil_to_step(amount: Money, step_minor: i64) -> Result<Money, MoneyError> {
    if step_minor <= 0 {
        return Err(MoneyError::InvalidDenominator);
    }
    let minor = i128::from(amount.minor());
    let step = i128::from(step_minor);
    let floor_steps = minor.div_euclid(step);
    let steps = if minor.rem_euclid(step) == 0 {
        floor_steps
    } else {
        floor_steps + 1
    };
    let value = i64::try_from(steps * step).map_err(|_| MoneyError::Overflow)?;
    Ok(Money::new(value, amount.currency()))
}

/// `numerator / denominator` ni butun songa yaxlitlaydi: yarmi noldan uzoqqa (half-up).
///
/// Misollar: `5/2 → 3`, `−5/2 → −3`, `7/3 → 2`, `−7/3 → −2`.
///
/// Bu loyihadagi **yagona** yaxlitlash joyi (DESKTOP_PROMPT.md 4-bo'lim, 6-qoida): boshqa joyda
/// yaxlitlash taqiqlangan. Maxraj musbat bo'lishi shart.
pub fn round_half_up_div(numerator: i128, denominator: i128) -> Result<i128, MoneyError> {
    if denominator <= 0 {
        return Err(MoneyError::InvalidDenominator);
    }
    let quotient = numerator / denominator; // nolga qarab kesiladi
    let remainder = numerator % denominator; // ishorasi surat ishorasi bilan bir xil
    if remainder == 0 {
        return Ok(quotient);
    }
    // |remainder| < denominator, shuning uchun 2·|remainder| u128 da sig'adi.
    let twice_remainder = remainder.unsigned_abs() * 2;
    if twice_remainder < denominator.unsigned_abs() {
        return Ok(quotient);
    }
    // Kasr yarmi yoki undan ko'p: noldan uzoqqa bir birlik.
    Ok(if numerator > 0 {
        quotient + 1
    } else {
        quotient - 1
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn round(numerator: i128, denominator: i128) -> i128 {
        round_half_up_div(numerator, denominator).expect("maxraj musbat")
    }

    #[test]
    fn yarmi_noldan_uzoqqa() {
        assert_eq!(round(5, 2), 3);
        assert_eq!(round(-5, 2), -3);
        assert_eq!(round(7, 3), 2);
        assert_eq!(round(-7, 3), -2);
        assert_eq!(round(5, 3), 2);
        assert_eq!(round(-5, 3), -2);
    }

    #[test]
    fn butun_son_va_nol_ozgarmaydi() {
        assert_eq!(round(0, 7), 0);
        assert_eq!(round(12, 4), 3);
        assert_eq!(round(-12, 4), -3);
    }

    #[test]
    fn maxraj_musbat_bolishi_shart() {
        assert_eq!(round_half_up_div(1, 0), Err(MoneyError::InvalidDenominator));
        assert_eq!(
            round_half_up_div(1, -2),
            Err(MoneyError::InvalidDenominator)
        );
    }
}
