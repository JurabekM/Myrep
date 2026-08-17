"""Reusable dark-theme widgets shared by every page."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import tr
from app.ui.styles import theme


class Panel(QFrame):
    """Rounded dark panel used as a section container."""

    def __init__(self, parent: QWidget | None = None, *, padding: int = 16, spacing: int = 12):
        super().__init__(parent)
        self.setObjectName("Panel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(spacing)

    def body(self) -> QVBoxLayout:
        """Return the panel's layout so callers can add widgets."""
        return self._layout


class Card(QFrame):
    """Compact card used inside panels."""

    def __init__(self, parent: QWidget | None = None, *, padding: int = 12, spacing: int = 8):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(spacing)

    def body(self) -> QVBoxLayout:
        """Return the card's layout."""
        return self._layout


class Badge(QLabel):
    """Small colored status pill."""

    def __init__(self, text: str = "", color: str = theme.ACCENT, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_color(color)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_color(self, color: str) -> None:
        """Recolor the badge."""
        self.setStyleSheet(
            f"background: {theme.with_alpha(color, 40)}; color: {color};"
            f" border: 1px solid {theme.with_alpha(color, 90)};"
            f" border-radius: 9px; padding: 2px 9px; font-size: 11px; font-weight: 600;"
        )

    def set_state(self, text: str, color: str) -> None:
        """Update text and colour together."""
        self.setText(text)
        self.setToolTip(text)
        self.set_color(color)
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(text) + 22)


class Avatar(QLabel):
    """Circular initials avatar."""

    def __init__(
        self,
        initials: str = "?",
        color: str = theme.ACCENT,
        size: int = 34,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._initials = initials
        self._color = color
        self._size = size
        self.setFixedSize(size, size)

    def set_data(self, initials: str, color: str) -> None:
        """Update the avatar content."""
        self._initials = initials
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt signature
        """Draw a filled circle with the initials on top."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        painter.fillPath(path, QColor(self._color))
        painter.setPen(QColor("#FFFFFF"))
        font = QFont(theme.pick_font(), int(self._size * 0.36))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initials)
        painter.end()


class SearchBox(QLineEdit):
    """Search input with a rounded pill look and debounce-free change signal."""

    def __init__(self, placeholder: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SearchInput")
        self.setPlaceholderText(placeholder or tr("common.search"))
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(34)


class FilterChip(QPushButton):
    """Toggleable filter chip."""

    def __init__(self, text: str, parent: QWidget | None = None, *, checked: bool = False):
        super().__init__(text, parent)
        self.setObjectName("FilterChip")
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MetricTile(Card):
    """KPI tile: big value plus caption."""

    def __init__(
        self,
        label: str,
        value: str = "—",
        color: str = theme.TEXT,
        parent: QWidget | None = None,
    ):
        super().__init__(parent, padding=12, spacing=2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        self.value_label.setStyleSheet(f"color: {color};")
        self.caption = QLabel(label)
        self.caption.setObjectName("MetricLabel")
        self.body().addWidget(self.value_label)
        self.body().addWidget(self.caption)
        self.setMinimumWidth(140)

    def set_value(self, value: str, color: str | None = None) -> None:
        """Update the displayed value."""
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color};")

    def set_label(self, label: str) -> None:
        """Update the caption (used when the language changes)."""
        self.caption.setText(label)


class DataTable(QTableWidget):
    """Pre-configured read-only table with sorting and full-row selection."""

    def __init__(
        self, headers: list[str], parent: QWidget | None = None, *, stretch_column: int = 0
    ):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setWordWrap(False)
        self.setShowGrid(False)
        self.verticalHeader().setDefaultSectionSize(38)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if 0 <= stretch_column < len(headers):
            header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

    def set_headers(self, headers: list[str]) -> None:
        """Replace the header labels (language switch)."""
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

    def fill(self, rows: Iterable[list[Any]], *, ids: list[int] | None = None) -> None:
        """Populate the table; ``ids`` are stored in the first column's user role."""
        self.setSortingEnabled(False)
        materialised = [list(row) for row in rows]
        self.setRowCount(len(materialised))
        for row_index, row in enumerate(materialised):
            for column_index, value in enumerate(row):
                if isinstance(value, QTableWidgetItem):
                    item = value
                else:
                    item = QTableWidgetItem("" if value is None else str(value))
                if column_index == 0 and ids and row_index < len(ids):
                    item.setData(Qt.ItemDataRole.UserRole, ids[row_index])
                self.setItem(row_index, column_index, item)
        self.setSortingEnabled(True)

    def selected_id(self) -> int | None:
        """Return the entity id of the current row."""
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, 0)
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def selected_ids(self) -> list[int]:
        """Return the entity ids of every selected row."""
        result: list[int] = []
        for index in self.selectionModel().selectedRows() if self.selectionModel() else []:
            item = self.item(index.row(), 0)
            if item is not None:
                value = item.data(Qt.ItemDataRole.UserRole)
                if value is not None:
                    result.append(int(value))
        return result


def colored_item(
    text: str, color: str, *, bold: bool = False, sort_value: Any = None
) -> QTableWidgetItem:
    """Build a coloured table cell."""
    item = QTableWidgetItem(text)
    item.setForeground(QColor(color))
    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    if sort_value is not None:
        # EditRole drives sorting; DisplayRole must be re-applied afterwards so
        # the raw number never replaces the formatted label.
        item.setData(Qt.ItemDataRole.EditRole, sort_value)
        item.setData(Qt.ItemDataRole.DisplayRole, text)
    return item


def numeric_item(value: float, text: str | None = None) -> QTableWidgetItem:
    """Build a right-aligned numeric cell that sorts correctly."""
    item = QTableWidgetItem()
    item.setData(Qt.ItemDataRole.EditRole, float(value))
    if text is not None:
        item.setData(Qt.ItemDataRole.DisplayRole, text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


class Pager(QWidget):
    """Pagination control used by large worksheets."""

    page_changed = Signal(int)

    def __init__(self, page_size: int = 50, parent: QWidget | None = None):
        super().__init__(parent)
        self.page_size = page_size
        self.page = 0
        self.total = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.prev_button = QPushButton(tr("common.prev"))
        self.prev_button.setObjectName("Ghost")
        self.next_button = QPushButton(tr("common.next"))
        self.next_button.setObjectName("Ghost")
        self.info = QLabel("—")
        self.info.setObjectName("Muted")
        layout.addWidget(self.prev_button)
        layout.addWidget(self.info)
        layout.addWidget(self.next_button)
        layout.addStretch(1)
        self.prev_button.clicked.connect(self._previous)
        self.next_button.clicked.connect(self._next)

    def set_total(self, total: int) -> None:
        """Update the total row count and refresh the label."""
        self.total = total
        self._refresh()

    def offset(self) -> int:
        """Current SQL offset."""
        return self.page * self.page_size

    def reset(self) -> None:
        """Jump back to the first page."""
        self.page = 0
        self._refresh()

    def _pages(self) -> int:
        """Total number of pages."""
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    def _refresh(self) -> None:
        """Update labels and button states."""
        self.info.setText(
            f"{tr('common.page')} {self.page + 1} / {self._pages()}  ·  "
            f"{self.total} {tr('common.rows')}"
        )
        self.prev_button.setEnabled(self.page > 0)
        self.next_button.setEnabled(self.page + 1 < self._pages())

    def _previous(self) -> None:
        """Go one page back."""
        if self.page > 0:
            self.page -= 1
            self._refresh()
            self.page_changed.emit(self.page)

    def _next(self) -> None:
        """Go one page forward."""
        if self.page + 1 < self._pages():
            self.page += 1
            self._refresh()
            self.page_changed.emit(self.page)

    def retranslate(self) -> None:
        """Reapply translated captions."""
        self.prev_button.setText(tr("common.prev"))
        self.next_button.setText(tr("common.next"))
        self._refresh()


class EmptyState(QWidget):
    """Placeholder shown when a list or table has no rows."""

    def __init__(self, title: str = "", hint: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)
        self.title_label = QLabel(title or tr("common.empty"))
        self.title_label.setObjectName("SectionTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("Muted")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)

    def set_texts(self, title: str, hint: str = "") -> None:
        """Update the placeholder texts."""
        self.title_label.setText(title)
        self.hint_label.setText(hint)


def combo(items: Iterable[tuple[str, Any]], parent: QWidget | None = None) -> QComboBox:
    """Build a combo box from ``(label, value)`` pairs."""
    box = QComboBox(parent)
    for label, value in items:
        box.addItem(label, value)
    box.setMinimumHeight(34)
    return box


def set_combo_value(box: QComboBox, value: Any) -> None:
    """Select the entry whose user data equals ``value``."""
    index = box.findData(value)
    box.setCurrentIndex(index if index >= 0 else 0)


def toolbar_button(
    text: str,
    on_click: Callable[[], None],
    *,
    object_name: str = "",
    icon_name: str = "",
    tooltip: str = "",
    color: str = theme.TEXT_MUTED,
) -> QPushButton:
    """Create a themed toolbar button."""
    button = QPushButton(text)
    if object_name:
        button.setObjectName(object_name)
    if icon_name:
        button.setIcon(theme.icon(icon_name, color))
        button.setIconSize(QSize(16, 16))
    if tooltip:
        button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(on_click)
    return button


def separator() -> QFrame:
    """Horizontal 1px separator."""
    line = QFrame()
    line.setObjectName("Separator")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def show_error(parent: QWidget | None, message: str, title: str = "") -> None:
    """Themed error dialog."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title or tr("common.error"))
    box.setText(message)
    box.exec()


def show_info(parent: QWidget | None, message: str, title: str = "") -> None:
    """Themed information dialog."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(title or tr("common.info"))
    box.setText(message)
    box.exec()


def confirm(parent: QWidget | None, message: str, title: str = "") -> bool:
    """Themed yes/no confirmation dialog."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title or tr("common.confirm"))
    box.setText(message)
    yes = box.addButton(tr("common.yes"), QMessageBox.ButtonRole.YesRole)
    box.addButton(tr("common.no"), QMessageBox.ButtonRole.NoRole)
    box.exec()
    return box.clickedButton() is yes
