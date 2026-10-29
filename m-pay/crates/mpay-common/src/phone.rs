//! Karta egasining telefon raqami (2-faza P2.1): tekshirish va log uchun maskalash.
//! Telefon shaxsiy ma'lumot — logga va API javobiga faqat maskalangan ko'rinishda chiqadi.

/// E.164: `+` va 7–15 raqam.
pub fn is_e164(p: &str) -> bool {
    p.len() >= 8
        && p.len() <= 16
        && p.starts_with('+')
        && p[1..].bytes().all(|b| b.is_ascii_digit())
}

/// Mamlakat kodi ochiq qoladigan prefikslar. E.164 kodlari 1–3 raqamli va uzunligi prefiksdan
/// ma'lum emas — noma'lum kodda birinchi raqamlarni ochsak, mahalliy raqam qismi ko'rinib qoladi.
/// TODO(spec): pilotdan keyingi bozorlar (roaming) uchun ro'yxatni kengaytirish.
const KNOWN_COUNTRY_CODES: &[&str] = &["+998"];

/// `+998901234512` → `+998*******12`: ma'lum mamlakat kodi va oxirgi 2 raqam qoladi;
/// boshqa kodlarda faqat `+` va oxirgi 2 raqam (`+12025550147` → `+*********47`).
pub fn mask_phone(p: &str) -> String {
    let n = p.len();
    if n < 7 || !p.is_ascii() {
        return "***".into();
    }
    let keep = KNOWN_COUNTRY_CODES
        .iter()
        .find(|c| p.starts_with(**c))
        .map_or(1, |c| c.len());
    format!("{}{}{}", &p[..keep], "*".repeat(n - keep - 2), &p[n - 2..])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn e164_and_mask() {
        assert!(is_e164("+998000000001"));
        assert!(!is_e164("998000000001"));
        assert!(!is_e164("+99800a"));
        assert!(!is_e164("+1234567890123456"));
        assert_eq!(mask_phone("+998901234512"), "+998*******12");
        assert_eq!(mask_phone("+1"), "***");
        assert_eq!(mask_phone("+12025550147"), "+*********47");
        assert_eq!(mask_phone("+447911123456"), "+**********56");
        assert_eq!(mask_phone("+99890ёё12345"), "***");
    }
}
