# -*- coding: utf-8 -*-
"""
Qayta ishlatiladigan GUI komponentlari: stat karta, grafik panellari,
jadval sahifasi (xizmatdan avtomatik to'ldiriladi).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

from src.core.utils import money
from src.ui.qt_compat import (
    HAS_CHARTS, Qt, QtCore, QtGui, QtWidgets,
)
from src.ui.theme_qss import COLORS

if HAS_CHARTS:
    from src.ui.qt_compat import (
        QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView,
        QLineSeries, QPieSeries, QValueAxis,
    )


def make_card(child: QtWidgets.QWidget, padding: int = 16) -> QtWidgets.QFrame:
    """Widget'ni kartochka ramkasiga o'raydi."""
    card = QtWidgets.QFrame()
    card.setObjectName("Card")
    layout = QtWidgets.QVBoxLayout(card)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.addWidget(child)
    return card


class StatCard(QtWidgets.QFrame):
    """KPI kartochkasi: yorliq, katta qiymat, izoh."""

    def __init__(self, label: str, value: str, sub: str = "",
                 accent: str = "text") -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(3)

        lbl = QtWidgets.QLabel(label)
        lbl.setObjectName("StatLabel")
        self.value_lbl = QtWidgets.QLabel(value)
        self.value_lbl.setObjectName("StatValue")
        self.value_lbl.setStyleSheet(
            f"color: {COLORS.get(accent, COLORS['text'])};")
        layout.addWidget(lbl)
        layout.addWidget(self.value_lbl)
        if sub:
            sub_lbl = QtWidgets.QLabel(sub)
            sub_lbl.setObjectName("StatSub")
            layout.addWidget(sub_lbl)

    def set_value(self, value: str) -> None:
        """Qiymatni yangilaydi (dashboard yangilanishida)."""
        self.value_lbl.setText(value)


def line_chart(title: str, labels: Sequence[str],
               series_data: list[tuple[str, list, str]]) -> QtWidgets.QWidget:
    """
    Chiziqli grafik (QtCharts). ``series_data``: (nom, qiymatlar, rang).

    QtCharts mavjud bo'lmasa oddiy matnli xabar qaytaradi.
    """
    if not HAS_CHARTS:
        return _no_charts_placeholder(title)

    chart = QChart()
    chart.setTitle(title)
    chart.setBackgroundBrush(QtGui.QColor(COLORS["panel"]))
    chart.setTitleBrush(QtGui.QColor(COLORS["text"]))
    chart.legend().setLabelColor(QtGui.QColor(COLORS["muted"]))

    max_val = 1.0
    for name, values, color in series_data:
        line = QLineSeries()
        line.setName(name)
        pen = QtGui.QPen(QtGui.QColor(color))
        pen.setWidth(2)
        line.setPen(pen)
        for i, v in enumerate(values):
            fv = float(v or 0)
            line.append(i, fv)
            max_val = max(max_val, fv)
        chart.addSeries(line)

    axis_x = QBarCategoryAxis()
    axis_x.append([str(l) for l in labels])
    axis_x.setLabelsColor(QtGui.QColor(COLORS["muted"]))
    axis_x.setGridLineColor(QtGui.QColor(COLORS["border"]))
    axis_y = QValueAxis()
    axis_y.setRange(0, max_val * 1.1)
    axis_y.setLabelsColor(QtGui.QColor(COLORS["muted"]))
    axis_y.setGridLineColor(QtGui.QColor(COLORS["border"]))
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    for s in chart.series():
        s.attachAxis(axis_x)
        s.attachAxis(axis_y)

    view = QChartView(chart)
    view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(260)
    return view


def bar_chart(title: str, labels: Sequence[str],
              values: list, color: str) -> QtWidgets.QWidget:
    """Ustunli grafik (QtCharts)."""
    if not HAS_CHARTS:
        return _no_charts_placeholder(title)

    chart = QChart()
    chart.setTitle(title)
    chart.setBackgroundBrush(QtGui.QColor(COLORS["panel"]))
    chart.setTitleBrush(QtGui.QColor(COLORS["text"]))
    chart.legend().hide()

    bar_set = QBarSet("")
    bar_set.setColor(QtGui.QColor(color))
    max_val = 1.0
    for v in values:
        fv = float(v or 0)
        bar_set.append(fv)
        max_val = max(max_val, fv)
    series = QBarSeries()
    series.append(bar_set)
    chart.addSeries(series)

    axis_x = QBarCategoryAxis()
    axis_x.append([str(l) for l in labels])
    axis_x.setLabelsColor(QtGui.QColor(COLORS["muted"]))
    axis_y = QValueAxis()
    axis_y.setRange(0, max_val * 1.1)
    axis_y.setLabelsColor(QtGui.QColor(COLORS["muted"]))
    axis_y.setGridLineColor(QtGui.QColor(COLORS["border"]))
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)

    view = QChartView(chart)
    view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(260)
    return view


def pie_chart(title: str, items: list[tuple[str, float]]) -> QtWidgets.QWidget:
    """Doiraviy diagramma (QtCharts)."""
    if not HAS_CHARTS:
        return _no_charts_placeholder(title)
    palette = [COLORS["accent"], COLORS["green"], COLORS["amber"],
               COLORS["red"], COLORS["violet"], "#22d3ee"]
    chart = QChart()
    chart.setTitle(title)
    chart.setBackgroundBrush(QtGui.QColor(COLORS["panel"]))
    chart.setTitleBrush(QtGui.QColor(COLORS["text"]))
    chart.legend().setLabelColor(QtGui.QColor(COLORS["muted"]))

    series = QPieSeries()
    for idx, (label, value) in enumerate(items):
        slice_ = series.append(label, float(value or 0))
        slice_.setColor(QtGui.QColor(palette[idx % len(palette)]))
        slice_.setLabelColor(QtGui.QColor(COLORS["muted"]))
    chart.addSeries(series)
    view = QChartView(chart)
    view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(260)
    return view


def _no_charts_placeholder(title: str) -> QtWidgets.QWidget:
    """QtCharts o'rnatilmagan bo'lsa ko'rsatiladigan panel."""
    lbl = QtWidgets.QLabel(
        f"{title}\n\n(QtCharts o'rnatilmagan — grafiklar web "
        "interfeysida to'liq ko'rinadi)")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"color: {COLORS['muted']}; padding: 40px;")
    return make_card(lbl)


class TablePage(QtWidgets.QWidget):
    """
    Umumiy jadval sahifasi: qidiruv + jadval + yangilash tugmasi.

    Ma'lumot ``loader(search) -> (headers, rows)`` funksiyasidan olinadi.
    """

    def __init__(self, title: str,
                 loader: Callable[[str], tuple[list[str], list[list]]],
                 searchable: bool = True) -> None:
        super().__init__()
        self._loader = loader
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Sarlavha qatori
        header = QtWidgets.QHBoxLayout()
        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setObjectName("PageTitle")
        header.addWidget(title_lbl)
        header.addStretch()

        if searchable:
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Qidiruv...")
            self.search.setFixedWidth(240)
            self.search.textChanged.connect(self.reload)
            header.addWidget(self.search)
        else:
            self.search = None

        refresh = QtWidgets.QPushButton("↻ Yangilash")
        refresh.clicked.connect(self.reload)
        header.addWidget(refresh)
        layout.addLayout(header)

        self.table = QtWidgets.QTableWidget()
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.reload()

    def reload(self) -> None:
        """Ma'lumotni loader'dan qayta yuklaydi."""
        search = self.search.text() if self.search else ""
        try:
            headers, rows = self._loader(search)
        except Exception as exc:  # noqa: BLE001
            headers, rows = ["Xato"], [[str(exc)]]

        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(_fmt(value))
                if isinstance(value, (int, float, Decimal)):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()


def _fmt(value) -> str:
    """Katak qiymatini matnga aylantiradi."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return money(value)
    return str(value)
