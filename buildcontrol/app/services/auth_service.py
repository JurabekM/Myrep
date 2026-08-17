"""Authentication, bootstrap and user management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import session_scope
from app.models.entities import Role, User
from app.models.enums import RoleCode
from app.repositories import Repositories
from app.services import audit_service
from app.services.permissions import has_perm
from app.utils.security import hash_password, validate_password, verify_password

#: Built-in roles created on first run.
DEFAULT_ROLES: list[tuple[str, str, str]] = [
    (RoleCode.ADMIN.value, "Administrator", "Administrator"),
    (RoleCode.MANAGER.value, "Loyiha rahbari", "Project manager"),
    (RoleCode.ESTIMATOR.value, "Smetachi", "Estimator"),
    (RoleCode.STOREKEEPER.value, "Omborchi", "Storekeeper"),
    (RoleCode.VIEWER.value, "Kuzatuvchi", "Viewer"),
]


@dataclass(frozen=True)
class CurrentUser:
    """Detached snapshot of the signed-in user (safe to keep in the UI)."""

    id: int
    username: str
    full_name: str
    role_code: str
    role_name_uz: str
    role_name_en: str

    @property
    def label(self) -> str:
        return self.full_name or self.username

    def can(self, permission: str) -> bool:
        """True when this user's role grants ``permission``."""
        return has_perm(self.role_code, permission)

    def role_label(self, lang: str = "uz") -> str:
        return self.role_name_uz if lang == "uz" else self.role_name_en


class AuthError(Exception):
    """Raised when authentication or user creation fails; carries an i18n key."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def ensure_roles(session: Session) -> None:
    """Create the built-in roles when missing."""
    repo = Repositories(session).roles
    for code, uz, en in DEFAULT_ROLES:
        if repo.by_code(code) is None:
            repo.create(code=code, name_uz=uz, name_en=en)


def has_any_user() -> bool:
    """True when at least one user account exists."""
    with session_scope() as session:
        return bool(session.scalar(select(func.count()).select_from(User)))


def _snapshot(user: User) -> CurrentUser:
    role = user.role
    return CurrentUser(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role_code=role.code if role else RoleCode.VIEWER.value,
        role_name_uz=role.name_uz if role else "",
        role_name_en=role.name_en if role else "",
    )


def create_user(
    *,
    username: str,
    password: str,
    full_name: str,
    role_code: str,
    email: str = "",
    phone: str = "",
    actor: User | None = None,
) -> CurrentUser:
    """Create a user account. Raises :class:`AuthError` on validation errors."""
    username = (username or "").strip().lower()
    if not username:
        raise AuthError("required_field")
    problem = validate_password(password)
    if problem:
        raise AuthError(problem)
    with session_scope() as session:
        ensure_roles(session)
        repos = Repositories(session)
        if repos.users.by_username(username):
            raise AuthError("username_taken")
        role = repos.roles.by_code(role_code) or repos.roles.by_code(RoleCode.VIEWER.value)
        assert role is not None
        user = repos.users.create(
            username=username,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            role_id=role.id,
            email=email.strip(),
            phone=phone.strip(),
            is_active=True,
        )
        audit_service.log(
            session,
            user=actor,
            action=audit_service.Action.CREATE,
            entity_type="User",
            entity_id=user.id,
            description=f"user {username} ({role.code})",
        )
        return _snapshot(user)


def authenticate(username: str, password: str) -> CurrentUser:
    """Validate credentials and return the signed-in user snapshot."""
    with session_scope() as session:
        repos = Repositories(session)
        user = repos.users.by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("login_failed")
        if not user.is_active or user.is_archived:
            raise AuthError("user_inactive")
        user.last_login = datetime.now()
        audit_service.log(
            session,
            user=user,
            action=audit_service.Action.LOGIN,
            entity_type="User",
            entity_id=user.id,
            description=user.username,
        )
        return _snapshot(user)


def logout(user: CurrentUser | None) -> None:
    """Record a sign-out event."""
    if user is None:
        return
    with session_scope() as session:
        db_user = session.get(User, user.id)
        audit_service.log(
            session,
            user=db_user,
            action=audit_service.Action.LOGOUT,
            entity_type="User",
            entity_id=user.id,
            description=user.username,
        )


def set_password(user_id: int, password: str, actor: CurrentUser | None = None) -> None:
    """Replace a user's password."""
    problem = validate_password(password)
    if problem:
        raise AuthError(problem)
    with session_scope() as session:
        repos = Repositories(session)
        user = repos.users.get_or_raise(user_id)
        user.password_hash = hash_password(password)
        audit_service.log(
            session,
            user=session.get(User, actor.id) if actor else None,
            action=audit_service.Action.UPDATE,
            entity_type="User",
            entity_id=user_id,
            description=f"password reset: {user.username}",
        )


def list_users() -> list[dict]:
    """Return users as plain dictionaries for the settings table."""
    with session_scope() as session:
        rows = []
        for user in Repositories(session).users.list(order_by=User.username, include_archived=True):
            rows.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role_code": user.role.code if user.role else "",
                    "email": user.email,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "is_archived": user.is_archived,
                    "last_login": user.last_login,
                }
            )
        return rows


def update_user(
    user_id: int,
    *,
    full_name: str,
    role_code: str,
    email: str,
    phone: str,
    is_active: bool,
    actor: CurrentUser | None = None,
) -> None:
    """Update a user's profile and role."""
    with session_scope() as session:
        repos = Repositories(session)
        user = repos.users.get_or_raise(user_id)
        role = repos.roles.by_code(role_code)
        before = f"{user.full_name}/{user.role.code if user.role else ''}/{user.is_active}"
        user.full_name = full_name
        user.email = email
        user.phone = phone
        user.is_active = is_active
        if role:
            user.role_id = role.id
        audit_service.log(
            session,
            user=session.get(User, actor.id) if actor else None,
            action=audit_service.Action.UPDATE,
            entity_type="User",
            entity_id=user_id,
            description=user.username,
            old_value=before,
            new_value=f"{full_name}/{role_code}/{is_active}",
        )


def roles() -> list[Role]:
    """Return all roles (detached copies are fine for combo boxes)."""
    with session_scope() as session:
        ensure_roles(session)
        return Repositories(session).roles.list(order_by=Role.id)
