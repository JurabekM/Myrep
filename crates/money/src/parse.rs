//! Foydalanuvchi kiritgan summa matnini [`Money`] ga aylantirish (DESKTOP_PROMPT.md 4-bo'lim).
//!
//! Qoidalar `spec/test-vectors/money_parse.json` bilan bir xil: bo'sh joy, `_` va apostroflar
//! e'tiborsiz; valyuta so'zi yoki belgisi (`so'm`, `soʻm`, `сум`, `$`, `€`, `₽`) oxiridan olib
//! tashlanadi; kasr qismi valyuta aniqligidan ko'p bo'lsa — xato.

use crate::{Currency, Money, MoneyError};

/// Butun qismning eng ko'p raqamlari soni (toshishdan himoya).
const MAX_MAJOR_DIGITS: usize = 15;

/// Matnni summaga aylantiradi. Noto'g'ri yozuv — [`MoneyError::ParseError`].
pub fn parse_amount(text: &str, currency: Currency) -> Result<Money, MoneyError> {
    let cleaned = strip_decorations(text);
    let (negative, body) = match cleaned.strip_prefix('-') {
        Some(rest) => (true, rest),
        None => (false, cleaned.as_str()),
    };
    let (major, fraction) = split_number(body).ok_or(MoneyError::ParseError)?;

    if major.len() > MAX_MAJOR_DIGITS || fraction.len() > currency.minor_digits() {
        return Err(MoneyError::ParseError);
    }
    let major_value: i64 = major.parse().map_err(|_| MoneyError::ParseError)?;
    let mut minor_text = fraction.to_owned();
    while minor_text.len() < currency.minor_digits() {
        minor_text.push('0');
    }
    let minor_value: i64 = if minor_text.is_empty() {
        0
    } else {
        minor_text.parse().map_err(|_| MoneyError::ParseError)?
    };

    let value = major_value
        .checked_mul(currency.minor_per_major())
        .and_then(|scaled| scaled.checked_add(minor_value))
        .ok_or(MoneyError::Overflow)?;
    Ok(Money::new(if negative { -value } else { value }, currency))
}

/// Bo'sh joy, `_` va ASCII apostrof olib tashlanadi; so'ng valyuta belgisi yoki so'zi oxiridan.
fn strip_decorations(text: &str) -> String {
    let stripped: String = text
        .chars()
        .filter(|c| !c.is_whitespace() && *c != '_' && *c != '\'')
        .collect();
    let mut chars: Vec<char> = stripped.chars().collect();
    strip_currency_suffix(&mut chars);
    chars.into_iter().collect()
}

/// Oxiridagi valyuta belgisini yoki so'zini olib tashlaydi (bir marta, katta-kichik harf farqisiz).
fn strip_currency_suffix(chars: &mut Vec<char>) {
    let Some(&last) = chars.last() else {
        return;
    };
    if matches!(last, '$' | '€' | '₽') {
        chars.pop();
        return;
    }
    for word in ["сум", "som"] {
        if ends_with_ignore_case(chars, word) {
            let keep = chars.len() - word.chars().count();
            chars.truncate(keep);
            return;
        }
    }
    // «so» + ixtiyoriy apostrof (U+2018, U+2019, U+02BB, U+02BC, `) + «m».
    if last.eq_ignore_ascii_case(&'m') && chars.len() >= 3 {
        let mut end = chars.len() - 1;
        if end >= 1 && is_apostrophe(chars[end - 1]) {
            end -= 1;
        }
        if end >= 2
            && chars[end - 2].eq_ignore_ascii_case(&'s')
            && chars[end - 1].eq_ignore_ascii_case(&'o')
        {
            chars.truncate(end - 2);
        }
    }
}

fn is_apostrophe(c: char) -> bool {
    matches!(c, '‘' | '’' | 'ʻ' | 'ʼ' | '`')
}

/// Belgilar ketma-ketligi oxirida `word` bormi (har bir belgi kichik harfga keltirilib solishtiriladi).
fn ends_with_ignore_case(chars: &[char], word: &str) -> bool {
    let word: Vec<char> = word.chars().collect();
    chars.len() >= word.len()
        && chars[chars.len() - word.len()..]
            .iter()
            .zip(&word)
            .all(|(a, b)| a.to_lowercase().eq(b.to_lowercase()))
}

/// `digits[.,]digits` yoki `digits` ni (butun, kasr) juftiga ajratadi. Boshqa shakl — `None`.
fn split_number(body: &str) -> Option<(&str, &str)> {
    let Some(separator) = body.find(['.', ',']) else {
        return is_digits(body).then_some((body, ""));
    };
    let (major, rest) = body.split_at(separator);
    let fraction = &rest[1..];
    if !is_digits(major) || !is_digits(fraction) {
        return None;
    }
    Some((major, fraction))
}

/// Faqat ASCII raqamlardan iborat va bo'sh bo'lmagan satr.
fn is_digits(text: &str) -> bool {
    !text.is_empty() && text.bytes().all(|b| b.is_ascii_digit())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(text: &str) -> Result<i64, MoneyError> {
        parse_amount(text, Currency::Uzs).map(Money::minor)
    }

    #[test]
    fn butun_summa_bo_sh_joy_bilan() {
        assert_eq!(uzs("8 000 000"), Ok(800_000_000));
        assert_eq!(uzs("8_000_000"), Ok(800_000_000));
    }

    #[test]
    fn valyuta_belgisi_va_apostroflar() {
        assert_eq!(uzs("8 000 000 soʻm"), Ok(800_000_000));
        for suffix in ["so'm", "so‘m", "so’m", "soʻm", "soʼm", "so`m", "som", "SOM"] {
            assert_eq!(uzs(&format!("1 500 {suffix}")), Ok(150_000), "{suffix}");
        }
        assert_eq!(uzs("150 000 сум"), Ok(15_000_000));
        assert_eq!(
            parse_amount("12.50 $", Currency::Usd).map(Money::minor),
            Ok(1250)
        );
        assert_eq!(
            parse_amount("5 €", Currency::Eur).map(Money::minor),
            Ok(500)
        );
    }

    #[test]
    fn kasr_qismi_va_manfiy() {
        assert_eq!(uzs("8000000,5"), Ok(800_000_050));
        assert_eq!(uzs("-300"), Ok(-30_000));
        assert_eq!(
            parse_amount("12.50", Currency::Usd).map(Money::minor),
            Ok(1250)
        );
    }

    #[test]
    fn notogri_yozuvlar_xato_beradi() {
        for bad in [
            "",
            "abc",
            "1,234",
            "1111111111111111",
            "-",
            "1..2",
            "1,",
            ",5",
        ] {
            assert_eq!(uzs(bad), Err(MoneyError::ParseError), "{bad:?}");
        }
    }

    #[test]
    fn valyuta_so_zi_raqamdan_oldin_emas() {
        assert_eq!(uzs("som 100"), Err(MoneyError::ParseError));
    }
}
