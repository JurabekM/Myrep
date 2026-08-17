"""SQLAlchemy models for the authentication and authorization system.

This module defines the database models for user management, role-based
access control, session tracking, and audit logging. All models inherit
from BaseModel which provides common fields (id, timestamps, soft delete).

Models:
    - User: User accounts with credentials and profile information.
    - Role: Named roles that group permissions together.
    - Permission: Individual module-level permission grants for roles.
    - Session: Active user sessions with token-based authentication.
    - AuditLog: Immutable audit trail of all significant system actions.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from src.database.models import BaseModel


class User(BaseModel):
    """Represents a system user with authentication credentials and profile.

    Users are associated with a single role which determines their
    permissions across all modules. Supports account locking after
    repeated failed login attempts.

    Attributes:
        username: Unique login identifier (max 50 chars).
        email: Optional unique email address.
        password_hash: Bcrypt or PBKDF2 hashed password.
        full_name: Display name (max 100 chars).
        phone: Optional phone number (max 20 chars).
        role_id: Foreign key to the user's assigned role.
        is_active: Whether the account is enabled.
        last_login: Timestamp of the most recent successful login.
        login_attempts: Counter for consecutive failed login attempts.
        locked_until: Timestamp until which the account is locked.
        avatar: Optional file path to the user's avatar image.
        language: Preferred UI language code (default 'uz').
    """

    __tablename__ = 'users'

    username = Column(
        String(50), unique=True, nullable=False, index=True,
        comment='Unique login identifier',
    )
    email = Column(
        String(255), unique=True, nullable=True, index=True,
        comment='User email address',
    )
    password_hash = Column(
        String(255), nullable=False,
        comment='Hashed password (bcrypt or PBKDF2)',
    )
    full_name = Column(
        String(100), nullable=True, default='',
        comment='Display name',
    )
    phone = Column(
        String(20), nullable=True,
        comment='Contact phone number',
    )
    role_id = Column(
        String(36), ForeignKey('roles.id'), nullable=True,
        comment='FK to the assigned role',
    )
    is_active = Column(
        Boolean, default=True, nullable=False,
        comment='Whether the account is enabled',
    )
    last_login = Column(
        DateTime, nullable=True,
        comment='Timestamp of last successful login',
    )
    login_attempts = Column(
        Integer, default=0, nullable=False,
        comment='Consecutive failed login attempts',
    )
    locked_until = Column(
        DateTime, nullable=True,
        comment='Account locked until this timestamp',
    )
    avatar = Column(
        String(500), nullable=True,
        comment='File path to avatar image',
    )
    language = Column(
        String(10), default='uz', nullable=False,
        comment='Preferred UI language code',
    )

    # ── Relationships ──────────────────────────────────────────────
    role = relationship('Role', back_populates='users', lazy='joined')
    sessions = relationship(
        'Session', back_populates='user', lazy='dynamic',
        cascade='all, delete-orphan',
    )
    audit_logs = relationship(
        'AuditLog', back_populates='user', lazy='dynamic',
    )

    def to_dict(self) -> dict:
        """Serialize user to dictionary, excluding the password hash.

        Returns:
            dict: User data with role information included.
        """
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'role_id': self.role_id,
            'is_active': self.is_active,
            'last_login': (
                self.last_login.isoformat() if self.last_login else None
            ),
            'login_attempts': self.login_attempts,
            'locked_until': (
                self.locked_until.isoformat() if self.locked_until else None
            ),
            'avatar': self.avatar,
            'language': self.language,
            'created_at': (
                self.created_at.isoformat() if self.created_at else None
            ),
            'updated_at': (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }
        if self.role:
            data['role'] = {
                'id': self.role.id,
                'name': self.role.name,
                'display_name': self.role.display_name,
            }
        else:
            data['role'] = None
        return data

    def is_locked(self) -> bool:
        """Check whether the user account is currently locked.

        Returns:
            bool: True if the account is locked and the lock has not expired.
        """
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def __repr__(self) -> str:
        """Return developer-friendly string representation."""
        return (
            f"<User(id='{self.id}', username='{self.username}', "
            f"role='{self.role_id}', active={self.is_active})>"
        )


class Role(BaseModel):
    """Represents a named role that groups permissions together.

    Roles are the cornerstone of the RBAC system. Each user is assigned
    exactly one role, and each role carries a set of module-level
    permissions. System roles (``is_system=True``) cannot be deleted
    through the application interface.

    Attributes:
        name: Unique role identifier matching a ``Roles`` enum value.
        display_name: Human-readable role name for the UI.
        description: Optional longer description of the role's purpose.
        is_system: If True, the role is protected from deletion.
    """

    __tablename__ = 'roles'

    name = Column(
        String(50), unique=True, nullable=False, index=True,
        comment='Unique role identifier (Roles enum value)',
    )
    display_name = Column(
        String(100), nullable=True, default='',
        comment='Human-readable name',
    )
    description = Column(
        Text, nullable=True,
        comment='Description of the role purpose',
    )
    is_system = Column(
        Boolean, default=True, nullable=False,
        comment='System roles cannot be deleted',
    )

    # ── Relationships ──────────────────────────────────────────────
    users = relationship(
        'User', back_populates='role', lazy='dynamic',
    )
    permissions = relationship(
        'Permission', back_populates='role',
        cascade='all, delete-orphan', lazy='joined',
    )

    def to_dict(self) -> dict:
        """Serialize role to dictionary including its permissions.

        Returns:
            dict: Role data with a nested list of permission dicts.
        """
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_system': self.is_system,
            'permissions': [p.to_dict() for p in (self.permissions or [])],
            'created_at': (
                self.created_at.isoformat() if self.created_at else None
            ),
            'updated_at': (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }

    def __repr__(self) -> str:
        """Return developer-friendly string representation."""
        return (
            f"<Role(id='{self.id}', name='{self.name}', "
            f"system={self.is_system})>"
        )


class Permission(BaseModel):
    """Represents a single permission grant for a role on a module.

    Each record authorises a specific action (e.g. VIEW, CREATE) on a
    specific module (e.g. SALES, INVENTORY) for the associated role.
    A unique constraint prevents duplicate grants.

    Attributes:
        role_id: Foreign key to the owning role.
        module: Module identifier (``ModuleNames`` enum value).
        permission: Permission identifier (``Permissions`` enum value).
    """

    __tablename__ = 'permissions'
    __table_args__ = (
        UniqueConstraint(
            'role_id', 'module', 'permission',
            name='uq_role_module_permission',
        ),
    )

    role_id = Column(
        String(36), ForeignKey('roles.id'), nullable=False,
        comment='FK to the owning role',
    )
    module = Column(
        String(50), nullable=False,
        comment='Module name (ModuleNames enum value)',
    )
    permission = Column(
        String(50), nullable=False,
        comment='Permission type (Permissions enum value)',
    )

    # ── Relationships ──────────────────────────────────────────────
    role = relationship('Role', back_populates='permissions')

    def to_dict(self) -> dict:
        """Serialize permission to dictionary.

        Returns:
            dict: Permission data including parent role id.
        """
        return {
            'id': self.id,
            'role_id': self.role_id,
            'module': self.module,
            'permission': self.permission,
        }

    def __repr__(self) -> str:
        """Return developer-friendly string representation."""
        return (
            f"<Permission(role='{self.role_id}', "
            f"module='{self.module}', permission='{self.permission}')>"
        )


class Session(BaseModel):
    """Tracks an active user session with a bearer token.

    Sessions are created on login and invalidated on logout or
    expiration. The ``token`` column is indexed for fast lookups during
    request authentication.

    Attributes:
        user_id: Foreign key to the authenticated user.
        token: Unique, cryptographically random session token.
        ip_address: Client IP address at login time.
        user_agent: Client User-Agent string at login time.
        expires_at: Timestamp after which the session is invalid.
        is_active: Manually deactivated on logout.
    """

    __tablename__ = 'sessions'

    user_id = Column(
        String(36), ForeignKey('users.id'), nullable=False,
        comment='FK to the authenticated user',
    )
    token = Column(
        String(255), unique=True, nullable=False, index=True,
        comment='Bearer session token',
    )
    ip_address = Column(
        String(45), nullable=True,
        comment='Client IP address',
    )
    user_agent = Column(
        String(500), nullable=True,
        comment='Client User-Agent header',
    )
    expires_at = Column(
        DateTime, nullable=False,
        comment='Session expiration timestamp',
    )
    is_active = Column(
        Boolean, default=True, nullable=False,
        comment='False after explicit logout',
    )

    # ── Relationships ──────────────────────────────────────────────
    user = relationship('User', back_populates='sessions')

    def is_expired(self) -> bool:
        """Check whether the session has expired.

        Returns:
            bool: True if the current time is past ``expires_at``.
        """
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        """Serialize session to dictionary.

        Returns:
            dict: Session metadata (token is intentionally included for
            internal use; API layers should strip it when needed).
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'expires_at': (
                self.expires_at.isoformat() if self.expires_at else None
            ),
            'is_active': self.is_active,
            'created_at': (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def __repr__(self) -> str:
        """Return developer-friendly string representation."""
        return (
            f"<Session(user='{self.user_id}', "
            f"active={self.is_active}, "
            f"expires='{self.expires_at}')>"
        )


class AuditLog(BaseModel):
    """Immutable record of a significant action performed in the system.

    Audit logs capture who did what, when, and from where. They are
    essential for compliance, debugging, and security analysis. The
    ``details`` field stores a JSON-encoded string with action-specific
    context.

    Attributes:
        user_id: FK to the acting user (nullable for system actions).
        action: Short action verb (e.g. 'LOGIN', 'CREATE', 'DELETE').
        module: Optional module context (e.g. 'SALES', 'INVENTORY').
        entity_type: Optional entity class name (e.g. 'Invoice').
        entity_id: Optional primary key of the affected entity.
        details: Optional JSON string with additional context.
        ip_address: Client IP address at the time of action.
    """

    __tablename__ = 'audit_logs'

    user_id = Column(
        String(36), ForeignKey('users.id'), nullable=True,
        comment='FK to the acting user',
    )
    action = Column(
        String(50), nullable=False, index=True,
        comment='Action verb (LOGIN, CREATE, UPDATE, DELETE, etc.)',
    )
    module = Column(
        String(50), nullable=True,
        comment='Module context',
    )
    entity_type = Column(
        String(100), nullable=True,
        comment='Affected entity class name',
    )
    entity_id = Column(
        String(36), nullable=True,
        comment='PK of the affected entity',
    )
    details = Column(
        Text, nullable=True,
        comment='JSON-encoded action details',
    )
    ip_address = Column(
        String(45), nullable=True,
        comment='Client IP address',
    )

    # ── Relationships ──────────────────────────────────────────────
    user = relationship('User', back_populates='audit_logs')

    # ── Indexes ────────────────────────────────────────────────────
    __table_args__ = (
        Index('ix_audit_logs_user_action', 'user_id', 'action'),
        Index('ix_audit_logs_module', 'module'),
        Index('ix_audit_logs_entity', 'entity_type', 'entity_id'),
    )

    def to_dict(self) -> dict:
        """Serialize audit log entry to dictionary.

        Returns:
            dict: Full audit log data including user information when
            the relationship is loaded.
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'module': self.module,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
        if self.user:
            data['user'] = {
                'id': self.user.id,
                'username': self.user.username,
                'full_name': self.user.full_name,
            }
        else:
            data['user'] = None
        return data

    def __repr__(self) -> str:
        """Return developer-friendly string representation."""
        return (
            f"<AuditLog(user='{self.user_id}', action='{self.action}', "
            f"module='{self.module}', entity='{self.entity_type}')>"
        )
