"""Qayta ishlatiladigan GUI komponentlari."""
from __future__ import annotations

from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from PySide6.QtCore import (QAbstractTableModel, QEasingCurve, QModelIndex,
                            QObject, QPropertyAnimation, QSize, Qt, QTimer,
                            Signal)
from PySide6.QtGui import QAction, QColor, QFont, QGuiApplication
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFrame,
                               QGraphicsOpacityEffect, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMenu, QPushButton, QScrollArea, QSizePolicy,
                               QTableView, QVBoxLayout, QWidget)

from ..config import LEVEL_COLORS, PALETTE, PREVIEW_ROWS
from ..core.profile import CATEGORICAL, DATETIME, NUMERIC, column_kind


# ---------------------------------------------------------------------------
# Oddiy elementlar
# ---------------------------------------------------------------------------
def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background:{PALETTE['border']}; max-height:1px; border:none;")
    return line


def spacer(h: int = 0) -> QWidget:
    w = QWidget()
    w.setSizePolicy(QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed if h else QSizePolicy.Policy.Expanding)
    if h:
        w.setFixedHeight(h)
    w.setObjectName("Spacer")
    w.setStyleSheet("#Spacer { background: transparent; }")
    return w


def fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if pd.isna(v):
            return "—"
        if abs(v) >= 1e7 or (v != 0 and abs(v) < 1e-4):
            return f"{v:,.3e}"
        return f"{v:,.{digits}f}".rstrip("0").rstrip(".") or "0"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    return str(v)


class Card(QFrame):
    """Sarlavhali karta konteyner."""

    def __init__(self, title: str = "", hint: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        if title:
            head = QHBoxLayout()
            head.setSpacing(8)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("CardTitle")
            head.addWidget(self.title_label)
            if hint:
                lbl = QLabel(hint)
                lbl.setObjectName("CardHint")
                head.addWidget(lbl)
            head.addStretch(1)
            self.header = head
            outer.addLayout(head)

        self.body = QVBoxLayout()
        self.body.setSpacing(9)
        outer.addLayout(self.body)

    def add(self, widget: QWidget) -> QWidget:
        self.body.addWidget(widget)
        return widget

    def add_layout(self, layout) -> Any:
        self.body.addLayout(layout)
        return layout

    def add_header_widget(self, widget: QWidget) -> QWidget:
        if hasattr(self, "header"):
            self.header.addWidget(widget)
        return widget


class StatTile(QFrame):
    """Ko'rsatkich kartochkasi: kalit, qiymat, izoh."""

    def __init__(self, key: str, value: str = "—", delta: str = "",
                 accent: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 12, 15, 13)
        lay.setSpacing(3)
        self.key_label = QLabel(key.upper())
        self.key_label.setObjectName("StatKey")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        if accent:
            self.value_label.setStyleSheet(f"color:{accent}; background:transparent;")
        self.delta_label = QLabel(delta)
        self.delta_label.setObjectName("StatDelta")
        lay.addWidget(self.key_label)
        lay.addWidget(self.value_label)
        lay.addWidget(self.delta_label)
        self.setMinimumWidth(140)

    def set_value(self, value: str, delta: str = "", accent: str | None = None) -> None:
        self.value_label.setText(str(value))
        self.delta_label.setText(delta)
        if accent:
            self.value_label.setStyleSheet(f"color:{accent}; background:transparent;")


class PageHeader(QWidget):
    """Sahifa sarlavhasi va tavsifi."""

    def __init__(self, title: str, subtitle: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.sub_label = QLabel(subtitle)
        self.sub_label.setObjectName("PageSub")
        self.sub_label.setWordWrap(True)
        lay.addWidget(self.title_label)
        lay.addWidget(self.sub_label)

    def set_subtitle(self, text: str) -> None:
        self.sub_label.setText(text)


class Toast(QFrame):
    """Ekran pastida qisqa vaqt ko'rinadigan xabar."""

    LEVEL_COLOR = {
        "info": PALETTE["accent"], "success": PALETTE["success"],
        "warn": PALETTE["warning"], "error": PALETTE["danger"],
    }

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        self.dot = QLabel("●")
        self.label = QLabel("")
        self.label.setStyleSheet("background: transparent;")
        lay.addWidget(self.dot)
        lay.addWidget(self.label)
        self.hide()
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._anim.finished.connect(self._on_anim_finished)
        self._hide_after_anim = False

    def show_message(self, text: str, level: str = "info", msec: int = 3200) -> None:
        color = self.LEVEL_COLOR.get(level, PALETTE["accent"])
        self.dot.setStyleSheet(f"color:{color}; background: transparent; font-size:15px;")
        self.label.setText(text[:220])
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._anim.stop()
        self._hide_after_anim = False
        self._anim.setStartValue(self._effect.opacity() if self.isVisible() else 0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(msec)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._hide_after_anim = True
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._hide_after_anim:
            self.hide()
            self._hide_after_anim = False

    def _reposition(self) -> None:
        if self.parentWidget():
            pw = self.parentWidget()
            self.move(max(12, (pw.width() - self.width()) // 2), pw.height() - self.height() - 28)


# ---------------------------------------------------------------------------
# Jadval modeli
# ---------------------------------------------------------------------------
class DataFrameModel(QAbstractTableModel):
    """DataFrame'ni QTableView'ga tahrirlash imkoniyati bilan bog'laydi."""

    edit_requested = Signal(int, str, object)   # (qator, ustun, yangi qiymat)

    def __init__(self, df: pd.DataFrame | None = None, editable: bool = True,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._df = df if df is not None else pd.DataFrame()
        self._view = self._df.head(PREVIEW_ROWS)
        self.editable = editable
        self._colors: dict[str, dict[Any, QColor]] = {}
        self._kinds: dict[str, str] = {}
        self._numeric_ranges: dict[str, tuple[float, float]] = {}
        self.heat_column: str | None = None
        self._refresh_hints()

    # ---- ma'lumot
    def set_df(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df if df is not None else pd.DataFrame()
        self._view = self._df.head(PREVIEW_ROWS)
        self._refresh_hints()
        self.endResetModel()

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _refresh_hints(self) -> None:
        self._kinds.clear()
        self._numeric_ranges.clear()
        for c in self._view.columns:
            kind = column_kind(self._view[c])
            self._kinds[str(c)] = kind
            if kind == NUMERIC:
                s = pd.to_numeric(self._view[c], errors="coerce")
                lo, hi = s.min(), s.max()
                if pd.notna(lo) and pd.notna(hi) and hi > lo:
                    self._numeric_ranges[str(c)] = (float(lo), float(hi))

    # ---- Qt interfeysi
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._view)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else self._view.shape[1]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self._view) or col >= self._view.shape[1]:
            return None
        colname = str(self._view.columns[col])
        value = self._view.iat[row, col]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            if value is None or (not isinstance(value, (list, dict, np.ndarray))
                                 and pd.isna(value)):
                return "" if role == Qt.ItemDataRole.DisplayRole else "bo'sh (NaN)"
            if isinstance(value, float):
                return fmt_num(value, 4)
            if isinstance(value, pd.Timestamp):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            text = str(value)
            return text if role == Qt.ItemDataRole.ToolTipRole else text[:300]

        if role == Qt.ItemDataRole.EditRole:
            return "" if pd.isna(value) else str(value)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if self._kinds.get(colname) == NUMERIC:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ForegroundRole:
            if value is None or (not isinstance(value, (list, dict, np.ndarray))
                                 and pd.isna(value)):
                return QColor(PALETTE["faint"])
            if colname.lower() in ("level", "severity", "holat", "status"):
                color = LEVEL_COLORS.get(str(value).upper())
                if color:
                    return QColor(color)
            return None

        if role == Qt.ItemDataRole.BackgroundRole and self.heat_column == colname:
            rng = self._numeric_ranges.get(colname)
            if rng and not pd.isna(value):
                lo, hi = rng
                try:
                    ratio = (float(value) - lo) / (hi - lo)
                except (TypeError, ValueError):
                    return None
                return QColor(76, 154, 255, int(20 + 110 * max(0.0, min(1.0, ratio))))
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,  # noqa: N802
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if section >= self._view.shape[1]:
                return None
            name = str(self._view.columns[section])
            if role == Qt.ItemDataRole.DisplayRole:
                return name
            if role == Qt.ItemDataRole.ToolTipRole:
                s = self._view.iloc[:, section]
                kind = self._kinds.get(name, "")
                return (f"{name}\nturi: {kind} ({s.dtype})\n"
                        f"bo'sh: {int(s.isna().sum()):,}\nunikal: {s.nunique():,}")
            if role == Qt.ItemDataRole.FontRole:
                f = QFont()
                f.setBold(True)
                return f
        elif orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = (Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        if self.editable:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value: Any,  # noqa: N802
                role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        colname = str(self._view.columns[index.column()])
        self.edit_requested.emit(index.row(), colname, value)
        return True

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if column >= self._view.shape[1]:
            return
        name = self._view.columns[column]
        self.beginResetModel()
        try:
            self._view = self._view.sort_values(
                name, ascending=order == Qt.SortOrder.AscendingOrder, kind="stable")
        except Exception:
            pass
        self.endResetModel()


class FrameTable(QTableView):
    """DataFrame ko'rsatish uchun sozlangan jadval."""

    column_action = Signal(str, str)   # (amal, ustun)

    def __init__(self, editable: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model_ = DataFrameModel(editable=editable, parent=self)
        self.setModel(self.model_)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setWordWrap(False)
        self.verticalHeader().setDefaultSectionSize(28)
        self.verticalHeader().setVisible(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._header_menu)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._cell_menu)

    def set_df(self, df: pd.DataFrame, autosize: bool = True) -> None:
        self.model_.set_df(df)
        if autosize:
            self.resize_columns()

    def resize_columns(self, max_width: int = 320) -> None:
        self.resizeColumnsToContents()
        for i in range(self.model_.columnCount()):
            if self.columnWidth(i) > max_width:
                self.setColumnWidth(i, max_width)
            elif self.columnWidth(i) < 70:
                self.setColumnWidth(i, 70)

    def current_column(self) -> str | None:
        idx = self.currentIndex()
        if idx.isValid() and idx.column() < self.model_.columnCount():
            return str(self.model_.df.columns[idx.column()])
        return None

    def selected_rows(self) -> list[int]:
        return sorted({i.row() for i in self.selectionModel().selectedIndexes()})

    def _header_menu(self, pos) -> None:
        col_idx = self.horizontalHeader().logicalIndexAt(pos)
        if col_idx < 0 or col_idx >= self.model_.columnCount():
            return
        name = str(self.model_.df.columns[col_idx])
        menu = QMenu(self)
        for label, key in (
            ("O'sish bo'yicha saralash", "sort_asc"),
            ("Kamayish bo'yicha saralash", "sort_desc"),
            (None, None),
            ("Nomini o'zgartirish…", "rename"),
            ("Turini o'zgartirish…", "astype"),
            ("Bo'shliklarni to'ldirish…", "fillna"),
            (None, None),
            ("Issiqlik bo'yashini yoqish", "heat"),
            ("Statistikani ko'rsatish", "stats"),
            (None, None),
            ("Ustunni nusxalash", "copy"),
            ("Ustunni o'chirish", "drop"),
        ):
            if label is None:
                menu.addSeparator()
                continue
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, k=key, n=name: self.column_action.emit(k, n))
            menu.addAction(act)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _cell_menu(self, pos) -> None:
        menu = QMenu(self)
        act_copy = QAction("Nusxalash (Ctrl+C)", self)
        act_copy.triggered.connect(self.copy_selection)
        menu.addAction(act_copy)
        act_rows = QAction("Tanlangan qatorlarni o'chirish", self)
        act_rows.triggered.connect(lambda: self.column_action.emit("drop_rows", ""))
        menu.addAction(act_rows)
        menu.addSeparator()
        act_filter = QAction("Shu qiymat bo'yicha filtrlash", self)
        act_filter.triggered.connect(lambda: self.column_action.emit("filter_value", ""))
        menu.addAction(act_filter)
        menu.exec(self.viewport().mapToGlobal(pos))

    def copy_selection(self) -> None:
        idxs = self.selectionModel().selectedIndexes()
        if not idxs:
            return
        rows = sorted({i.row() for i in idxs})
        cols = sorted({i.column() for i in idxs})
        lines = []
        for r in rows:
            vals = []
            for c in cols:
                idx = self.model_.index(r, c)
                vals.append(str(self.model_.data(idx, Qt.ItemDataRole.DisplayRole) or ""))
            lines.append("\t".join(vals))
        QGuiApplication.clipboard().setText("\n".join(lines))

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.matches(Qt.Key.Key_Copy if hasattr(Qt.Key, "Key_Copy") else 0):
            self.copy_selection()
            return
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and event.key() == Qt.Key.Key_C):
            self.copy_selection()
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Ustun tanlagichlar
# ---------------------------------------------------------------------------
KIND_FILTERS = {
    "any": lambda s: True,
    "num": lambda s: column_kind(s) == NUMERIC,
    "cat": lambda s: column_kind(s) in (CATEGORICAL, "mantiqiy"),
    "dt": lambda s: column_kind(s) == DATETIME,
    "text": lambda s: column_kind(s) in ("matn", CATEGORICAL),
}


class ColumnCombo(QComboBox):
    """Ustun tanlash uchun ochiluvchi ro'yxat (tur bo'yicha filtrlanadi)."""

    def __init__(self, kind: str = "any", allow_empty: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.allow_empty = allow_empty
        self.setMinimumWidth(150)

    def populate(self, df: pd.DataFrame, keep: bool = True) -> None:
        prev = self.currentText()
        self.blockSignals(True)
        self.clear()
        if self.allow_empty:
            self.addItem("—")
        test = KIND_FILTERS.get(self.kind, KIND_FILTERS["any"])
        for c in df.columns:
            try:
                if test(df[c]):
                    self.addItem(str(c))
            except Exception:
                continue
        if keep and prev:
            i = self.findText(prev)
            if i >= 0:
                self.setCurrentIndex(i)
        self.blockSignals(False)

    def value(self) -> str | None:
        txt = self.currentText()
        return None if txt in ("", "—") else txt


class MultiColumnSelect(QWidget):
    """Ko'p ustun tanlash — qidiruv va 'hammasi' tugmasi bilan."""

    changed = Signal()

    def __init__(self, kind: str = "any", height: int = 150,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Ustun qidirish…")
        self.search.textChanged.connect(self._filter)
        btn_all = QPushButton("Hammasi")
        btn_all.setObjectName("Chip")
        btn_all.clicked.connect(lambda: self.set_all(True))
        btn_none = QPushButton("Tozalash")
        btn_none.setObjectName("Chip")
        btn_none.clicked.connect(lambda: self.set_all(False))
        top.addWidget(self.search, 1)
        top.addWidget(btn_all)
        top.addWidget(btn_none)
        lay.addLayout(top)

        self.list = QListWidget()
        self.list.setFixedHeight(height)
        self.list.itemChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self.list)

    def populate(self, df: pd.DataFrame, checked: Iterable[str] | None = None) -> None:
        prev = set(self.values()) if self.list.count() else set(checked or [])
        self.list.blockSignals(True)
        self.list.clear()
        test = KIND_FILTERS.get(self.kind, KIND_FILTERS["any"])
        for c in df.columns:
            try:
                if not test(df[c]):
                    continue
            except Exception:
                continue
            item = QListWidgetItem(str(c))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if str(c) in prev
                               else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _filter(self, text: str) -> None:
        text = text.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text not in item.text().lower())

    def set_all(self, checked: bool) -> None:
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked if checked
                                   else Qt.CheckState.Unchecked)
        self.list.blockSignals(False)
        self.changed.emit()

    def values(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def set_values(self, names: Iterable[str]) -> None:
        want = set(names)
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setCheckState(Qt.CheckState.Checked if item.text() in want
                               else Qt.CheckState.Unchecked)
        self.list.blockSignals(False)
        self.changed.emit()


# ---------------------------------------------------------------------------
# Grafik kanvasi
# ---------------------------------------------------------------------------
class ChartCanvas(QWidget):
    """Matplotlib figurasini ko'rsatuvchi vidjet (navigatsiya paneli bilan)."""

    def __init__(self, parent: QWidget | None = None, toolbar: bool = True) -> None:
        super().__init__(parent)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.backends.backend_qtagg import \
            NavigationToolbar2QT as NavToolbar
        from matplotlib.figure import Figure

        self._FigureCanvas = FigureCanvasQTAgg
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor(PALETTE["surface"])
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet(f"background:{PALETTE['surface']};")

        self.toolbar = None
        if toolbar:
            self.toolbar = NavToolbar(self.canvas, self)
            self.toolbar.setStyleSheet(
                f"QToolBar{{background:{PALETTE['surface2']}; border:none;"
                f"border-radius:8px; padding:2px;}}"
                f"QToolButton{{color:{PALETTE['muted']};}}"
                f"QLabel{{color:{PALETTE['muted']}; font-size:11px;}}")
            lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, 1)
        self.show_message("Grafik qurish uchun sozlamalarni tanlang")

    def set_figure(self, fig) -> None:
        """Yangi figurani ko'rsatadi (eskisini almashtiradi)."""
        lay = self.layout()
        old = self.canvas
        self.figure = fig
        self.canvas = self._FigureCanvas(fig)
        self.canvas.setStyleSheet(f"background:{PALETTE['surface']};")
        lay.replaceWidget(old, self.canvas)
        old.setParent(None)
        old.deleteLater()
        if self.toolbar is not None:
            from matplotlib.backends.backend_qtagg import \
                NavigationToolbar2QT as NavToolbar

            new_tb = NavToolbar(self.canvas, self)
            new_tb.setStyleSheet(self.toolbar.styleSheet())
            lay.replaceWidget(self.toolbar, new_tb)
            self.toolbar.setParent(None)
            self.toolbar.deleteLater()
            self.toolbar = new_tb
        self.canvas.draw_idle()

    def show_message(self, text: str) -> None:
        from matplotlib.figure import Figure

        fig = Figure(figsize=(8, 5), dpi=100)
        fig.patch.set_facecolor(PALETTE["surface"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(PALETTE["surface"])
        ax.text(0.5, 0.5, text, ha="center", va="center",
                color=PALETTE["muted"], fontsize=12, wrap=True)
        ax.set_axis_off()
        self.set_figure(fig)

    def save(self, path: str, dpi: int = 150) -> None:
        self.figure.savefig(path, dpi=dpi, bbox_inches="tight",
                            facecolor=self.figure.get_facecolor())

    def copy_to_clipboard(self) -> None:
        import io

        from PySide6.QtGui import QImage

        buf = io.BytesIO()
        self.figure.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                            facecolor=self.figure.get_facecolor())
        img = QImage.fromData(buf.getvalue())
        QGuiApplication.clipboard().setImage(img)


class ScrollPage(QScrollArea):
    """Vertikal scroll qilinadigan sahifa konteyneri."""

    def __init__(self, parent: QWidget | None = None, margins=(20, 18, 20, 20),
                 spacing: int = 14) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inner = QWidget()
        # Uslub faqat shu konteynerga tegishli bo'lishi kerak — aks holda u
        # ichidagi tugmalarning fonini ham shaffof qilib yuboradi.
        inner.setObjectName("ScrollInner")
        inner.setStyleSheet("#ScrollInner { background: transparent; }")
        self.vbox = QVBoxLayout(inner)
        self.vbox.setContentsMargins(*margins)
        self.vbox.setSpacing(spacing)
        self.setWidget(inner)

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self.vbox.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout) -> Any:
        self.vbox.addLayout(layout)
        return layout

    def add_stretch(self) -> None:
        self.vbox.addStretch(1)


def make_button(text: str, kind: str = "", on_click: Callable[[], None] | None = None,
                tooltip: str = "", width: int | None = None) -> QPushButton:
    btn = QPushButton(text)
    if kind:
        btn.setObjectName(kind)
    if on_click:
        btn.clicked.connect(lambda: on_click())
    if tooltip:
        btn.setToolTip(tooltip)
    if width:
        btn.setMinimumWidth(width)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def make_checkbox(text: str, checked: bool = False,
                  on_change: Callable[[bool], None] | None = None) -> QCheckBox:
    cb = QCheckBox(text)
    cb.setChecked(checked)
    if on_change:
        cb.toggled.connect(on_change)
    return cb


def icon_size(w: int = 18, h: int = 18) -> QSize:
    return QSize(w, h)


class WheelGuard(QObject):
    """Fokusda bo'lmagan combobox/spinbox g'ildirak bilan o'zgarmasin.

    Scroll qilinadigan panellarda sichqoncha g'ildiragi ostidagi ochiluvchi
    ro'yxat qiymatini tasodifan almashtirib yuborishi oldini oladi.
    """

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QAbstractSpinBox, QComboBox

        if event.type() == QEvent.Type.Wheel and isinstance(
                obj, (QComboBox, QAbstractSpinBox)):
            if not obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
