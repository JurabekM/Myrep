"""`table` vidjeti: filtr maydonlari, jadval va tanlangan qator ustidagi amallar."""

from collections.abc import Callable
from datetime import datetime
from functools import partial
from typing import Any, cast

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from srv1_sdk.panel import FormField, RowAction, TableColumn, TableWidget
from srv1_shell.common import section_title
from srv1_shell.i18n import I18n

Row = dict[str, Any]
Fetch = Callable[[str, dict[str, Any], Callable[[Any], None]], None]
Act = Callable[[RowAction, str, dict[str, Any]], None]
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def format_cell(value: Any, column: TableColumn, i18n: I18n) -> str:  # noqa: ANN401
    if value is None:
        return ""
    if column.format == "size" and isinstance(value, int | float):
        return i18n.size(float(value))
    if column.format == "datetime" and isinstance(value, int | float):
        return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
    if isinstance(value, bool):
        return "✓" if value else ""
    return str(value)


def make_editor(field: FormField) -> QWidget:
    if field.kind == "bool":
        return QCheckBox()
    if field.kind == "choice":
        combo = QComboBox()
        combo.addItems(list(field.choices))
        return combo
    return QLineEdit()


class DataTable(QWidget):
    """Ma'lumotni `fetch` orqali oladi; qator amallarini `act` orqali bajaradi."""

    def __init__(self, spec: TableWidget, i18n: I18n, fetch: Fetch, act: Act) -> None:
        super().__init__()
        self.spec = spec
        self._i18n = i18n
        self._fetch = fetch
        self._act = act
        self.rows: list[Row] = []
        self.filters: dict[str, QWidget] = {}
        self.action_buttons: dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section_title(i18n.pick(spec.label)))
        if spec.filters:
            layout.addLayout(self._build_filters())
        self.table = self._build_table()
        layout.addWidget(self.table)
        if spec.row_actions:
            layout.addLayout(self._build_actions())
        self._timer = QTimer(self)
        self._timer.setInterval(round(spec.refresh_s * 1000))
        self._timer.timeout.connect(self.refresh)

    # --- qurish -------------------------------------------------------------
    def _build_filters(self) -> QHBoxLayout:
        row = QHBoxLayout()
        for field in self.spec.filters:
            editor = make_editor(field)
            self.filters[field.name] = editor
            row.addWidget(QLabel(self._i18n.pick(field.label)))
            row.addWidget(editor, 1 if isinstance(editor, QLineEdit) else 0)
            if isinstance(editor, QLineEdit):
                editor.returnPressed.connect(self.refresh)
        self.search_button = QPushButton(self._i18n.t("panel.search"))
        self.search_button.setObjectName("Primary")
        self.search_button.clicked.connect(self.refresh)
        row.addWidget(self.search_button)
        return row

    def _build_table(self) -> QTableWidget:
        columns = self.spec.columns
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels([self._i18n.pick(column.title) for column in columns])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setMinimumHeight(190)
        header = table.horizontalHeader()
        if header is not None:
            # Kenglik mazmunga qarab (har to'ldirishda bir marta), oxirgi ustun qolganini oladi.
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setStretchLastSection(True)
            header.setMinimumSectionSize(70)
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        vertical = table.verticalHeader()
        if vertical is not None:
            vertical.setVisible(False)
        table.itemSelectionChanged.connect(self._update_actions)
        return table

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        for action in self.spec.row_actions:
            label = self._i18n.pick(action.label)
            button = QPushButton(label)
            button.setObjectName("Danger" if action.confirm else "")
            button.setEnabled(False)
            button.clicked.connect(partial(self._run, action, label))
            self.action_buttons[f"{action.method} {action.path}"] = button
            row.addWidget(button)
        return row

    # --- ma'lumot -------------------------------------------------------------
    def start(self) -> None:
        self.refresh()
        if self.spec.auto_refresh:
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def params(self) -> dict[str, Any]:
        """To'ldirilgan filtrlar (bo'shlari yuborilmaydi)."""
        values: dict[str, Any] = {}
        for name, editor in self.filters.items():
            if isinstance(editor, QCheckBox):
                if editor.isChecked():
                    values[name] = True
            elif isinstance(editor, QComboBox):
                if editor.currentText():
                    values[name] = editor.currentText()
            elif isinstance(editor, QLineEdit) and editor.text().strip():
                values[name] = editor.text().strip()
        return values

    def refresh(self) -> None:
        self._fetch(self.spec.source, self.params(), self.show_rows)

    def show_rows(self, data: Any) -> None:  # noqa: ANN401
        selected = self.selected_row()
        raw = cast(list[Any], data) if isinstance(data, list) else []
        self.rows = [cast(Row, row) for row in raw if isinstance(row, dict)]
        table = self.table
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            for column_index, column in enumerate(self.spec.columns):
                text = format_cell(row.get(column.key), column, self._i18n)
                item = QTableWidgetItem(text)
                item.setToolTip(text)  # tor ustunda kesilgan matn to'liq ko'rinsin
                if column.format == "size":
                    item.setTextAlignment(_RIGHT)
                table.setItem(index, column_index, item)
        table.clearSelection()
        if selected is not None and selected in self.rows:
            table.selectRow(self.rows.index(selected))
        # Oxirgi ustunga tegilmaydi: u qolgan joyni egallaydi (stretchLastSection).
        for column_index in range(len(self.spec.columns) - 1):
            table.resizeColumnToContents(column_index)
        table.blockSignals(False)
        table.setUpdatesEnabled(True)
        self._update_actions()

    def selected_row(self) -> Row | None:
        index = self.table.currentRow()
        if not self.table.selectedItems() or not 0 <= index < len(self.rows):
            return None
        return self.rows[index]

    def _update_actions(self) -> None:
        enabled = self.selected_row() is not None
        for button in self.action_buttons.values():
            button.setEnabled(enabled)

    def _run(self, action: RowAction, label: str, _checked: bool = False) -> None:
        row = self.selected_row()
        if row is not None:
            self._act(action, label, {name: row.get(name) for name in action.params})
