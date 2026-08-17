"""Custom exception hierarchy for the Enterprise ERP platform.

Provides a structured set of domain-specific exceptions that allow
call sites to catch errors at the appropriate level of granularity.

All custom exceptions inherit from :class:`ERPException`, making it
possible to catch any ERP-specific error with a single handler while
still distinguishing individual failure modes.

Example::

    try:
        validate_order(data)
    except ValidationError as exc:
        logger.warning('Invalid order: %s (field=%s)', exc, exc.field_name)
    except ERPException as exc:
        logger.error('ERP error: %s [%s]', exc, exc.error_code)
"""

from typing import Any, Dict, Optional


class ERPException(Exception):
    """Base exception for all ERP-specific errors.

    Attributes:
        message: Human-readable error description.
        error_code: Optional machine-readable error code for API responses.
    """

    def __init__(
        self,
        message: str = 'An ERP error occurred',
        error_code: Optional[str] = None,
    ) -> None:
        """Initialise the exception.

        Args:
            message: Human-readable error description.
            error_code: Optional machine-readable error code (e.g. ``'ERR_001'``).
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        if self.error_code:
            return f'{self.__class__.__name__}({self.message!r}, code={self.error_code!r})'
        return f'{self.__class__.__name__}({self.message!r})'


class AuthenticationError(ERPException):
    """Raised when user authentication fails.

    Covers invalid credentials, expired tokens, and locked accounts.
    """

    def __init__(
        self,
        message: str = 'Authentication failed',
        error_code: Optional[str] = 'AUTH_001',
    ) -> None:
        """Initialise the authentication error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class AuthorizationError(ERPException):
    """Raised when an authenticated user lacks the required permissions.

    Indicates that the user's role does not grant access to the
    requested resource or operation.
    """

    def __init__(
        self,
        message: str = 'Permission denied',
        error_code: Optional[str] = 'AUTH_002',
    ) -> None:
        """Initialise the authorisation error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class ValidationError(ERPException):
    """Raised when input data fails validation rules.

    Supports both single-field and multi-field error reporting.

    Attributes:
        field_name: Name of the field that failed validation (optional).
        field_errors: Mapping of field names to their error messages.
    """

    def __init__(
        self,
        message: str = 'Validation failed',
        error_code: Optional[str] = 'VAL_001',
        field_name: Optional[str] = None,
        field_errors: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialise the validation error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
            field_name: Name of the single field that failed (convenience).
            field_errors: Mapping of field names to error messages/lists.
        """
        self.field_name = field_name
        self.field_errors = field_errors or {}
        super().__init__(message, error_code)

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        parts = [f'{self.__class__.__name__}({self.message!r}']
        if self.field_name:
            parts.append(f', field={self.field_name!r}')
        if self.field_errors:
            parts.append(f', errors={self.field_errors!r}')
        parts.append(')')
        return ''.join(parts)


class DatabaseError(ERPException):
    """Raised when a database operation fails.

    Covers connection failures, query errors, migration issues,
    and integrity constraint violations.
    """

    def __init__(
        self,
        message: str = 'Database operation failed',
        error_code: Optional[str] = 'DB_001',
    ) -> None:
        """Initialise the database error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class ConfigError(ERPException):
    """Raised when configuration loading or validation fails.

    Covers missing config files, invalid values, and schema mismatches.
    """

    def __init__(
        self,
        message: str = 'Configuration error',
        error_code: Optional[str] = 'CFG_001',
    ) -> None:
        """Initialise the configuration error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class ModuleError(ERPException):
    """Raised when an ERP module fails to load or initialise.

    Covers import failures, dependency issues, and runtime module errors.
    """

    def __init__(
        self,
        message: str = 'Module error',
        error_code: Optional[str] = 'MOD_001',
    ) -> None:
        """Initialise the module error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class ExportError(ERPException):
    """Raised when a data export operation fails.

    Covers file-system errors, format conversion issues, and
    permission problems during export.
    """

    def __init__(
        self,
        message: str = 'Export operation failed',
        error_code: Optional[str] = 'EXP_001',
    ) -> None:
        """Initialise the export error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class ImportError_(ERPException):
    """Raised when a data import operation fails.

    The trailing underscore avoids shadowing Python's built-in
    :class:`ImportError`.

    Covers file parsing errors, data mapping issues, and
    validation failures during import.
    """

    def __init__(
        self,
        message: str = 'Import operation failed',
        error_code: Optional[str] = 'IMP_001',
    ) -> None:
        """Initialise the import error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class BackupError(ERPException):
    """Raised when a backup or restore operation fails.

    Covers file-system errors, compression issues, and
    database dump/restore failures.
    """

    def __init__(
        self,
        message: str = 'Backup operation failed',
        error_code: Optional[str] = 'BKP_001',
    ) -> None:
        """Initialise the backup error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class PluginError(ERPException):
    """Raised when a plugin fails to load, activate, or deactivate.

    Covers discovery errors, missing dependencies, and runtime
    plugin failures.
    """

    def __init__(
        self,
        message: str = 'Plugin error',
        error_code: Optional[str] = 'PLG_001',
    ) -> None:
        """Initialise the plugin error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)


class IntegrationError(ERPException):
    """Raised when an external service integration fails.

    Covers API call failures, timeout errors, and response
    parsing issues with third-party services.
    """

    def __init__(
        self,
        message: str = 'Integration error',
        error_code: Optional[str] = 'INT_001',
    ) -> None:
        """Initialise the integration error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)
