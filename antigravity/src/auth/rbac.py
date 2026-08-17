"""Role-Based Access Control (RBAC) manager for the ERP platform.

Provides a centralised service for checking, granting, and revoking
permissions. Permissions are cached in memory to minimise database
round-trips during request handling. Cache entries are automatically
invalidated whenever permissions are modified.

Classes:
    RBACManager: Main RBAC engine with caching and permission CRUD.
"""

import logging
from typing import Optional

from src.core.constants import Roles, Permissions, ModuleNames, PERMISSION_MATRIX
from src.core.exceptions import AuthorizationError
from src.auth.models import User, Role, Permission


logger = logging.getLogger(__name__)


class RBACManager:
    """Manages role-based access control with in-memory caching.

    The manager sits between the application layer and the database,
    providing fast permission lookups via a two-tier cache (per-user
    and per-role). All mutating operations automatically invalidate
    affected cache entries.

    Attributes:
        _session_factory: Callable returning a new SQLAlchemy session.
        _cache: Per-user permission cache mapping
                ``user_id -> {module: [permissions]}``.
        _role_cache: Per-role permission cache mapping
                     ``role_name -> {module: [permissions]}``.
    """

    def __init__(self, session_factory) -> None:
        """Initialise the RBAC manager.

        Args:
            session_factory: A callable (e.g. ``sessionmaker``) that
                returns a new SQLAlchemy ``Session`` instance.
        """
        self._session_factory = session_factory
        self._cache: dict[str, dict[str, list[str]]] = {}
        self._role_cache: dict[str, dict[str, list[str]]] = {}
        self.logger = logger

    # ── Cache management ───────────────────────────────────────────

    def _invalidate_cache(self, user_id: Optional[str] = None) -> None:
        """Invalidate permission caches.

        Args:
            user_id: If provided, only the cache for this user is
                cleared. Otherwise **all** user and role caches are
                flushed.
        """
        if user_id:
            self._cache.pop(user_id, None)
            self.logger.debug("Cache invalidated for user '%s'", user_id)
        else:
            self._cache.clear()
            self._role_cache.clear()
            self.logger.debug("All permission caches invalidated")

    # ── Query helpers ──────────────────────────────────────────────

    def has_permission(
        self,
        user_id: str,
        module: str,
        permission: str,
    ) -> bool:
        """Check whether a user holds a specific permission.

        Administrators are implicitly granted **all** permissions.

        Args:
            user_id: Primary key of the user to check.
            module: Module name (``ModuleNames`` enum value).
            permission: Permission name (``Permissions`` enum value).

        Returns:
            bool: True if the user has the specified permission.
        """
        if self.is_admin(user_id):
            return True

        permissions = self.get_user_permissions(user_id)
        module_perms = permissions.get(module, [])
        has = permission in module_perms
        self.logger.debug(
            "Permission check: user=%s module=%s perm=%s → %s",
            user_id, module, permission, has,
        )
        return has

    def get_user_permissions(
        self,
        user_id: str,
    ) -> dict[str, list[str]]:
        """Retrieve the full permission map for a user.

        Results are cached per ``user_id``. On cache miss the user's
        role is loaded from the database and all associated
        ``Permission`` records are aggregated.

        Args:
            user_id: Primary key of the target user.

        Returns:
            dict: Mapping of module name to list of permission names.
                  Returns an empty dict if the user is not found.
        """
        if user_id in self._cache:
            return self._cache[user_id]

        permissions: dict[str, list[str]] = {}
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user or not user.role:
                self._cache[user_id] = permissions
                return permissions

            role_perms = (
                session.query(Permission)
                .filter(Permission.role_id == user.role_id)
                .all()
            )
            for perm in role_perms:
                permissions.setdefault(perm.module, [])
                if perm.permission not in permissions[perm.module]:
                    permissions[perm.module].append(perm.permission)

            self._cache[user_id] = permissions
            return permissions
        except Exception:
            self.logger.exception(
                "Error fetching permissions for user '%s'", user_id,
            )
            return permissions
        finally:
            session.close()

    def get_role_permissions(
        self,
        role_name: str,
    ) -> dict[str, list[str]]:
        """Retrieve the full permission map for a role by name.

        Results are cached per ``role_name``.

        Args:
            role_name: The ``Roles`` enum value identifying the role.

        Returns:
            dict: Mapping of module name to list of permission names.
        """
        if role_name in self._role_cache:
            return self._role_cache[role_name]

        permissions: dict[str, list[str]] = {}
        session = self._session_factory()
        try:
            role = (
                session.query(Role)
                .filter(Role.name == role_name, Role.is_deleted.is_(False))
                .first()
            )
            if not role:
                self._role_cache[role_name] = permissions
                return permissions

            for perm in role.permissions:
                permissions.setdefault(perm.module, [])
                if perm.permission not in permissions[perm.module]:
                    permissions[perm.module].append(perm.permission)

            self._role_cache[role_name] = permissions
            return permissions
        except Exception:
            self.logger.exception(
                "Error fetching permissions for role '%s'", role_name,
            )
            return permissions
        finally:
            session.close()

    # ── Permission mutation ────────────────────────────────────────

    def grant_permission(
        self,
        role_id: str,
        module: str,
        permission: str,
    ) -> None:
        """Grant a permission to a role.

        If the permission already exists the call is a no-op. All
        caches are invalidated after a successful grant.

        Args:
            role_id: Primary key of the target role.
            module: Module name (``ModuleNames`` enum value).
            permission: Permission name (``Permissions`` enum value).

        Raises:
            ValueError: If the role does not exist.
        """
        session = self._session_factory()
        try:
            role = session.query(Role).filter(Role.id == role_id).first()
            if not role:
                raise ValueError(f"Role '{role_id}' not found")

            existing = (
                session.query(Permission)
                .filter(
                    Permission.role_id == role_id,
                    Permission.module == module,
                    Permission.permission == permission,
                )
                .first()
            )
            if existing:
                self.logger.info(
                    "Permission already exists: role=%s module=%s perm=%s",
                    role_id, module, permission,
                )
                return

            new_perm = Permission(
                role_id=role_id,
                module=module,
                permission=permission,
            )
            session.add(new_perm)
            session.commit()
            self._invalidate_cache()
            self.logger.info(
                "Granted permission: role=%s module=%s perm=%s",
                role_id, module, permission,
            )
        except Exception:
            session.rollback()
            self.logger.exception(
                "Error granting permission: role=%s module=%s perm=%s",
                role_id, module, permission,
            )
            raise
        finally:
            session.close()

    def revoke_permission(
        self,
        role_id: str,
        module: str,
        permission: str,
    ) -> None:
        """Revoke a permission from a role.

        If the permission does not exist the call is a no-op. All
        caches are invalidated after a successful revocation.

        Args:
            role_id: Primary key of the target role.
            module: Module name (``ModuleNames`` enum value).
            permission: Permission name (``Permissions`` enum value).
        """
        session = self._session_factory()
        try:
            perm = (
                session.query(Permission)
                .filter(
                    Permission.role_id == role_id,
                    Permission.module == module,
                    Permission.permission == permission,
                )
                .first()
            )
            if not perm:
                self.logger.info(
                    "Permission not found for revocation: "
                    "role=%s module=%s perm=%s",
                    role_id, module, permission,
                )
                return

            session.delete(perm)
            session.commit()
            self._invalidate_cache()
            self.logger.info(
                "Revoked permission: role=%s module=%s perm=%s",
                role_id, module, permission,
            )
        except Exception:
            session.rollback()
            self.logger.exception(
                "Error revoking permission: role=%s module=%s perm=%s",
                role_id, module, permission,
            )
            raise
        finally:
            session.close()

    # ── Convenience helpers ────────────────────────────────────────

    def get_accessible_modules(self, user_id: str) -> list[str]:
        """Return the list of modules the user can access (VIEW).

        A module is accessible if the user holds at least the ``VIEW``
        permission on it. Administrators can access all modules.

        Args:
            user_id: Primary key of the user.

        Returns:
            list[str]: Module names with VIEW permission.
        """
        if self.is_admin(user_id):
            return [m.value for m in ModuleNames]

        permissions = self.get_user_permissions(user_id)
        view_value = Permissions.VIEW.value
        return [
            module
            for module, perms in permissions.items()
            if view_value in perms
        ]

    def is_admin(self, user_id: str) -> bool:
        """Check whether the user holds the ADMINISTRATOR role.

        This is checked against the database (with caching) rather
        than relying on a cached permission set, so that role changes
        take effect immediately.

        Args:
            user_id: Primary key of the user.

        Returns:
            bool: True if the user's role is ``ADMINISTRATOR``.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user or not user.role:
                return False
            return user.role.name == Roles.ADMINISTRATOR.value
        except Exception:
            self.logger.exception(
                "Error checking admin status for user '%s'", user_id,
            )
            return False
        finally:
            session.close()

    def check_permission(
        self,
        user_id: str,
        module: str,
        permission: str,
    ) -> None:
        """Assert that a user holds a permission; raise on failure.

        Administrators always pass this check. Non-admin users without
        the required permission trigger an ``AuthorizationError``.

        Args:
            user_id: Primary key of the user.
            module: Module name (``ModuleNames`` enum value).
            permission: Permission name (``Permissions`` enum value).

        Raises:
            AuthorizationError: If the user lacks the permission.
        """
        if self.is_admin(user_id):
            return

        if not self.has_permission(user_id, module, permission):
            raise AuthorizationError(
                f"User '{user_id}' does not have '{permission}' "
                f"permission on module '{module}'"
            )
