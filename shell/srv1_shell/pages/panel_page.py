"""Plagin panelini `PanelSpec` tavsifidan chizadi. Bu yerda plaginga xos mantiq yo'q."""

import json
from collections.abc import Callable
from functools import partial
from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from srv1_sdk.panel import (
    ButtonWidget,
    ChartWidget,
    FormField,
    FormWidget,
    LabelWidget,
    PanelSpec,
    TableWidget,
    ValueWidget,
)
from srv1_shell.api import Reply
from srv1_shell.charts import LineChart
from srv1_shell.common import AppContext, Card, Page, section_title

RESULT_MAX_CHARS = 300
CHART_HEIGHT = 220
Consumer = Callable[[Any], None]


def _compact(data: Any) -> str:  # noqa: ANN401 — ixtiyoriy JSON
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return text if len(text) <= RESULT_MAX_CHARS else text[: RESULT_MAX_CHARS - 1] + "…"


class _Form(QFrame):
    """Bitta `form` vidjeti: maydonlar + yuborish tugmasi."""

    def __init__(self, spec: FormWidget, page: "PanelPage") -> None:
        super().__init__()
        self.setObjectName("Card")
        self.spec = spec
        self._page = page
        i18n = page.ctx.i18n
        self.inputs: dict[str, QWidget] = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.addWidget(section_title(i18n.pick(spec.label)))
        form = QFormLayout()
        for field in spec.fields:
            editor = self._editor(field)
            self.inputs[field.name] = editor
            form.addRow(i18n.pick(field.label), editor)
        outer.addLayout(form)
        self.submit = QPushButton(i18n.t("panel.submit"))
        self.submit.setObjectName("Primary")
        self.submit.clicked.connect(self._send)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.submit)
        outer.addLayout(row)

    def _editor(self, field: FormField) -> QWidget:
        if field.kind == "bool":
            return QCheckBox()
        if field.kind == "choice":
            combo = QComboBox()
            combo.addItems(list(field.choices))
            return combo
        return QLineEdit()

    def values(self) -> dict[str, Any] | None:
        """Maydon qiymatlari; xato bo'lsa xabar ko'rsatib `None` qaytaradi."""
        i18n = self._page.ctx.i18n
        result: dict[str, Any] = {}
        for field in self.spec.fields:
            editor = self.inputs[field.name]
            label = i18n.pick(field.label)
            if isinstance(editor, QCheckBox):
                result[field.name] = editor.isChecked()
                continue
            text = editor.currentText() if isinstance(editor, QComboBox) else ""
            if isinstance(editor, QLineEdit):
                text = editor.text().strip()
            if not text:
                if field.required:
                    self._page.show_error(i18n.t("panel.required", field=label))
                    return None
                continue
            if field.kind == "number":
                try:
                    number = float(text.replace(",", "."))
                except ValueError:
                    self._page.show_error(i18n.t("panel.number", field=label))
                    return None
                result[field.name] = int(number) if number.is_integer() else number
            else:
                result[field.name] = text
        return result

    def _send(self) -> None:
        values = self.values()
        if values is None:
            return
        if self.spec.method == "GET":
            self._page.call(self.spec.method, self.spec.path, params=values)
        else:
            self._page.call(self.spec.method, self.spec.path, body=values)


class PanelPage(Page):
    def __init__(self, ctx: AppContext, plugin: str, spec: PanelSpec) -> None:
        super().__init__(ctx)
        self.plugin = plugin
        self.spec = spec
        self._prefix = f"/api/v1/plugins/{plugin}/api"
        self._topic_prefix = f"plugin.{plugin}."
        self._consumers: dict[str, list[Consumer]] = {}
        self._intervals: dict[str, float] = {}
        self._timers: list[QTimer] = []
        self._charts: list[tuple[str, str, LineChart]] = []
        self.values: dict[str, Card] = {}
        self.buttons: dict[str, QPushButton] = {}
        self.forms: dict[str, _Form] = {}
        self.tables: dict[str, QTableWidget] = {}
        self.charts: dict[str, LineChart] = {}

        self.add_title(ctx.i18n.pick(spec.title))
        self.result = QLabel("")
        self.result.setObjectName("ResultText")
        self.result.setWordWrap(True)

        content = QWidget()
        self._content = QVBoxLayout(content)
        self._content.setContentsMargins(0, 0, 8, 0)
        self._content.setSpacing(12)
        self._value_row: QHBoxLayout | None = None
        self._button_row: QHBoxLayout | None = None
        for widget in spec.widgets:
            self._add(widget)
        self._content.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.layout_root.addWidget(scroll, 1)
        self.layout_root.addWidget(self.result)

        for source, interval in self._intervals.items():
            timer = QTimer(self)
            timer.setInterval(round(interval * 1000))
            timer.timeout.connect(partial(self._fetch, source))
            self._timers.append(timer)
        ctx.events.received.connect(self._on_event)

    # --- vidjetlarni qurish -------------------------------------------------
    def _add(self, widget: object) -> None:
        if not isinstance(widget, ValueWidget):
            self._value_row = None
        if not isinstance(widget, ButtonWidget):
            self._button_row = None
        if isinstance(widget, LabelWidget):
            label = QLabel(self.ctx.i18n.pick(widget.text))
            label.setWordWrap(True)
            self._content.addWidget(label)
        elif isinstance(widget, ValueWidget):
            self._add_value(widget)
        elif isinstance(widget, ButtonWidget):
            self._add_button(widget)
        elif isinstance(widget, FormWidget):
            form = _Form(widget, self)
            self.forms[widget.path] = form
            self._content.addWidget(form)
        elif isinstance(widget, TableWidget):
            self._add_table(widget)
        elif isinstance(widget, ChartWidget):
            self._add_chart(widget)

    def _watch(self, source: str, refresh_s: float, consumer: Consumer) -> None:
        self._consumers.setdefault(source, []).append(consumer)
        self._intervals[source] = min(refresh_s, self._intervals.get(source, refresh_s))

    def _add_value(self, widget: ValueWidget) -> None:
        if self._value_row is None:
            self._value_row = QHBoxLayout()
            self._value_row.setSpacing(12)
            self._content.addLayout(self._value_row)
        card = Card(self.ctx.i18n.pick(widget.label))
        self.values[widget.field] = card
        self._value_row.addWidget(card, 1)

        def show(data: Any) -> None:  # noqa: ANN401
            value = data.get(widget.field) if isinstance(data, dict) else None  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            card.set("—" if value is None else str(value))  # pyright: ignore[reportUnknownArgumentType]

        self._watch(widget.source, widget.refresh_s, show)

    def _add_button(self, widget: ButtonWidget) -> None:
        if self._button_row is None:
            self._button_row = QHBoxLayout()
            self._button_row.addStretch(1)
            self._content.addLayout(self._button_row)
        label = self.ctx.i18n.pick(widget.label)
        button = QPushButton(label)
        button.setObjectName("Danger" if widget.confirm else "")
        button.clicked.connect(partial(self._press, widget, label))
        self.buttons[f"{widget.method} {widget.path}"] = button
        self._button_row.insertWidget(self._button_row.count() - 1, button)

    def _add_table(self, widget: TableWidget) -> None:
        i18n = self.ctx.i18n
        self._content.addWidget(section_title(i18n.pick(widget.label)))
        table = QTableWidget(0, len(widget.columns))
        table.setHorizontalHeaderLabels([i18n.pick(column.title) for column in widget.columns])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setMinimumHeight(160)
        header = table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vertical = table.verticalHeader()
        if vertical is not None:
            vertical.setVisible(False)
        self.tables[widget.source] = table
        self._content.addWidget(table)
        keys = [column.key for column in widget.columns]

        def show(data: Any) -> None:  # noqa: ANN401
            rows = cast(list[Any], data) if isinstance(data, list) else []
            table.setUpdatesEnabled(False)
            table.setRowCount(len(rows))
            for index, row in enumerate(rows):
                for column, key in enumerate(keys):
                    value = row.get(key, "") if isinstance(row, dict) else ""  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                    table.setItem(index, column, QTableWidgetItem(str(value)))  # pyright: ignore[reportUnknownArgumentType]
            table.setUpdatesEnabled(True)

        self._watch(widget.source, widget.refresh_s, show)

    def _add_chart(self, widget: ChartWidget) -> None:
        label = self.ctx.i18n.pick(widget.label)
        self._content.addWidget(section_title(label))
        chart = LineChart([label], window=widget.window)
        chart.setFixedHeight(CHART_HEIGHT)
        self.charts[widget.topic] = chart
        self._charts.append((self._topic_prefix + widget.topic, widget.field, chart))
        self._content.addWidget(chart)

    # --- ma'lumot -------------------------------------------------------------
    def activate(self) -> None:
        self.refresh_sources()
        for timer in self._timers:
            timer.start()

    def deactivate(self) -> None:
        for timer in self._timers:
            timer.stop()

    def refresh_sources(self) -> None:
        for source in self._consumers:
            self._fetch(source)

    def _fetch(self, source: str) -> None:
        self.ctx.api.get(self._prefix + source, partial(self._on_source, source), owner=self)

    def _on_source(self, source: str, reply: Reply) -> None:
        if not reply.ok:
            self.show_error(self.describe_error(reply))
            return
        for consumer in self._consumers.get(source, []):
            consumer(reply.data)

    def _on_event(self, topic: str, data: dict[str, Any]) -> None:
        for chart_topic, field, chart in self._charts:
            value = data.get(field)
            if topic == chart_topic and isinstance(value, int | float):
                chart.append([float(value)])

    # --- amallar ----------------------------------------------------------------
    def _press(self, widget: ButtonWidget, label: str) -> None:
        if widget.confirm and not self.confirm(label):
            return
        self.call(widget.method, widget.path)

    def confirm(self, action: str) -> bool:
        t = self.ctx.i18n.t
        box = QMessageBox(self)
        box.setWindowTitle(t("panel.confirm.title"))
        box.setText(t("panel.confirm.text", action=action))
        yes = box.addButton(t("common.yes"), QMessageBox.ButtonRole.YesRole)
        box.addButton(t("common.no"), QMessageBox.ButtonRole.NoRole)
        box.exec()
        return box.clickedButton() is yes

    def call(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,  # noqa: ANN401
    ) -> None:
        self.ctx.api.request(
            method, self._prefix + path, self._on_called, owner=self, params=params, body=body
        )

    def _on_called(self, reply: Reply) -> None:
        if not reply.ok:
            self.show_error(self.describe_error(reply))
            return
        self.result.setObjectName("ResultText")
        self._restyle_result()
        self.result.setText(self.ctx.i18n.t("panel.done", result=_compact(reply.data)))
        self.refresh_sources()

    def show_error(self, text: str) -> None:
        self.result.setObjectName("ErrorText")
        self._restyle_result()
        self.result.setText(text)

    def _restyle_result(self) -> None:
        style = self.result.style()
        if style is not None:
            style.unpolish(self.result)
            style.polish(self.result)
