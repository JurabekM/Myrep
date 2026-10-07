use std::sync::Mutex;

use money::{allocate, Currency, Locale, Money, MoneyError};
use security::{KeyringStore, SecurityError};
use serde::Serialize;
use services::ServiceError;
use specta::Type;
use tauri::State;
use zeroize::Zeroizing;

use crate::{
    dto::MoneyDto,
    session::{Session, SessionError, VaultState},
};

pub type AppSession = Mutex<Session<KeyringStore>>;

/// Frontendga qaytadigan xatolar. Matnlarda summa, ism yoki PIN bo'lmaydi.
#[derive(Debug, Serialize, Type)]
#[serde(tag = "kind")]
pub enum CommandError {
    InvalidPin,
    WrongPin,
    Locked {
        retry_after_secs: u32,
    },
    NotInitialized,
    AlreadyInitialized,
    KeyringMissing,
    /// Summa matni noto'g'ri (masalan, "12abc").
    InvalidAmount,
    Invalid {
        message: String,
    },
    NotFound,
    InsufficientFunds,
    OpeningBalanceExists,
    /// A'zoning PIN'i noto'g'ri (havas chegarasiga rozilik).
    MemberWrongPin,
    MemberPinLocked {
        retry_after_secs: u32,
    },
    MemberNoPin,
    /// "Kelajagim"dan pul olish pauzasi tugamagan.
    Cooling {
        remaining_secs: u32,
    },
    Internal {
        message: String,
    },
}

impl From<ServiceError> for CommandError {
    fn from(e: ServiceError) -> Self {
        match e {
            ServiceError::Money(MoneyError::Parse(_)) => Self::InvalidAmount,
            ServiceError::Invalid(m) => Self::Invalid {
                message: m.to_owned(),
            },
            ServiceError::NotFound => Self::NotFound,
            ServiceError::InsufficientFunds => Self::InsufficientFunds,
            ServiceError::OpeningBalanceExists => Self::OpeningBalanceExists,
            ServiceError::WrongPin => Self::MemberWrongPin,
            ServiceError::PinLocked { retry_after_secs } => Self::MemberPinLocked {
                retry_after_secs: secs(retry_after_secs),
            },
            ServiceError::NoPin => Self::MemberNoPin,
            ServiceError::Cooling { remaining_secs } => Self::Cooling {
                remaining_secs: u32::try_from(remaining_secs.max(0)).unwrap_or(u32::MAX),
            },
            // Ichki xato matnlarida ma'lumot bo'lmasligi uchun umumiy xabar.
            ServiceError::Storage(_) | ServiceError::Money(_) => Self::Internal {
                message: "xizmat xatosi".into(),
            },
        }
    }
}

fn secs(v: u64) -> u32 {
    u32::try_from(v).unwrap_or(u32::MAX)
}

impl From<SessionError> for CommandError {
    fn from(e: SessionError) -> Self {
        match e {
            SessionError::Security(s) => match s {
                SecurityError::InvalidPin => Self::InvalidPin,
                SecurityError::WrongPin => Self::WrongPin,
                SecurityError::Locked { retry_after_secs } => Self::Locked {
                    retry_after_secs: secs(retry_after_secs),
                },
                SecurityError::NotInitialized => Self::NotInitialized,
                SecurityError::AlreadyInitialized => Self::AlreadyInitialized,
                SecurityError::KeyringMissing => Self::KeyringMissing,
                other => Self::Internal {
                    message: other.to_string(),
                },
            },
            SessionError::Locked => Self::Locked {
                retry_after_secs: 0,
            },
            SessionError::Storage(_) => Self::Internal {
                message: "baza xatosi".into(),
            },
            SessionError::Service(s) => s.into(),
        }
    }
}

#[derive(Debug, Serialize, Type)]
#[serde(tag = "kind")]
pub enum VaultStateDto {
    Uninitialized,
    Locked { retry_after_secs: u32 },
    Unlocked,
}

impl From<VaultState> for VaultStateDto {
    fn from(s: VaultState) -> Self {
        match s {
            VaultState::Uninitialized => Self::Uninitialized,
            VaultState::Locked { retry_after_secs } => Self::Locked {
                retry_after_secs: secs(retry_after_secs),
            },
            VaultState::Unlocked => Self::Unlocked,
        }
    }
}

pub fn unix_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::SystemTime::UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

pub fn with_session<T>(
    state: &State<'_, AppSession>,
    f: impl FnOnce(&mut Session<KeyringStore>) -> Result<T, SessionError>,
) -> Result<T, CommandError> {
    let mut guard = state
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    f(&mut guard).map_err(Into::into)
}

#[tauri::command]
#[specta::specta]
pub fn vault_state(state: State<'_, AppSession>) -> Result<VaultStateDto, CommandError> {
    with_session(&state, |s| s.state()).map(Into::into)
}

/// Birinchi ishga tushirish: PIN o'rnatadi va bazani ochadi.
#[tauri::command]
#[specta::specta]
pub fn setup_pin(pin: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    let pin = Zeroizing::new(pin);
    with_session(&state, |s| s.setup(&pin, unix_now()))
}

#[tauri::command]
#[specta::specta]
pub fn unlock(pin: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    let pin = Zeroizing::new(pin);
    with_session(&state, |s| s.unlock(&pin, unix_now()))
}

#[tauri::command]
#[specta::specta]
pub fn lock(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.lock();
        Ok(())
    })
}

/// Foydalanuvchi faolligi: avto-qulf hisoblagichini yangilaydi.
#[tauri::command]
#[specta::specta]
pub fn activity(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.touch(unix_now());
        Ok(())
    })
}

#[derive(Debug, Serialize, Type)]
#[serde(tag = "kind")]
pub enum DemoError {
    InvalidInput { message: String },
}

/// Namunaviy command (D1): summani nisbatlar bo'yicha bo'ladi.
/// Summa string sifatida keladi va Rustda parse qilinadi (frontend pul hisoblamaydi).
#[tauri::command]
#[specta::specta]
pub fn allocate_demo(total_minor: String, ratios: Vec<u32>) -> Result<Vec<MoneyDto>, DemoError> {
    let minor = total_minor
        .parse::<i64>()
        .map_err(|_| DemoError::InvalidInput {
            message: "summa butun son bo'lishi kerak".into(),
        })?;
    let ratios: Vec<u64> = ratios.into_iter().map(u64::from).collect();
    let parts = allocate(Money::new(minor, Currency::Uzs), &ratios).map_err(|e| {
        DemoError::InvalidInput {
            message: e.to_string(),
        }
    })?;
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

    #[test]
    fn security_errors_map_to_dedicated_variants() {
        let e: CommandError = SessionError::Security(SecurityError::Locked {
            retry_after_secs: 30,
        })
        .into();
        assert!(matches!(
            e,
            CommandError::Locked {
                retry_after_secs: 30
            }
        ));
        let e: CommandError = SessionError::Security(SecurityError::WrongPin).into();
        assert!(matches!(e, CommandError::WrongPin));
        let e: CommandError = SessionError::Locked.into();
        assert!(matches!(
            e,
            CommandError::Locked {
                retry_after_secs: 0
            }
        ));
    }
}
