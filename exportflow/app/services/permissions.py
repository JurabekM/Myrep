"""Permission catalogue and role -> permission matrix."""

from __future__ import annotations

from app.utils.enums import (
    ROLE_ADMIN,
    ROLE_CATALOG_MANAGER,
    ROLE_EXPORT_MANAGER,
    ROLE_LOGISTICS,
    ROLE_SALES_MANAGER,
    ROLE_VIEWER,
)

#: ``code -> (module, description)`` for every capability in the application.
PERMISSIONS: dict[str, tuple[str, str]] = {
    "product.view": ("product", "View products"),
    "product.edit": ("product", "Create and edit products"),
    "product.archive": ("product", "Archive products"),
    "price.view": ("product", "View prices"),
    "price.edit": ("product", "Create and edit prices"),
    "price.approve": ("product", "Approve prices"),
    "catalog.view": ("catalog", "View catalogs"),
    "catalog.edit": ("catalog", "Create and edit catalogs"),
    "catalog.export": ("catalog", "Export catalogs to PDF/HTML/ZIP"),
    "buyer.view": ("crm", "View buyers"),
    "buyer.edit": ("crm", "Create and edit buyers"),
    "lead.view": ("crm", "View leads"),
    "lead.edit": ("crm", "Create and edit leads"),
    "lead.assign": ("crm", "Assign leads to managers"),
    "rfq.view": ("sales", "View RFQs"),
    "rfq.edit": ("sales", "Create and edit RFQs"),
    "quotation.view": ("sales", "View quotations"),
    "quotation.edit": ("sales", "Create and edit quotations"),
    "quotation.approve": ("sales", "Approve quotations"),
    "quotation.send": ("sales", "Mark quotations as sent"),
    "contract.view": ("sales", "View contracts"),
    "contract.edit": ("sales", "Create and edit contracts"),
    "checklist.view": ("checklist", "View checklists"),
    "checklist.edit": ("checklist", "Create and edit checklists"),
    "certificate.view": ("documents", "View certificates and documents"),
    "certificate.edit": ("documents", "Create and edit certificates and documents"),
    "shipment.view": ("logistics", "View shipments"),
    "shipment.edit": ("logistics", "Create and edit shipments"),
    "email.view": ("email", "View email history"),
    "email.send": ("email", "Compose and send emails"),
    "ai.use": ("ai", "Use the AI Content Studio"),
    "agent.view": ("crm", "View sales agents"),
    "agent.edit": ("crm", "Create and edit sales agents"),
    "report.view": ("report", "View reports"),
    "report.export": ("report", "Export reports"),
    "settings.view": ("settings", "View settings"),
    "settings.edit": ("settings", "Change settings"),
    "user.manage": ("settings", "Manage users and roles"),
    "integration.manage": ("settings", "Configure integrations"),
    "audit.view": ("settings", "View the audit log"),
    "backup.manage": ("settings", "Create and restore backups"),
}

_VIEW_ONLY = tuple(code for code in PERMISSIONS if code.endswith(".view")) + ("report.export",)

_CATALOG_MANAGER = (
    "product.view",
    "product.edit",
    "product.archive",
    "price.view",
    "catalog.view",
    "catalog.edit",
    "catalog.export",
    "certificate.view",
    "certificate.edit",
    "checklist.view",
    "checklist.edit",
    "ai.use",
    "report.view",
    "report.export",
    "buyer.view",
    "lead.view",
    "quotation.view",
    "settings.view",
)

_SALES_MANAGER = (
    "product.view",
    "price.view",
    "catalog.view",
    "catalog.export",
    "buyer.view",
    "buyer.edit",
    "lead.view",
    "lead.edit",
    "rfq.view",
    "rfq.edit",
    "quotation.view",
    "quotation.edit",
    "checklist.view",
    "checklist.edit",
    "certificate.view",
    "shipment.view",
    "email.view",
    "email.send",
    "ai.use",
    "agent.view",
    "report.view",
    "report.export",
    "settings.view",
)

_EXPORT_MANAGER = _SALES_MANAGER + (
    "product.edit",
    "product.archive",
    "price.edit",
    "price.approve",
    "catalog.edit",
    "lead.assign",
    "quotation.approve",
    "quotation.send",
    "contract.view",
    "contract.edit",
    "certificate.edit",
    "shipment.edit",
    "agent.edit",
)

_LOGISTICS = (
    "product.view",
    "price.view",
    "buyer.view",
    "lead.view",
    "quotation.view",
    "contract.view",
    "checklist.view",
    "checklist.edit",
    "certificate.view",
    "certificate.edit",
    "shipment.view",
    "shipment.edit",
    "email.view",
    "report.view",
    "report.export",
    "settings.view",
)

#: Which permissions each system role receives at seed time.
ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    ROLE_ADMIN: tuple(PERMISSIONS),
    ROLE_EXPORT_MANAGER: tuple(dict.fromkeys(_EXPORT_MANAGER)),
    ROLE_SALES_MANAGER: tuple(dict.fromkeys(_SALES_MANAGER)),
    ROLE_LOGISTICS: tuple(dict.fromkeys(_LOGISTICS)),
    ROLE_CATALOG_MANAGER: tuple(dict.fromkeys(_CATALOG_MANAGER)),
    ROLE_VIEWER: tuple(dict.fromkeys(_VIEW_ONLY)),
}

ROLE_NAMES: dict[str, str] = {
    ROLE_ADMIN: "Administrator",
    ROLE_EXPORT_MANAGER: "Export Manager",
    ROLE_SALES_MANAGER: "Sales Manager",
    ROLE_LOGISTICS: "Logistics Specialist",
    ROLE_CATALOG_MANAGER: "Catalog Manager",
    ROLE_VIEWER: "Viewer",
}


def permissions_for_role(role_code: str) -> tuple[str, ...]:
    """Return the permission codes granted to a role code."""
    return ROLE_PERMISSIONS.get(role_code, ())
