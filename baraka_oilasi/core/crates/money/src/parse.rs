use crate::{Currency, Money, MoneyError, ParseError};

fn is_group_separator(c: char) -> bool {
    matches!(c, ' ' | '\u{00A0}' | '\u{202F}')
}

/// Foydalanuvchi kiritgan summani o'qiydi: `"8 000 000"`, `"123,45"`, `"-1.5"`.
///
/// * minglik ajratuvchi: oddiy bo'shliq, NBSP yoki U+202F (faqat raqamlar orasida);
/// * kasr ajratuvchi: `,` yoki `.` (bitta), valyuta kasr xonasidan ko'p bo'lmagan raqam bilan;
/// * natija — minor birlikda, yaxlitlashsiz.
pub fn parse_amount(input: &str, currency: Currency) -> Result<Money, MoneyError> {
    let s = input.trim();
    let (negative, body) = match s.strip_prefix('-') {
        Some(rest) => (true, rest),
        None => (false, s),
    };
    if body.is_empty() {
        return Err(MoneyError::Parse(ParseError::Empty));
    }
    let exp = currency.exponent();
    let mut major: i128 = 0;
    let mut frac: i128 = 0;
    let mut frac_digits: u32 = 0;
    let mut in_frac = false;
    let mut prev_digit = false;
    let mut chars = body.chars().peekable();
    while let Some(c) = chars.next() {
        if let Some(d) = c.to_digit(10) {
            if in_frac {
                frac_digits += 1;
                if frac_digits > exp {
                    return Err(MoneyError::Parse(ParseError::TooManyDecimals));
                }
                frac = frac * 10 + i128::from(d);
            } else {
                major = major
                    .checked_mul(10)
                    .and_then(|v| v.checked_add(i128::from(d)))
                    .ok_or(MoneyError::Overflow)?;
            }
            prev_digit = true;
        } else if is_group_separator(c) {
            let next_is_digit = chars.peek().is_some_and(|n| n.is_ascii_digit());
            if in_frac || !prev_digit || !next_is_digit {
                return Err(MoneyError::Parse(ParseError::MisplacedSeparator));
            }
            prev_digit = false;
        } else if c == ',' || c == '.' {
            if in_frac || !prev_digit {
                return Err(MoneyError::Parse(ParseError::MisplacedSeparator));
            }
            if exp == 0 {
                return Err(MoneyError::Parse(ParseError::TooManyDecimals));
            }
            in_frac = true;
            prev_digit = false;
        } else {
            return Err(MoneyError::Parse(ParseError::InvalidCharacter));
        }
    }
    if !prev_digit {
        return Err(MoneyError::Parse(ParseError::MisplacedSeparator));
    }
    let scale = i128::from(currency.minor_per_major());
    let frac_scaled = frac * 10_i128.pow(exp - frac_digits);
    let value = major
        .checked_mul(scale)
        .and_then(|v| v.checked_add(frac_scaled))
        .ok_or(MoneyError::Overflow)?;
    let value = if negative { -value } else { value };
    let minor = i64::try_from(value).map_err(|_| MoneyError::Overflow)?;
    Ok(Money::new(minor, currency))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(s: &str) -> Result<i64, MoneyError> {
        parse_amount(s, Currency::Uzs).map(|m| m.minor())
    }

    #[test]
    fn accepted_inputs() {
        assert_eq!(uzs("8 000 000"), Ok(800_000_000));
        assert_eq!(uzs("8\u{a0}000\u{a0}000"), Ok(800_000_000));
        assert_eq!(uzs("8000000"), Ok(800_000_000));
        assert_eq!(uzs("123,45"), Ok(12_345));
        assert_eq!(uzs("123.4"), Ok(12_340));
        assert_eq!(uzs("-1,5"), Ok(-150));
        assert_eq!(uzs("  42 "), Ok(4_200));
        assert_eq!(
            parse_amount("1 000 000", Currency::Krw).map(|m| m.minor()),
            Ok(1_000_000)
        );
    }

    #[test]
    fn rejected_inputs() {
        assert_eq!(uzs(""), Err(MoneyError::Parse(ParseError::Empty)));
        assert_eq!(uzs("-"), Err(MoneyError::Parse(ParseError::Empty)));
        assert_eq!(
            uzs("1,234"),
            Err(MoneyError::Parse(ParseError::TooManyDecimals))
        );
        assert_eq!(
            uzs("12a"),
            Err(MoneyError::Parse(ParseError::InvalidCharacter))
        );
        assert_eq!(
            uzs("1,2,3"),
            Err(MoneyError::Parse(ParseError::MisplacedSeparator))
        );
        assert_eq!(uzs("1 "), Ok(100));
        assert_eq!(
            uzs("1  000"),
            Err(MoneyError::Parse(ParseError::MisplacedSeparator))
        );
        assert_eq!(
            uzs(",5"),
            Err(MoneyError::Parse(ParseError::MisplacedSeparator))
        );
        assert_eq!(
            uzs("5,"),
            Err(MoneyError::Parse(ParseError::MisplacedSeparator))
        );
        assert_eq!(
            parse_amount("1,5", Currency::Krw),
            Err(MoneyError::Parse(ParseError::TooManyDecimals))
        );
        assert_eq!(uzs("99999999999999999999"), Err(MoneyError::Overflow));
    }
}
