"""Base classes for application pages."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QSplitter, QVBoxLayout, QWidget

from app.controllers.app_context import AppContext
from app.ui.i18n import t
from app.ui.widgets.common import PageHeader, button
from app.ui.widgets.detail_panel import DetailPanel
from app.ui.widgets.table import Column, DataTable, FilterBar, FilterSpec
from app.utils.errors import ExportFlowError
from app.utils.logging_setup import get_logger

log = get_logger(__name__)


class BasePage(QWidget):
    """Common behaviour: context access, error dialogs and retranslation."""

    #: Permission required to open the page (empty means always available).
    permission: str = ""
    #: Data topics this page reacts to.
    topics: tuple[str, ...] = ()

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._loaded = False
        ctx.data_changed.connect(self._on_data_changed)
        ctx.language_changed.connect(self.retranslate)

    # ------------------------------------------------------------ lifecycle
    def ensure_loaded(self) -> None:
        """Load data the first time the page becomes visible."""
        if not self._loaded:
            self._loaded = True
            self.refresh()

    def refresh(self) -> None:
        """Reload the page content. Subclasses override this."""

    def retranslate(self) -> None:
        """Re-apply every visible string after a language change."""

    def _on_data_changed(self, topic: str) -> None:
        if not self._loaded:
            return
        if topic == "*" or not self.topics or topic in self.topics:
            self.refresh()

    # --------------------------------------------------------------- errors
    def handle_error(self, exc: Exception) -> None:
        """Show a translated, user-friendly error dialog."""
        if isinstance(exc, ExportFlowError):
            params = {
                key: value
                for key, value in exc.params.items()
                if isinstance(value, (str, int, float))
            }
            message = t(exc.key, **params)
            if message == exc.key.rsplit(".", 1)[-1].replace("_", " ").capitalize() and exc.message:
                message = exc.message
            log.info("User error: %s", exc.key)
        else:
            message = f"{t('error.generic')}\n\n{type(exc).__name__}: {exc}"
            log.exception("Unhandled error in %s", type(self).__name__)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(t("app.title"))
        box.setText(message)
        box.exec()

    def confirm(self, message: str, title: str | None = None) -> bool:
        """Ask a yes/no question."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(title or t("common.confirm"))
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText(t("common.yes"))
        box.button(QMessageBox.StandardButton.No).setText(t("common.no"))
        return box.exec() == QMessageBox.StandardButton.Yes

    def info(self, message: str) -> None:
        """Show an informational toast."""
        self.ctx.show_toast(message, "success")

    # ----------------------------------------------------------- shortcuts
    def on_new(self) -> None:
        """Ctrl+N handler."""

    def on_save(self) -> None:
        """Ctrl+S handler."""

    def on_export(self) -> None:
        """Ctrl+E handler."""


class RecordPage(BasePage):
    """Page layout: header, filter bar, table and a detail panel."""

    #: Overridden by subclasses.
    title_key: str = ""
    subtitle_key: str = ""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)

        self.filter_bar = FilterBar(self.filter_specs())
        self.filter_bar.changed.connect(self.refresh)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(self.filter_bar, 1)
        self.reset_button = button(t("common.reset"), self.filter_bar.reset, "Ghost")
        filter_row.addWidget(self.reset_button)
        root.addLayout(filter_row)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = DataTable(self.columns())
        self.table.selection_changed.connect(self._on_selection)
        self.table.row_activated.connect(self.on_row_activated)
        self.detail = DetailPanel()
        self.detail.setVisible(False)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.detail)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter, 1)

        self.retranslate()

    # ----------------------------------------------------- to be overridden
    def columns(self) -> list[Column]:
        """Column definitions of the table."""
        return []

    def filter_specs(self) -> list[FilterSpec]:
        """Filter controls shown above the table."""
        return []

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch the rows matching the current filters."""
        return []

    def fill_detail(self, row: dict) -> None:
        """Populate the detail panel for the selected row."""

    def on_row_activated(self, row: dict) -> None:
        """Double-click handler; usually opens the editor."""

    # -------------------------------------------------------------- shared
    def refresh(self) -> None:
        """Reload the table, keeping the current selection when possible."""
        current = self.table.current_row()
        current_id = current.get("id") if current else None
        try:
            rows = self.load_rows(self.filter_bar.values())
        except Exception as exc:
            self.handle_error(exc)
            rows = []
        self.table.set_rows(rows)
        if current_id is not None:
            self.table.select_id(current_id)
        if self.table.current_row() is None:
            self.detail.set_empty()

    def retranslate(self) -> None:
        """Re-apply header captions and column titles."""
        self.header.set_texts(
            t(self.title_key) if self.title_key else "",
            t(self.subtitle_key) if self.subtitle_key else "",
        )
        self.reset_button.setText(t("common.reset"))
        self.table.set_columns(self.columns())
        if self._loaded:
            self.refresh()

    def _on_selection(self, row: dict | None) -> None:
        if row is None:
            self.detail.set_empty()
            return
        self.detail.clear_tabs()
        self.detail.clear_actions()
        try:
            self.fill_detail(row)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.detail.setVisible(True)
