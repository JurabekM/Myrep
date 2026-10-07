use crate::{Currency, Money};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Locale {
    Uz,
    Ru,
}

/// Ko'rsatish uchun formatlash. Qoidalar (spec/test-vectors/money_format.json):
/// - minglar oddiy probel bilan ajratiladi, kasr qismi vergul bilan (`12 345,67`);
/// - kasr nol bo'lsa tushirib qoldiriladi (`8 000 000`);
/// - manfiy qiymat oldida ASCII `-`;
/// - qo'shimcha: `uz` — `so'm` (UZS) yoki valyuta kodi, `ru` — `сум` (UZS) yoki valyuta kodi.
#[must_use]
pub fn format_money(m: Money, locale: Locale) -> String {
    let abs = i128::from(m.minor()).unsigned_abs();
    let scale = 10u128.pow(m.currency().minor_digits());
    let (major, frac) = (abs / scale, abs % scale);

    let digits = major.to_string();
    let mut grouped = String::with_capacity(digits.len() + digits.len() / 3);
    for (i, ch) in digits.chars().enumerate() {
        if i > 0 && (digits.len() - i) % 3 == 0 {
            grouped.push(' ');
        }
        grouped.push(ch);
    }

    let mut out = String::new();
    if m.is_negative() {
        out.push('-');
    }
    out.push_str(&grouped);
    if frac != 0 {
        out.push(',');
        out.push_str(&format!("{frac:02}"));
    }
    out.push(' ');
    out.push_str(suffix(m.currency(), locale));
    out
}

const fn suffix(currency: Currency, locale: Locale) -> &'static str {
    match (currency, locale) {
        (Currency::Uzs, Locale::Uz) => "so'm",
        (Currency::Uzs, Locale::Ru) => "сум",
        (other, _) => other.code(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn groups_and_suffixes() {
        assert_eq!(
            format_money(Money::new(800_000_000, Currency::Uzs), Locale::Uz),
            "8 000 000 so'm"
        );
        assert_eq!(
            format_money(Money::new(800_000_050, Currency::Uzs), Locale::Uz),
            "8 000 000,50 so'm"
        );
        assert_eq!(
            format_money(Money::new(99, Currency::Uzs), Locale::Uz),
            "0,99 so'm"
        );
        assert_eq!(
            format_money(Money::new(-150_000, Currency::Uzs), Locale::Uz),
            "-1 500 so'm"
        );
        assert_eq!(
            format_money(Money::new(800_000_000, Currency::Uzs), Locale::Ru),
            "8 000 000 сум"
        );
        assert_eq!(
            format_money(Money::new(12345, Currency::Usd), Locale::Uz),
            "123,45 USD"
        );
    }

    #[test]
    fn handles_i64_min() {
        let s = format_money(Money::new(i64::MIN, Currency::Uzs), Locale::Uz);
        assert!(s.starts_with("-92 233 720 368 547 758,08"));
    }
}
