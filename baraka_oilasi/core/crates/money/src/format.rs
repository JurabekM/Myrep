use alloc::string::String;

use crate::{Currency, Money};

/// Ko'rsatish lokali. Formatlash shu yerda bajariladi, ICU/intl ishlatilmaydi (5.7).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Locale {
    Uz,
    UzCyrl,
    Ru,
}

impl Locale {
    pub fn from_tag(tag: &str) -> Option<Self> {
        match tag {
            "uz" => Some(Self::Uz),
            "uz-Cyrl" => Some(Self::UzCyrl),
            "ru" => Some(Self::Ru),
            _ => None,
        }
    }
}

const NBSP: char = '\u{00A0}';

fn unit(currency: Currency, locale: Locale) -> &'static str {
    match (currency, locale) {
        (Currency::Uzs, Locale::Uz) => "so\u{02BB}m",
        (Currency::Uzs, Locale::UzCyrl) => "сўм",
        (Currency::Uzs, Locale::Ru) => "сум",
        (other, _) => other.code(),
    }
}

fn push_grouped(out: &mut String, mut value: u64) {
    let mut digits = [0u8; 20];
    let mut len = 0;
    loop {
        // value % 10 < 10, shuning uchun u8 ga sig'adi
        digits[len] = b'0' + (value % 10) as u8;
        len += 1;
        value /= 10;
        if value == 0 {
            break;
        }
    }
    for i in (0..len).rev() {
        out.push(char::from(digits[i]));
        if i > 0 && i % 3 == 0 {
            out.push(NBSP);
        }
    }
}

/// `8 000 000 soʻm`, `123,45 soʻm`, `-8 000 000 soʻm`, `1 000 000 KRW` (NBSP bilan).
pub fn format_minor(minor: i64, currency: Currency, locale: Locale) -> String {
    let mut out = String::new();
    if minor < 0 {
        out.push('-');
    }
    let abs = minor.unsigned_abs();
    let exp = currency.exponent();
    let scale = 10_u64.pow(exp);
    push_grouped(&mut out, abs / scale);
    let frac = abs % scale;
    if exp > 0 && frac > 0 {
        out.push(',');
        let mut digits = [b'0'; 4];
        let mut f = frac;
        let width = exp as usize;
        for slot in digits[..width].iter_mut().rev() {
            *slot = b'0' + (f % 10) as u8;
            f /= 10;
        }
        for &d in &digits[..width] {
            out.push(char::from(d));
        }
    }
    out.push(NBSP);
    out.push_str(unit(currency, locale));
    out
}

/// Tahrirlash uchun oddiy ko'rinish: guruhlashsiz, vergul kasr bilan (`40000`, `123,45`, `-5`).
/// `parse_amount` uni aynan shu qiymatga qaytaradi — UI summani o'zi hisoblamasdan qayta yuboradi.
pub fn format_plain(minor: i64, currency: Currency) -> String {
    let mut out = String::new();
    if minor < 0 {
        out.push('-');
    }
    let abs = minor.unsigned_abs();
    let exp = currency.exponent();
    let scale = 10_u64.pow(exp);
    let mut major = alloc::format!("{}", abs / scale);
    let frac = abs % scale;
    if exp > 0 && frac > 0 {
        major.push(',');
        let digits = alloc::format!("{frac:0width$}", width = exp as usize);
        major.push_str(digits.trim_end_matches('0'));
    }
    out.push_str(&major);
    out
}

/// Basis points'ni foiz matniga aylantiradi: `600` → `6`, `650` → `6,5`, `1225` → `12,25`.
pub fn format_percent_bp(bp: i64) -> String {
    let mut out = String::new();
    if bp < 0 {
        out.push('-');
    }
    let abs = bp.unsigned_abs();
    out.push_str(&alloc::format!("{}", abs / 100));
    let frac = abs % 100;
    if frac > 0 {
        out.push(',');
        out.push_str(alloc::format!("{frac:02}").trim_end_matches('0'));
    }
    out
}

pub fn format(amount: Money, locale: Locale) -> String {
    format_minor(amount.minor(), amount.currency(), locale)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn documented_cases() {
        let uzs = |m| format_minor(m, Currency::Uzs, Locale::Uz);
        assert_eq!(uzs(800_000_000), "8\u{a0}000\u{a0}000\u{a0}so\u{2bb}m");
        assert_eq!(uzs(12_345), "123,45\u{a0}so\u{2bb}m");
        assert_eq!(uzs(-800_000_000), "-8\u{a0}000\u{a0}000\u{a0}so\u{2bb}m");
        assert_eq!(uzs(5), "0,05\u{a0}so\u{2bb}m");
        assert_eq!(uzs(0), "0\u{a0}so\u{2bb}m");
        assert_eq!(
            format_minor(800_000_000, Currency::Uzs, Locale::Ru),
            "8\u{a0}000\u{a0}000\u{a0}сум"
        );
        assert_eq!(
            format_minor(800_000_000, Currency::Uzs, Locale::UzCyrl),
            "8\u{a0}000\u{a0}000\u{a0}сўм"
        );
        assert_eq!(
            format_minor(1_000_000, Currency::Krw, Locale::Uz),
            "1\u{a0}000\u{a0}000\u{a0}KRW"
        );
        assert_eq!(
            format_minor(10_000, Currency::Usd, Locale::Uz),
            "100\u{a0}USD"
        );
    }

    #[test]
    fn plain_roundtrips_through_parse() {
        for (m, c, text) in [
            (4_000_000, Currency::Uzs, "40000"),
            (12_345, Currency::Uzs, "123,45"),
            (12_340, Currency::Uzs, "123,4"),
            (-500, Currency::Uzs, "-5"),
            (1_000_000, Currency::Krw, "1000000"),
            (0, Currency::Usd, "0"),
        ] {
            assert_eq!(format_plain(m, c), text);
            assert_eq!(crate::parse_amount(text, c).map(|x| x.minor()), Ok(m));
        }
    }

    #[test]
    fn percent_from_bp() {
        assert_eq!(format_percent_bp(600), "6");
        assert_eq!(format_percent_bp(650), "6,5");
        assert_eq!(format_percent_bp(1225), "12,25");
        assert_eq!(format_percent_bp(5), "0,05");
        assert_eq!(format_percent_bp(-250), "-2,5");
    }

    #[test]
    fn extremes() {
        assert_eq!(
            format_minor(i64::MIN, Currency::Krw, Locale::Uz),
            "-9\u{a0}223\u{a0}372\u{a0}036\u{a0}854\u{a0}775\u{a0}808\u{a0}KRW"
        );
    }
}
