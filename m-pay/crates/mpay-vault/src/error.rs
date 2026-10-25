//! Vault xatolari. Har biri barqaror `code()` ga ega (HTTP API'da qaytariladi).
//! Matnlarda PAN, kalit yoki LUK bo'lmaydi.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum VaultError {
    #[error("noto'g'ri so'rov: {0}")]
    BadRequest(&'static str),
    #[error("token topilmadi")]
    TokenNotFound,
    #[error("holat o'tishi ruxsat etilmagan: {from} → {to}")]
    InvalidState {
        from: &'static str,
        to: &'static str,
    },
    #[error("token boshqa qurilmaga bog'langan")]
    DeviceMismatch,
    #[error("qurilmadagi tokenlar limiti to'ldi")]
    TooManyTokens,
    #[error("faol LUK'lar limiti to'ldi")]
    TooManyLuks,
    #[error("ID&V rad etdi")]
    IdvDeclined,
    #[error("ID&V xizmati javob bermadi: {0}")]
    IdvUnavailable(String),
    #[error("OTP challenge topilmadi")]
    ChallengeNotFound,
    #[error("OTP noto'g'ri")]
    OtpInvalid,
    #[error("OTP muddati o'tgan")]
    OtpExpired,
    #[error("OTP urinishlari tugadi")]
    OtpLocked,
    #[error("OTP qayta yuborish chegarasi tugadi")]
    OtpResendLimit,
    #[error("audit zanjiri buzilgan: seq {0}")]
    AuditBroken(i64),
    #[error("kriptografiya xatosi: {0}")]
    Crypto(#[from] mpay_crypto::CryptoError),
    #[error("ma'lumotlar bazasi xatosi: {0}")]
    Db(String),
}

impl VaultError {
    /// Barqaror mashina o'qiydigan kod.
    pub fn code(&self) -> &'static str {
        match self {
            Self::BadRequest(_) => "BAD_REQUEST",
            Self::TokenNotFound => "TOKEN_NOT_FOUND",
            Self::InvalidState { .. } => "INVALID_STATE",
            Self::DeviceMismatch => "DEVICE_MISMATCH",
            Self::TooManyTokens => "TOO_MANY_TOKENS",
            Self::TooManyLuks => "TOO_MANY_LUKS",
            Self::IdvDeclined => "IDV_DECLINED",
            Self::IdvUnavailable(_) => "IDV_UNAVAILABLE",
            Self::ChallengeNotFound => "CHALLENGE_NOT_FOUND",
            Self::OtpInvalid => "OTP_INVALID",
            Self::OtpExpired => "OTP_EXPIRED",
            Self::OtpLocked => "OTP_LOCKED",
            Self::OtpResendLimit => "OTP_RESEND_LIMIT",
            Self::AuditBroken(_) => "AUDIT_BROKEN",
            Self::Crypto(_) => "CRYPTO_ERROR",
            Self::Db(_) => "DB_ERROR",
        }
    }
}

impl From<sqlx::Error> for VaultError {
    fn from(e: sqlx::Error) -> Self {
        // sqlx xatolari so'rov parametrlarini o'z ichiga olmaydi.
        Self::Db(e.to_string())
    }
}

impl From<sqlx::migrate::MigrateError> for VaultError {
    fn from(e: sqlx::migrate::MigrateError) -> Self {
        Self::Db(e.to_string())
    }
}
