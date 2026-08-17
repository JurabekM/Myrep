"""Editable line-item grid used by RFQ, quotation and shipment editors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import t
from app.ui.widgets.common import button

#: Item-data role used when the anchor cell is a plain table item.
_HIDDEN_ROLE = int(Qt.ItemDataRole.UserRole) + 1


@dataclass
class ItemColumn:
    """Column definition for the item grid."""

    key: str
    title: str
    kind: str = "text"  # text | number | money | combo | readonly
    width: int = 110
    options: list[tuple[Any, str]] | None = None
    decimals: int = 2
    editable: bool = True


class ItemsEditor(QWidget):
    """Small spreadsheet-like editor over a list of dictionaries."""

    changed = Signal()

    def __init__(
        self,
        columns: list[ItemColumn],
        rows: list[dict] | None = None,
        parent: QWidget | None = None,
        on_add: Callable[[], dict | None] | None = None,
        allow_manual_add: bool = True,
    ) -> None:
        super().__init__(parent)
        self.columns = columns
        self._on_add = on_add
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        if on_add is not None:
            toolbar.addWidget(
                button(t("quotation.add_from_price"), self._add_via_callback, "Primary")
            )
        if allow_manual_add:
            toolbar.addWidget(button("+ " + t("common.add"), self.add_row, "Ghost"))
        toolbar.addWidget(button("− " + t("common.remove"), self.remove_selected, "Ghost"))
        toolbar.addStretch(1)
        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        toolbar.addWidget(self.summary)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels([column.title for column in columns])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(180)
        header = self.table.horizontalHeader()
        for index, column in enumerate(columns):
            if column.kind == "text" and column.width >= 200:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(index, column.width)
        layout.addWidget(self.table, 1)

        self.set_rows(rows or [])

    # ---------------------------------------------------------------- rows
    def set_rows(self, rows: list[dict]) -> None:
        """Replace the whole item list."""
        self._updating = True
        self.table.setRowCount(0)
        for row in rows:
            self._append(row)
        self._updating = False
        self.changed.emit()

    def add_row(self, values: dict | None = None) -> None:
        """Append one editable line."""
        self._append(values or {})
        self.changed.emit()

    def _add_via_callback(self) -> None:
        if self._on_add is None:
            return
        values = self._on_add()
        if values:
            self.add_row(values)

    def _append(self, values: dict) -> None:
        row_index = self.table.rowCount()
        self.table.insertRow(row_index)
        for col_index, column in enumerate(self.columns):
            value = values.get(column.key)
            if column.kind in ("number", "money"):
                widget = QDoubleSpinBox()
                widget.setRange(0, 1e12)
                widget.setDecimals(column.decimals)
                widget.setGroupSeparatorShown(True)
                widget.setValue(float(value or 0))
                widget.setReadOnly(not column.editable)
                widget.valueChanged.connect(self._on_cell_changed)
                self.table.setCellWidget(row_index, col_index, widget)
            elif column.kind == "combo":
                widget = QComboBox()
                for option_value, option_label in column.options or []:
                    widget.addItem(option_label, option_value)
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
                widget.currentIndexChanged.connect(self._on_cell_changed)
                self.table.setCellWidget(row_index, col_index, widget)
            elif column.kind == "readonly":
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row_index, col_index, item)
            else:
                widget = QLineEdit("" if value is None else str(value))
                widget.textChanged.connect(self._on_cell_changed)
                self.table.setCellWidget(row_index, col_index, widget)
        # Hidden payload (ids) is attached to the first cell so that it moves
        # with the row when other rows are inserted or removed.
        hidden = {
            key: value
            for key, value in values.items()
            if key not in {column.key for column in self.columns}
        }
        anchor = self.table.cellWidget(row_index, 0)
        if anchor is not None:
            anchor.setProperty("hidden_payload", hidden)
        else:
            item = self.table.item(row_index, 0)
            if item is not None:
                item.setData(_HIDDEN_ROLE, hidden)

    def remove_selected(self) -> None:
        """Delete every selected line."""
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        if not rows and self.table.rowCount():
            rows = [self.table.rowCount() - 1]
        for row in rows:
            self.table.removeRow(row)
        self.changed.emit()

    def rows(self) -> list[dict]:
        """Read every line back into dictionaries."""
        result: list[dict] = []
        for row_index in range(self.table.rowCount()):
            anchor = self.table.cellWidget(row_index, 0)
            if anchor is not None:
                payload = anchor.property("hidden_payload")
            else:
                item = self.table.item(row_index, 0)
                payload = item.data(_HIDDEN_ROLE) if item is not None else None
            values: dict[str, Any] = dict(payload or {})
            for col_index, column in enumerate(self.columns):
                widget = self.table.cellWidget(row_index, col_index)
                if isinstance(widget, QDoubleSpinBox):
                    values[column.key] = widget.value()
                elif isinstance(widget, QComboBox):
                    values[column.key] = widget.currentData()
                elif isinstance(widget, QLineEdit):
                    values[column.key] = widget.text().strip()
                else:
                    item = self.table.item(row_index, col_index)
                    values[column.key] = item.text() if item else ""
            result.append(values)
        return result

    def set_summary(self, text: str) -> None:
        """Update the caption shown on the toolbar."""
        self.summary.setText(text)

    def _on_cell_changed(self) -> None:
        if not self._updating:
            self.changed.emit()
