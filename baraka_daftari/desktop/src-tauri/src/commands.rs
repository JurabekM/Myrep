use money::{allocate, Currency, Locale, Money};
use serde::Serialize;
use specta::Type;

use crate::dto::MoneyDto;

#[derive(Debug, Serialize, Type, thiserror::Error)]
#[serde(tag = "kind", content = "message")]
pub enum CommandError {
    #[error("noto'g'ri kiritish: {0}")]
    InvalidInput(String),
}

/// Namunaviy command (D1): summani nisbatlar bo'yicha bo'ladi.
/// Summa string sifatida keladi va Rustda parse qilinadi (frontend pul hisoblamaydi).
#[tauri::command]
#[specta::specta]
pub fn allocate_demo(total_minor: String, ratios: Vec<u32>) -> Result<Vec<MoneyDto>, CommandError> {
    let minor = total_minor
        .parse::<i64>()
        .map_err(|_| CommandError::InvalidInput("summa butun son bo'lishi kerak".into()))?;
    let ratios: Vec<u64> = ratios.into_iter().map(u64::from).collect();
    let parts = allocate(Money::new(minor, Currency::Uzs), &ratios)
        .map_err(|e| CommandError::InvalidInput(e.to_string()))?;
    Ok(parts
        .into_iter()
        .map(|m| MoneyDto::from_money(m, Locale::Uz))
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splits_by_ratio() {
        let parts = allocate_demo("100".into(), vec![1, 1, 1]).unwrap();
        let minors: Vec<_> = parts.iter().map(|p| p.minor.as_str()).collect();
        assert_eq!(minors, ["34", "33", "33"]);
    }

    #[test]
    fn rejects_garbage() {
        assert!(allocate_demo("12x".into(), vec![1]).is_err());
        assert!(allocate_demo("10".into(), vec![]).is_err());
    }
}
