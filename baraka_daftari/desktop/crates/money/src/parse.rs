use crate::{Currency, Money, MoneyError};

/// Foydalanuvchi kiritgan summa matnini (asosiy birlikda, masalan so'mda) `Money` ga o'giradi.
///
/// Qoidalar (spec/test-vectors/money_parse.json):
/// - raqamlar; guruhlash uchun oddiy probel yoki NBSP (`U+00A0`); chetdagi probellar tashlanadi;
/// - kasr ajratgich `,` yoki `.` — bittadan ortiq emas va undan keyin 1–2 raqam;
/// - manfiy belgi, ilmiy yozuv, boshqa belgilar va ASCII bo'lmagan raqamlar rad etiladi.
///
/// # Errors
/// Format noto'g'ri bo'lsa [`MoneyError::Parse`], `i64` ga sig'masa [`MoneyError::Overflow`].
pub fn parse_amount(text: &str, currency: Currency) -> Result<Money, MoneyError> {
    let bad = || MoneyError::Parse(text.trim().to_owned());
    let t = text.trim_matches(|c: char| c == ' ' || c == '\u{a0}');
    let (int_part, frac_part) = match t.find([',', '.']) {
        Some(i) => (&t[..i], Some(&t[i + 1..])),
        None => (t, None),
    };
    let int_digits: String = int_part
        .chars()
        .filter(|c| *c != ' ' && *c != '\u{a0}')
        .collect();
    if int_digits.is_empty() || !int_digits.bytes().all(|b| b.is_ascii_digit()) {
        return Err(bad());
    }
    let scale = 10i128.pow(currency.minor_digits());
    let frac_minor: i128 = match frac_part {
        None => 0,
        Some(f) if (1..=2).contains(&f.len()) && f.bytes().all(|b| b.is_ascii_digit()) => {
            let n: i128 = f.parse().map_err(|_| bad())?;
            if f.len() == 1 {
                n * 10
            } else {
                n
            }
        }
        Some(_) => return Err(bad()),
    };
    let major: i128 = int_digits.parse().map_err(|_| MoneyError::Overflow)?;
    let minor = major
        .checked_mul(scale)
        .and_then(|v| v.checked_add(frac_minor))
        .ok_or(MoneyError::Overflow)?;
    i64::try_from(minor)
        .map(|m| Money::new(m, currency))
        .map_err(|_| MoneyError::Overflow)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn p(s: &str) -> Result<i64, MoneyError> {
        parse_amount(s, Currency::Uzs).map(Money::minor)
    }

    #[test]
    fn accepts_common_inputs() {
        assert_eq!(p("800000"), Ok(80_000_000));
        assert_eq!(p("8 000 000"), Ok(800_000_000));
        assert_eq!(p("1500,50"), Ok(150_050));
        assert_eq!(p("1500.5"), Ok(150_050));
        assert_eq!(p("0,99"), Ok(99));
        assert_eq!(p(" 7 "), Ok(700));
    }

    #[test]
    fn rejects_garbage() {
        for bad in [
            "", " ", "abc", "1,234,56", "1,234", "12,", ",5", "-5", "+5", "1e6", "1.5.0", "٣٠٠",
            "1 2 ,5 6",
        ] {
            assert!(matches!(p(bad), Err(MoneyError::Parse(_))), "{bad:?}");
        }
    }

    #[test]
    fn overflow_is_detected() {
        assert_eq!(p("99999999999999999999"), Err(MoneyError::Overflow));
        assert_eq!(p("92233720368547758,07"), Ok(i64::MAX));
        assert_eq!(p("92233720368547758,08"), Err(MoneyError::Overflow));
        assert_eq!(p("92233720368547759"), Err(MoneyError::Overflow));
    }

    #[test]
    fn uses_currency() {
        assert_eq!(
            parse_amount("1,5", Currency::Usd).unwrap().currency(),
            Currency::Usd
        );
    }
}
