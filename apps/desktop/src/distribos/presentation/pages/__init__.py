"""Sahifalar fabrikasi."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from distribos.app_context import AppContext
from distribos.presentation.pages.operations import (
    FinancePage,
    InventoryPage,
    VisitsPage,
)
from distribos.presentation.pages.reporting import (
    AssistantPage,
    DocumentsPage,
    ReportsPage,
)
from distribos.presentation.pages.sales import (
    CustomersPage,
    OrdersPage,
    ProductsPage,
)
from distribos.presentation.pages.system import (
    AuditPage,
    BackupPage,
    ConflictsPage,
    SecurityPage,
    SettingsPage,
    SyncPage,
)


def build_pages(context: AppContext) -> dict[str, QWidget]:
    """Barcha sahifalarni yaratadi. Kalitlar `main_window.NAVIGATION` bilan mos."""
    return {
        "orders": OrdersPage(context),
        "customers": CustomersPage(context),
        "products": ProductsPage(context),
        "inventory": InventoryPage(context),
        "finance": FinancePage(context),
        "visits": VisitsPage(context),
        "reports": ReportsPage(context),
        "documents": DocumentsPage(context),
        "assistant": AssistantPage(context),
        "sync": SyncPage(context),
        "conflicts": ConflictsPage(context),
        "security": SecurityPage(context),
        "backup": BackupPage(context),
        "audit": AuditPage(context),
        "settings": SettingsPage(context),
    }


__all__ = ["build_pages"]
