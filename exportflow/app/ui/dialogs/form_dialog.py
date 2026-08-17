"""Declarative form dialog used by most editors."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import t
from app.ui.widgets.common import (
    button,
    checkbox,
    combo,
    combo_value,
    date_edit,
    date_value,
    enum_combo,
    int_spin,
    line_edit,
    set_combo,
    set_date,
    spin,
    text_area,
)
from app.utils.errors import ValidationError


@dataclass
class Field:
    """Declarative description of one form field."""

    key: str
    label: str
    kind: str = (
        "text"  # text | textarea | int | float | money | date | combo | enum | check | label
    )
    options: Iterable[Any] = field(default_factory=list)
    group: str = ""
    tab: str = ""
    required: bool = False
    placeholder: str = ""
    minimum: float = 0.0
    maximum: float = 1e12
    decimals: int = 2
    height: int = 90
    with_empty: bool = True
    tooltip: str = ""
    enabled: bool = True


class FormDialog(QDialog):
    """Modal dialog rendering :class:`Field` definitions into a form.

    ``on_save`` receives the collected values and may raise
    :class:`ValidationError`; the message is then shown inside the dialog
    instead of closing it.
    """

    def __init__(
        self,
        title: str,
        fields: list[Field],
        values: dict[str, Any] | None = None,
        on_save: Callable[[dict[str, Any]], Any] | None = None,
        parent: QWidget | None = None,
        width: int = 760,
        extra_widgets: dict[str, QWidget] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(width, 640)
        self.fields = fields
        self.values = dict(values or {})
        self._on_save = on_save
        self.widgets: dict[str, QWidget] = {}
        self.result_value: Any = None
        self.extra_widgets = extra_widgets or {}

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        root.addWidget(heading)

        self.error_label = QLabel("")
        self.error_label.setObjectName("BannerDanger")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        tabs = sorted({f.tab for f in fields if f.tab})
        if tabs:
            self.tab_widget = QTabWidget()
            for tab in tabs:
                self.tab_widget.addTab(
                    self._build_page([f for f in fields if f.tab == tab], tab), tab
                )
            root.addWidget(self.tab_widget, 1)
        else:
            self.tab_widget = None
            root.addWidget(self._build_page(fields, ""), 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(button(t("common.cancel"), self.reject, "Ghost"))
        buttons.addWidget(button(t("common.save"), self._save, "Primary"))
        root.addLayout(buttons)

    # ------------------------------------------------------------- building
    def _build_page(self, fields: list[Field], tab: str) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        layout = QFormLayout(container)
        layout.setContentsMargins(6, 10, 12, 10)
        layout.setSpacing(9)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        for spec in fields:
            widget = self._build_widget(spec)
            self.widgets[spec.key] = widget
            if spec.tooltip:
                widget.setToolTip(spec.tooltip)
            widget.setEnabled(spec.enabled)
            caption = spec.label + (" *" if spec.required else "")
            layout.addRow(caption, widget)

        for key, widget in self.extra_widgets.items():
            if tab and getattr(widget, "form_tab", "") != tab:
                continue
            layout.addRow(key, widget)

        scroll.setWidget(container)
        return scroll

    def _build_widget(self, spec: Field) -> QWidget:
        value = self.values.get(spec.key)
        if spec.kind == "textarea":
            return text_area(spec.placeholder, value or "", spec.height)
        if spec.kind == "int":
            return int_spin(int(spec.minimum), int(spec.maximum), int(value or 0))
        if spec.kind in ("float", "money"):
            return spin(spec.minimum, spec.maximum, float(value or 0), spec.decimals)
        if spec.kind == "date":
            return date_edit(value if isinstance(value, dt.date) else None)
        if spec.kind == "combo":
            return combo(list(spec.options), value, spec.with_empty, t("common.none"))
        if spec.kind == "enum":
            return enum_combo(spec.group or spec.key, list(spec.options), value, spec.with_empty)
        if spec.kind == "check":
            return checkbox("", bool(value))
        if spec.kind == "label":
            widget = QLabel(str(value or "—"))
            widget.setWordWrap(True)
            return widget
        return line_edit(spec.placeholder, str(value) if value not in (None, "") else "")

    # -------------------------------------------------------------- values
    def collect(self) -> dict[str, Any]:
        """Read every widget back into a value dictionary."""
        result: dict[str, Any] = dict(self.values)
        for spec in self.fields:
            widget = self.widgets[spec.key]
            if spec.kind == "textarea":
                result[spec.key] = widget.toPlainText().strip() or None
            elif spec.kind == "int":
                result[spec.key] = int(widget.value()) or None
            elif spec.kind in ("float", "money"):
                result[spec.key] = float(widget.value())
            elif spec.kind == "date":
                result[spec.key] = date_value(widget)
            elif spec.kind in ("combo", "enum"):
                result[spec.key] = combo_value(widget)
            elif spec.kind == "check":
                result[spec.key] = widget.isChecked()
            elif spec.kind == "label":
                continue
            else:
                result[spec.key] = widget.text().strip() or None
        return result

    def set_values(self, values: dict[str, Any]) -> None:
        """Write values into the widgets."""
        for spec in self.fields:
            if spec.key not in values:
                continue
            widget = self.widgets[spec.key]
            value = values[spec.key]
            if spec.kind == "textarea":
                widget.setPlainText(value or "")
            elif spec.kind in ("int", "float", "money"):
                widget.setValue(float(value or 0))
            elif spec.kind == "date":
                set_date(widget, value)
            elif spec.kind in ("combo", "enum"):
                set_combo(widget, value)
            elif spec.kind == "check":
                widget.setChecked(bool(value))
            elif spec.kind == "label":
                widget.setText(str(value or "—"))
            else:
                widget.setText("" if value is None else str(value))

    def show_error(self, message: str) -> None:
        """Display a validation message at the top of the dialog."""
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def _validate_required(self, values: dict[str, Any]) -> None:
        missing = []
        for spec in self.fields:
            if not spec.required:
                continue
            value = values.get(spec.key)
            invalid = (
                value in (None, "", 0)
                if spec.kind in ("float", "money", "int")
                else value in (None, "")
            )
            widget = self.widgets[spec.key]
            widget.setProperty("invalid", invalid)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            if invalid:
                missing.append(spec.label)
        if missing:
            raise ValidationError(", ".join(missing), key="error.validation")

    def _save(self) -> None:
        values = self.collect()
        try:
            self._validate_required(values)
            if self._on_save is not None:
                self.result_value = self._on_save(values)
            else:
                self.result_value = values
        except ValidationError as exc:
            params = {k: v for k, v in exc.params.items() if isinstance(v, (str, int, float))}
            message = t(exc.key, **params)
            if message.lower() == exc.key.rsplit(".", 1)[-1].replace("_", " ").capitalize().lower():
                message = exc.message or message
            self.show_error(message)
            return
        except Exception as exc:  # noqa: BLE001 - surfaced inside the dialog
            self.show_error(f"{type(exc).__name__}: {exc}")
            return
        self.accept()
