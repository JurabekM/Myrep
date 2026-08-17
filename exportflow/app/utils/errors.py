"""Application-level exception types.

Every exception carries a translation key so the UI can present the message in
the active interface language, plus an already-formatted English fallback.
"""

from __future__ import annotations


class ExportFlowError(Exception):
    """Base class for expected, user-facing failures."""

    default_key = "error.generic"

    def __init__(self, message: str = "", key: str | None = None, **params: object) -> None:
        super().__init__(message or key or self.default_key)
        self.message = message
        self.key = key or self.default_key
        self.params = params


class ValidationError(ExportFlowError):
    """Input did not satisfy a business rule."""

    default_key = "error.validation"


class PermissionDenied(ExportFlowError):
    """The current user's role does not allow the requested action."""

    default_key = "error.permission_denied"


class NotFoundError(ExportFlowError):
    """A referenced record does not exist (or was archived)."""

    default_key = "error.not_found"


class DuplicateError(ExportFlowError):
    """A uniqueness constraint would be violated."""

    default_key = "error.duplicate"


class IntegrationError(ExportFlowError):
    """An external provider could not be reached or rejected the request."""

    default_key = "error.integration"


class WorkflowError(ExportFlowError):
    """A state transition is not allowed from the current state."""

    default_key = "error.workflow"
