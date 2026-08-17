"""Global purchasing page: requests workspace + issued orders."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.services.permissions import Perm
from app.ui.pages.purchases_view import OrdersView, PurchasesView
from app.ui.styles.theme import SPACING, SPACING_LG
from app.utils.i18n import tr


class PurchasesPage(QWidget):
    """Purchase requests and orders across every project."""

    permission = Perm.PURCHASE_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING, SPACING_LG, SPACING)
        self.tabs = QTabWidget()
        self.requests_view = PurchasesView()
        self.orders_view = OrdersView()
        self.tabs.addTab(self.requests_view, tr("purchase_request"))
        self.tabs.addTab(self.orders_view, tr("purchase_order"))
        layout.addWidget(self.tabs)

    def refresh(self) -> None:
        """Refresh the visible tab."""
        widget = self.tabs.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()
