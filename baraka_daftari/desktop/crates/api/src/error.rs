//! Frontendga qaytadigan xatolar (`CommandError`) va ularning servis/sessiya xatolaridan xaritalanishi.
//! Tauri'siz: testlar har qanday platformada ishlaydi.

use money::MoneyError;
use security::SecurityError;
use serde::Serialize;
use services::ServiceError;
use specta::Type;

use crate::session::{SessionError, VaultState};

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
    /// Eksport paroli noto'g'ri yoki fayl buzilgan.
    WrongPassword,
    /// Eksport paroli 8 belgidan qisqa.
    WeakPassword,
    /// Almashish fayli yaroqsiz yoki yangiroq versiyada.
    BadFile {
        message: String,
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
            ServiceError::WrongPassword => Self::WrongPassword,
            ServiceError::WeakPassword => Self::WeakPassword,
            ServiceError::BadFile(message) => Self::BadFile { message },
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

#[cfg(test)]
mod tests {
    use super::*;

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
