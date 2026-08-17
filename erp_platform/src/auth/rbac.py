# -*- coding: utf-8 -*-
"""
RBAC — Rol asosidagi kirish nazorati (Role Based Access Control).

Ruxsatlar ``modul.harakat`` ko'rinishida (masalan ``sales.create``).
Har bir rolga aniq ruxsatlar to'plami biriktirilgan (Permission Matrix).
``administrator`` uchun maxsus ``*`` (hamma narsa) ruxsati bor.
"""
from __future__ import annotations

#: Rol nomlari va o'zbekcha yorliqlari
ROLE_LABELS: dict[str, str] = {
    "administrator": "Administrator",
    "owner": "Rahbar (Owner)",
    "accountant": "Buxgalter",
    "cashier": "Kassir",
    "warehouse": "Omborchi",
    "sales_manager": "Savdo menejeri",
    "hr": "HR menejer",
    "auditor": "Auditor",
    "guest": "Mehmon",
}

#: Modullar va ularda mavjud harakatlar
MODULES: dict[str, tuple[str, ...]] = {
    "dashboard": ("view",),
    "sales": ("view", "create", "edit", "delete", "approve", "export"),
    "pos": ("operate",),
    "inventory": ("view", "create", "edit", "delete", "adjust", "transfer", "export"),
    "purchases": ("view", "create", "edit", "delete", "receive", "export"),
    "customers": ("view", "create", "edit", "delete", "export"),
    "suppliers": ("view", "create", "edit", "delete", "export"),
    "accounting": ("view", "create", "edit", "post", "export"),
    "cash": ("view", "operate"),
    "bank": ("view", "operate"),
    "hr": ("view", "create", "edit", "delete", "export"),
    "payroll": ("view", "create", "approve", "export"),
    "crm": ("view", "create", "edit", "delete"),
    "reports": ("view", "export"),
    "analytics": ("view",),
    "users": ("manage",),
    "settings": ("manage",),
    "backup": ("manage",),
    "audit": ("view",),
    "api": ("access",),
}


def _module(name: str) -> set[str]:
    """Bitta modulning barcha ruxsatlarini qaytaradi."""
    return {f"{name}.{action}" for action in MODULES[name]}


def _all_permissions() -> set[str]:
    """Tizimdagi barcha mavjud ruxsatlar to'plami."""
    perms: set[str] = set()
    for module in MODULES:
        perms |= _module(module)
    return perms


def _all_views() -> set[str]:
    """Barcha modullarning faqat ko'rish (view) ruxsatlari."""
    return {f"{m}.view" for m, actions in MODULES.items() if "view" in actions}


ALL_PERMISSIONS: frozenset[str] = frozenset(_all_permissions())

#: Permission Matrix — rol -> ruxsatlar to'plami
PERMISSION_MATRIX: dict[str, frozenset[str]] = {
    "administrator": frozenset({"*"}),
    "owner": frozenset(_all_permissions() - {"users.manage"}),
    "accountant": frozenset(
        _module("accounting") | _module("cash") | _module("bank")
        | _module("payroll") | _module("reports")
        | {"dashboard.view", "analytics.view", "sales.view", "purchases.view",
           "customers.view", "suppliers.view", "api.access"}
    ),
    "cashier": frozenset({
        "dashboard.view", "pos.operate", "sales.view", "sales.create",
        "cash.view", "cash.operate", "customers.view", "customers.create",
    }),
    "warehouse": frozenset(
        _module("inventory")
        | {"dashboard.view", "purchases.view", "purchases.create",
           "purchases.receive", "suppliers.view"}
    ),
    "sales_manager": frozenset(
        _module("sales") | _module("crm") | _module("customers")
        | {"dashboard.view", "pos.operate", "inventory.view",
           "reports.view", "reports.export", "analytics.view", "api.access"}
    ),
    "hr": frozenset(
        _module("hr")
        | {"dashboard.view", "payroll.view", "payroll.create",
           "payroll.export", "reports.view"}
    ),
    "auditor": frozenset(
        _all_views() | {"audit.view", "reports.export", "analytics.view"}
    ),
    "guest": frozenset({"dashboard.view"}),
}


def has_permission(role: str, permission: str) -> bool:
    """
    Rol berilgan ruxsatga ega yoki yo'qligini tekshiradi.

    ``administrator`` roli (``*``) har qanday ruxsatga ega.
    """
    perms = PERMISSION_MATRIX.get(role)
    if not perms:
        return False
    return "*" in perms or permission in perms


def role_permissions(role: str) -> frozenset[str]:
    """Rolning to'liq ruxsatlar to'plamini qaytaradi (UI matritsa uchun)."""
    perms = PERMISSION_MATRIX.get(role, frozenset())
    if "*" in perms:
        return frozenset(ALL_PERMISSIONS)
    return perms


def valid_roles() -> list[str]:
    """Tizimda mavjud rollar ro'yxati."""
    return list(ROLE_LABELS.keys())
