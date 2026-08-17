"""Authentication, session and role-based access control."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.enums import ROLE_PERMISSIONS, RoleName
from app.models.enums import Permission as Perm
from app.models.organization import Company, Permission, Role, User
from app.services import audit_service
from app.utils.dates import now
from app.utils.security import hash_password, password_strength, verify_password

logger = logging.getLogger(__name__)

ROLE_TITLES: dict[str, tuple[str, str]] = {
    RoleName.ADMIN: ("Administrator", "Администратор"),
    RoleName.SALES_MANAGER: ("Sotuv rahbari", "Руководитель продаж"),
    RoleName.OPERATOR: ("Operator", "Оператор"),
    RoleName.ANALYST: ("Analitik", "Аналитик"),
    RoleName.VIEWER: ("Kuzatuvchi", "Наблюдатель"),
}


class AuthError(Exception):
    """Raised when authentication fails. ``code`` is an i18n key."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PermissionDenied(Exception):
    """Raised when the current user lacks a required permission."""

    def __init__(self, permission: str) -> None:
        super().__init__(permission)
        self.permission = permission


@dataclass
class CurrentUser:
    """Detached snapshot of the signed-in user shared across the UI."""

    id: int
    username: str
    full_name: str
    role: str
    role_title_uz: str = ""
    role_title_ru: str = ""
    company_id: int = 1
    company_name: str = ""
    branch_id: int | None = None
    language: str = "uz"
    is_operator: bool = False
    avatar_color: str = "#3B82F6"
    permissions: set[str] = field(default_factory=set)

    def can(self, permission: str) -> bool:
        """Whether the user holds ``permission``."""
        return permission in self.permissions

    def require(self, permission: str) -> None:
        """Raise :class:`PermissionDenied` when the permission is missing."""
        if not self.can(permission):
            raise PermissionDenied(permission)

    @property
    def is_admin(self) -> bool:
        """Convenience flag."""
        return self.role == RoleName.ADMIN

    @property
    def sees_all_leads(self) -> bool:
        """Whether the user may see leads assigned to other operators."""
        return Perm.LEAD_VIEW_ALL in self.permissions


def ensure_roles(session: Session) -> None:
    """Create the built-in permissions and roles when missing."""
    existing_perms = {code for (code,) in session.execute(select(Permission.code)).all()}
    for perm in Perm:
        if perm.value not in existing_perms:
            session.add(Permission(code=perm.value, description=perm.value))
    session.flush()
    perm_map = {p.code: p for p in session.execute(select(Permission)).scalars().all()}

    for role_name, codes in ROLE_PERMISSIONS.items():
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
        titles = ROLE_TITLES.get(role_name, (role_name, role_name))
        if role is None:
            role = Role(name=role_name, title_uz=titles[0], title_ru=titles[1], is_system=True)
            session.add(role)
            session.flush()
        role.title_uz = role.title_uz or titles[0]
        role.title_ru = role.title_ru or titles[1]
        role.permissions = [perm_map[c] for c in sorted(codes) if c in perm_map]
    session.flush()


def has_any_user() -> bool:
    """Whether at least one active user exists (drives the first-run wizard)."""
    with session_scope() as session:
        count = session.execute(
            select(func.count(User.id)).where(User.is_archived.is_(False))
        ).scalar_one()
        return int(count) > 0


def to_current_user(user: User) -> CurrentUser:
    """Build a detached :class:`CurrentUser` snapshot from an ORM row."""
    return CurrentUser(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role.name,
        role_title_uz=user.role.title_uz,
        role_title_ru=user.role.title_ru,
        company_id=user.company_id,
        company_name=user.company.name if user.company else "",
        branch_id=user.branch_id,
        language=user.language,
        is_operator=user.is_operator,
        avatar_color=user.avatar_color,
        permissions=set(user.role.permission_codes()),
    )


def authenticate(username: str, password: str) -> CurrentUser:
    """Verify credentials and return the signed-in user snapshot.

    Raises :class:`AuthError` with an i18n code on failure.
    """
    clean = (username or "").strip().lower()
    if not clean or not password:
        raise AuthError("login_empty_fields")
    with session_scope() as session:
        user = session.execute(
            select(User).where(func.lower(User.username) == clean)
        ).scalar_one_or_none()
        if user is None:
            raise AuthError("login_bad_credentials")
        if user.is_archived or not user.is_active:
            raise AuthError("login_user_disabled")
        if not verify_password(password, user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            audit_service.record(
                session,
                action="login_failed",
                entity_type="user",
                entity_id=user.id,
                entity_label=user.username,
                user_id=user.id,
                username=user.username,
            )
            raise AuthError("login_bad_credentials")
        user.failed_attempts = 0
        user.last_login_at = now()
        audit_service.record(
            session,
            action="login",
            entity_type="user",
            entity_id=user.id,
            entity_label=user.username,
            user_id=user.id,
            username=user.username,
        )
        return to_current_user(user)


def create_user(
    *,
    username: str,
    password: str,
    full_name: str,
    role_name: str,
    company_id: int = 1,
    email: str = "",
    phone: str = "",
    language: str = "uz",
    branch_id: int | None = None,
    is_operator: bool = False,
    actor: CurrentUser | None = None,
) -> int:
    """Create a user; returns the new id. Raises :class:`AuthError` on bad input."""
    clean = (username or "").strip().lower()
    if not clean:
        raise AuthError("username_required")
    if not full_name.strip():
        raise AuthError("fullname_required")
    valid, reason = password_strength(password)
    if not valid:
        raise AuthError(reason)
    with session_scope() as session:
        ensure_roles(session)
        exists = session.execute(
            select(User).where(func.lower(User.username) == clean)
        ).scalar_one_or_none()
        if exists is not None:
            raise AuthError("username_taken")
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
        if role is None:
            raise AuthError("role_not_found")
        company = session.get(Company, company_id)
        if company is None:
            company = session.execute(select(Company)).scalars().first()
        if company is None:
            raise AuthError("company_missing")
        user = User(
            company_id=company.id,
            role_id=role.id,
            branch_id=branch_id,
            username=clean,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            email=email.strip(),
            phone=phone.strip(),
            language=language,
            is_operator=is_operator or role.name == RoleName.OPERATOR,
        )
        session.add(user)
        session.flush()
        audit_service.record(
            session,
            action="user_created",
            entity_type="user",
            entity_id=user.id,
            entity_label=user.username,
            new_value=f"role={role.name}",
            user_id=actor.id if actor else None,
            username=actor.username if actor else clean,
        )
        return user.id


def update_user(
    user_id: int,
    *,
    actor: CurrentUser,
    full_name: str | None = None,
    role_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    language: str | None = None,
    branch_id: int | None = None,
    is_active: bool | None = None,
    is_operator: bool | None = None,
) -> None:
    """Update user attributes (admin only)."""
    actor.require(Perm.USER_MANAGE)
    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            raise AuthError("user_not_found")
        before = f"{user.full_name}|{user.role.name}|active={user.is_active}"
        if full_name is not None:
            user.full_name = full_name.strip()
        if email is not None:
            user.email = email.strip()
        if phone is not None:
            user.phone = phone.strip()
        if language is not None:
            user.language = language
        if branch_id is not None:
            user.branch_id = branch_id or None
        if is_active is not None:
            user.is_active = is_active
        if is_operator is not None:
            user.is_operator = is_operator
        if role_name:
            role = session.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
            if role is None:
                raise AuthError("role_not_found")
            user.role_id = role.id
        session.flush()
        after = f"{user.full_name}|{role_name or user.role.name}|active={user.is_active}"
        audit_service.record(
            session,
            action="user_updated",
            entity_type="user",
            entity_id=user.id,
            entity_label=user.username,
            old_value=before,
            new_value=after,
            user_id=actor.id,
            username=actor.username,
        )


def change_password(user_id: int, new_password: str, *, actor: CurrentUser) -> None:
    """Set a new password for a user (self or admin)."""
    if actor.id != user_id:
        actor.require(Perm.USER_MANAGE)
    valid, reason = password_strength(new_password)
    if not valid:
        raise AuthError(reason)
    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            raise AuthError("user_not_found")
        user.password_hash = hash_password(new_password)
        audit_service.record(
            session,
            action="password_changed",
            entity_type="user",
            entity_id=user.id,
            entity_label=user.username,
            user_id=actor.id,
            username=actor.username,
        )


def archive_user(user_id: int, *, actor: CurrentUser) -> None:
    """Soft delete a user; the last active administrator cannot be removed."""
    actor.require(Perm.USER_MANAGE)
    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            raise AuthError("user_not_found")
        if user.role.name == RoleName.ADMIN:
            admins = session.execute(
                select(func.count(User.id))
                .join(Role, Role.id == User.role_id)
                .where(
                    Role.name == RoleName.ADMIN,
                    User.is_archived.is_(False),
                    User.is_active.is_(True),
                )
            ).scalar_one()
            if int(admins) <= 1:
                raise AuthError("last_admin")
        user.is_archived = True
        user.archived_at = now()
        user.is_active = False
        audit_service.record(
            session,
            action="user_archived",
            entity_type="user",
            entity_id=user.id,
            entity_label=user.username,
            user_id=actor.id,
            username=actor.username,
        )


def list_users(include_archived: bool = False) -> list[User]:
    """All users ordered by name."""
    with session_scope() as session:
        stmt = select(User).order_by(User.full_name)
        if not include_archived:
            stmt = stmt.where(User.is_archived.is_(False))
        return list(session.execute(stmt).scalars().unique().all())


def list_operators() -> list[User]:
    """Active users who can own leads (operators and managers)."""
    with session_scope() as session:
        stmt = (
            select(User)
            .join(Role, Role.id == User.role_id)
            .where(
                User.is_archived.is_(False),
                User.is_active.is_(True),
                Role.name.in_([RoleName.OPERATOR, RoleName.SALES_MANAGER, RoleName.ADMIN]),
            )
            .order_by(User.full_name)
        )
        return list(session.execute(stmt).scalars().unique().all())


def list_roles() -> list[Role]:
    """All roles."""
    with session_scope() as session:
        return list(session.execute(select(Role).order_by(Role.id)).scalars().unique().all())
