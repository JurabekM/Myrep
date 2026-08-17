"""Domain exceptions and their HTTP mapping.

Domain and infrastructure layers raise these instead of HTTPException so the
business logic stays framework-independent (usable from FastAPI, Flask-compat
adapter and Celery alike).
"""

from typing import Any


class AppError(Exception):
    """Base application error."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str = "Internal error", *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"error": self.error_code, "message": self.message, "details": self.details}


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"


class AuthenticationError(AppError):
    status_code = 401
    error_code = "authentication_failed"


class PermissionDeniedError(AppError):
    status_code = 403
    error_code = "permission_denied"


class RateLimitExceededError(AppError):
    status_code = 429
    error_code = "rate_limit_exceeded"


class PlanLimitExceededError(AppError):
    status_code = 402
    error_code = "plan_limit_exceeded"


class AIProviderError(AppError):
    status_code = 502
    error_code = "ai_provider_error"


class AllProvidersFailedError(AIProviderError):
    error_code = "all_providers_failed"


class FileTooLargeError(ValidationError):
    error_code = "file_too_large"


class UnsupportedFileTypeError(ValidationError):
    error_code = "unsupported_file_type"
