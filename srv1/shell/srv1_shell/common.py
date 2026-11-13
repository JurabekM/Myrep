"""Sahifalar uchun umumiy narsalar: kontekst, bazaviy sahifa, kartochka."""

import ctypes
import sys
from dataclasses import dataclass

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from srv1_shell.api import Api, Reply
from srv1_shell.events import EventStream
from srv1_shell.i18n import I18n

CARD_MIN_WIDTH = 190
CARD_SPACING = 12


@dataclass(frozen=True, slots=True)
class AppContext:
    api: Api
    events: EventStream
    i18n: I18n


class Page(QWidget):
    """Sahifa faqat ko'rinib turganda so'rov yuboradi: `activate` / `deactivate`."""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(22, 18, 22, 18)
        self.layout_root.setSpacing(14)

    def add_title(self, text: str) -> QLabel:
        title = QLabel(text)
        title.setObjectName("PageTitle")
        self.layout_root.addWidget(title)
        return title

    def activate(self) -> None:
        """Sahifa ochildi."""

    def deactivate(self) -> None:
        """Sahifa yopildi yoki boshqasiga o'tildi."""

    def describe_error(self, reply: Reply) -> str:
        t = self.ctx.i18n.t
        if reply.status == 0:
            return t("error.network")
        if reply.status == 401:
            return t("error.unauthorized")
        return t("error.http", status=reply.status, detail=reply.error)


class Card(QFrame):
    """Sarlavha, katta qiymat va kichik izohdan iborat kartochka."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.title = QLabel(title)
        self.title.setObjectName("CardTitle")
        self.value = QLabel("—")
        self.value.setObjectName("CardValue")
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        self.detail.setWordWrap(True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 12, 16, 12)
        self.body.setSpacing(4)
        for label in (self.title, self.value, self.detail):
            self.body.addWidget(label)
        self.body.addStretch(1)
        self.setMinimumWidth(CARD_MIN_WIDTH)

    def set(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)


class CardRow(QWidget):
    """Kartochkalar qatori: kenglik yetmasa, teng bo'lingan bir necha qatorga o'tadi.

    Oyna toraysa kartochkalar siqilmaydi va gorizontal aylantirish chiqmaydi.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[QWidget] = []
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(CARD_SPACING)

    def add(self, card: QWidget) -> None:
        self._cards.append(card)
        self._arrange(self.columns_for(self.width()) if self.isVisible() else len(self._cards))

    def columns(self) -> int:
        return self._columns

    def columns_for(self, width: int) -> int:
        """Shu kenglikka sig'adigan ustunlar soni; qatorlar imkon qadar teng to'ladi."""
        count = len(self._cards)
        if count == 0:
            return 0
        fits = max(1, (width + CARD_SPACING) // (CARD_MIN_WIDTH + CARD_SPACING))
        rows = -(-count // min(count, fits))
        return -(-count // rows)

    def _arrange(self, columns: int) -> None:
        if columns == self._columns and self._grid.count() == len(self._cards):
            return
        for card in self._cards:
            self._grid.removeWidget(card)
        for index, card in enumerate(self._cards):
            self._grid.addWidget(card, index // columns, index % columns)
        for column in range(max(columns, self._columns)):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)
        self._columns = columns

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self._arrange(self.columns_for(self.width()))

    def minimumSizeHint(self) -> QSize:
        # Bitta kartochka kengligi: ota-joylashuv qatorni bundan torroq qila olmaydi.
        return QSize(CARD_MIN_WIDTH, super().minimumSizeHint().height())


def dark_title_bar(hwnd: int) -> bool:
    """Oyna sarlavhasini to'q qiladi (Windows 10 2004+ / 11). Bo'lmasa jim o'tadi."""
    if sys.platform != "win32":
        return False
    value = ctypes.c_int(1)
    # 20 — DWMWA_USE_IMMERSIVE_DARK_MODE; eski Windows 10 yig'ilishlarida 19 edi.
    for attribute in (20, 19):
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), attribute, ctypes.byref(value), ctypes.sizeof(value)
        )
        if result == 0:
            return True
    return False


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionTitle")
    return label


def muted(text: str = "", *, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(wrap)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label
