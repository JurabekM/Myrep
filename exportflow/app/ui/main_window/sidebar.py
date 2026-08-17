"""Collapsible navigation sidebar."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import t

EXPANDED_WIDTH = 232
COLLAPSED_WIDTH = 62


@dataclass(frozen=True)
class NavItem:
    """One navigation entry."""

    key: str
    label_key: str
    icon: str
    permission: str = ""


@dataclass(frozen=True)
class NavGroup:
    """A titled group of navigation entries."""

    label_key: str
    items: tuple[NavItem, ...]


#: Full navigation structure of the application.
NAVIGATION: tuple[NavGroup, ...] = (
    NavGroup(
        "nav.group_catalog",
        (
            NavItem("workspace", "nav.workspace", "◧"),
            NavItem("products", "nav.products", "▤", "product.view"),
            NavItem("prices", "nav.prices", "≡", "price.view"),
            NavItem("catalogs", "nav.catalogs", "❏", "catalog.view"),
            NavItem("ai_studio", "nav.ai_studio", "✦", "ai.use"),
        ),
    ),
    NavGroup(
        "nav.group_crm",
        (
            NavItem("buyers", "nav.buyers", "⚇", "buyer.view"),
            NavItem("leads", "nav.leads", "➜", "lead.view"),
            NavItem("pipeline", "nav.pipeline", "⊞", "lead.view"),
        ),
    ),
    NavGroup(
        "nav.group_sales",
        (
            NavItem("rfq", "nav.rfq", "✉", "rfq.view"),
            NavItem("quotations", "nav.quotations", "₮", "quotation.view"),
            NavItem("contracts", "nav.contracts", "✎", "contract.view"),
        ),
    ),
    NavGroup(
        "nav.group_operations",
        (
            NavItem("checklists", "nav.checklists", "☑", "checklist.view"),
            NavItem("certificates", "nav.certificates", "❖", "certificate.view"),
            NavItem("shipments", "nav.shipments", "⛴", "shipment.view"),
            NavItem("email", "nav.email", "✍", "email.view"),
        ),
    ),
    NavGroup(
        "nav.group_analytics",
        (
            NavItem("agents", "nav.agents", "◈", "agent.view"),
            NavItem("reports", "nav.reports", "▦", "report.view"),
            NavItem("settings", "nav.settings", "⚙", "settings.view"),
        ),
    ),
)


class Sidebar(QWidget):
    """Vertical navigation with collapse support and permission filtering."""

    navigated = Signal(str)

    def __init__(self, allowed: set[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(EXPANDED_WIDTH)
        self._collapsed = False
        self._buttons: dict[str, QPushButton] = {}
        self._group_labels: list[tuple[QLabel, str]] = []
        self._items: dict[str, NavItem] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self._content = QVBoxLayout(container)
        self._content.setContentsMargins(0, 0, 0, 0)
        self._content.setSpacing(0)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        for nav_group in NAVIGATION:
            visible_items = [
                item
                for item in nav_group.items
                if not item.permission or item.permission in allowed
            ]
            if not visible_items:
                continue
            label = QLabel(t(nav_group.label_key))
            label.setObjectName("SidebarGroup")
            self._content.addWidget(label)
            self._group_labels.append((label, nav_group.label_key))
            for item in visible_items:
                button = QPushButton(f"{item.icon}   {t(item.label_key)}")
                button.setObjectName("NavButton")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(
                    lambda _checked=False, key=item.key: self.navigated.emit(key)
                )
                self.group.addButton(button)
                self._content.addWidget(button)
                self._buttons[item.key] = button
                self._items[item.key] = item
        self._content.addStretch(1)

        self.collapse_button = QPushButton("⟨   " + t("nav.collapse"))
        self.collapse_button.setObjectName("NavButton")
        self.collapse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        root.addWidget(self.collapse_button)

    # ------------------------------------------------------------- actions
    def select(self, key: str) -> None:
        """Highlight a navigation entry without emitting a signal."""
        button = self._buttons.get(key)
        if button is not None:
            button.setChecked(True)

    def toggle_collapsed(self) -> None:
        """Collapse the sidebar to icons only, or expand it again."""
        self._collapsed = not self._collapsed
        self.setFixedWidth(COLLAPSED_WIDTH if self._collapsed else EXPANDED_WIDTH)
        for label, _key in self._group_labels:
            label.setVisible(not self._collapsed)
        self.retranslate()

    def retranslate(self) -> None:
        """Re-apply captions after a language change or a collapse toggle."""
        for label, key in self._group_labels:
            label.setText(t(key))
        for key, button in self._buttons.items():
            item = self._items[key]
            if self._collapsed:
                button.setText(item.icon)
                button.setToolTip(t(item.label_key))
            else:
                button.setText(f"{item.icon}   {t(item.label_key)}")
                button.setToolTip("")
        self.collapse_button.setText("⟩" if self._collapsed else "⟨   " + t("nav.collapse"))

    def available_keys(self) -> list[str]:
        """Keys of every visible navigation entry."""
        return list(self._buttons)
