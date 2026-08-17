"""Default configuration values for the Enterprise ERP platform.

Provides two top-level dictionaries:

- :data:`DEFAULT_CONFIG` — complete application configuration with
  sensible defaults for all subsystems (database, server, security,
  company, backup, logging).
- :data:`PERMISSION_MATRIX` — serialisable role-based permission
  matrix using plain strings instead of enum members, suitable for
  JSON/YAML export and API responses.

These dictionaries serve as the canonical source of truth for default
values and can be imported by any module that needs fallback settings.
"""

import os
import uuid

# ---------------------------------------------------------------------------
# Default application configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    'app': {
        'name': 'Enterprise ERP',
        'version': '1.0.0',
    },
    'database': {
        'type': 'sqlite',
        'path': os.path.join('data', 'db', 'erp_database.db'),
        'postgresql': {
            'host': 'localhost',
            'port': 5432,
            'name': 'erp_database',
            'user': 'erp_user',
            'password': '',
        },
    },
    'server': {
        'host': '0.0.0.0',
        'port': 8000,
        'debug': False,
    },
    'security': {
        'secret_key': uuid.uuid4().hex + uuid.uuid4().hex,
        'session_timeout': 3600,
        'max_login_attempts': 5,
        'password_min_length': 8,
    },
    'company': {
        'name': 'My Company',
        'currency': 'UZS',
        'vat_rate': 0.12,
        'language': 'uz',
    },
    'backup': {
        'auto_backup': True,
        'interval_hours': 24,
        'max_backups': 30,
        'path': os.path.join('data', 'backups'),
    },
    'logging': {
        'level': 'INFO',
        'file': os.path.join('data', 'logs', 'erp.log'),
    },
}
"""Complete default configuration dictionary.

Used as a fallback when no ``config.yaml`` file is present.
The ``security.secret_key`` is auto-generated at module load time.
"""


# ---------------------------------------------------------------------------
# Serialisable permission matrix (string keys)
# ---------------------------------------------------------------------------

# Convenience permission sets (plain strings)
_ALL = ['view', 'create', 'edit', 'delete', 'export', 'import', 'backup', 'admin']
_CRUD_EXPORT_IMPORT = ['view', 'create', 'edit', 'delete', 'export', 'import']
_CRUD_EXPORT = ['view', 'create', 'edit', 'delete', 'export']
_CRUD = ['view', 'create', 'edit', 'delete']
_VIEW_EXPORT = ['view', 'export']
_VIEW_ONLY = ['view']
_NONE: list = []

# All module names as strings
_MODULES = [
    'dashboard', 'sales', 'inventory', 'accounting',
    'hr', 'crm', 'reports', 'analytics', 'settings',
]

PERMISSION_MATRIX: dict = {
    # Full access roles
    'administrator': {mod: list(_ALL) for mod in _MODULES},
    'owner': {mod: list(_ALL) for mod in _MODULES},

    # Accountant — full CRUD on accounting, read-only elsewhere
    'accountant': {
        'dashboard': list(_VIEW_ONLY),
        'sales': list(_VIEW_EXPORT),
        'inventory': list(_VIEW_EXPORT),
        'accounting': list(_CRUD_EXPORT_IMPORT),
        'hr': list(_NONE),
        'crm': list(_VIEW_ONLY),
        'reports': list(_CRUD_EXPORT),
        'analytics': list(_VIEW_EXPORT),
        'settings': list(_NONE),
    },

    # Cashier — can operate sales, read-only on inventory/accounting
    'cashier': {
        'dashboard': list(_VIEW_ONLY),
        'sales': list(_CRUD_EXPORT),
        'inventory': list(_VIEW_ONLY),
        'accounting': list(_VIEW_ONLY),
        'hr': list(_NONE),
        'crm': list(_VIEW_ONLY),
        'reports': list(_NONE),
        'analytics': list(_NONE),
        'settings': list(_NONE),
    },

    # Warehouse — full CRUD on inventory
    'warehouse': {
        'dashboard': list(_VIEW_ONLY),
        'sales': list(_VIEW_ONLY),
        'inventory': list(_CRUD_EXPORT_IMPORT),
        'accounting': list(_NONE),
        'hr': list(_NONE),
        'crm': list(_NONE),
        'reports': list(_VIEW_EXPORT),
        'analytics': list(_VIEW_ONLY),
        'settings': list(_NONE),
    },

    # Sales Manager — full CRUD on sales and CRM
    'sales_manager': {
        'dashboard': list(_VIEW_ONLY),
        'sales': list(_CRUD_EXPORT_IMPORT),
        'inventory': list(_VIEW_EXPORT),
        'accounting': list(_VIEW_ONLY),
        'hr': list(_NONE),
        'crm': list(_CRUD_EXPORT),
        'reports': list(_CRUD_EXPORT),
        'analytics': list(_VIEW_EXPORT),
        'settings': list(_NONE),
    },

    # HR — full CRUD on HR module
    'hr': {
        'dashboard': list(_VIEW_ONLY),
        'sales': list(_NONE),
        'inventory': list(_NONE),
        'accounting': list(_VIEW_ONLY),
        'hr': list(_CRUD_EXPORT_IMPORT),
        'crm': list(_NONE),
        'reports': list(_CRUD_EXPORT),
        'analytics': list(_VIEW_EXPORT),
        'settings': list(_NONE),
    },

    # Auditor — view + export on everything
    'auditor': {mod: list(_VIEW_EXPORT) for mod in _MODULES},

    # Guest — dashboard view only
    'guest': {
        'dashboard': list(_VIEW_ONLY),
        'sales': list(_NONE),
        'inventory': list(_NONE),
        'accounting': list(_NONE),
        'hr': list(_NONE),
        'crm': list(_NONE),
        'reports': list(_NONE),
        'analytics': list(_NONE),
        'settings': list(_NONE),
    },
}
"""Serialisable role-based permission matrix.

Uses plain string keys (suitable for JSON/YAML serialisation) rather
than enum members.  Each role maps to a dictionary of module names
to lists of permitted actions.

This mirrors the enum-based :data:`~src.core.constants.PERMISSION_MATRIX`
but is safe for export to config files and API responses.
"""
