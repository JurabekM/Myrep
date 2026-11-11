"""Sahifalar uchun umumiy narsalar: kontekst, bazaviy sahifa, kartochka."""

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from srv1_shell.api import Api, Reply
from srv1_shell.events import EventStream
from srv1_shell.i18n import I18n


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
        self.setMinimumWidth(190)

    def set(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)


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
