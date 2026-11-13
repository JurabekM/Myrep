"""`query` vidjeti: so'rov matni, «Bajarish» tugmasi va ustunlari javobdan olinadigan jadval."""

from collections.abc import Callable
from typing import Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from srv1_sdk.panel import QueryWidget
from srv1_shell.common import section_title
from srv1_shell.i18n import I18n
from srv1_shell.pages.data_table import ErrorSink

EDITOR_HEIGHT = 110
RESULT_MIN_HEIGHT = 260
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
# (yo'l, JSON tana, natija qabul qiluvchi, xato qabul qiluvchi)
Send = Callable[[str, dict[str, Any], Callable[[Any], None], ErrorSink], None]


def cell_text(value: Any, i18n: I18n) -> str:  # noqa: ANN401
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return i18n.number(value, 4).rstrip("0").rstrip(",.") or "0"
    return str(value)


class QueryView(QWidget):
    """Javob shakli: `{columns: [{name, type}], rows: [[...]], truncated, seconds}`."""

    def __init__(self, spec: QueryWidget, i18n: I18n, send: Send) -> None:
        super().__init__()
        self.spec = spec
        self._i18n = i18n
        self._send = send
        self.columns: list[str] = []
        self.rows: list[list[Any]] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_title(i18n.pick(spec.label)))

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.setFixedHeight(EDITOR_HEIGHT)
        self.editor.setPlaceholderText(i18n.pick(spec.placeholder))
        self.editor.setTabChangesFocus(True)
        layout.addWidget(self.editor)

        self.status = QLabel("")
        self.status.setObjectName("ResultText")
        self.status.setWordWrap(True)
        self.run_button = QPushButton(i18n.t("panel.run"))
        self.run_button.setObjectName("Primary")
        self.run_button.clicked.connect(self.run)
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.editor)
        shortcut.activated.connect(self.run)
        row = QHBoxLayout()
        row.addWidget(self.status, 1)
        row.addWidget(self.run_button)
        layout.addLayout(row)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setMinimumHeight(RESULT_MIN_HEIGHT)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            # Ustunlar soni oldindan noma'lum: har biri mazmuniga qarab, cho'zilmaydi.
            header.setStretchLastSection(False)
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        vertical = self.table.verticalHeader()
        if vertical is not None:
            vertical.setVisible(False)
            vertical.setDefaultSectionSize(28)
        layout.addWidget(self.table)

    def run(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            return
        self.run_button.setEnabled(False)
        self._set_status(self._i18n.t("panel.running"), error=False)
        self._send(self.spec.path, {self.spec.field: text}, self.show_result, self.show_error)

    def show_error(self, text: str) -> None:
        self.run_button.setEnabled(True)
        self._set_status(text, error=True)

    def show_result(self, data: Any) -> None:  # noqa: ANN401
        self.run_button.setEnabled(True)
        body = cast(dict[str, Any], data) if isinstance(data, dict) else {}
        columns = cast(list[dict[str, Any]], body.get("columns") or [])
        self.columns = [str(column.get("name", "")) for column in columns]
        self.rows = [list(row) for row in cast(list[list[Any]], body.get("rows") or [])]
        table = self.table
        table.setUpdatesEnabled(False)
        table.clear()
        table.setColumnCount(len(self.columns))
        table.setRowCount(len(self.rows))
        for index, column in enumerate(columns):
            item = QTableWidgetItem(self.columns[index])
            item.setToolTip(str(column.get("type", "")))
            table.setHorizontalHeaderItem(index, item)
        for row_index, row in enumerate(self.rows):
            for column_index, value in enumerate(row[: len(self.columns)]):
                text = cell_text(value, self._i18n)
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if isinstance(value, int | float) and not isinstance(value, bool):
                    item.setTextAlignment(_RIGHT)
                table.setItem(row_index, column_index, item)
        table.resizeColumnsToContents()
        table.setUpdatesEnabled(True)
        key = "panel.rows_truncated" if body.get("truncated") else "panel.rows"
        seconds = self._i18n.number(float(body.get("seconds") or 0.0), 2)
        self._set_status(self._i18n.t(key, rows=len(self.rows), seconds=seconds), error=False)

    def _set_status(self, text: str, *, error: bool) -> None:
        self.status.setObjectName("ErrorText" if error else "ResultText")
        style = self.status.style()
        if style is not None:
            style.unpolish(self.status)
            style.polish(self.status)
        self.status.setText(text)
