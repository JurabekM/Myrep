"""Umumiy vidjetlar: karta, sahifa (QScrollArea ichida), jadval, raqam formati."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHeaderView, QLabel, QScrollArea,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


def som(n: int | float) -> str:
    return f"{int(n):,}".replace(",", " ") + " so'm"


def son(n: int | float) -> str:
    return f"{int(n):,}".replace(",", " ")


def yorliq(matn: str = "", nom: str | None = None, sarlavha: bool = False) -> QLabel:
    lb = QLabel(matn)
    if nom:
        lb.setObjectName(nom)
    lb.setWordWrap(True)
    lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lb


class Karta(QFrame):
    def __init__(self, sarlavha: str | None = None):
        super().__init__()
        self.setObjectName("karta")
        self.qator = QVBoxLayout(self)
        self.qator.setContentsMargins(16, 14, 16, 16)
        self.qator.setSpacing(10)
        if sarlavha:
            self.qator.addWidget(yorliq(sarlavha, "karta_sarlavha"))

    def qosh(self, w) -> None:
        if isinstance(w, QWidget):
            self.qator.addWidget(w)
        else:
            self.qator.addLayout(w)


class Sahifa(QScrollArea):
    """Kontent siqilmasin — har sahifa QScrollArea ichida (§16.4)."""

    sarlavha_matni = ""

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        ich = QWidget()
        self.qator = QVBoxLayout(ich)
        self.qator.setContentsMargins(24, 20, 24, 24)
        self.qator.setSpacing(14)
        self.qator.addWidget(yorliq(self.sarlavha_matni, "sarlavha"))
        self.setWidget(ich)

    def qosh(self, w) -> None:
        if isinstance(w, QWidget):
            self.qator.addWidget(w)
        else:
            self.qator.addLayout(w)

    def oxiri(self) -> None:
        self.qator.addStretch(1)

    def yangila(self) -> None:
        """Sahifaga o'tilganda chaqiriladi."""

    def holat(self, matn: str) -> None:
        self.ctx.holat(matn)


def jadval(ustunlar: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(ustunlar))
    t.setHorizontalHeaderLabels(ustunlar)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.horizontalHeader().setStretchLastSection(True)
    t.setMinimumHeight(220)
    return t


def jadval_toldir(t: QTableWidget, qatorlar: list[list], kalitlar: list | None = None) -> None:
    """To'ldirish paytida avto-o'lcham va chizish o'chiriladi — aks holda har katak
    butun maketni qayta hisoblaydi (O(n²), yuzlab partiyada oyna qotadi)."""
    h = t.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    t.setUpdatesEnabled(False)
    t.blockSignals(True)
    try:
        t.setRowCount(len(qatorlar))
        for i, q in enumerate(qatorlar):
            for j, v in enumerate(q):
                it = QTableWidgetItem("" if v is None else str(v))
                if j == 0 and kalitlar is not None:
                    it.setData(Qt.ItemDataRole.UserRole, kalitlar[i])
                t.setItem(i, j, it)
    finally:
        t.blockSignals(False)
        t.setUpdatesEnabled(True)
    t.resizeColumnsToContents()
    h.setStretchLastSection(False)
    h.setStretchLastSection(True)


def tanlangan_kalit(t: QTableWidget):
    r = t.currentRow()
    if r < 0 or t.item(r, 0) is None:
        return None
    return t.item(r, 0).data(Qt.ItemDataRole.UserRole)
