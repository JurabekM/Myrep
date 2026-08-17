from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QTableView, QVBoxLayout, QWidget)

from ..config import MAX_PREVIEW_ROWS


class FrameModel(QAbstractTableModel):
    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        super().__init__()
        self.frame = frame if frame is not None else pd.DataFrame()

    def set_frame(self, frame: pd.DataFrame) -> None:
        self.beginResetModel()
        self.frame = frame.head(MAX_PREVIEW_ROWS)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.frame)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else self.frame.shape[1]

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        value = self.frame.iat[index.row(), index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
                return ""
            if isinstance(value, float):
                return f"{value:,.6g}"
            if isinstance(value, pd.Timestamp):
                return value.isoformat(sep=" ")
            return str(value)[:500]
        if role == Qt.ItemDataRole.TextAlignmentRole and isinstance(value, (int, float, np.number)):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role=Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return str(self.frame.columns[section]) if orientation == Qt.Orientation.Horizontal else f"{section + 1:,}"


class FrameTable(QTableView):
    def __init__(self) -> None:
        super().__init__()
        self.model_ = FrameModel()
        self.setModel(self.model_)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.verticalHeader().setDefaultSectionSize(28)

    def set_frame(self, frame: pd.DataFrame) -> None:
        self.model_.set_frame(frame)
        self.resizeColumnsToContents()
        for column in range(self.model_.columnCount()):
            if self.columnWidth(column) > 240:
                self.setColumnWidth(column, 240)


class Card(QFrame):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(16, 14, 16, 16)
        self.layout_.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setStyleSheet("font-weight:700;font-size:14px")
            self.layout_.addWidget(label)


class StatCard(QFrame):
    def __init__(self, label: str, value: str = "—") -> None:
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        self.value = QLabel(value)
        self.value.setObjectName("statValue")
        caption = QLabel(label)
        caption.setObjectName("statLabel")
        layout.addWidget(self.value)
        layout.addWidget(caption)


class PageHeader(QWidget):
    def __init__(self, title: str, hint: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        name = QLabel(title)
        name.setObjectName("pageTitle")
        layout.addWidget(name)
        if hint:
            detail = QLabel(hint)
            detail.setObjectName("pageHint")
            layout.addWidget(detail)


class ColumnCombo(QComboBox):
    def __init__(self, numeric: bool = False, empty: bool = False) -> None:
        super().__init__()
        self.numeric, self.empty = numeric, empty

    def populate(self, frame: pd.DataFrame) -> None:
        current = self.currentText()
        self.clear()
        if self.empty:
            self.addItem("—")
        columns = frame.select_dtypes(include=np.number).columns if self.numeric else frame.columns
        self.addItems(map(str, columns))
        if current:
            self.setCurrentText(current)

    def value(self) -> str | None:
        return None if self.currentText() == "—" else self.currentText() or None


def button(text: str, primary: bool = False, danger: bool = False) -> QPushButton:
    item = QPushButton(text)
    item.setProperty("primary", primary)
    item.setProperty("danger", danger)
    return item


def row(*widgets: QWidget) -> QWidget:
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return wrapper


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
