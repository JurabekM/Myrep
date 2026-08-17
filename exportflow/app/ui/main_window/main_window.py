"""Frameless main window hosting the sidebar and the page stack."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from app.config import APP_NAME
from app.controllers.app_context import AppContext
from app.services.permissions import PERMISSIONS
from app.ui.dialogs.global_search import GlobalSearchDialog
from app.ui.main_window.sidebar import Sidebar
from app.ui.main_window.title_bar import TitleBar
from app.ui.pages.agents_page import AgentsPage
from app.ui.pages.ai_studio_page import AIStudioPage
from app.ui.pages.buyers_page import BuyersPage
from app.ui.pages.catalogs_page import CatalogsPage
from app.ui.pages.certificates_page import CertificatesPage
from app.ui.pages.checklists_page import ChecklistsPage
from app.ui.pages.contracts_page import ContractsPage
from app.ui.pages.email_page import EmailPage
from app.ui.pages.leads_page import LeadsPage
from app.ui.pages.pipeline_page import PipelinePage
from app.ui.pages.prices_page import PricesPage
from app.ui.pages.products_page import ProductsPage
from app.ui.pages.quotations_page import QuotationsPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.rfq_page import RFQPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.shipments_page import ShipmentsPage
from app.ui.pages.workspace_page import WorkspacePage
from app.ui.widgets.common import Toast
from app.utils.enums import ROLE_ADMIN
from app.utils.logging_setup import get_logger

log = get_logger(__name__)

#: Navigation key -> page class.
PAGE_CLASSES = {
    "workspace": WorkspacePage,
    "products": ProductsPage,
    "prices": PricesPage,
    "catalogs": CatalogsPage,
    "ai_studio": AIStudioPage,
    "buyers": BuyersPage,
    "leads": LeadsPage,
    "pipeline": PipelinePage,
    "rfq": RFQPage,
    "quotations": QuotationsPage,
    "contracts": ContractsPage,
    "checklists": ChecklistsPage,
    "certificates": CertificatesPage,
    "shipments": ShipmentsPage,
    "email": EmailPage,
    "agents": AgentsPage,
    "reports": ReportsPage,
    "settings": SettingsPage,
}


class MainWindow(QWidget):
    """Application shell: title bar, sidebar and the stacked pages."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.logout_requested = False
        self.setObjectName("RootWindow")
        self.setWindowTitle(APP_NAME)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.resize(1500, 900)
        self.setMinimumSize(1180, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(ctx, self)
        self.title_bar.logout_requested.connect(self._logout)
        self.title_bar.profile_requested.connect(lambda: self.navigate("settings"))
        self.title_bar.search_requested.connect(self.open_search)
        root.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Administrators always see the full navigation.
        allowed = (
            set(PERMISSIONS) if ctx.user.role_code == ROLE_ADMIN else set(ctx.user.permissions)
        )
        self.sidebar = Sidebar(allowed)
        self.sidebar.navigated.connect(self.navigate)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self.pages: dict[str, QWidget] = {}
        for key in self.sidebar.available_keys():
            page_class = PAGE_CLASSES.get(key)
            if page_class is None:
                continue
            page = page_class(ctx)
            if isinstance(page, WorkspacePage):
                page.navigate.connect(self.navigate)
            self.pages[key] = page
            self.stack.addWidget(page)

        self.toast = Toast(self)
        ctx.toast.connect(self._show_toast)
        ctx.language_changed.connect(self._on_language_changed)

        self._install_shortcuts()
        first = "workspace" if "workspace" in self.pages else next(iter(self.pages), "")
        if first:
            self.navigate(first)

    # ------------------------------------------------------------- actions
    def navigate(self, key: str) -> None:
        """Show the requested page, loading its data on first visit."""
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.select(key)
        page.ensure_loaded()

    def open_search(self) -> None:
        """Open the Ctrl+K global search."""
        dialog = GlobalSearchDialog(self.ctx, self)
        if dialog.exec() and dialog.target:
            page_key, entity_id = dialog.target
            self.navigate(page_key)
            page = self.pages.get(page_key)
            table = getattr(page, "table", None)
            if table is not None:
                table.select_id(entity_id)

    def _current_page(self):
        return self.stack.currentWidget()

    def _install_shortcuts(self) -> None:
        bindings = (
            ("Ctrl+K", self.open_search),
            ("Ctrl+N", lambda: self._delegate("on_new")),
            ("Ctrl+S", lambda: self._delegate("on_save")),
            ("Ctrl+E", lambda: self._delegate("on_export")),
            ("Ctrl+Q", self._new_quotation),
            ("F5", lambda: self._delegate("refresh")),
        )
        for sequence, slot in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(slot)

    def _delegate(self, method: str) -> None:
        page = self._current_page()
        handler = getattr(page, method, None)
        if callable(handler):
            handler()

    def _new_quotation(self) -> None:
        if not self.ctx.can("quotation.edit"):
            return
        from app.ui.pages.quotations_page import open_quotation_editor

        if open_quotation_editor(self, self.ctx, None):
            self.ctx.notify("quotation")
            self.navigate("quotations")

    def _show_toast(self, message: str, level: str) -> None:
        self.toast.show_message(message, level)

    def _on_language_changed(self, _language: str) -> None:
        self.sidebar.retranslate()
        self.title_bar.refresh_state()

    def _logout(self) -> None:
        self.logout_requested = True
        self.close()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Keep the toast anchored to the bottom centre."""
        super().resizeEvent(event)
        if self.toast.isVisible():
            self.toast.reposition()

    def refresh_chrome(self) -> None:
        """Refresh the title bar after settings changed."""
        self.title_bar.refresh_state()
