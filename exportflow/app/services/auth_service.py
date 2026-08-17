"""Authentication, user management and role-based access control."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models import Role, User
from app.services import audit_service
from app.services.permissions import PERMISSIONS, ROLE_NAMES, permissions_for_role
from app.utils.enums import ROLE_ADMIN
from app.utils.errors import PermissionDenied, ValidationError
from app.utils.formatting import now
from app.utils.logging_setup import get_logger
from app.utils.security import hash_password, verify_password

log = get_logger(__name__)


@dataclass(frozen=True)
class CurrentUser:
    """Immutable snapshot of the signed-in user carried by the UI layer."""

    id: int
    username: str
    full_name: str
    role_code: str
    role_name: str
    language: str
    email: str | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    def can(self, permission: str) -> bool:
        """Return True when this user holds the given permission."""
        return self.role_code == ROLE_ADMIN or permission in self.permissions

    def require(self, permission: str) -> None:
        """Raise :class:`PermissionDenied` when the permission is missing."""
        if not self.can(permission):
            raise PermissionDenied(
                f"Permission '{permission}' is required",
                key="error.permission_denied_named",
                permission=permission,
            )


def _to_current_user(user: User) -> CurrentUser:
    codes = {perm.code for perm in user.role.permissions}
    if not codes:
        codes = set(permissions_for_role(user.role.code))
    return CurrentUser(
        id=user.id,
        username=user.username,
        full_name=user.full_name or user.username,
        role_code=user.role.code,
        role_name=user.role.name or ROLE_NAMES.get(user.role.code, user.role.code),
        language=user.language or "uz",
        email=user.email,
        permissions=frozenset(codes),
    )


def has_any_user() -> bool:
    """True when at least one non-archived account exists."""
    with session_scope() as session:
        count = session.scalar(
            select(func.count()).select_from(User).where(User.is_archived.is_(False))
        )
        return bool(count)


def authenticate(username: str, password: str) -> CurrentUser:
    """Validate credentials and return the signed-in user snapshot."""
    username = (username or "").strip()
    if not username or not password:
        raise ValidationError("Username and password are required", key="error.login_empty")
    with session_scope() as session:
        user = session.scalar(select(User).where(func.lower(User.username) == username.lower()))
        if user is None or not verify_password(password, user.password_hash):
            raise ValidationError("Invalid username or password", key="error.login_invalid")
        if not user.is_active or user.is_archived:
            raise PermissionDenied("Account is disabled", key="error.login_disabled")
        user.last_login_at = now()
        snapshot = _to_current_user(user)
        audit_service.record(
            session,
            action="login",
            entity_type="user",
            entity_id=user.id,
            summary=f"User {user.username} signed in",
            user_id=user.id,
            username=user.username,
        )
    log.info("User %s authenticated as %s", snapshot.username, snapshot.role_code)
    return snapshot


def create_first_admin(
    username: str, password: str, full_name: str, language: str = "uz"
) -> CurrentUser:
    """Create the initial administrator account on first launch."""
    if has_any_user():
        raise ValidationError("Users already exist", key="error.admin_exists")
    with session_scope() as session:
        role = session.scalar(select(Role).where(Role.code == ROLE_ADMIN))
        if role is None:
            raise ValidationError("Administrator role is missing", key="error.role_missing")
        user = User(
            username=username.strip(),
            password_hash=hash_password(password),
            full_name=full_name or username,
            role_id=role.id,
            language=language,
            is_active=True,
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        snapshot = _to_current_user(user)
        audit_service.record(
            session,
            action="create",
            entity_type="user",
            entity_id=user.id,
            summary=f"First administrator {user.username} created",
            user_id=user.id,
            username=user.username,
        )
    return snapshot


def validate_password(password: str, confirm: str | None = None) -> None:
    """Enforce the minimal password policy."""
    if not password or len(password) < 6:
        raise ValidationError("Password must be at least 6 characters", key="error.password_short")
    if confirm is not None and password != confirm:
        raise ValidationError("Passwords do not match", key="error.password_mismatch")


# --------------------------------------------------------------------- users


def list_users(session: Session, include_archived: bool = False) -> list[dict]:
    """Return every user account as display dictionaries."""
    stmt = select(User).order_by(User.username)
    if not include_archived:
        stmt = stmt.where(User.is_archived.is_(False))
    return [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "position": user.position,
            "role_code": user.role.code,
            "role_name": user.role.name,
            "role_id": user.role_id,
            "language": user.language,
            "is_active": user.is_active,
            "is_archived": user.is_archived,
            "last_login_at": user.last_login_at,
        }
        for user in session.scalars(stmt).unique().all()
    ]


def list_roles(session: Session) -> list[dict]:
    """Return every role with its permission codes."""
    roles = session.scalars(select(Role).order_by(Role.id)).unique().all()
    return [
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "permissions": sorted(perm.code for perm in role.permissions),
        }
        for role in roles
    ]


def save_user(
    session: Session,
    actor: CurrentUser,
    *,
    user_id: int | None,
    username: str,
    full_name: str,
    role_id: int,
    email: str | None = None,
    phone: str | None = None,
    position: str | None = None,
    language: str = "uz",
    is_active: bool = True,
    password: str | None = None,
) -> User:
    """Create or update a user account (requires ``user.manage``)."""
    actor.require("user.manage")
    username = (username or "").strip()
    if not username:
        raise ValidationError("Username is required", key="error.username_required")

    duplicate = session.scalar(
        select(User).where(func.lower(User.username) == username.lower(), User.id != (user_id or 0))
    )
    if duplicate is not None:
        raise ValidationError("Username already taken", key="error.username_taken")

    if user_id:
        user = session.get(User, user_id)
        if user is None:
            raise ValidationError("User not found", key="error.not_found")
        action = "update"
    else:
        if not password:
            raise ValidationError("Password is required", key="error.password_required")
        user = User(username=username, password_hash=hash_password(password))
        session.add(user)
        action = "create"

    user.username = username
    user.full_name = full_name or username
    user.role_id = role_id
    user.email = email
    user.phone = phone
    user.position = position
    user.language = language
    user.is_active = is_active
    if password:
        validate_password(password)
        user.password_hash = hash_password(password)
    session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="user",
        entity_id=user.id,
        summary=f"User {user.username} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    return user


def archive_user(session: Session, actor: CurrentUser, user_id: int) -> None:
    """Disable and archive a user account."""
    actor.require("user.manage")
    if user_id == actor.id:
        raise ValidationError("You cannot archive your own account", key="error.self_archive")
    user = session.get(User, user_id)
    if user is None:
        raise ValidationError("User not found", key="error.not_found")
    user.is_archived = True
    user.is_active = False
    user.archived_at = now()
    session.flush()
    audit_service.record(
        session,
        action="archive",
        entity_type="user",
        entity_id=user.id,
        summary=f"User {user.username} archived",
        user_id=actor.id,
        username=actor.username,
    )


def change_password(session: Session, actor: CurrentUser, user_id: int, new_password: str) -> None:
    """Set a new password for one's own account or, as admin, for anyone."""
    if user_id != actor.id:
        actor.require("user.manage")
    validate_password(new_password)
    user = session.get(User, user_id)
    if user is None:
        raise ValidationError("User not found", key="error.not_found")
    user.password_hash = hash_password(new_password)
    session.flush()
    audit_service.record(
        session,
        action="update",
        entity_type="user",
        entity_id=user.id,
        summary=f"Password changed for {user.username}",
        user_id=actor.id,
        username=actor.username,
    )


def all_permission_codes() -> list[str]:
    """Sorted list of every permission code known to the application."""
    return sorted(PERMISSIONS)
