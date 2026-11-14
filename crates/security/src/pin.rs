use crate::SecurityError;

/// PIN uzunligi: aniq 6 ta raqam (DESKTOP_PROMPT.md 6.2).
pub const PIN_LEN: usize = 6;

/// PIN formatini tekshiradi: aniq 6 ta ASCII raqam. Qiymat hech qayerga saqlanmaydi.
pub fn validate_pin(pin: &str) -> Result<(), SecurityError> {
    if pin.len() == PIN_LEN && pin.bytes().all(|byte| byte.is_ascii_digit()) {
        Ok(())
    } else {
        Err(SecurityError::InvalidPin)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn olti_raqamli_pin_qabul_qilinadi() {
        assert!(validate_pin("135790").is_ok());
        assert!(validate_pin("000000").is_ok());
    }

    #[test]
    fn notogri_pin_rad_etiladi() {
        for pin in ["12345", "1234567", "12a456", " 12345", "", "١٢٣٤٥٦"] {
            assert!(
                matches!(validate_pin(pin), Err(SecurityError::InvalidPin)),
                "{pin:?} rad etilishi kerak"
            );
        }
    }
}
