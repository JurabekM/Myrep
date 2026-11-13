"""Plaginlar ro'yxati: holat, xato matni, yoqish/o'chirish."""

from functools import partial
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from srv1_shell.api import Reply
from srv1_shell.common import AppContext, Page

STATE_TOPIC = "plugins.state"
STATUS_COLORS = {
    "running": "#3fb950",
    "stopped": "#8b95a5",
    "error": "#f85149",
    "crashed": "#f85149",
    "invalid": "#d29922",
}
_COLUMNS = ("name", "version", "mode", "status", "description", "action")
_ACTION_COLUMN = len(_COLUMNS) - 1


class PluginsPage(Page):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        t = ctx.i18n.t
        header = QHBoxLayout()
        title = QLabel(t("nav.plugins"))
        title.setObjectName("PageTitle")
        self.refresh_button = QPushButton(t("common.refresh"))
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.refresh_button)
        self.layout_root.addLayout(header)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([t(f"plugins.col.{column}") for column in _COLUMNS])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        vertical = self.table.verticalHeader()
        if vertical is not None:
            vertical.setVisible(False)
            vertical.setDefaultSectionSize(40)
        horizontal = self.table.horizontalHeader()
        if horizontal is not None:
            horizontal.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            horizontal.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            horizontal.setMinimumSectionSize(90)
            horizontal.setDefaultAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        for column, width in enumerate((140, 90, 150, 140, 240, 130)):
            self.table.setColumnWidth(column, width)
        self.layout_root.addWidget(self.table, 1)

        self.message = QLabel("")
        self.message.setObjectName("ErrorText")
        self.message.setWordWrap(True)
        self.layout_root.addWidget(self.message)
        self.buttons: dict[str, QPushButton] = {}
        self.plugins: list[dict[str, Any]] = []
        ctx.events.received.connect(self._on_event)

    def activate(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.ctx.api.get("/api/v1/plugins", self._on_list, owner=self)

    def _on_event(self, topic: str, data: dict[str, Any]) -> None:
        if topic == STATE_TOPIC:
            self.refresh()

    def _on_list(self, reply: Reply) -> None:
        if not reply.ok or not isinstance(reply.data, list):
            self.message.setText(self.describe_error(reply))
            return
        self.plugins = reply.rows()
        self._fill()

    def _fill(self) -> None:
        t = self.ctx.i18n.t
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self.plugins))
        self.buttons = {}
        errors: list[str] = []
        for row, plugin in enumerate(self.plugins):
            name, status = str(plugin["name"]), str(plugin["status"])
            mode = t(f"mode.{plugin['mode']}") if plugin["mode"] else "—"
            if plugin["heavy"]:
                mode += f" ({t('plugins.heavy')})"
            cells = (
                name,
                plugin["version"] or "—",
                mode,
                t(f"status.{status}"),
                plugin["description"],
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                if column == 3:
                    item.setForeground(QColor(STATUS_COLORS.get(status, "#e6e9ee")))
                self.table.setItem(row, column, item)
            self.table.setCellWidget(row, _ACTION_COLUMN, self._action_button(name, status, plugin))
            if plugin["error"]:
                errors.append(t("plugins.error", name=name, error=plugin["error"]))
        self.table.setUpdatesEnabled(True)
        self.message.setText("\n".join(errors) if self.plugins else t("plugins.empty"))

    def _action_button(self, name: str, status: str, plugin: dict[str, Any]) -> QPushButton:
        t = self.ctx.i18n.t
        running = status == "running"
        button = QPushButton(t("plugins.disable" if running else "plugins.enable"))
        button.setObjectName("Danger" if running else "Primary")
        button.setEnabled(status != "invalid")
        action = "disable" if running else "enable"
        button.clicked.connect(partial(self._clicked, name, action))
        self.buttons[name] = button
        return button

    def _clicked(self, name: str, action: str, _checked: bool = False) -> None:
        self.toggle(name, action)

    def toggle(self, name: str, action: str) -> None:
        button = self.buttons.get(name)
        if button is not None:
            button.setEnabled(False)
        self.ctx.api.post(f"/api/v1/plugins/{name}/{action}", self._on_toggled, owner=self)

    def _on_toggled(self, reply: Reply) -> None:
        if not reply.ok:
            self.message.setText(self.describe_error(reply))
        self.refresh()
