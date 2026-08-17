"""Authentication service for the ERP platform.

Provides the core business logic for user authentication, session
management, user CRUD operations, password management, and audit
logging. Integrates with the RBAC manager for permission retrieval
and emits domain events through the event bus.

Classes:
    AuthService: Stateless service orchestrating authentication workflows.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from src.core.constants import Roles
from src.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
)
from src.core.utils import generate_uuid, validate_email
from src.core.events import event_bus, Events
from src.auth.models import User, Role, Session, AuditLog
from src.auth.security import (
    hash_password,
    verify_password,
    generate_session_token,
    check_password_strength,
    sanitize_input,
)
from src.auth.rbac import RBACManager


logger = logging.getLogger(__name__)


class AuthService:
    """Core authentication service for the ERP platform.

    Handles user authentication, session management, user CRUD,
    password management, and audit logging.  Account locking is
    enforced after a configurable number of failed login attempts.

    Class Attributes:
        MAX_LOGIN_ATTEMPTS: Failed attempts before auto-lock (default 5).
        LOCK_DURATION_MINUTES: Lock duration in minutes (default 30).
        SESSION_TIMEOUT_SECONDS: Session TTL in seconds (default 3600).
    """

    MAX_LOGIN_ATTEMPTS: int = 5
    LOCK_DURATION_MINUTES: int = 30
    SESSION_TIMEOUT_SECONDS: int = 3600

    def __init__(
        self,
        session_factory,
        rbac_manager: RBACManager,
    ) -> None:
        """Initialise the authentication service.

        Args:
            session_factory: Callable returning a new SQLAlchemy
                ``Session`` instance.
            rbac_manager: An initialised ``RBACManager`` for permission
                queries.
        """
        self._session_factory = session_factory
        self._rbac = rbac_manager
        self.logger = logger

    # ================================================================
    # Authentication
    # ================================================================

    def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """Authenticate a user and create a new session.

        On success the user's login counter is reset, a session token
        is generated, and domain events are emitted. On failure the
        login attempt counter is incremented; after
        ``MAX_LOGIN_ATTEMPTS`` consecutive failures the account is
        locked for ``LOCK_DURATION_MINUTES``.

        Args:
            username: The user's login name.
            password: The plaintext password to verify.
            ip_address: Optional client IP for the session record.
            user_agent: Optional client User-Agent for the session.

        Returns:
            dict: ``{'user': dict, 'token': str, 'permissions': dict}``

        Raises:
            AuthenticationError: On invalid credentials, locked or
                deactivated accounts, or when the user is not found.
        """
        username = sanitize_input(username).strip()
        if not username or not password:
            raise AuthenticationError("Username and password are required")

        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(
                    User.username == username,
                    User.is_deleted.is_(False),
                )
                .first()
            )

            if not user:
                raise AuthenticationError("Invalid credentials")

            # Check account lock
            if user.is_locked():
                remaining = (
                    user.locked_until - datetime.utcnow()
                ).seconds // 60
                raise AuthenticationError(
                    f"Account is locked. Try again in {remaining} minute(s)"
                )

            # Check active status
            if not user.is_active:
                raise AuthenticationError("Account is deactivated")

            # Verify password
            if not verify_password(password, user.password_hash):
                user.login_attempts = (user.login_attempts or 0) + 1
                if user.login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                    user.locked_until = datetime.utcnow() + timedelta(
                        minutes=self.LOCK_DURATION_MINUTES,
                    )
                    self.logger.warning(
                        "Account locked for user '%s' after %d attempts",
                        username, user.login_attempts,
                    )
                session.commit()
                raise AuthenticationError("Invalid credentials")

            # Successful authentication
            user.login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()

            # Create session
            token = generate_session_token()
            new_session = Session(
                user_id=user.id,
                token=token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(
                    seconds=self.SESSION_TIMEOUT_SECONDS,
                ),
                is_active=True,
            )
            session.add(new_session)
            session.commit()

            # Gather permissions
            permissions = self._rbac.get_user_permissions(user.id)

            # Audit log
            self._create_audit_log_internal(
                session, user.id, 'LOGIN', ip_address=ip_address,
                details=json.dumps({'user_agent': user_agent}),
            )
            session.commit()

            # Emit event
            try:
                event_bus.emit(Events.USER_LOGIN, {
                    'user_id': user.id,
                    'username': user.username,
                    'ip_address': ip_address,
                })
            except Exception:
                self.logger.debug("Event emission failed for USER_LOGIN")

            user_dict = user.to_dict()
            return {
                'user': user_dict,
                'token': token,
                'permissions': permissions,
            }

        except AuthenticationError:
            raise
        except Exception as exc:
            session.rollback()
            self.logger.exception("Login error for user '%s'", username)
            raise AuthenticationError(
                "An error occurred during authentication"
            ) from exc
        finally:
            session.close()

    def logout(self, token: str) -> bool:
        """Invalidate a session token.

        Args:
            token: The bearer token to revoke.

        Returns:
            bool: True if the session was found and deactivated.
        """
        if not token:
            return False

        session = self._session_factory()
        try:
            sess = (
                session.query(Session)
                .filter(Session.token == token, Session.is_active.is_(True))
                .first()
            )
            if not sess:
                return False

            sess.is_active = False

            self._create_audit_log_internal(
                session, sess.user_id, 'LOGOUT',
            )
            session.commit()

            # Emit event
            try:
                event_bus.emit(Events.USER_LOGOUT, {
                    'user_id': sess.user_id,
                    'token': token,
                })
            except Exception:
                self.logger.debug("Event emission failed for USER_LOGOUT")

            return True
        except Exception:
            session.rollback()
            self.logger.exception("Logout error")
            return False
        finally:
            session.close()

    def validate_session(self, token: str) -> Optional[User]:
        """Validate a session token and return the associated user.

        Expired sessions are automatically deactivated.

        Args:
            token: The bearer token to validate.

        Returns:
            User: The authenticated user, or None if invalid/expired.
        """
        if not token:
            return None

        session = self._session_factory()
        try:
            sess = (
                session.query(Session)
                .filter(Session.token == token, Session.is_active.is_(True))
                .first()
            )
            if not sess:
                return None

            if sess.is_expired():
                sess.is_active = False
                session.commit()
                return None

            user = (
                session.query(User)
                .filter(
                    User.id == sess.user_id,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
                .first()
            )
            return user
        except Exception:
            self.logger.exception("Session validation error")
            return None
        finally:
            session.close()

    # ================================================================
    # User CRUD
    # ================================================================

    def create_user(
        self,
        data: dict,
        created_by: Optional[str] = None,
    ) -> User:
        """Create a new user account.

        Args:
            data: Dictionary with user fields. Required keys:
                ``username``, ``password``. Optional: ``email``,
                ``full_name``, ``phone``, ``role_id``, ``language``,
                ``avatar``.
            created_by: ID of the user performing the creation.

        Returns:
            User: The newly created user instance.

        Raises:
            ValidationError: On missing/invalid fields or duplicates.
        """
        username = sanitize_input(data.get('username', ''))
        password = data.get('password', '')
        email = data.get('email')
        role_id = data.get('role_id')

        # Validate required fields
        if not username:
            raise ValidationError("Username is required")
        if not password:
            raise ValidationError("Password is required")

        # Password strength
        is_strong, message = check_password_strength(password)
        if not is_strong:
            raise ValidationError(message)

        session = self._session_factory()
        try:
            # Check username uniqueness
            existing = (
                session.query(User)
                .filter(User.username == username)
                .first()
            )
            if existing:
                raise ValidationError(
                    f"Username '{username}' is already taken"
                )

            # Check email uniqueness
            if email:
                if not validate_email(email):
                    raise ValidationError(f"Invalid email: '{email}'")
                existing_email = (
                    session.query(User)
                    .filter(User.email == email)
                    .first()
                )
                if existing_email:
                    raise ValidationError(
                        f"Email '{email}' is already registered"
                    )

            # Resolve role
            if not role_id and data.get('role'):
                role = (
                    session.query(Role)
                    .filter(Role.name == data['role'])
                    .first()
                )
                if role:
                    role_id = role.id

            user = User(
                id=generate_uuid(),
                username=username,
                email=email,
                password_hash=hash_password(password),
                full_name=sanitize_input(data.get('full_name', '')),
                phone=data.get('phone'),
                role_id=role_id,
                is_active=data.get('is_active', True),
                language=data.get('language', 'uz'),
                avatar=data.get('avatar'),
                created_by=created_by,
            )
            session.add(user)
            session.commit()

            # Audit log
            self._create_audit_log_internal(
                session, created_by, 'CREATE',
                module='AUTH',
                entity_type='User',
                entity_id=user.id,
                details=json.dumps({'username': username}),
            )
            session.commit()

            # Emit event
            try:
                event_bus.emit(Events.USER_CREATED, {
                    'user_id': user.id,
                    'username': user.username,
                    'created_by': created_by,
                })
            except Exception:
                self.logger.debug("Event emission failed for USER_CREATED")

            session.refresh(user)
            return user

        except (ValidationError, AuthenticationError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            self.logger.exception("Error creating user '%s'", username)
            raise ValidationError(
                "An error occurred while creating the user"
            ) from exc
        finally:
            session.close()

    def update_user(
        self,
        user_id: str,
        data: dict,
        updated_by: Optional[str] = None,
    ) -> User:
        """Update an existing user's profile fields.

        Password changes are **not** handled by this method; use
        :meth:`change_password` or :meth:`reset_password` instead.

        Args:
            user_id: Primary key of the user to update.
            data: Dictionary of fields to update. Allowed keys:
                ``full_name``, ``email``, ``phone``, ``role_id``,
                ``is_active``, ``avatar``, ``language``.
            updated_by: ID of the user performing the update.

        Returns:
            User: The updated user instance.

        Raises:
            ValidationError: If the user is not found or data is
                invalid.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user:
                raise ValidationError(f"User '{user_id}' not found")

            allowed_fields = {
                'full_name', 'email', 'phone', 'role_id',
                'is_active', 'avatar', 'language',
            }
            for field in allowed_fields:
                if field not in data:
                    continue
                value = data[field]
                if field == 'email' and value:
                    if not validate_email(value):
                        raise ValidationError(f"Invalid email: '{value}'")
                    existing = (
                        session.query(User)
                        .filter(User.email == value, User.id != user_id)
                        .first()
                    )
                    if existing:
                        raise ValidationError(
                            f"Email '{value}' is already registered"
                        )
                if isinstance(value, str) and field in (
                    'full_name', 'phone', 'avatar', 'language',
                ):
                    value = sanitize_input(value)
                setattr(user, field, value)

            user.updated_by = updated_by
            user.updated_at = datetime.utcnow()
            session.commit()

            self._create_audit_log_internal(
                session, updated_by, 'UPDATE',
                module='AUTH',
                entity_type='User',
                entity_id=user_id,
                details=json.dumps({
                    'fields': list(
                        set(data.keys()) & allowed_fields
                    ),
                }),
            )
            session.commit()
            session.refresh(user)
            return user

        except ValidationError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            self.logger.exception("Error updating user '%s'", user_id)
            raise ValidationError(
                "An error occurred while updating the user"
            ) from exc
        finally:
            session.close()

    def delete_user(self, user_id: str, deleted_by: Optional[str] = None) -> bool:
        """Soft-delete a user account.

        Sets ``is_deleted``, ``deleted_at``, and ``is_active=False``.
        Active sessions are also deactivated.

        Args:
            user_id: Primary key of the user to delete.
            deleted_by: ID of the user performing the deletion.

        Returns:
            bool: True if the user was found and deleted.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user:
                return False

            user.is_deleted = True
            user.deleted_at = datetime.utcnow()
            user.is_active = False
            user.updated_by = deleted_by

            # Deactivate all sessions
            (
                session.query(Session)
                .filter(
                    Session.user_id == user_id,
                    Session.is_active.is_(True),
                )
                .update({'is_active': False})
            )

            session.commit()

            self._create_audit_log_internal(
                session, deleted_by, 'DELETE',
                module='AUTH',
                entity_type='User',
                entity_id=user_id,
                details=json.dumps({'username': user.username}),
            )
            session.commit()
            return True

        except Exception:
            session.rollback()
            self.logger.exception("Error deleting user '%s'", user_id)
            return False
        finally:
            session.close()

    def get_user(self, user_id: str) -> Optional[User]:
        """Retrieve a single user by primary key.

        Args:
            user_id: The user's UUID.

        Returns:
            User: The user instance, or None if not found or deleted.
        """
        session = self._session_factory()
        try:
            return (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
        except Exception:
            self.logger.exception("Error fetching user '%s'", user_id)
            return None
        finally:
            session.close()

    def get_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        """Retrieve a paginated list of users.

        Args:
            page: Page number (1-based).
            per_page: Maximum results per page.
            search: Optional search term matched against username,
                full_name, and email (case-insensitive LIKE).
            role_id: Optional filter by role ID.

        Returns:
            tuple: ``(list_of_user_dicts, total_count)``
        """
        session = self._session_factory()
        try:
            query = session.query(User).filter(User.is_deleted.is_(False))

            if search:
                pattern = f"%{search}%"
                query = query.filter(
                    (User.username.ilike(pattern))
                    | (User.full_name.ilike(pattern))
                    | (User.email.ilike(pattern))
                )

            if role_id:
                query = query.filter(User.role_id == role_id)

            total = query.count()

            users = (
                query
                .order_by(User.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return [u.to_dict() for u in users], total

        except Exception:
            self.logger.exception("Error listing users")
            return [], 0
        finally:
            session.close()

    # ================================================================
    # Password Management
    # ================================================================

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change a user's password after verifying the old one.

        Args:
            user_id: Primary key of the user.
            old_password: Current plaintext password for verification.
            new_password: New plaintext password to set.

        Returns:
            bool: True on success.

        Raises:
            AuthenticationError: If the old password is incorrect.
            ValidationError: If the new password is too weak or the
                user is not found.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user:
                raise ValidationError("User not found")

            if not verify_password(old_password, user.password_hash):
                raise AuthenticationError("Current password is incorrect")

            is_strong, message = check_password_strength(new_password)
            if not is_strong:
                raise ValidationError(message)

            user.password_hash = hash_password(new_password)
            user.updated_at = datetime.utcnow()
            session.commit()

            self._create_audit_log_internal(
                session, user_id, 'PASSWORD_CHANGE',
                module='AUTH', entity_type='User', entity_id=user_id,
            )
            session.commit()
            return True

        except (AuthenticationError, ValidationError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            self.logger.exception(
                "Error changing password for user '%s'", user_id,
            )
            raise ValidationError(
                "An error occurred while changing the password"
            ) from exc
        finally:
            session.close()

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """Reset a user's password without requiring the old one.

        Intended for administrator use only. Callers are responsible
        for enforcing authorisation before invoking this method.

        Args:
            user_id: Primary key of the user.
            new_password: New plaintext password to set.

        Returns:
            bool: True on success.

        Raises:
            ValidationError: If the password is too weak or the user
                is not found.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user:
                raise ValidationError("User not found")

            is_strong, message = check_password_strength(new_password)
            if not is_strong:
                raise ValidationError(message)

            user.password_hash = hash_password(new_password)
            user.login_attempts = 0
            user.locked_until = None
            user.updated_at = datetime.utcnow()
            session.commit()

            self._create_audit_log_internal(
                session, user_id, 'PASSWORD_RESET',
                module='AUTH', entity_type='User', entity_id=user_id,
            )
            session.commit()
            return True

        except ValidationError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            self.logger.exception(
                "Error resetting password for user '%s'", user_id,
            )
            raise ValidationError(
                "An error occurred while resetting the password"
            ) from exc
        finally:
            session.close()

    # ================================================================
    # Account Locking
    # ================================================================

    def lock_user(self, user_id: str) -> bool:
        """Manually lock a user account for 365 days.

        Args:
            user_id: Primary key of the user to lock.

        Returns:
            bool: True if the user was found and locked.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user:
                return False

            user.locked_until = datetime.utcnow() + timedelta(days=365)
            session.commit()

            self._create_audit_log_internal(
                session, user_id, 'LOCK_USER',
                module='AUTH', entity_type='User', entity_id=user_id,
            )
            session.commit()
            return True

        except Exception:
            session.rollback()
            self.logger.exception("Error locking user '%s'", user_id)
            return False
        finally:
            session.close()

    def unlock_user(self, user_id: str) -> bool:
        """Unlock a previously locked user account.

        Resets both the lock timestamp and the login attempt counter.

        Args:
            user_id: Primary key of the user to unlock.

        Returns:
            bool: True if the user was found and unlocked.
        """
        session = self._session_factory()
        try:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False))
                .first()
            )
            if not user:
                return False

            user.locked_until = None
            user.login_attempts = 0
            session.commit()

            self._create_audit_log_internal(
                session, user_id, 'UNLOCK_USER',
                module='AUTH', entity_type='User', entity_id=user_id,
            )
            session.commit()
            return True

        except Exception:
            session.rollback()
            self.logger.exception("Error unlocking user '%s'", user_id)
            return False
        finally:
            session.close()

    # ================================================================
    # Online Users
    # ================================================================

    def get_online_users(self) -> list[dict]:
        """Return users with at least one active, non-expired session.

        Returns:
            list[dict]: Serialised user dictionaries.
        """
        session = self._session_factory()
        try:
            now = datetime.utcnow()
            users = (
                session.query(User)
                .join(Session, Session.user_id == User.id)
                .filter(
                    Session.is_active.is_(True),
                    Session.expires_at > now,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
                .distinct()
                .all()
            )
            return [u.to_dict() for u in users]
        except Exception:
            self.logger.exception("Error fetching online users")
            return []
        finally:
            session.close()

    # ================================================================
    # Audit Logging
    # ================================================================

    def create_audit_log(
        self,
        user_id: Optional[str] = None,
        action: str = '',
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Any = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry.

        This is the public API for recording audit events from outside
        the auth service.

        Args:
            user_id: ID of the acting user (None for system actions).
            action: Short action verb (e.g. 'CREATE', 'UPDATE').
            module: Module context (e.g. 'SALES').
            entity_type: Affected entity class name.
            entity_id: Primary key of the affected entity.
            details: Additional context; dicts are JSON-serialised.
            ip_address: Client IP address.

        Returns:
            AuditLog: The persisted audit log instance.
        """
        session = self._session_factory()
        try:
            log = self._create_audit_log_internal(
                session, user_id, action, module,
                entity_type, entity_id, details, ip_address,
            )
            session.commit()
            return log
        except Exception:
            session.rollback()
            self.logger.exception("Error creating audit log")
            raise
        finally:
            session.close()

    def get_audit_logs(
        self,
        page: int = 1,
        per_page: int = 50,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        module: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[list[dict], int]:
        """Retrieve a paginated, filterable list of audit logs.

        Args:
            page: Page number (1-based).
            per_page: Maximum results per page.
            user_id: Optional filter by acting user.
            action: Optional filter by action verb.
            module: Optional filter by module name.
            date_from: Optional inclusive start date.
            date_to: Optional inclusive end date.

        Returns:
            tuple: ``(list_of_audit_dicts, total_count)``
        """
        session = self._session_factory()
        try:
            query = session.query(AuditLog)

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action)
            if module:
                query = query.filter(AuditLog.module == module)
            if date_from:
                query = query.filter(AuditLog.created_at >= date_from)
            if date_to:
                query = query.filter(AuditLog.created_at <= date_to)

            total = query.count()

            logs = (
                query
                .order_by(AuditLog.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return [log.to_dict() for log in logs], total

        except Exception:
            self.logger.exception("Error listing audit logs")
            return [], 0
        finally:
            session.close()

    # ================================================================
    # Internal Helpers
    # ================================================================

    def _create_audit_log_internal(
        self,
        session,
        user_id: Optional[str],
        action: str,
        module: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Any = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry within an existing session.

        This private helper avoids opening a new database session,
        allowing callers to batch the audit record into their own
        transaction.

        Args:
            session: Active SQLAlchemy session.
            user_id: ID of the acting user.
            action: Short action verb.
            module: Module context.
            entity_type: Affected entity class name.
            entity_id: Primary key of the affected entity.
            details: Additional context (dicts are JSON-serialised).
            ip_address: Client IP address.

        Returns:
            AuditLog: The (not yet committed) audit log instance.
        """
        if isinstance(details, dict):
            details = json.dumps(details, ensure_ascii=False)

        log = AuditLog(
            id=generate_uuid(),
            user_id=user_id,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details if isinstance(details, str) else (
                str(details) if details is not None else None
            ),
            ip_address=ip_address,
        )
        session.add(log)
        return log
