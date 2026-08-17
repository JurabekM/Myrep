"""Qayta ishlatiladigan GUI komponentlari."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import theme as T


# ---------------------------------------------------------------------------
class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 14, 16, 14)
        self._lay.setSpacing(10)
        if title:
            head = QVBoxLayout()
            head.setSpacing(2)
            lbl = QLabel(title)
            lbl.setObjectName("CardTitle")
            head.addWidget(lbl)
            if subtitle:
                sub = QLabel(subtitle)
                sub.setObjectName("CardSub")
                sub.setWordWrap(True)
                head.addWidget(sub)
            self._lay.addLayout(head)

    def body(self) -> QVBoxLayout:
        return self._lay

    def add(self, w) -> None:
        if isinstance(w, QWidget):
            self._lay.addWidget(w)
        else:
            self._lay.addLayout(w)


# ---------------------------------------------------------------------------
class Badge(QLabel):
    def __init__(self, text: str, color: str = T.PRIMARY, parent=None) -> None:
        super().__init__(text, parent)
        self.set_color(color)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    def set_color(self, color: str) -> None:
        self.setStyleSheet(
            f"background: rgba({QColor(color).red()},{QColor(color).green()},"
            f"{QColor(color).blue()},0.15); color: {color};"
            f"border: 1px solid {color}; border-radius: 9px;"
            f"padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )

    def set(self, text: str, color: str) -> None:
        self.setText(text)
        self.set_color(color)


# ---------------------------------------------------------------------------
class StatTile(QFrame):
    def __init__(self, label: str, value: str = "—", color: str = T.TEXT, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        self.value = QLabel(value)
        self.value.setObjectName("StatValue")
        self.value.setStyleSheet(f"color: {color};")
        self.label = QLabel(label.upper())
        self.label.setObjectName("StatLabel")
        lay.addWidget(self.value)
        lay.addWidget(self.label)

    def set_value(self, v, color: Optional[str] = None) -> None:
        self.value.setText(str(v))
        if color:
            self.value.setStyleSheet(f"color: {color};")


# ---------------------------------------------------------------------------
class KeyValue(QWidget):
    """Ikki ustunli kalit-qiymat ro'yxati (monospace qiymatlar bilan)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(5)
        self._rows: dict[str, QLabel] = {}

    def add_row(self, key: str, value: str = "", mono: bool = True,
                color: str = T.TEXT) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(10)
        k = QLabel(key)
        k.setStyleSheet(f"color: {T.MUTED}; font-size: 12px;")
        k.setMinimumWidth(150)
        k.setMaximumWidth(190)
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 12px;")
        if mono:
            v.setFont(T.mono_font(9))
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.setWordWrap(True)
        row.addWidget(k, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(v, 1)
        self._lay.addLayout(row)
        self._rows[key] = v
        return v

    def set(self, key: str, value: str, color: Optional[str] = None) -> None:
        lbl = self._rows.get(key)
        if lbl is None:
            lbl = self.add_row(key, value)
            return
        lbl.setText(value)
        if color:
            lbl.setStyleSheet(f"color: {color}; font-size: 12px;")


# ---------------------------------------------------------------------------
class HexView(QPlainTextEdit):
    """Klassik hex dump."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(T.mono_font(9))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def show_bytes(self, data: bytes, limit: int = 4096) -> None:
        shown = data[:limit]
        lines = []
        for off in range(0, len(shown), 16):
            chunk = shown[off : off + 16]
            hexs = " ".join(f"{b:02x}" for b in chunk)
            asci = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{off:08x}  {hexs:<47}  |{asci}|")
        if len(data) > limit:
            lines.append(f"… yana {len(data) - limit} bayt")
        self.setPlainText("\n".join(lines) or "(bo'sh)")


# ---------------------------------------------------------------------------
class LogView(QPlainTextEdit):
    COLORS = {
        "INFO": T.MUTED,
        "OK": T.OK,
        "WARN": T.WARN,
        "FAIL": T.FAIL,
        "ATTACK": T.ATTACK,
        "WIRE": T.INFO,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(T.mono_font(9))
        self.setMaximumBlockCount(3000)

    def append_event(self, ev) -> None:
        color = self.COLORS.get(getattr(ev.level, "value", str(ev.level)), T.MUTED)
        lvl = getattr(ev.level, "value", str(ev.level))
        self.appendHtml(
            f'<span style="color:{T.DIM}">{ev.clock}</span> '
            f'<span style="color:{color};font-weight:600">[{lvl:<6}]</span> '
            f'<span style="color:{T.VIOLET}">{ev.actor:<8}</span> '
            f'<span style="color:{T.TEXT}">{_esc(ev.text)}</span>'
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def append_line(self, text: str, color: str = T.TEXT) -> None:
        self.appendHtml(f'<span style="color:{color}">{_esc(text)}</span>')
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


def _esc(s: str) -> str:
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
class Table(QTableWidget):
    def __init__(self, headers: list[str], parent=None) -> None:
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.horizontalHeader().setStretchLastSection(True)

    def add_row(self, values: list, colors: Optional[list[Optional[str]]] = None,
                mono_cols: tuple[int, ...] = ()) -> int:
        r = self.rowCount()
        self.insertRow(r)
        for c, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            if colors and c < len(colors) and colors[c]:
                item.setForeground(QColor(colors[c]))
            if c in mono_cols:
                item.setFont(T.mono_font(9))
            self.setItem(r, c, item)
        return r

    def clear_rows(self) -> None:
        self.setRowCount(0)


# ---------------------------------------------------------------------------
def scroll_page(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(inner)
    area.setFrameShape(QFrame.Shape.NoFrame)
    return area


def page_header(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 6)
    lay.setSpacing(3)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(subtitle)
    s.setObjectName("PageSub")
    s.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(s)
    return w


def hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"background:{T.BORDER_SOFT}; max-height:1px; border:none;")
    return f


def fmt_hex(b: Optional[bytes], n: int = 12) -> str:
    if b is None:
        return "—"
    h = b.hex()
    return h[: n * 2] + ("…" if len(b) > n else "")
