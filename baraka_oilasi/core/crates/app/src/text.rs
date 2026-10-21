use unicode_normalization::UnicodeNormalization;

use crate::AppError;

/// Kiritilgan matn: bo'shliqlar kesiladi va **bir marta** NFC ga keltiriladi (6.4).
pub(crate) fn clean(s: &str) -> String {
    s.trim().nfc().collect()
}

pub(crate) fn clean_opt(s: Option<&str>) -> Option<String> {
    s.map(clean).filter(|t| !t.is_empty())
}

pub(crate) fn required(s: &str, field: &str) -> Result<String, AppError> {
    let t = clean(s);
    if t.is_empty() {
        Err(AppError::on("REQUIRED", field))
    } else {
        Ok(t)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nfc() {
        // «o» + birlashtiruvchi belgi -> bitta kod nuqta bo'lmasa ham baytlar barqaror bo'ladi.
        let decomposed = "e\u{0301}";
        assert_eq!(clean(decomposed), "\u{00E9}");
        assert_eq!(clean_opt(Some("   ")), None);
        assert!(required(" ", "note").is_err());
    }
}
