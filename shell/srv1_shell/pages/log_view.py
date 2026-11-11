"""`log` vidjeti: filtr maydonlari va faqat o'qish uchun matn oynasi."""

from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from srv1_sdk.panel import LogWidget
from srv1_shell.common import section_title
from srv1_shell.i18n import I18n
from srv1_shell.pages.data_table import Fetch, make_editor

LOG_HEIGHT = 240


class LogView(QWidget):
    """Majburiy filtr to'ldirilmaguncha so'rov yubormaydi."""

    def __init__(self, spec: LogWidget, i18n: I18n, fetch: Fetch) -> None:
        super().__init__()
        self.spec = spec
        self._fetch = fetch
        self.filters: dict[str, QWidget] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_title(i18n.pick(spec.label)))
        if spec.filters:
            row = QHBoxLayout()
            for field in spec.filters:
                editor = make_editor(field)
                self.filters[field.name] = editor
                row.addWidget(QLabel(i18n.pick(field.label)))
                row.addWidget(editor, 1 if isinstance(editor, QLineEdit) else 0)
                if isinstance(editor, QLineEdit):
                    editor.returnPressed.connect(self.refresh)
            self.show_button = QPushButton(i18n.t("panel.show"))
            self.show_button.setObjectName("Primary")
            self.show_button.clicked.connect(self.refresh)
            row.addWidget(self.show_button)
            layout.addLayout(row)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.view.setFixedHeight(LOG_HEIGHT)
        layout.addWidget(self.view)
        self._timer = QTimer(self)
        self._timer.setInterval(round(spec.refresh_s * 1000))
        self._timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def params(self) -> dict[str, Any] | None:
        """Filtr qiymatlari; majburiy maydon bo'sh bo'lsa `None`."""
        values: dict[str, Any] = {}
        for field in self.spec.filters:
            editor = self.filters[field.name]
            if isinstance(editor, QCheckBox):
                values[field.name] = editor.isChecked()
                continue
            text = editor.currentText() if isinstance(editor, QComboBox) else ""
            if isinstance(editor, QLineEdit):
                text = editor.text().strip()
            if text:
                values[field.name] = text
            elif field.required:
                return None
        return values

    def refresh(self) -> None:
        params = self.params()
        if params is not None:
            self._fetch(self.spec.source, params, self.show_lines)

    def show_lines(self, data: Any) -> None:  # noqa: ANN401
        lines = [str(line) for line in cast(list[Any], data)] if isinstance(data, list) else []
        text = "\n".join(lines)
        if text == self.view.toPlainText():
            return
        bar = self.view.verticalScrollBar()
        at_bottom = bar is None or bar.value() >= bar.maximum() - 4
        self.view.setPlainText(text)
        if bar is not None and at_bottom:
            bar.setValue(bar.maximum())
