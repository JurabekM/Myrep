use money::{format_money, Locale, Money};
use serde::Serialize;
use specta::Type;

/// Pul DTO (DESKTOP_PROMPT 3.2): `minor` JS 2^53 chegarasidan himoya uchun string.
#[derive(Debug, Clone, Serialize, Type)]
pub struct MoneyDto {
    pub minor: String,
    pub currency: String,
    pub formatted: String,
}

impl MoneyDto {
    pub fn from_money(m: Money, locale: Locale) -> Self {
        Self {
            minor: m.minor().to_string(),
            currency: m.currency().code().to_owned(),
            formatted: format_money(m, locale),
        }
    }
}
