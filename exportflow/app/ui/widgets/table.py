"""Dictionary-backed table model, view and the filter bar above it."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import t, te
from app.ui.styles.theme import COLORS, status_colors
from app.utils.formatting import fmt_date, fmt_datetime, fmt_money, fmt_number


@dataclass
class Column:
    """Declarative description of one table column."""

    key: str
    title: str
    kind: str = "text"  # text | number | money | date | datetime | status | bool | percent
    width: int | None = None
    group: str = ""  # enum group for ``status`` columns
    currency_key: str = "currency"
    decimals: int = 2
    align: str = ""
    stretch: bool = False
    formatter: Callable[[dict], str] | None = None


class DictTableModel(QAbstractTableModel):
    """Table model over a list of dictionaries."""

    def __init__(self, columns: list[Column], rows: list[dict] | None = None) -> None:
        super().__init__()
        self.columns = columns
        self._rows: list[dict] = rows or []
        #: keys whose truthiness marks a row as overdue (painted red)
        self.danger_keys: tuple[str, ...] = ("overdue", "expired", "delayed")

    # ------------------------------------------------------------- Qt API
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        """Number of rows currently held by the model."""
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        """Number of declared columns."""
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        """Column captions."""
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return self.columns[section].title

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Cell text, colours and sort keys."""
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        column = self.columns[index.column()]
        value = row.get(column.key)

        if role == Qt.ItemDataRole.DisplayRole:
            return self.format_value(row, column)
        if role == Qt.ItemDataRole.UserRole:  # raw sort value
            if isinstance(value, (int, float, dt.date, dt.datetime)):
                return value
            return str(value or "").lower()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column.align == "right" or column.kind in ("number", "money", "percent"):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if column.align == "center" or column.kind in ("status", "bool"):
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if column.kind == "status":
                return QBrush(QColor(status_colors(str(value or ""))[0]))
            if any(row.get(key) for key in self.danger_keys):
                return QBrush(QColor(COLORS["danger"]))
            if row.get("is_archived"):
                return QBrush(QColor(COLORS["text_dim"]))
            return None
        if role == Qt.ItemDataRole.FontRole:
            if column.kind == "status" or (column.key in ("number", "sku") and value):
                font = QFont()
                font.setBold(True)
                return font
            return None
        if role == Qt.ItemDataRole.ToolTipRole:
            text = self.format_value(row, column)
            return text if len(text) > 24 else None
        return None

    # ---------------------------------------------------------- formatting
    def format_value(self, row: dict, column: Column) -> str:
        """Render one cell as display text."""
        if column.formatter is not None:
            return column.formatter(row)
        value = row.get(column.key)
        if value is None or value == "":
            return ""
        if column.kind == "status":
            return te(column.group or column.key, str(value))
        if column.kind == "money":
            return fmt_money(value, row.get(column.currency_key) or "USD", column.decimals)
        if column.kind == "number":
            return fmt_number(value, column.decimals)
        if column.kind == "percent":
            return f"{float(value):.{column.decimals}f}%"
        if column.kind == "date":
            return fmt_date(value)
        if column.kind == "datetime":
            return fmt_datetime(value)
        if column.kind == "bool":
            return t("common.yes") if value else t("common.no")
        return str(value)

    # -------------------------------------------------------------- rows
    def set_rows(self, rows: list[dict]) -> None:
        """Replace the whole dataset."""
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, index: int) -> dict | None:
        """Return the dictionary behind a row index."""
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    @property
    def rows(self) -> list[dict]:
        """Current dataset."""
        return self._rows

    def set_columns(self, columns: list[Column]) -> None:
        """Replace the column definitions (used on language change)."""
        self.beginResetModel()
        self.columns = columns
        self.endResetModel()


class DataTable(QWidget):
    """Sortable table with selection signals and a row counter."""

    selection_changed = Signal(object)
    row_activated = Signal(object)

    def __init__(self, columns: list[Column], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.model = DictTableModel(columns)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.verticalHeader().setVisible(False)
        self.view.verticalHeader().setDefaultSectionSize(30)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setWordWrap(False)
        self.view.doubleClicked.connect(self._on_double_click)
        self.view.selectionModel().selectionChanged.connect(self._on_selection)

        self.counter = QLabel("")
        self.counter.setObjectName("Hint")

        layout.addWidget(self.view, 1)
        layout.addWidget(self.counter)
        self._apply_widths()

    # ------------------------------------------------------------ helpers
    def _apply_widths(self) -> None:
        header = self.view.horizontalHeader()
        for index, column in enumerate(self.model.columns):
            if column.stretch:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
            elif column.width:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
                self.view.setColumnWidth(index, column.width)
            else:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)

    def set_rows(self, rows: list[dict]) -> None:
        """Load data and refresh the row counter."""
        self.model.set_rows(rows)
        self.counter.setText(t("common.rows", count=len(rows)))
        self._apply_widths()

    def set_columns(self, columns: list[Column]) -> None:
        """Swap the column definitions."""
        self.model.set_columns(columns)
        self._apply_widths()

    def set_text_filter(self, text: str) -> None:
        """Apply a client-side text filter across every column."""
        self.proxy.setFilterFixedString(text or "")
        self.counter.setText(t("common.rows", count=self.proxy.rowCount()))

    def current_row(self) -> dict | None:
        """Dictionary of the currently focused row."""
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return None
        source = self.proxy.mapToSource(indexes[0])
        return self.model.row_at(source.row())

    def selected_rows(self) -> list[dict]:
        """Dictionaries of every selected row."""
        result = []
        for index in self.view.selectionModel().selectedRows():
            row = self.model.row_at(self.proxy.mapToSource(index).row())
            if row is not None:
                result.append(row)
        return result

    def select_id(self, entity_id: int) -> None:
        """Select the row whose ``id`` matches."""
        for row_index in range(self.proxy.rowCount()):
            source = self.proxy.mapToSource(self.proxy.index(row_index, 0))
            row = self.model.row_at(source.row())
            if row and row.get("id") == entity_id:
                self.view.selectRow(row_index)
                self.view.scrollTo(self.proxy.index(row_index, 0))
                return

    def _on_selection(self) -> None:
        self.selection_changed.emit(self.current_row())

    def _on_double_click(self, index: QModelIndex) -> None:
        row = self.model.row_at(self.proxy.mapToSource(index).row())
        if row is not None:
            self.row_activated.emit(row)


@dataclass
class FilterSpec:
    """Declarative definition of one filter control."""

    key: str
    label: str
    kind: str = "combo"  # combo | enum | text | check | date
    options: Iterable[Any] = field(default_factory=list)
    group: str = ""
    width: int = 150


class FilterBar(QWidget):
    """Row of search and filter controls emitting a single change signal."""

    changed = Signal()

    def __init__(self, specs: list[FilterSpec], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.specs = specs
        self.widgets: dict[str, QWidget] = {}
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setObjectName("SearchInput")
        self.search.setPlaceholderText(t("common.search"))
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(240)
        self.search.textChanged.connect(lambda: self.changed.emit())
        self._layout.addWidget(self.search)

        for spec in specs:
            self._layout.addWidget(self._build(spec))
        self._layout.addStretch(1)

    def _build(self, spec: FilterSpec) -> QWidget:
        from app.ui.widgets.common import checkbox, combo, date_edit, enum_combo

        if spec.kind == "check":
            widget = checkbox(spec.label)
            widget.stateChanged.connect(lambda: self.changed.emit())
        elif spec.kind == "date":
            widget = date_edit(None)
            # Show the filter caption while no date is picked.
            widget.setSpecialValueText(spec.label)
            widget.setToolTip(spec.label)
            widget.dateChanged.connect(lambda: self.changed.emit())
        elif spec.kind == "enum":
            widget = enum_combo(spec.group or spec.key, list(spec.options), with_empty=True)
            widget.setToolTip(spec.label)
            widget.currentIndexChanged.connect(lambda: self.changed.emit())
        elif spec.kind == "text":
            widget = QLineEdit()
            widget.setPlaceholderText(spec.label)
            widget.textChanged.connect(lambda: self.changed.emit())
        else:
            widget = combo(list(spec.options), with_empty=True, empty_label=spec.label)
            widget.setToolTip(spec.label)
            widget.currentIndexChanged.connect(lambda: self.changed.emit())
        if spec.width:
            widget.setMinimumWidth(spec.width)
        self.widgets[spec.key] = widget
        return widget

    def set_options(self, key: str, options: Iterable[Any], label: str | None = None) -> None:
        """Repopulate a combo filter, preserving the current selection."""
        widget = self.widgets.get(key)
        if not isinstance(widget, QComboBox):
            return
        current = widget.currentData()
        widget.blockSignals(True)
        widget.clear()
        widget.addItem(label or t("common.all"), None)
        for option in options:
            if isinstance(option, tuple):
                widget.addItem(str(option[1]), option[0])
            else:
                widget.addItem(str(option), option)
        index = widget.findData(current)
        widget.setCurrentIndex(index if index >= 0 else 0)
        widget.blockSignals(False)

    def values(self) -> dict[str, Any]:
        """Current filter values keyed by spec key (``text`` holds the search)."""
        from app.ui.widgets.common import date_value

        result: dict[str, Any] = {"text": self.search.text().strip()}
        for spec in self.specs:
            widget = self.widgets[spec.key]
            if spec.kind == "check":
                result[spec.key] = widget.isChecked()
            elif spec.kind == "date":
                result[spec.key] = date_value(widget)
            elif spec.kind == "text":
                result[spec.key] = widget.text().strip()
            else:
                result[spec.key] = widget.currentData()
        return result

    def reset(self) -> None:
        """Clear every control."""
        self.search.clear()
        for spec in self.specs:
            widget = self.widgets[spec.key]
            if spec.kind == "check":
                widget.setChecked(False)
            elif spec.kind == "date":
                widget.setDate(widget.minimumDate())
            elif spec.kind == "text":
                widget.clear()
            else:
                widget.setCurrentIndex(0)
        self.changed.emit()
