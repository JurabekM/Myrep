use std::fmt;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SecurityError {
    /// PIN 6 ta raqamdan iborat emas.
    PinFormat,
    /// Tiklash kodi formati noto'g'ri.
    RecoveryCodeFormat,
    /// PIN, tiklash kodi yoki platforma siri noto'g'ri (ular ataylab farqlanmaydi).
    WrongSecret,
    /// Ko'p marta xato — `until` (unix soniya) gacha kutish.
    LockedOut {
        until: i64,
    },
    SlotMissing,
    KeyFileCorrupt,
    Random,
    Crypto,
}

impl SecurityError {
    pub const fn code(&self) -> &'static str {
        match self {
            Self::PinFormat => "PIN_FORMAT",
            Self::RecoveryCodeFormat => "RECOVERY_CODE_FORMAT",
            Self::WrongSecret => "WRONG_SECRET",
            Self::LockedOut { .. } => "LOCKED_OUT",
            Self::SlotMissing => "SLOT_MISSING",
            Self::KeyFileCorrupt => "KEYFILE_CORRUPT",
            Self::Random => "RANDOM_UNAVAILABLE",
            Self::Crypto => "CRYPTO_FAILURE",
        }
    }
}

impl fmt::Display for SecurityError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for SecurityError {}
