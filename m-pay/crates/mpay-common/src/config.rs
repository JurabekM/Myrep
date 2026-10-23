//! Umumiy konfiguratsiya bo'laklari va TOML yuklovchi.

use std::path::Path;

use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Konfiguratsiya xatolari.
#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("konfiguratsiya faylini o'qib bo'lmadi: {path}: {source}")]
    Io {
        path: String,
        source: std::io::Error,
    },
    #[error("konfiguratsiya TOML xatosi: {0}")]
    Toml(#[from] toml::de::Error),
    #[error("konfiguratsiya qiymati noto'g'ri: {0}")]
    Invalid(String),
}

/// TOML faylni o'qiydi.
pub fn load_toml<T: DeserializeOwned>(path: &Path) -> Result<T, ConfigError> {
    let text = std::fs::read_to_string(path).map_err(|source| ConfigError::Io {
        path: path.display().to_string(),
        source,
    })?;
    Ok(toml::from_str(&text)?)
}

/// LUK siyosati (`emv-profile.md` §8).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct LukPolicy {
    /// Bitta LUK bilan ruxsat etilgan tranzaksiyalar soni.
    pub max_uses: u32,
    /// LUK amal qilish muddati (sekund).
    pub ttl_secs: u64,
    /// Provisioning yoki to'ldirishda beriladigan LUK'lar soni.
    pub batch_size: u32,
}

impl Default for LukPolicy {
    fn default() -> Self {
        Self {
            max_uses: 10,
            ttl_secs: 24 * 3600,
            batch_size: 5,
        }
    }
}

impl LukPolicy {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.max_uses == 0 || self.ttl_secs == 0 || self.batch_size == 0 || self.batch_size > 100
        {
            return Err(ConfigError::Invalid(
                "luk: max_uses, ttl_secs > 0 va 1 <= batch_size <= 100 bo'lishi shart".into(),
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn luk_defaults_and_parse() {
        let p: LukPolicy = toml::from_str("max_uses = 3").unwrap();
        assert_eq!(p.max_uses, 3);
        assert_eq!(p.ttl_secs, 86_400);
        assert!(p.validate().is_ok());
        assert!(toml::from_str::<LukPolicy>("unknown = 1").is_err());
        assert!(LukPolicy {
            max_uses: 0,
            ..Default::default()
        }
        .validate()
        .is_err());
    }
}
