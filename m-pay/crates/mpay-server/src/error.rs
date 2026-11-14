//! HTTP xatolari: barqaror kod + HTTP status. 5xx xatolarda ichki tafsilot faqat logga yoziladi.

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use mpay_common::api::{ErrorBody, ErrorResponse};
use mpay_pqlink::PqLinkError;
use mpay_vault::VaultError;

/// API xatosi.
#[derive(Debug)]
pub struct ApiError {
    pub status: StatusCode,
    pub code: &'static str,
    pub message: String,
}

impl ApiError {
    pub fn new(status: StatusCode, code: &'static str, message: impl Into<String>) -> Self {
        Self {
            status,
            code,
            message: message.into(),
        }
    }

    pub fn unauthorized() -> Self {
        Self::new(
            StatusCode::UNAUTHORIZED,
            "UNAUTHORIZED",
            "yaroqli Bearer kalit kerak",
        )
    }

    pub fn forbidden() -> Self {
        Self::new(
            StatusCode::FORBIDDEN,
            "FORBIDDEN",
            "bu rol uchun ruxsat yo'q",
        )
    }

    pub fn bad_request(msg: impl Into<String>) -> Self {
        Self::new(StatusCode::BAD_REQUEST, "BAD_REQUEST", msg)
    }

    pub fn not_found() -> Self {
        Self::new(StatusCode::NOT_FOUND, "NOT_FOUND", "topilmadi")
    }

    pub fn body(&self) -> ErrorBody {
        ErrorBody {
            code: self.code.to_owned(),
            message: self.message.clone(),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let body = ErrorResponse { error: self.body() };
        (self.status, Json(body)).into_response()
    }
}

impl From<VaultError> for ApiError {
    fn from(e: VaultError) -> Self {
        let status = match &e {
            VaultError::BadRequest(_) => StatusCode::BAD_REQUEST,
            VaultError::TokenNotFound | VaultError::ChallengeNotFound => StatusCode::NOT_FOUND,
            VaultError::InvalidState { .. }
            | VaultError::TooManyTokens
            | VaultError::TooManyLuks => StatusCode::CONFLICT,
            VaultError::DeviceMismatch | VaultError::IdvDeclined => StatusCode::FORBIDDEN,
            VaultError::OtpInvalid => StatusCode::UNPROCESSABLE_ENTITY,
            VaultError::OtpExpired => StatusCode::GONE,
            VaultError::OtpLocked => StatusCode::LOCKED,
            VaultError::IdvUnavailable(_) => StatusCode::SERVICE_UNAVAILABLE,
            VaultError::AuditBroken(_) | VaultError::Crypto(_) | VaultError::Db(_) => {
                StatusCode::INTERNAL_SERVER_ERROR
            }
        };
        let message = if status.is_server_error() {
            tracing::error!(error = %e, code = e.code(), "vault ichki xatosi");
            "ichki xato".to_owned()
        } else {
            e.to_string()
        };
        Self {
            status,
            code: e.code(),
            message,
        }
    }
}

impl From<PqLinkError> for ApiError {
    fn from(e: PqLinkError) -> Self {
        use PqLinkError as E;
        let (status, code) = match &e {
            E::Malformed(_) | E::UnexpectedMessage | E::UnsupportedSuite => {
                (StatusCode::BAD_REQUEST, "PQLINK_MALFORMED")
            }
            E::Attestation(_) => (StatusCode::FORBIDDEN, "PQLINK_ATTESTATION"),
            E::BadDeviceSignature | E::BadFinished => (StatusCode::FORBIDDEN, "PQLINK_AUTH"),
            E::UnknownSession | E::Decrypt => (StatusCode::UNAUTHORIZED, "PQLINK_SESSION"),
            E::Replay { .. } => (StatusCode::CONFLICT, "PQLINK_REPLAY"),
            E::TooManySessions => (StatusCode::SERVICE_UNAVAILABLE, "PQLINK_BUSY"),
            E::ServerNotPinned | E::BadServerSignature(_) | E::KeyExchange(_) => {
                (StatusCode::BAD_REQUEST, "PQLINK_HANDSHAKE")
            }
            E::Crypto(_) => (StatusCode::INTERNAL_SERVER_ERROR, "PQLINK_INTERNAL"),
        };
        tracing::warn!(error = %e, code, "pqlink xatosi");
        let message = if status.is_server_error() {
            "ichki xato".to_owned()
        } else {
            e.to_string()
        };
        Self {
            status,
            code,
            message,
        }
    }
}
