"""Ctrl+K global search across buyers, leads, products and quotations."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import buyer_service, lead_service, product_service, quotation_service
from app.ui.i18n import t, te
from app.utils.formatting import fmt_money


class GlobalSearchDialog(QDialog):
    """Type-ahead search returning a (page, entity id) navigation target."""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.target: tuple[str, int] | None = None
        self.setModal(True)
        self.setWindowTitle(t("shortcut.global_search"))
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        self.query = QLineEdit()
        self.query.setObjectName("SearchInput")
        self.query.setPlaceholderText(t("search.placeholder"))
        self.query.textChanged.connect(self._search)
        self.query.returnPressed.connect(self._activate)
        root.addWidget(self.query)

        self.results = QListWidget()
        self.results.itemActivated.connect(self._activate)
        self.results.itemDoubleClicked.connect(self._activate)
        root.addWidget(self.results, 1)

        self.hint = QLabel(t("search.no_results"))
        self.hint.setObjectName("Hint")
        root.addWidget(self.hint)

        self._rows: list[tuple[str, int]] = []
        self.query.setFocus()

    def _search(self) -> None:
        text = self.query.text().strip()
        self.results.clear()
        self._rows = []
        if len(text) < 2:
            self.hint.setText(t("search.placeholder"))
            return

        def _load(session: Session) -> list[tuple[str, str, int]]:
            found: list[tuple[str, str, int]] = []
            if self.ctx.can("buyer.view"):
                for row in buyer_service.search_buyers(session, text=text, limit=12):
                    found.append(
                        ("buyers", f"⚇  {row['company_name']} · {row['country']}", row["id"])
                    )
            if self.ctx.can("lead.view"):
                for row in lead_service.search_leads(session, text=text, limit=12):
                    found.append(
                        (
                            "leads",
                            f"➜  {row['title']} · {te('lead_status', row['status'])}",
                            row["id"],
                        )
                    )
            if self.ctx.can("product.view"):
                for row in product_service.search_products(
                    session, text=text, lang=self.ctx.language(), limit=12
                ):
                    found.append(("products", f"▤  {row['sku']} · {row['name']}", row["id"]))
            if self.ctx.can("quotation.view"):
                for row in quotation_service.list_quotations(session, text=text)[:12]:
                    found.append(
                        (
                            "quotations",
                            f"₮  {row['number']} · {row['buyer']} · "
                            f"{fmt_money(row['grand_total'], row['currency'])}",
                            row["id"],
                        )
                    )
            return found

        try:
            found = self.ctx.read(_load)
        except Exception:  # pragma: no cover - search must never crash the app
            found = []

        for page, label, entity_id in found:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, len(self._rows))
            self.results.addItem(item)
            self._rows.append((page, entity_id))
        self.hint.setText(t("common.rows", count=len(found)) if found else t("search.no_results"))
        if found:
            self.results.setCurrentRow(0)

    def _activate(self) -> None:
        index = self.results.currentRow()
        if 0 <= index < len(self._rows):
            self.target = self._rows[index]
            self.accept()
