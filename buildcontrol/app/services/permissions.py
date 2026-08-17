"""Role based access control.

A permission is a dotted string ``<domain>.<action>``. The administrator role
holds the wildcard ``*``. Checks are performed in the service layer *and* used
by the UI to disable controls, so a read-only user never sees an enabled button
that would later fail.
"""

from __future__ import annotations

from app.models.enums import RoleCode


class Perm:
    """Namespace of permission constants."""

    PROJECT_VIEW = "project.view"
    PROJECT_EDIT = "project.edit"
    PROJECT_ARCHIVE = "project.archive"

    ESTIMATE_VIEW = "estimate.view"
    ESTIMATE_EDIT = "estimate.edit"
    ESTIMATE_APPROVE = "estimate.approve"

    PURCHASE_VIEW = "purchase.view"
    PURCHASE_EDIT = "purchase.edit"
    PURCHASE_APPROVE = "purchase.approve"

    WAREHOUSE_VIEW = "warehouse.view"
    WAREHOUSE_EDIT = "warehouse.edit"

    STAGE_VIEW = "stage.view"
    STAGE_EDIT = "stage.edit"

    COUNTERPARTY_VIEW = "counterparty.view"
    COUNTERPARTY_EDIT = "counterparty.edit"

    EXPENSE_VIEW = "expense.view"
    EXPENSE_EDIT = "expense.edit"
    EXPENSE_APPROVE = "expense.approve"

    REPORT_VIEW = "report.view"
    SETTINGS_MANAGE = "settings.manage"
    USER_MANAGE = "user.manage"
    AUDIT_VIEW = "audit.view"


_VIEW_ONLY: set[str] = {
    Perm.PROJECT_VIEW,
    Perm.ESTIMATE_VIEW,
    Perm.PURCHASE_VIEW,
    Perm.WAREHOUSE_VIEW,
    Perm.STAGE_VIEW,
    Perm.COUNTERPARTY_VIEW,
    Perm.EXPENSE_VIEW,
    Perm.REPORT_VIEW,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleCode.ADMIN.value: {"*"},
    RoleCode.MANAGER.value: _VIEW_ONLY
    | {
        Perm.PROJECT_EDIT,
        Perm.PROJECT_ARCHIVE,
        Perm.ESTIMATE_EDIT,
        Perm.ESTIMATE_APPROVE,
        Perm.PURCHASE_EDIT,
        Perm.PURCHASE_APPROVE,
        Perm.WAREHOUSE_EDIT,
        Perm.STAGE_EDIT,
        Perm.COUNTERPARTY_EDIT,
        Perm.EXPENSE_EDIT,
        Perm.EXPENSE_APPROVE,
        Perm.AUDIT_VIEW,
    },
    RoleCode.ESTIMATOR.value: _VIEW_ONLY
    | {
        Perm.ESTIMATE_EDIT,
        Perm.PURCHASE_EDIT,
        Perm.STAGE_EDIT,
        Perm.EXPENSE_EDIT,
        Perm.COUNTERPARTY_EDIT,
    },
    RoleCode.STOREKEEPER.value: _VIEW_ONLY
    | {
        Perm.WAREHOUSE_EDIT,
        Perm.PURCHASE_EDIT,
    },
    RoleCode.VIEWER.value: set(_VIEW_ONLY),
}


def permissions_for(role_code: str) -> set[str]:
    """Return the permission set granted to ``role_code``."""
    return ROLE_PERMISSIONS.get(role_code, set())


def has_perm(role_code: str, permission: str) -> bool:
    """True when ``role_code`` grants ``permission`` (or the wildcard)."""
    perms = permissions_for(role_code)
    return "*" in perms or permission in perms


class PermissionDenied(Exception):
    """Raised when an operation is attempted without the required permission."""

    def __init__(self, permission: str) -> None:
        super().__init__(f"Permission denied: {permission}")
        self.permission = permission


def require(role_code: str, permission: str) -> None:
    """Raise :class:`PermissionDenied` unless the role grants ``permission``."""
    if not has_perm(role_code, permission):
        raise PermissionDenied(permission)
