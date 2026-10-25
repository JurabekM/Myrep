//! Karta egasining telefon raqami (2-faza P2.1): tekshirish va log uchun maskalash.
//! Telefon shaxsiy ma'lumot — logga va API javobiga faqat maskalangan ko'rinishda chiqadi.

/// E.164: `+` va 7–15 raqam.
pub fn is_e164(p: &str) -> bool {
    p.len() >= 8
        && p.len() <= 16
        && p.starts_with('+')
        && p[1..].bytes().all(|b| b.is_ascii_digit())
}

/// `+998901234512` → `+998*******12`: mamlakat kodi va oxirgi 2 raqam qoladi.
pub fn mask_phone(p: &str) -> String {
    let n = p.len();
    if n < 7 || !p.is_ascii() {
        return "***".into();
    }
    format!("{}{}{}", &p[..4], "*".repeat(n - 6), &p[n - 2..])
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
        assert_eq!(mask_phone("+99890ёё12345"), "***");
    }
}
