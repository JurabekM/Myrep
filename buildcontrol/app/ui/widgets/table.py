"""Reusable data table: column specs, paging model, delegates and toolbar."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_PAGE_SIZE, PAGE_SIZES
from app.ui.styles.theme import COLORS, ROW_HEIGHT, SPACING_SM, status_colors
from app.ui.widgets.common import SearchBox, button
from app.utils.formatting import fmt_date, fmt_datetime, fmt_money, fmt_percent, fmt_qty
from app.utils.i18n import tr

# Column kinds
TEXT = "text"
MONEY = "money"
NUMBER = "number"
PERCENT = "percent"
DATE = "date"
DATETIME = "datetime"
BADGE = "badge"
PROGRESS = "progress"
BOOL = "bool"

_RIGHT = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
_LEFT = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
_CENTER = int(Qt.AlignmentFlag.AlignCenter)

ROW_DATA_ROLE = int(Qt.ItemDataRole.UserRole) + 1
BADGE_ROLE = int(Qt.ItemDataRole.UserRole) + 2
PROGRESS_ROLE = int(Qt.ItemDataRole.UserRole) + 3


@dataclass
class Col:
    """Declarative column definition."""

    key: str
    title: str
    kind: str = TEXT
    width: int | None = None
    stretch: bool = False
    #: ``(row) -> str`` custom text
    formatter: Callable[[dict], str] | None = None
    #: ``(row) -> (label, badge_kind)`` used with :data:`BADGE`
    badge: Callable[[dict], tuple[str, str]] | None = None
    #: ``(row) -> color`` foreground override
    color: Callable[[dict], str | None] | None = None
    tooltip: Callable[[dict], str] | None = None

    def align(self) -> int:
        if self.kind in (MONEY, NUMBER, PERCENT):
            return _RIGHT
        if self.kind in (DATE, DATETIME, BADGE, PROGRESS, BOOL):
            return _CENTER
        return _LEFT


def _default_text(value: Any, kind: str) -> str:
    """Format ``value`` according to the column ``kind``."""
    if value is None or value == "":
        return "—" if kind in (DATE, DATETIME) else ""
    if kind == MONEY:
        return fmt_money(float(value))
    if kind == NUMBER:
        return fmt_qty(float(value))
    if kind == PERCENT:
        return fmt_percent(float(value), 0)
    if kind == DATE:
        return fmt_date(value if isinstance(value, (date, datetime)) else None)
    if kind == DATETIME:
        return fmt_datetime(value if isinstance(value, datetime) else None)
    if kind == BOOL:
        return tr("yes") if value else tr("no")
    return str(value)


class PagedTableModel(QAbstractTableModel):
    """Table model with in-memory filtering, sorting and pagination."""

    def __init__(self, columns: list[Col], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.columns = columns
        self._all: list[dict] = []
        self._filtered: list[dict] = []
        self._page = 0
        self._page_size = DEFAULT_PAGE_SIZE
        self._filter = ""
        self._sort_column = -1
        self._sort_desc = False
        self._row_color: Callable[[dict], str | None] | None = None

    # -- data plumbing ------------------------------------------------------ #
    def set_rows(self, rows: list[dict]) -> None:
        """Replace the underlying dataset, keeping filter and sort."""
        self.beginResetModel()
        self._all = list(rows)
        self._apply()
        self.endResetModel()

    def set_row_color(self, func: Callable[[dict], str | None] | None) -> None:
        """Set a callback coloring whole rows."""
        self._row_color = func

    def set_filter(self, text: str) -> None:
        """Filter rows by a case-insensitive substring across all columns."""
        self.beginResetModel()
        self._filter = (text or "").strip().lower()
        self._page = 0
        self._apply()
        self.endResetModel()

    def set_page(self, page: int) -> None:
        self.beginResetModel()
        self._page = max(0, min(page, max(0, self.page_count() - 1)))
        self.endResetModel()

    def set_page_size(self, size: int) -> None:
        self.beginResetModel()
        self._page_size = max(1, size)
        self._page = 0
        self.endResetModel()

    def _apply(self) -> None:
        rows = self._all
        if self._filter:
            needle = self._filter
            rows = [row for row in rows if needle in self._haystack(row)]
        if 0 <= self._sort_column < len(self.columns):
            key = self.columns[self._sort_column].key
            rows = sorted(rows, key=lambda r: _sort_key(r.get(key)), reverse=self._sort_desc)
        self._filtered = rows
        if self._page > max(0, self.page_count() - 1):
            self._page = max(0, self.page_count() - 1)

    def _haystack(self, row: dict) -> str:
        parts = []
        for column in self.columns:
            parts.append(self._cell_text(row, column).lower())
        return " ".join(parts)

    def _cell_text(self, row: dict, column: Col) -> str:
        if column.formatter is not None:
            return column.formatter(row)
        if column.kind == BADGE and column.badge is not None:
            return column.badge(row)[0]
        return _default_text(row.get(column.key), column.kind)

    # -- paging ------------------------------------------------------------- #
    def page_count(self) -> int:
        """Number of pages under the current filter."""
        if self._page_size <= 0:
            return 1
        return max(1, (len(self._filtered) + self._page_size - 1) // self._page_size)

    def current_page(self) -> int:
        return self._page

    def total_rows(self) -> int:
        return len(self._filtered)

    def page_rows(self) -> list[dict]:
        start = self._page * self._page_size
        return self._filtered[start : start + self._page_size]

    def row_dict(self, row_index: int) -> dict | None:
        rows = self.page_rows()
        if 0 <= row_index < len(rows):
            return rows[row_index]
        return None

    def all_rows(self) -> list[dict]:
        """Every row matching the current filter (ignoring pagination)."""
        return list(self._filtered)

    # -- QAbstractTableModel ------------------------------------------------ #
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.page_rows())

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.columns)

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self.columns[section].title
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return self.columns[section].align()
        elif role == Qt.ItemDataRole.DisplayRole:
            return str(self._page * self._page_size + section + 1)
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self.row_dict(index.row())
        if row is None:
            return None
        column = self.columns[index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if column.kind == PROGRESS:
                return ""
            return self._cell_text(row, column)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return column.align()
        if role == Qt.ItemDataRole.ForegroundRole:
            color = column.color(row) if column.color else None
            if color is None and self._row_color:
                color = self._row_color(row)
            if color:
                return QColor(color)
            if column.kind == MONEY and (row.get(column.key) or 0) < 0:
                return QColor(COLORS.danger)
        if role == Qt.ItemDataRole.ToolTipRole and column.tooltip:
            return column.tooltip(row)
        if role == BADGE_ROLE and column.kind == BADGE and column.badge:
            return column.badge(row)
        if role == PROGRESS_ROLE and column.kind == PROGRESS:
            try:
                return float(row.get(column.key) or 0.0)
            except (TypeError, ValueError):
                return 0.0
        if role == ROW_DATA_ROLE:
            return row
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.beginResetModel()
        self._sort_column = column
        self._sort_desc = order == Qt.SortOrder.DescendingOrder
        self._apply()
        self.endResetModel()


def _sort_key(value: Any) -> tuple[int, Any]:
    """Return a sortable key tolerating mixed / missing values."""
    if value is None or value == "":
        return (2, "")
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, (int, float)):
        return (0, float(value))
    if isinstance(value, datetime):
        return (1, value.timestamp())
    if isinstance(value, date):
        return (1, datetime(value.year, value.month, value.day).timestamp())
    return (3, str(value).lower())


class BadgeDelegate(QStyledItemDelegate):
    """Paints pill-shaped status badges."""

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        payload = index.data(BADGE_ROLE)
        if not payload:
            super().paint(painter, option, index)
            return
        text, kind = payload
        fg, bg = status_colors(kind)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = QFont(option.font)
        font.setPointSizeF(max(7.5, font.pointSizeF() - 1))
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        width = min(option.rect.width() - 8, metrics.horizontalAdvance(text) + 20)
        height = min(option.rect.height() - 8, 20)
        rect = QRect(
            option.rect.center().x() - width // 2,
            option.rect.center().y() - height // 2,
            width,
            height,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, height // 2, height // 2)
        painter.setPen(QColor(fg))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)
        painter.restore()


class ProgressDelegate(QStyledItemDelegate):
    """Paints an inline progress bar with the percentage on top."""

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        value = index.data(PROGRESS_ROLE)
        if value is None:
            super().paint(painter, option, index)
            return
        value = max(0.0, min(100.0, float(value)))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = option.rect.adjusted(8, 9, -8, -9)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS.bg_alt))
        painter.drawRoundedRect(rect, 5, 5)
        if value > 0:
            filled = QRect(rect)
            filled.setWidth(int(rect.width() * value / 100.0))
            color = (
                COLORS.success
                if value >= 100
                else (COLORS.accent if value >= 50 else COLORS.warning)
            )
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(filled, 5, 5)
        font = QFont(option.font)
        font.setPointSizeF(max(7.0, font.pointSizeF() - 2))
        painter.setFont(font)
        painter.setPen(QColor(COLORS.text))
        painter.drawText(option.rect, int(Qt.AlignmentFlag.AlignCenter), f"{value:.0f}%")
        painter.restore()


class DataTable(QWidget):
    """Search + filters + table + pagination, wired together."""

    selection_changed = Signal(object)
    row_activated = Signal(object)

    def __init__(
        self,
        columns: list[Col],
        searchable: bool = True,
        paginated: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.columns = columns
        self.model = PagedTableModel(columns, self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_SM)

        # toolbar ---------------------------------------------------------- #
        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(SPACING_SM)
        self.search = SearchBox()
        self.search.textChanged.connect(self._on_search)
        self.search.setVisible(searchable)
        self.toolbar.addWidget(self.search)
        self.filters = QHBoxLayout()
        self.filters.setSpacing(SPACING_SM)
        self.toolbar.addLayout(self.filters)
        self.toolbar.addStretch(1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(SPACING_SM)
        self.toolbar.addLayout(self.actions)
        root.addLayout(self.toolbar)

        # table ------------------------------------------------------------ #
        self.view = QTableView(self)
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setSortingEnabled(True)
        self.view.setWordWrap(False)
        self.view.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setStretchLastSection(False)
        self.view.setShowGrid(False)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.doubleClicked.connect(self._on_activated)
        self.view.selectionModel().selectionChanged.connect(self._on_selection)
        root.addWidget(self.view, 1)

        header = self.view.horizontalHeader()
        for index, column in enumerate(self.columns):
            if column.kind == BADGE:
                self.view.setItemDelegateForColumn(index, BadgeDelegate(self.view))
            elif column.kind == PROGRESS:
                self.view.setItemDelegateForColumn(index, ProgressDelegate(self.view))
            if column.stretch:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
            elif column.width:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
                self.view.setColumnWidth(index, column.width)
            else:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)

        # pagination -------------------------------------------------------- #
        self.footer = QHBoxLayout()
        self.footer.setSpacing(SPACING_SM)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Hint")
        self.footer.addWidget(self.count_label)
        self.footer.addStretch(1)
        self.page_size_box = QComboBox()
        for size in PAGE_SIZES:
            self.page_size_box.addItem(f"{size} {tr('rows')}", size)
        self.page_size_box.setCurrentIndex(list(PAGE_SIZES).index(DEFAULT_PAGE_SIZE))
        self.page_size_box.currentIndexChanged.connect(self._on_page_size)
        self.prev_btn = button("‹", tooltip=tr("page"))
        self.prev_btn.setFixedWidth(34)
        self.prev_btn.clicked.connect(lambda: self._step(-1))
        self.next_btn = button("›", tooltip=tr("page"))
        self.next_btn.setFixedWidth(34)
        self.next_btn.clicked.connect(lambda: self._step(1))
        self.page_label = QLabel("1 / 1")
        self.page_label.setObjectName("Hint")
        for widget in (self.page_size_box, self.prev_btn, self.page_label, self.next_btn):
            self.footer.addWidget(widget)
        self._paginated = paginated
        if not paginated:
            self.model.set_page_size(10_000_000)
            for widget in (self.page_size_box, self.prev_btn, self.page_label, self.next_btn):
                widget.setVisible(False)
        root.addLayout(self.footer)

    # -- public API --------------------------------------------------------- #
    def set_rows(self, rows: list[dict]) -> None:
        """Replace the table content."""
        self.model.set_rows(rows)
        self._refresh_footer()

    def rows(self) -> list[dict]:
        """Return the filtered rows (all pages)."""
        return self.model.all_rows()

    def current_row(self) -> dict | None:
        """Return the selected row dictionary, or ``None``."""
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.model.row_dict(indexes[0].row())

    def select_first(self) -> None:
        """Select the first visible row when nothing is selected."""
        if self.model.rowCount() and not self.view.selectionModel().selectedRows():
            self.view.selectRow(0)

    def add_action(self, widget: QWidget) -> QWidget:
        """Append a widget to the toolbar's right-hand area."""
        self.actions.addWidget(widget)
        return widget

    def add_filter(self, widget: QWidget) -> QWidget:
        """Append a filter control next to the search box."""
        self.filters.addWidget(widget)
        return widget

    def set_row_color(self, func: Callable[[dict], str | None] | None) -> None:
        """Color entire rows through a callback."""
        self.model.set_row_color(func)

    # -- internals ---------------------------------------------------------- #
    def _on_search(self, text: str) -> None:
        self.model.set_filter(text)
        self._refresh_footer()

    def _on_page_size(self) -> None:
        self.model.set_page_size(int(self.page_size_box.currentData()))
        self._refresh_footer()

    def _step(self, delta: int) -> None:
        self.model.set_page(self.model.current_page() + delta)
        self._refresh_footer()

    def _refresh_footer(self) -> None:
        total = self.model.total_rows()
        pages = self.model.page_count()
        page = self.model.current_page() + 1
        self.count_label.setText(f"{tr('total')}: {total} {tr('rows')}")
        self.page_label.setText(f"{page} / {pages}")
        self.prev_btn.setEnabled(page > 1)
        self.next_btn.setEnabled(page < pages)

    def _on_selection(self) -> None:
        self.selection_changed.emit(self.current_row())

    def _on_activated(self, index: QModelIndex) -> None:
        row = self.model.row_dict(index.row())
        if row is not None:
            self.row_activated.emit(row)


@dataclass
class FilterCombo:
    """Helper describing a combo filter attached to a table."""

    widget: QComboBox
    key: str
    options: list[tuple[Any, str]] = field(default_factory=list)

    def value(self) -> Any:
        return self.widget.currentData()


def make_combo(options: list[tuple[Any, str]], width: int = 170) -> QComboBox:
    """Build a themed combo box from ``[(value, label)]`` pairs."""
    combo = QComboBox()
    for value, label in options:
        combo.addItem(label, value)
    combo.setMinimumWidth(width)
    return combo
