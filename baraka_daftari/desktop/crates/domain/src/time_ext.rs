use time::{
    format_description::well_known::Rfc3339, macros::format_description, Date, OffsetDateTime,
};

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("noto'g'ri sana yoki vaqt: {0}")]
pub struct TimeError(pub String);

/// UTC instant → ISO-8601 (RFC 3339).
///
/// # Errors
/// Formatlash imkonsiz bo'lsa.
pub fn ts_to_string(t: OffsetDateTime) -> Result<String, TimeError> {
    t.to_offset(time::UtcOffset::UTC)
        .format(&Rfc3339)
        .map_err(|e| TimeError(e.to_string()))
}

/// # Errors
/// Matn RFC 3339 bo'lmasa.
pub fn ts_from_str(s: &str) -> Result<OffsetDateTime, TimeError> {
    OffsetDateTime::parse(s, &Rfc3339).map_err(|e| TimeError(e.to_string()))
}

/// Lokal sana (`Asia/Tashkent` bo'yicha) `YYYY-MM-DD` ko'rinishida saqlanadi.
///
/// # Errors
/// Formatlash imkonsiz bo'lsa.
pub fn date_to_string(d: Date) -> Result<String, TimeError> {
    d.format(format_description!("[year]-[month]-[day]"))
        .map_err(|e| TimeError(e.to_string()))
}

/// # Errors
/// Matn `YYYY-MM-DD` bo'lmasa.
pub fn date_from_str(s: &str) -> Result<Date, TimeError> {
    Date::parse(s, format_description!("[year]-[month]-[day]"))
        .map_err(|e| TimeError(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrips() {
        let t = ts_from_str("2026-10-07T05:03:16Z").unwrap();
        assert_eq!(ts_to_string(t).unwrap(), "2026-10-07T05:03:16Z");
        let d = date_from_str("2026-10-07").unwrap();
        assert_eq!(date_to_string(d).unwrap(), "2026-10-07");
        assert!(date_from_str("07.10.2026").is_err());
    }

    #[test]
    fn non_utc_offset_is_normalized() {
        let t = ts_from_str("2026-10-07T10:00:00+05:00").unwrap();
        assert_eq!(ts_to_string(t).unwrap(), "2026-10-07T05:00:00Z");
    }
}
