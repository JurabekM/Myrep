"""Authentication and authorization decorators for Flask routes.

Provides reusable decorators that enforce authentication and
permission requirements on Flask view functions. Decorators
extract the session token from the ``Authorization`` header
(Bearer scheme) or the ``session_token`` cookie, validate it
via :class:`~src.auth.service.AuthService`, and attach the
authenticated user to Flask's ``g`` context.

Usage::

    from src.auth.decorators import require_auth, require_role, require_permission

    @app.route('/api/dashboard')
    @require_auth
    def dashboard():
        user = g.current_user
        ...

    @app.route('/api/admin/users')
    @require_auth
    @require_role('ADMINISTRATOR', 'OWNER')
    def list_users():
        ...

    @app.route('/api/sales/invoices', methods=['POST'])
    @require_auth
    @require_permission('SALES', 'CREATE')
    def create_invoice():
        ...

Functions:
    init_auth: Wire up service instances (called once at startup).
    require_auth: Decorator enforcing a valid session.
    require_role: Decorator factory enforcing role membership.
    require_permission: Decorator factory enforcing module permission.
"""

import logging
from functools import wraps
from typing import Callable, Any

from flask import request, g, jsonify

from src.core.exceptions import AuthenticationError, AuthorizationError


# ── Module-level service references (set during app init) ──────────
_auth_service = None
_rbac_manager = None

logger = logging.getLogger(__name__)


def init_auth(auth_service, rbac_manager) -> None:
    """Initialise the decorator module with live service instances.

    Must be called once during application startup **after** the
    ``AuthService`` and ``RBACManager`` have been constructed.

    Args:
        auth_service: A fully initialised
            :class:`~src.auth.service.AuthService` instance.
        rbac_manager: A fully initialised
            :class:`~src.auth.rbac.RBACManager` instance.
    """
    global _auth_service, _rbac_manager  # noqa: PLW0603
    _auth_service = auth_service
    _rbac_manager = rbac_manager
    logger.info("Auth decorators initialised")


def _get_token_from_request() -> str | None:
    """Extract the authentication token from the current request.

    Inspection order:

    1. ``Authorization`` header with the ``Bearer`` scheme.
    2. ``session_token`` cookie.

    Returns:
        str | None: The raw token string, or None if absent.
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return request.cookies.get('session_token')


# ====================================================================
# @require_auth
# ====================================================================

def require_auth(f: Callable) -> Callable:
    """Decorator that requires a valid authenticated session.

    Extracts the session token from the request, validates it
    through the ``AuthService``, and sets the following on
    Flask's ``g`` context:

    * ``g.current_user`` — the authenticated :class:`User` instance.
    * ``g.session_token`` — the raw bearer token string.

    Returns a ``401`` JSON response if authentication fails.

    Args:
        f: The Flask view function to protect.

    Returns:
        Callable: The wrapped view function.
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if _auth_service is None:
            logger.error("require_auth called before init_auth")
            return jsonify({
                'error': 'Authentication service not initialised',
                'code': 'SERVER_ERROR',
            }), 500

        token = _get_token_from_request()
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED',
            }), 401

        user = _auth_service.validate_session(token)
        if user is None:
            return jsonify({
                'error': 'Invalid or expired session',
                'code': 'INVALID_SESSION',
            }), 401

        g.current_user = user
        g.session_token = token
        return f(*args, **kwargs)

    return decorated


# ====================================================================
# @require_role
# ====================================================================

def require_role(*roles: str) -> Callable:
    """Decorator factory that restricts access to specific roles.

    Must be applied **after** ``@require_auth`` so that
    ``g.current_user`` is available.

    Args:
        *roles: One or more role names (``Roles`` enum values)
            that are granted access.

    Returns:
        Callable: A decorator that enforces role membership.

    Example::

        @app.route('/admin')
        @require_auth
        @require_role('ADMINISTRATOR', 'OWNER')
        def admin_panel():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            if not hasattr(g, 'current_user') or g.current_user is None:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED',
                }), 401

            user = g.current_user
            user_role = user.role.name if user.role else None

            if user_role not in roles:
                logger.warning(
                    "Role check failed for user '%s': "
                    "required one of %s, has '%s'",
                    user.username, roles, user_role,
                )
                return jsonify({
                    'error': 'Insufficient role privileges',
                    'code': 'ROLE_DENIED',
                    'required_roles': list(roles),
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# ====================================================================
# @require_permission
# ====================================================================

def require_permission(module: str, permission: str) -> Callable:
    """Decorator factory that enforces a module-level permission.

    Must be applied **after** ``@require_auth`` so that
    ``g.current_user`` is available. Uses the ``RBACManager`` to
    perform the permission check; administrators pass automatically.

    Args:
        module: Module name (``ModuleNames`` enum value).
        permission: Permission name (``Permissions`` enum value).

    Returns:
        Callable: A decorator that enforces the permission.

    Example::

        @app.route('/api/sales', methods=['POST'])
        @require_auth
        @require_permission('SALES', 'CREATE')
        def create_sale():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            if not hasattr(g, 'current_user') or g.current_user is None:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED',
                }), 401

            if _rbac_manager is None:
                logger.error(
                    "require_permission called before init_auth",
                )
                return jsonify({
                    'error': 'Authorisation service not initialised',
                    'code': 'SERVER_ERROR',
                }), 500

            user = g.current_user
            if not _rbac_manager.has_permission(
                user.id, module, permission,
            ):
                logger.warning(
                    "Permission denied for user '%s': %s.%s",
                    user.username, module, permission,
                )
                return jsonify({
                    'error': 'Permission denied',
                    'code': 'PERMISSION_DENIED',
                    'required_module': module,
                    'required_permission': permission,
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
