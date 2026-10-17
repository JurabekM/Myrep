use crate::{Currency, Money};

/// Ko'rsatish tili. `uz` — asosiy (lotin), `ru` — ikkinchi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Locale {
    /// O'zbekcha (lotin): `8 000 000 soʻm`.
    Uz,
    /// Ruscha: `8 000 000 сум`.
    Ru,
}

/// Bo'linmas bo'sh joy (U+00A0): guruhlarni va summani valyuta belgisidan ajratadi.
const NBSP: char = '\u{00A0}';

/// Pulni inson o'qiydigan matnga aylantiradi (mobil ilova bilan bir xil qoidalar):
///
/// * guruhlash — 3 xonadan bo'linmas bo'sh joy: `8 000 000`;
/// * kasr ajratgichi — vergul; kasr faqat tiyin (sent) nolga teng bo'lmasa ko'rsatiladi;
/// * manfiy summa — oddiy `-` belgisi bilan;
/// * valyuta belgisi bo'linmas bo'sh joy bilan: UZS — uz `soʻm` (U+02BB), ru `сум`; USD `$`, EUR `€`, RUB `₽`.
pub fn format_money(money: Money, locale: Locale) -> String {
    let per_major = money.currency().minor_per_major().unsigned_abs();
    let magnitude = money.minor().unsigned_abs();
    let major = magnitude / per_major;
    let minor = magnitude % per_major;

    let mut text = String::new();
    if money.minor() < 0 {
        text.push('-');
    }
    text.push_str(&group_thousands(major));
    if minor != 0 {
        let width = money.currency().minor_digits();
        text.push_str(&format!(",{minor:0width$}"));
    }
    text.push(NBSP);
    text.push_str(symbol(money.currency(), locale));
    text
}

/// `8000000` → `8 000 000` (har uch raqamdan keyin bo'linmas bo'sh joy).
fn group_thousands(value: u64) -> String {
    let digits = value.to_string();
    let mut grouped = String::with_capacity(digits.len() + digits.len() / 3);
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index).is_multiple_of(3) {
            grouped.push(NBSP);
        }
        grouped.push(digit);
    }
    grouped
}

const fn symbol(currency: Currency, locale: Locale) -> &'static str {
    match (currency, locale) {
        // O'zbek imlosi: U+02BB (ʻ), oddiy apostrof emas.
        (Currency::Uzs, Locale::Uz) => "so\u{02BB}m",
        (Currency::Uzs, Locale::Ru) => "сум",
        (Currency::Usd, _) => "$",
        (Currency::Eur, _) => "€",
        (Currency::Rub, _) => "₽",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn text(minor: i64, currency: Currency, locale: Locale) -> String {
        format_money(Money::new(minor, currency), locale)
    }

    #[test]
    fn uzs_ikki_tilda() {
        assert_eq!(
            text(800_000_000, Currency::Uzs, Locale::Uz),
            "8\u{a0}000\u{a0}000\u{a0}so\u{2bb}m"
        );
        assert_eq!(
            text(800_000_000, Currency::Uzs, Locale::Ru),
            "8\u{a0}000\u{a0}000\u{a0}сум"
        );
    }

    #[test]
    fn kasr_faqat_tiyin_bolsa() {
        assert_eq!(
            text(800_000_050, Currency::Uzs, Locale::Uz),
            "8\u{a0}000\u{a0}000,50\u{a0}so\u{2bb}m"
        );
        assert_eq!(text(99, Currency::Uzs, Locale::Uz), "0,99\u{a0}so\u{2bb}m");
        assert_eq!(text(1250, Currency::Usd, Locale::Uz), "12,50\u{a0}$");
    }

    #[test]
    fn manfiy_va_nol() {
        assert_eq!(
            text(-150_000_000, Currency::Uzs, Locale::Uz),
            "-1\u{a0}500\u{a0}000\u{a0}so\u{2bb}m"
        );
        assert_eq!(text(0, Currency::Uzs, Locale::Uz), "0\u{a0}so\u{2bb}m");
    }

    #[test]
    fn tiyin_nol_bilan_toldiriladi() {
        assert_eq!(text(105, Currency::Usd, Locale::Uz), "1,05\u{a0}$");
    }

    #[test]
    fn valyuta_belgilari() {
        assert_eq!(text(100, Currency::Eur, Locale::Ru), "1\u{a0}€");
        assert_eq!(text(100, Currency::Rub, Locale::Uz), "1\u{a0}₽");
    }

    #[test]
    fn eng_chekka_qiymatlar() {
        assert_eq!(
            text(i64::MIN, Currency::Uzs, Locale::Uz),
            "-92\u{a0}233\u{a0}720\u{a0}368\u{a0}547\u{a0}758,08\u{a0}so\u{2bb}m"
        );
        assert_eq!(
            text(i64::MAX, Currency::Uzs, Locale::Ru),
            "92\u{a0}233\u{a0}720\u{a0}368\u{a0}547\u{a0}758,07\u{a0}сум"
        );
    }
}
