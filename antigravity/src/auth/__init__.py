"""Authentication and authorization package for the ERP platform.

This package provides comprehensive authentication, authorization,
and access control functionality including:

- User authentication and session management
- Role-based access control (RBAC)
- Security utilities (password hashing, token generation)
- Flask route decorators for access control
- Audit logging

Typical usage::

    from src.auth import AuthService, RBACManager, init_auth
    from src.auth import require_auth, require_role, require_permission

    # Initialise services
    rbac = RBACManager(session_factory)
    auth = AuthService(session_factory, rbac)
    init_auth(auth, rbac)

    # Authenticate a user
    result = auth.login('admin', 'secret')
    token = result['token']
"""

from src.auth.models import User, Role, Permission, Session, AuditLog
from src.auth.security import (
    hash_password,
    verify_password,
    generate_session_token,
    generate_secret_key,
    check_password_strength,
    sanitize_input,
)
from src.auth.rbac import RBACManager
from src.auth.service import AuthService
from src.auth.decorators import (
    require_auth,
    require_role,
    require_permission,
    init_auth,
)

__all__ = [
    # Models
    'User',
    'Role',
    'Permission',
    'Session',
    'AuditLog',
    # Security
    'hash_password',
    'verify_password',
    'generate_session_token',
    'generate_secret_key',
    'check_password_strength',
    'sanitize_input',
    # RBAC
    'RBACManager',
    # Service
    'AuthService',
    # Decorators
    'require_auth',
    'require_role',
    'require_permission',
    'init_auth',
]
