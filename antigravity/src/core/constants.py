"""System-wide constants for the Enterprise ERP platform.

This module defines all application-level constants, enumerations,
and the role-based permission matrix used throughout the system.

Constants:
    APP_NAME: Application display name.
    APP_VERSION: Semantic version string.
    DEFAULT_PORT: Default HTTP server port.
    DEFAULT_DB: Default SQLite database filename.
    DATE_FORMAT / DATETIME_FORMAT: Standard strftime patterns.
    CURRENCY: Default currency code (Uzbek Som).
    VAT_RATE: Value-added tax rate (QQS 12%).

Enumerations:
    UserRole: System-level user roles for RBAC.
    Permission: Granular permission flags.
    ModuleName: ERP module identifiers.
    OrderStatus / PaymentStatus / InvoiceStatus / EmployeeStatus: Status enums.

Mappings:
    PERMISSION_MATRIX: Maps each UserRole to its allowed permissions per module.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------

APP_NAME: str = 'Enterprise ERP'
"""Display name of the application."""

APP_VERSION: str = '1.0.0'
"""Semantic version of the application."""

DEFAULT_PORT: int = 8000
"""Default HTTP server port."""

DEFAULT_DB: str = 'erp_database.db'
"""Default SQLite database filename."""

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

DATE_FORMAT: str = '%Y-%m-%d'
"""Standard date format used across the application."""

DATETIME_FORMAT: str = '%Y-%m-%d %H:%M:%S'
"""Standard datetime format used across the application."""

# ---------------------------------------------------------------------------
# Localization / finance
# ---------------------------------------------------------------------------

CURRENCY: str = 'UZS'
"""Default currency code (Uzbek Som)."""

VAT_RATE: float = 0.12
"""Value-Added Tax rate (QQS) — 12 %."""


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UserRole(Enum):
    """System-level user roles for role-based access control.

    Each role determines which modules and permissions a user can access,
    as defined in :data:`PERMISSION_MATRIX`.
    """

    ADMINISTRATOR = 'administrator'
    OWNER = 'owner'
    ACCOUNTANT = 'accountant'
    CASHIER = 'cashier'
    WAREHOUSE = 'warehouse'
    SALES_MANAGER = 'sales_manager'
    HR = 'hr'
    AUDITOR = 'auditor'
    GUEST = 'guest'


class Permission(Enum):
    """Granular permission flags applied per module.

    Permissions are combined into frozensets and mapped to roles
    via :data:`PERMISSION_MATRIX`.
    """

    VIEW = 'view'
    CREATE = 'create'
    EDIT = 'edit'
    DELETE = 'delete'
    EXPORT = 'export'
    IMPORT = 'import'
    BACKUP = 'backup'
    ADMIN = 'admin'


class ModuleName(Enum):
    """Identifiers for each ERP functional module.

    Used as keys in the permission matrix and for module registration.
    """

    DASHBOARD = 'dashboard'
    SALES = 'sales'
    INVENTORY = 'inventory'
    ACCOUNTING = 'accounting'
    HR = 'hr'
    CRM = 'crm'
    REPORTS = 'reports'
    ANALYTICS = 'analytics'
    SETTINGS = 'settings'


class OrderStatus(Enum):
    """Lifecycle states of a sales or purchase order."""

    DRAFT = 'draft'
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    RETURNED = 'returned'


class PaymentStatus(Enum):
    """States of a payment transaction."""

    PENDING = 'pending'
    PARTIAL = 'partial'
    PAID = 'paid'
    OVERDUE = 'overdue'
    REFUNDED = 'refunded'
    CANCELLED = 'cancelled'


class InvoiceStatus(Enum):
    """Lifecycle states of an invoice."""

    DRAFT = 'draft'
    SENT = 'sent'
    VIEWED = 'viewed'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    VOID = 'void'


class EmployeeStatus(Enum):
    """Employment states of an HR employee record."""

    ACTIVE = 'active'
    ON_LEAVE = 'on_leave'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'
    RETIRED = 'retired'


# ---------------------------------------------------------------------------
# Convenience sets
# ---------------------------------------------------------------------------

_ALL_PERMISSIONS: frozenset = frozenset(Permission)
"""All available permissions — shortcut for admin/owner roles."""

_VIEW_EXPORT: frozenset = frozenset({Permission.VIEW, Permission.EXPORT})
"""Read-only plus export — shortcut for auditor role."""

_CRUD: frozenset = frozenset({
    Permission.VIEW, Permission.CREATE, Permission.EDIT, Permission.DELETE,
})
"""Standard CRUD permission set."""

_CRUD_EXPORT: frozenset = frozenset({
    Permission.VIEW, Permission.CREATE, Permission.EDIT, Permission.DELETE,
    Permission.EXPORT,
})
"""CRUD plus export capability."""

_CRUD_EXPORT_IMPORT: frozenset = frozenset({
    Permission.VIEW, Permission.CREATE, Permission.EDIT, Permission.DELETE,
    Permission.EXPORT, Permission.IMPORT,
})
"""CRUD plus export and import capabilities."""

_VIEW_ONLY: frozenset = frozenset({Permission.VIEW})
"""View-only permission set."""


# ---------------------------------------------------------------------------
# All modules set (convenience)
# ---------------------------------------------------------------------------

_ALL_MODULES: frozenset = frozenset(ModuleName)
"""All available modules."""


# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------
# Some modules import using the names ``Roles``, ``Permissions``,
# ``ModuleNames``.  These aliases keep both conventions working.

Roles = UserRole
"""Alias for :class:`UserRole` — provided for backward compatibility."""

Permissions = Permission
"""Alias for :class:`Permission` — provided for backward compatibility."""

ModuleNames = ModuleName
"""Alias for :class:`ModuleName` — provided for backward compatibility."""


PERMISSION_MATRIX: dict = {
    UserRole.ADMINISTRATOR: {module: _ALL_PERMISSIONS for module in ModuleName},
    UserRole.OWNER: {module: _ALL_PERMISSIONS for module in ModuleName},

    UserRole.ACCOUNTANT: {
        ModuleName.DASHBOARD: _VIEW_ONLY,
        ModuleName.SALES: _VIEW_EXPORT,
        ModuleName.INVENTORY: _VIEW_EXPORT,
        ModuleName.ACCOUNTING: _CRUD_EXPORT_IMPORT,
        ModuleName.HR: frozenset(),
        ModuleName.CRM: _VIEW_ONLY,
        ModuleName.REPORTS: _CRUD_EXPORT,
        ModuleName.ANALYTICS: _VIEW_EXPORT,
        ModuleName.SETTINGS: frozenset(),
    },

    UserRole.CASHIER: {
        ModuleName.DASHBOARD: _VIEW_ONLY,
        ModuleName.SALES: _CRUD_EXPORT,
        ModuleName.INVENTORY: _VIEW_ONLY,
        ModuleName.ACCOUNTING: _VIEW_ONLY,
        ModuleName.HR: frozenset(),
        ModuleName.CRM: _VIEW_ONLY,
        ModuleName.REPORTS: frozenset(),
        ModuleName.ANALYTICS: frozenset(),
        ModuleName.SETTINGS: frozenset(),
    },

    UserRole.WAREHOUSE: {
        ModuleName.DASHBOARD: _VIEW_ONLY,
        ModuleName.SALES: _VIEW_ONLY,
        ModuleName.INVENTORY: _CRUD_EXPORT_IMPORT,
        ModuleName.ACCOUNTING: frozenset(),
        ModuleName.HR: frozenset(),
        ModuleName.CRM: frozenset(),
        ModuleName.REPORTS: _VIEW_EXPORT,
        ModuleName.ANALYTICS: _VIEW_ONLY,
        ModuleName.SETTINGS: frozenset(),
    },

    UserRole.SALES_MANAGER: {
        ModuleName.DASHBOARD: _VIEW_ONLY,
        ModuleName.SALES: _CRUD_EXPORT_IMPORT,
        ModuleName.INVENTORY: _VIEW_EXPORT,
        ModuleName.ACCOUNTING: _VIEW_ONLY,
        ModuleName.HR: frozenset(),
        ModuleName.CRM: _CRUD_EXPORT,
        ModuleName.REPORTS: _CRUD_EXPORT,
        ModuleName.ANALYTICS: _VIEW_EXPORT,
        ModuleName.SETTINGS: frozenset(),
    },

    UserRole.HR: {
        ModuleName.DASHBOARD: _VIEW_ONLY,
        ModuleName.SALES: frozenset(),
        ModuleName.INVENTORY: frozenset(),
        ModuleName.ACCOUNTING: _VIEW_ONLY,
        ModuleName.HR: _CRUD_EXPORT_IMPORT,
        ModuleName.CRM: frozenset(),
        ModuleName.REPORTS: _CRUD_EXPORT,
        ModuleName.ANALYTICS: _VIEW_EXPORT,
        ModuleName.SETTINGS: frozenset(),
    },

    UserRole.AUDITOR: {module: _VIEW_EXPORT for module in ModuleName},

    UserRole.GUEST: {
        ModuleName.DASHBOARD: _VIEW_ONLY,
        ModuleName.SALES: frozenset(),
        ModuleName.INVENTORY: frozenset(),
        ModuleName.ACCOUNTING: frozenset(),
        ModuleName.HR: frozenset(),
        ModuleName.CRM: frozenset(),
        ModuleName.REPORTS: frozenset(),
        ModuleName.ANALYTICS: frozenset(),
        ModuleName.SETTINGS: frozenset(),
    },
}
"""Role-based permission matrix.

Maps each :class:`UserRole` to a dictionary of
:class:`ModuleName` → ``frozenset[Permission]`` entries, defining exactly
which operations a user with that role may perform in each module.
"""
