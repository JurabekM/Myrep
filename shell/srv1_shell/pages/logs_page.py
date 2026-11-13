"""Jonli jurnal: oxirgi yozuvlar + `log` hodisalari, daraja filtri bilan."""

from typing import Any

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton

from srv1_shell.api import Reply
from srv1_shell.common import AppContext, Page

LOG_TOPIC = "log"
MAX_LINES = 2000
_LEVELS = ("info", "warning", "error")
_RANK = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}
_HIDDEN_KEYS = frozenset({"timestamp", "level", "logger", "event"})


def format_entry(entry: dict[str, Any]) -> str:
    """`12:34:56 INFO    srv1.core  core_started  version=1.0.0`."""
    timestamp = str(entry.get("timestamp", ""))
    clock = timestamp[11:19] if len(timestamp) >= 19 else timestamp
    level = str(entry.get("level", "")).upper()
    extras = " ".join(f"{key}={value}" for key, value in entry.items() if key not in _HIDDEN_KEYS)
    line = f"{clock} {level:<8}{entry.get('logger', '')}  {entry.get('event', '')}"
    return f"{line}  {extras}" if extras else line


class LogsPage(Page):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        t = ctx.i18n.t
        header = QHBoxLayout()
        title = QLabel(t("nav.logs"))
        title.setObjectName("PageTitle")
        self.level = QComboBox()
        self.level.addItem(t("logs.all"), "info")
        for name in _LEVELS[1:]:
            self.level.addItem(name.upper(), name)
        self.level.currentIndexChanged.connect(self._render_all)
        self.pause = QCheckBox(t("logs.pause"))
        self.clear_button = QPushButton(t("logs.clear"))
        self.clear_button.clicked.connect(self._clear)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel(t("logs.level")))
        header.addWidget(self.level)
        header.addWidget(self.pause)
        header.addWidget(self.clear_button)
        self.layout_root.addLayout(header)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(MAX_LINES)
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.layout_root.addWidget(self.view, 1)

        self.entries: list[dict[str, Any]] = []
        self._loaded = False
        ctx.events.received.connect(self._on_event)

    def activate(self) -> None:
        if not self._loaded:
            self.ctx.api.request(
                "GET", "/api/v1/logs", self._on_tail, owner=self, params={"tail": 200}
            )

    def _on_tail(self, reply: Reply) -> None:
        if not reply.ok or not isinstance(reply.data, list):
            self.view.setPlainText(self.describe_error(reply))
            return
        self._loaded = True
        live, self.entries = self.entries, list(reply.rows())
        known = {(e.get("timestamp"), e.get("event")) for e in self.entries}
        self.entries += [e for e in live if (e.get("timestamp"), e.get("event")) not in known]
        self._render_all()

    def _on_event(self, topic: str, data: dict[str, Any]) -> None:
        if topic != LOG_TOPIC:
            return
        self.entries.append(data)
        del self.entries[:-MAX_LINES]
        if not self.pause.isChecked() and self._visible(data):
            self.view.appendPlainText(format_entry(data))

    def _visible(self, entry: dict[str, Any]) -> bool:
        threshold = _RANK[str(self.level.currentData())]
        return _RANK.get(str(entry.get("level", "info")), 1) >= threshold

    def _render_all(self) -> None:
        lines = [format_entry(entry) for entry in self.entries if self._visible(entry)]
        self.view.setPlainText("\n".join(lines))
        bar = self.view.verticalScrollBar()
        if bar is not None:
            bar.setValue(bar.maximum())

    def _clear(self) -> None:
        self.entries = []
        self.view.clear()
