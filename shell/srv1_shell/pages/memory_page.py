"""Xotira: har jarayon bo'yicha RAM va 350 MB chegarasiga nisbatan jami."""

import os
from typing import Any

import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
)

from srv1_shell.api import Reply
from srv1_shell.common import AppContext, Page, muted
from srv1_shell.pages.system_page import set_level

REFRESH_MS = 3000
_COLUMNS = ("process", "pid", "ws", "private")


def shell_memory() -> dict[str, Any]:
    """Shell'ning o'z xotirasi — yadro buni bilmaydi, shuning uchun shu yerda o'lchanadi."""
    process = psutil.Process(os.getpid())
    memory = process.memory_info()
    return {
        "name": "shell",
        "kind": "shell",
        "pid": process.pid,
        "rss": memory.rss,
        "private": getattr(memory, "private", None),
    }


class MemoryPage(Page):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        t = ctx.i18n.t
        self.add_title(t("nav.memory"))
        self.total = QLabel("—")
        self.total.setObjectName("SectionTitle")
        self.layout_root.addWidget(self.total)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.layout_root.addWidget(self.bar)
        self.layout_root.addWidget(muted(t("memory.note")))

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([t(f"memory.col.{column}") for column in _COLUMNS])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        vertical = self.table.verticalHeader()
        if vertical is not None:
            vertical.setVisible(False)
        horizontal = self.table.horizontalHeader()
        if horizontal is not None:
            horizontal.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            horizontal.setDefaultAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        self.layout_root.addWidget(self.table, 1)

        self.error = QLabel("")
        self.error.setObjectName("ErrorText")
        self.layout_root.addWidget(self.error)
        self.rows: list[dict[str, Any]] = []
        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

    def activate(self) -> None:
        self.refresh()
        self._timer.start()

    def deactivate(self) -> None:
        self._timer.stop()

    def refresh(self) -> None:
        self.ctx.api.get("/api/v1/system/processes", self._on_reply, owner=self)

    def _on_reply(self, reply: Reply) -> None:
        if not reply.ok:
            self.error.setText(self.describe_error(reply))
            return
        self.error.setText("")
        self.show_report(reply.data)

    def _label(self, row: dict[str, Any]) -> str:
        t = self.ctx.i18n.t
        if row["kind"] == "plugin":
            return t("memory.plugin", name=row["name"])
        return t("memory.core" if row["kind"] == "core" else "memory.shell")

    def show_report(self, report: dict[str, Any]) -> None:
        i18n = self.ctx.i18n
        self.rows = [*report["processes"], shell_memory()]
        total = sum(int(row["rss"]) for row in self.rows)
        budget = int(report["budget_bytes"])
        self.total.setText(i18n.t("memory.total", used=i18n.size(total), budget=i18n.size(budget)))
        set_level(self.bar, min(100.0, 100.0 * total / budget))
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            private = "—" if row["private"] is None else i18n.size(row["private"])
            cells = (self._label(row), str(row["pid"]), i18n.size(row["rss"]), private)
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(index, column, item)
        self.table.setUpdatesEnabled(True)
