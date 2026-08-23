"""Qayta ishlatiladigan UI qismlari."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from distribos.presentation.status import StatusLabel
from distribos.presentation.theme import (
    PALETTE,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    badge_style,
)


class Badge(QLabel):
    """Rangli holat belgisi."""

    def __init__(self, text: str = "", tone: str = "progress") -> None:
        super().__init__(text)
        self.setObjectName("Badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setStyleSheet(badge_style(tone))

    def apply(self, label: StatusLabel) -> None:
        self.setText(label.text)
        self.set_tone(label.tone)
        if label.hint:
            self.setToolTip(label.hint)


class Card(QFrame):
    """Kartochka — sarlavha + katta qiymat + izoh."""

    def __init__(self, title: str, value: str = "—", hint: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_MD)
        layout.setSpacing(SPACE_SM // 2)

        self._title = QLabel(title)
        self._title.setObjectName("CardTitle")
        self._value = QLabel(value)
        self._value.setObjectName("CardValue")
        self._hint = QLabel(hint)
        self._hint.setObjectName("PageSubtitle")
        self._hint.setWordWrap(True)
        self._hint.setVisible(bool(hint))

        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addWidget(self._hint)

    def set_value(self, value: str, hint: str = "") -> None:
        self._value.setText(value)
        if hint:
            self._hint.setText(hint)
            self._hint.setVisible(True)

    def set_tone(self, tone: str) -> None:
        self._value.setStyleSheet(f"color: {PALETTE.tone_color(tone)};")


class PageHeader(QWidget):
    """Sahifa sarlavhasi va o'ng tomondagi amallar."""

    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, SPACE_MD)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("PageSubtitle")
        self._subtitle.setVisible(bool(subtitle))
        texts.addWidget(self._title)
        texts.addWidget(self._subtitle)

        layout.addLayout(texts)
        layout.addStretch(1)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(SPACE_SM)
        layout.addLayout(self._actions)

    def add_action(self, button: QPushButton) -> QPushButton:
        self._actions.addWidget(button)
        return button

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))


class SearchBox(QLineEdit):
    """Tezkor qidiruv."""

    def __init__(self, placeholder: str = "Qidirish…") -> None:
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)


class DataTable(QWidget):
    """Qidiruvli jadval.

    Qidiruv `QSortFilterProxyModel` orqali — ma'lumot qayta yuklanmaydi,
    ya'ni 100 000 qatorda ham UI bloklanmaydi.
    """

    def __init__(
        self,
        headers: Sequence[str],
        *,
        searchable: bool = True,
        placeholder: str = "Qidirish…",
    ) -> None:
        super().__init__()
        self._headers = list(headers)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_SM)

        self.search: SearchBox | None = None
        if searchable:
            self.search = SearchBox(placeholder)
            layout.addWidget(self.search)

        self._model = QStandardItemModel(0, len(self._headers))
        self._model.setHorizontalHeaderLabels(self._headers)

        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)   # barcha ustunlar bo'ylab

        self.view = QTableView()
        self.view.setModel(self._proxy)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setSortingEnabled(True)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        layout.addWidget(self.view, 1)

        if self.search is not None:
            self.search.textChanged.connect(self._proxy.setFilterFixedString)

    def set_rows(self, rows: Sequence[Sequence[Any]]) -> None:
        """Jadvalni to'ldiradi. Har hujayra matn sifatida ko'rsatiladi."""
        self._model.removeRows(0, self._model.rowCount())
        for row in rows:
            items: list[QStandardItem] = []
            for value in row:
                item = QStandardItem("" if value is None else str(value))
                item.setEditable(False)
                items.append(item)
            self._model.appendRow(items)
        self.view.resizeColumnsToContents()

    def row_count(self) -> int:
        return self._model.rowCount()

    def selected_row(self) -> list[str] | None:
        """Tanlangan qator qiymatlari (proxy indeksini manbaga o'giradi)."""
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return None
        source = self._proxy.mapToSource(indexes[0])
        return [
            self._model.item(source.row(), column).text()
            for column in range(self._model.columnCount())
        ]

    def set_row_tone(self, row: int, tone: str) -> None:
        from PySide6.QtGui import QColor

        color = QColor(PALETTE.tone_color(tone))
        for column in range(self._model.columnCount()):
            item = self._model.item(row, column)
            if item is not None:
                item.setForeground(color)


class EmptyState(QWidget):
    """Ma'lumot yo'q holati — bo'sh oq ekran o'rniga tushuntirish."""

    def __init__(self, title: str, hint: str = "", action: QPushButton | None = None) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(SPACE_SM)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        if hint:
            note = QLabel(hint)
            note.setObjectName("PageSubtitle")
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note.setWordWrap(True)
            layout.addWidget(note)

        if action is not None:
            wrapper = QHBoxLayout()
            wrapper.addStretch(1)
            wrapper.addWidget(action)
            wrapper.addStretch(1)
            layout.addLayout(wrapper)


class WarningBanner(QFrame):
    """Muhim ogohlantirish (masalan ochiq broker rejimi)."""

    def __init__(self, text: str, action_text: str = "", on_action: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.setObjectName("WarningBanner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)

        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label, 1)

        if action_text and on_action is not None:
            button = QPushButton(action_text)
            button.setObjectName("Ghost")
            # DIQQAT: lambda ISHLATILMAYDI — signal ulanishi lambda'ga
            # bog'lansa, obyekt yo'q qilinganda osilgan havola qoladi va
            # PySide6 kutilmaganda yiqiladi.
            button.clicked.connect(on_action)
            layout.addWidget(button)


def horizontal_separator() -> QFrame:
    line = QFrame()
    line.setObjectName("Separator")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def primary_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Primary")
    return button


def ghost_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Ghost")
    return button


def danger_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Danger")
    return button
