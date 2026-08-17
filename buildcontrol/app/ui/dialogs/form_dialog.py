"""Declarative form dialog.

A form is described by a list of :class:`Field` specs; the dialog builds the
widgets, applies validation states and returns a plain ``{key: value}`` dict.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QWidget,
)

from app.ui.dialogs.base_dialog import BaseDialog
from app.ui.styles.theme import SPACING_SM
from app.ui.widgets.common import button, field_label
from app.utils.i18n import tr

# Field kinds
TEXT = "text"
TEXTAREA = "textarea"
MONEY = "money"
NUMBER = "number"
INT = "int"
PERCENT = "percent"
DATE = "date"
COMBO = "combo"
CHECK = "check"
FILE = "file"
PASSWORD = "password"
LABEL = "label"


@dataclass
class Field:
    """Declarative description of one form field."""

    key: str
    label: str
    kind: str = TEXT
    required: bool = False
    default: Any = None
    options: list[tuple[Any, str]] = dc_field(default_factory=list)
    placeholder: str = ""
    minimum: float = 0.0
    maximum: float = 1e15
    decimals: int = 0
    span: int = 1
    hint: str = ""
    enabled: bool = True
    #: ``(values) -> bool`` toggling visibility as the user types
    visible_if: Callable[[dict], bool] | None = None


class FormDialog(BaseDialog):
    """Modal dialog rendering a two-column form."""

    def __init__(
        self,
        title: str,
        fields: list[Field],
        values: dict | None = None,
        subtitle: str = "",
        parent: QWidget | None = None,
        columns: int = 2,
        width: int = 620,
        read_only: bool = False,
    ) -> None:
        super().__init__(title, subtitle, parent, width=width)
        self.fields = fields
        self._widgets: dict[str, QWidget] = {}
        self._initial = values or {}
        self._read_only = read_only

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        row = 0
        col = 0
        for spec in fields:
            container = self._build_field(spec)
            span = min(spec.span, columns)
            if col + span > columns:
                row += 1
                col = 0
            grid.addWidget(container, row, col, 1, span)
            col += span
            if col >= columns:
                row += 1
                col = 0
        for index in range(columns):
            grid.setColumnStretch(index, 1)
        self.body().addLayout(grid)
        self.body().addStretch(1)
        self._apply_visibility()

    # -- construction ------------------------------------------------------- #
    def _build_field(self, spec: Field) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container) if spec.kind == CHECK else None
        if layout is None:
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout(container)
            layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        widget = self._create_widget(spec)
        # FILE fields register their inner line edit themselves.
        self._widgets.setdefault(spec.key, widget)
        widget.setEnabled(spec.enabled and not self._read_only)

        if spec.kind == CHECK:
            layout.addWidget(widget)
            layout.addStretch(1)
        else:
            layout.addWidget(field_label(spec.label, spec.required))
            layout.addWidget(widget)
            if spec.hint:
                hint = QLabel(spec.hint)
                hint.setObjectName("Hint")
                hint.setWordWrap(True)
                layout.addWidget(hint)
        container.setProperty("field_key", spec.key)
        return container

    def _create_widget(self, spec: Field) -> QWidget:
        value = self._initial.get(spec.key, spec.default)
        if spec.kind in (TEXT, PASSWORD, FILE, LABEL):
            widget = QLineEdit(str(value) if value not in (None, "") else "")
            widget.setPlaceholderText(spec.placeholder)
            if spec.kind == PASSWORD:
                widget.setEchoMode(QLineEdit.EchoMode.Password)
            if spec.kind == LABEL:
                widget.setReadOnly(True)
            if spec.kind == FILE:
                holder = QWidget()
                row = QHBoxLayout(holder)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(SPACING_SM)
                row.addWidget(widget, 1)
                browse = button(tr("browse"), "attach")
                browse.clicked.connect(lambda _=False, target=widget: self._pick_file(target))
                row.addWidget(browse)
                holder.setProperty("inner", widget)
                self._widgets[spec.key] = widget
                return holder
            widget.textChanged.connect(self._apply_visibility)
            return widget
        if spec.kind == TEXTAREA:
            widget = QTextEdit(str(value or ""))
            widget.setMinimumHeight(72)
            widget.setMaximumHeight(130)
            return widget
        if spec.kind in (MONEY, NUMBER, PERCENT):
            widget = QDoubleSpinBox()
            widget.setRange(spec.minimum, spec.maximum)
            widget.setDecimals(spec.decimals if spec.kind != MONEY else 0)
            widget.setGroupSeparatorShown(True)
            widget.setValue(float(value or 0.0))
            widget.setAlignment(Qt.AlignmentFlag.AlignRight)
            if spec.kind == PERCENT:
                widget.setRange(0, 100)
                widget.setSuffix(" %")
            widget.valueChanged.connect(self._apply_visibility)
            return widget
        if spec.kind == INT:
            widget = QSpinBox()
            widget.setRange(int(spec.minimum), int(min(spec.maximum, 2_000_000_000)))
            widget.setValue(int(value or 0))
            widget.setAlignment(Qt.AlignmentFlag.AlignRight)
            return widget
        if spec.kind == DATE:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
            if isinstance(value, date):
                widget.setDate(QDate(value.year, value.month, value.day))
            else:
                widget.setDate(QDate.currentDate())
            return widget
        if spec.kind == COMBO:
            widget = QComboBox()
            for option_value, option_label in spec.options:
                widget.addItem(option_label, option_value)
            index = widget.findData(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
            widget.currentIndexChanged.connect(self._apply_visibility)
            return widget
        if spec.kind == CHECK:
            widget = QCheckBox(spec.label)
            widget.setChecked(bool(value))
            widget.stateChanged.connect(self._apply_visibility)
            return widget
        return QLineEdit(str(value or ""))

    def _pick_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("browse"))
        if path:
            target.setText(path)

    # -- values ------------------------------------------------------------- #
    def values(self) -> dict:
        """Return the current form values keyed by field name."""
        result: dict[str, Any] = {}
        for spec in self.fields:
            widget = self._widgets.get(spec.key)
            if widget is None:
                continue
            result[spec.key] = self._widget_value(spec, widget)
        return result

    def _widget_value(self, spec: Field, widget: QWidget) -> Any:
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentData()
        if isinstance(widget, QDateEdit):
            qdate = widget.date()
            return date(qdate.year(), qdate.month(), qdate.day())
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        del spec
        return None

    def widget(self, key: str) -> QWidget | None:
        """Return the widget bound to ``key``."""
        return self._widgets.get(key)

    def set_value(self, key: str, value: Any) -> None:
        """Programmatically update one field."""
        widget = self._widgets.get(key)
        if widget is None:
            return
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value or ""))
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setValue(float(value or 0))

    # -- validation --------------------------------------------------------- #
    def validate(self) -> str | None:
        """Highlight empty required fields and return the first error."""
        problem: str | None = None
        values = self.values()
        for spec in self.fields:
            widget = self._widgets.get(spec.key)
            if widget is None:
                continue
            invalid = False
            if spec.required and self._is_visible(spec, values):
                value = values.get(spec.key)
                invalid = value in (None, "", 0) and spec.kind not in (CHECK, PERCENT)
            widget.setProperty("invalid", "true" if invalid else "false")
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            if invalid and problem is None:
                problem = f"{spec.label}: {tr('required_field')}"
        return problem

    def _is_visible(self, spec: Field, values: dict) -> bool:
        return spec.visible_if is None or bool(spec.visible_if(values))

    def _apply_visibility(self) -> None:
        values = self.values()
        for spec in self.fields:
            if spec.visible_if is None:
                continue
            widget = self._widgets.get(spec.key)
            if widget is None:
                continue
            container = widget
            while container.parentWidget() is not None and not container.property("field_key"):
                container = container.parentWidget()
            container.setVisible(bool(spec.visible_if(values)))


def open_form(
    parent: QWidget,
    title: str,
    fields: list[Field],
    values: dict | None = None,
    subtitle: str = "",
    width: int = 620,
) -> dict | None:
    """Open a form dialog; return the values dict or ``None`` when cancelled."""
    dialog = FormDialog(title, fields, values, subtitle, parent, width=width)
    if dialog.exec():
        return dialog.values()
    return None
