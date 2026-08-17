#!/usr/bin/env python3
"""
GCOM Signal Monitor - desktop dashboard (PyQt6 + pyqtgraph + pandas).

gcom_signal_logger/logger.py yozib borayotgan CSV log faylini real vaqtda
o'qib, quyidagilarni bitta desktop oynada ko'rsatadi:
  - Jonli monitoring: joriy holat kartalari + RSRP/RSRQ/SINR trendlari
  - Statistika: tanlangan vaqt oynasi bo'yicha min/max/o'rtacha/median/std/
    p5/p95, taqsimot gistogrammalari, ko'rsatkichlar orasidagi korrelyatsiya
  - Band tahlili: har bir diapazonda o'tkazilgan vaqt va o'rtacha signal sifati
  - Hodisalar: uzilish/qayta ulanish/handover/band va CA o'zgarishi/sifat
    pasayishi avtomatik aniqlanadigan xronologik jurnal
  - Trafik: kumulyativ trafik va baholangan tezlik (MB/daqiqa)

Ishga tushirish:
    python main.py
    python main.py --logfile "..\\gcom_signal_logger\\gcom_signal_log.csv"
"""

import argparse
import configparser
import csv
import os
import sys
from pathlib import Path

# Fraksion Windows DPI masshtabida (125%/150% va h.k.) oyna maksimallashtirilganda
# yorliq matnlari bir-birining ustiga tushib qolishining oldini oladi - PyQt6'ning
# Qt::HighDpiScaleFactorRoundingPolicy::Round (standart) siyosati bilan bog'liq
# taniqli muammo. QApplication yaratilishidan OLDIN o'rnatilishi shart.
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import analytics

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = SCRIPT_DIR / "config.ini"

ACCENT = {
    "rsrp": "#ff9f43",
    "rsrq": "#a29bfe",
    "sinr": "#1dd1a1",
    "rssi": "#54a0ff",
    "band": "#feca57",
    "bad": "#ff6b6b",
    "ok": "#1dd1a1",
    "info": "#54a0ff",
    "warning": "#feca57",
    "text": "#e0e0e0",
    "muted": "#8a8a8a",
    "bg": "#121212",
    "card": "#1b1b1f",
}

SEVERITY_COLOR = {
    "info": ACCENT["info"],
    "success": ACCENT["ok"],
    "warning": ACCENT["warning"],
    "critical": ACCENT["bad"],
}

WINDOW_OPTIONS = {
    "Barchasi": None,
    "So'nggi 10 daqiqa": 10,
    "So'nggi 1 soat": 60,
    "So'nggi 24 soat": 60 * 24,
}


def load_config(path: Path) -> dict:
    cfg = {
        "logfile": str(SCRIPT_DIR.parent / "gcom_signal_logger" / "gcom_signal_log.csv"),
        "poll_interval_ms": 3000,
        "live_window_points": 500,
        "max_stored_rows": 200000,
    }
    if path.exists():
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8")
        if "dashboard" in parser:
            section = parser["dashboard"]
            cfg["logfile"] = section.get("logfile", cfg["logfile"])
            cfg["poll_interval_ms"] = section.getint("poll_interval_ms", cfg["poll_interval_ms"])
            cfg["live_window_points"] = section.getint("live_window_points", cfg["live_window_points"])
            cfg["max_stored_rows"] = section.getint("max_stored_rows", cfg["max_stored_rows"])

    logfile_path = Path(cfg["logfile"])
    if not logfile_path.is_absolute():
        logfile_path = (SCRIPT_DIR / logfile_path).resolve()
    cfg["logfile"] = str(logfile_path)
    return cfg


def format_duration(seconds) -> str:
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt(value, digits=1) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    return f"{value:.{digits}f}"


class SignalReader:
    """CSV log faylini vaqti bilan o'sib boruvchi holatda o'qiydi - har chaqiriqda
    faqat oxirgi o'qishdan keyin qo'shilgan qatorlarni qaytaradi."""

    def __init__(self, logfile: Path):
        self.logfile = logfile
        self._rows_seen = 0

    def poll_new_rows(self) -> list:
        if not self.logfile.exists():
            return []
        try:
            with open(self.logfile, encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        except (OSError, csv.Error):
            return []

        if len(rows) < self._rows_seen:
            self._rows_seen = 0

        new_rows = rows[self._rows_seen :]
        self._rows_seen = len(rows)
        return new_rows


class StatCard(QFrame):
    def __init__(self, title: str, accent: str, unit: str = ""):
        super().__init__()
        self.unit = unit
        self.setObjectName("statCard")
        self.setStyleSheet(
            f"""
            QFrame#statCard {{
                background-color: {ACCENT['card']};
                border-left: 4px solid {accent};
                border-radius: 8px;
            }}
            """
        )
        # Qat'iy fiksirlangan balandlik - QGridLayout ko'p qatorli holatda
        # kartalar balandligini "muzokara" qilib noto'g'ri siqib qo'yishi
        # kuzatilgan (shu sabab kartalar endi QHBoxLayout qatorlarida
        # joylashtiriladi, grid emas); bu yerda ham qo'shimcha kafolat sifatida
        # setFixedHeight ishlatiladi - setMinimumHeight'dan farqli o'laroq
        # layout bu qiymatdan pastga HAM, yuqoriga HAM siqib/cho'zib bo'lmaydi.
        self.setFixedHeight(80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet(f"color: {ACCENT['muted']}; letter-spacing: 1px;")
        title_font = QFont()
        title_font.setPointSize(8)
        self.title_label.setFont(title_font)
        self.title_label.setFixedHeight(18)

        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(f"color: {ACCENT['text']}; font-weight: 600;")
        value_font = QFont()
        value_font.setPointSize(15)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setFixedHeight(36)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str, color: str = None):
        text = f"{value} {self.unit}".strip() if value not in (None, "") else "—"
        self.value_label.setText(text)
        self.value_label.setStyleSheet(f"color: {color or ACCENT['text']}; font-weight: 600;")


def quality_color(metric: str, value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ACCENT["muted"]
    thresholds = {
        "rsrp": [(-90, ACCENT["ok"]), (-105, ACCENT["warning"]), (-1e9, ACCENT["bad"])],
        "rsrq": [(-10, ACCENT["ok"]), (-15, ACCENT["warning"]), (-1e9, ACCENT["bad"])],
        "sinr": [(13, ACCENT["ok"]), (0, ACCENT["warning"]), (-1e9, ACCENT["bad"])],
        "rssi": [(20, ACCENT["ok"]), (10, ACCENT["warning"]), (-1e9, ACCENT["bad"])],
    }
    for limit, color in thresholds.get(metric, []):
        if value >= limit:
            return color
    return ACCENT["bad"]


class TrendPlot(pg.PlotWidget):
    def __init__(self, title: str, color: str, y_label: str):
        axis = pg.DateAxisItem(orientation="bottom")
        super().__init__(axisItems={"bottom": axis})
        self.setBackground(ACCENT["bg"])
        self.setTitle(title, color=ACCENT["text"], size="11pt")
        self.setLabel("left", y_label, color=ACCENT["muted"])
        self.showGrid(x=True, y=True, alpha=0.15)
        self.getAxis("left").setTextPen(ACCENT["muted"])
        self.getAxis("bottom").setTextPen(ACCENT["muted"])
        self.curve = self.plot([], [], pen=pg.mkPen(color=color, width=2))

    def update_data(self, xs, ys):
        self.curve.setData(xs, ys)


class HistogramPlot(pg.PlotWidget):
    def __init__(self, title: str, color: str):
        super().__init__()
        self.color = color
        self.setBackground(ACCENT["bg"])
        self.setTitle(title, color=ACCENT["text"], size="10pt")
        self.showGrid(x=True, y=True, alpha=0.1)
        self.getAxis("left").setTextPen(ACCENT["muted"])
        self.getAxis("bottom").setTextPen(ACCENT["muted"])
        self._bar_item = None

    def update_data(self, values: pd.Series):
        self.clear()
        clean = values.dropna()
        if clean.empty:
            return
        counts, edges = np.histogram(clean, bins=min(20, max(5, clean.nunique())))
        widths = np.diff(edges)
        self._bar_item = pg.BarGraphItem(
            x0=edges[:-1], x1=edges[1:], height=counts, brush=pg.mkBrush(self.color), pen=pg.mkPen(None)
        )
        self.addItem(self._bar_item)


class CategoryBarPlot(pg.PlotWidget):
    def __init__(self, title: str, color: str):
        super().__init__()
        self.color = color
        self.setBackground(ACCENT["bg"])
        self.setTitle(title, color=ACCENT["text"], size="10pt")
        self.showGrid(y=True, alpha=0.1)
        self.getAxis("left").setTextPen(ACCENT["muted"])
        self.getAxis("bottom").setTextPen(ACCENT["muted"])

    def update_data(self, labels: list, values: list):
        self.clear()
        if not labels:
            return
        xs = list(range(len(labels)))
        bar = pg.BarGraphItem(x=xs, height=values, width=0.6, brush=pg.mkBrush(self.color), pen=pg.mkPen(None))
        self.addItem(bar)
        self.getAxis("bottom").setTicks([list(zip(xs, labels))])


class MainWindow(QMainWindow):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.reader = SignalReader(Path(cfg["logfile"]))
        self.live_window_points = cfg["live_window_points"]
        self.max_stored_rows = cfg["max_stored_rows"]

        self.df = pd.DataFrame()
        self.detector = analytics.EventDetector()
        self.events = []
        self.stats_window_minutes = None

        self.setWindowTitle("GCOM Signal Monitor")
        self.resize(1280, 860)
        self._build_ui()
        self._apply_dark_theme()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(cfg["poll_interval_ms"])
        self.poll()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("GCOM Signal Monitor")
        title.setStyleSheet(f"color: {ACCENT['text']}; font-size: 18px; font-weight: 700;")
        self.status_label = QLabel("● Kutilmoqda...")
        self.status_label.setStyleSheet(f"color: {ACCENT['muted']}; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)
        root.addLayout(header)

        self.path_label = QLabel(str(self.reader.logfile))
        self.path_label.setStyleSheet(f"color: {ACCENT['muted']}; font-size: 11px;")
        root.addWidget(self.path_label)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self._build_live_tab()
        self._build_stats_tab()
        self._build_band_tab()
        self._build_ca_tab()
        self._build_events_tab()
        self._build_traffic_tab()

    @staticmethod
    def _card_row(cards: list) -> QHBoxLayout:
        """QGridLayout ko'p qatorli holatda satr balandligini noto'g'ri
        taqsimlab, kartalar matnini bir-biriga qo'shib yuborishi kuzatilgan -
        shuning uchun har bir qator alohida QHBoxLayout sifatida quriladi,
        bu holatda balandlik hech qachon boshqa qatorlar bilan
        "muzokara" qilinmaydi."""
        row = QHBoxLayout()
        row.setSpacing(10)
        for card in cards:
            row.addWidget(card)
        return row

    def _build_live_tab(self):
        # QScrollArea'ga o'ralgan: agar kartalar+grafiklarning umumiy talab
        # qilingan balandligi tab ko'rinadigan balandligidan katta bo'lsa, Qt
        # ularni MAJBURIY siqib qo'yishi mumkin edi (grafiklarning pastki vaqt
        # o'qi ko'rinmay qolishiga sabab bo'lgan) - scroll bilan hech narsa
        # hech qachon siqilmaydi, kerak bo'lsa shunchaki pastga aylantiriladi.
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        self.cards = {
            "state": StatCard("Holat", ACCENT["ok"]),
            "network_type": StatCard("Tarmoq turi", ACCENT["band"]),
            "band": StatCard("Diapazon", ACCENT["band"]),
            "rssi": StatCard("RSSI", ACCENT["rssi"]),
            "rsrp": StatCard("RSRP", ACCENT["rsrp"], "dBm"),
            "rsrq": StatCard("RSRQ", ACCENT["rsrq"], "dB"),
            "sinr": StatCard("SINR", ACCENT["sinr"], "dB"),
            "scc_count": StatCard("SCC soni", "#48dbfb"),
            "external_ip": StatCard("Tashqi IP", ACCENT["muted"]),
            "connection_uptime": StatCard("Ulanish vaqti", ACCENT["muted"]),
            "bandwidth": StatCard("Kanal kengligi (UL/DL)", ACCENT["muted"]),
            "traffic": StatCard("Trafik (TX/RX)", ACCENT["muted"]),
        }
        card_list = list(self.cards.values())
        for start in range(0, len(card_list), 4):
            layout.addLayout(self._card_row(card_list[start : start + 4]))

        # --- Carrier aggregation komponentlari (PCC + SCC1..4) ---
        ca_label = QLabel("Component carrier'lar (PCC / SCC)")
        ca_label.setStyleSheet(f"color: {ACCENT['text']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(ca_label)
        self.carrier_cards = {
            "pcc": StatCard("PCC (asosiy)", "#48dbfb"),
            "scc1": StatCard("SCC1", "#48dbfb"),
            "scc2": StatCard("SCC2", "#48dbfb"),
            "scc3": StatCard("SCC3", "#48dbfb"),
            "scc4": StatCard("SCC4", "#48dbfb"),
        }
        layout.addLayout(self._card_row(list(self.carrier_cards.values())))

        self.plot_rsrp = TrendPlot("RSRP", ACCENT["rsrp"], "dBm")
        self.plot_rsrq = TrendPlot("RSRQ", ACCENT["rsrq"], "dB")
        self.plot_sinr = TrendPlot("SINR", ACCENT["sinr"], "dB")
        for p in (self.plot_rsrp, self.plot_rsrq, self.plot_sinr):
            p.setFixedHeight(220)
            layout.addWidget(p)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tabs.addTab(scroll, "Jonli monitoring")

    def _build_stats_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        controls = QHBoxLayout()
        label = QLabel("Vaqt oynasi:")
        label.setStyleSheet(f"color: {ACCENT['text']};")
        self.window_combo = QComboBox()
        self.window_combo.addItems(list(WINDOW_OPTIONS.keys()))
        self.window_combo.currentTextChanged.connect(self._on_window_changed)
        controls.addWidget(label)
        controls.addWidget(self.window_combo)
        controls.addStretch()
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.stats_table = QTableWidget(4, 8)
        self.stats_table.setHorizontalHeaderLabels(["Ko'rsatkich", "Soni", "Min", "Max", "O'rtacha", "Median", "Std", "P5 / P95"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, metric in enumerate(["RSSI", "RSRP", "RSRQ", "SINR"]):
            self.stats_table.setItem(row, 0, QTableWidgetItem(metric))
        splitter.addWidget(self.stats_table)

        self.corr_table = QTableWidget(4, 4)
        labels = ["RSSI", "RSRP", "RSRQ", "SINR"]
        self.corr_table.setHorizontalHeaderLabels(labels)
        self.corr_table.setVerticalHeaderLabels(labels)
        self.corr_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.corr_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        splitter.addWidget(self.corr_table)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        hist_layout = QHBoxLayout()
        self.hist_rsrp = HistogramPlot("RSRP taqsimoti", ACCENT["rsrp"])
        self.hist_rsrq = HistogramPlot("RSRQ taqsimoti", ACCENT["rsrq"])
        self.hist_sinr = HistogramPlot("SINR taqsimoti", ACCENT["sinr"])
        for p in (self.hist_rsrp, self.hist_rsrq, self.hist_sinr):
            p.setMinimumHeight(180)
            hist_layout.addWidget(p)
        layout.addLayout(hist_layout)

        self.tabs.addTab(tab, "Statistika")

    def _build_band_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        self.band_table = QTableWidget(0, 7)
        self.band_table.setHorizontalHeaderLabels(
            ["Band", "Namunalar", "Vaqt ulushi %", "O'rt RSRP", "O'rt RSRQ", "O'rt SINR", "O'rt RSSI"]
        )
        self.band_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.band_table.verticalHeader().setVisible(False)
        self.band_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.band_table, stretch=1)

        self.band_bar = CategoryBarPlot("Band bo'yicha o'rtacha RSRP (dBm)", ACCENT["rsrp"])
        self.band_bar.setMinimumHeight(220)
        layout.addWidget(self.band_bar)

        self.tabs.addTab(tab, "Band tahlili")

    def _build_ca_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        self.scc_trend = TrendPlot("Faol carrier'lar soni (1=PCC + SCC soni)", "#48dbfb", "carrier soni")
        self.scc_trend.setMinimumHeight(150)
        layout.addWidget(self.scc_trend)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        combo_widget = QWidget()
        combo_layout = QVBoxLayout(combo_widget)
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_label = QLabel("CA konfiguratsiyalari (band kombinatsiyasi bo'yicha)")
        combo_label.setStyleSheet(f"color: {ACCENT['text']}; font-size: 13px; font-weight: 600;")
        self.ca_combo_table = QTableWidget(0, 4)
        self.ca_combo_table.setHorizontalHeaderLabels(["Kombinatsiya", "Soni", "Vaqt ulushi %", "O'rt RSRP / SINR"])
        self.ca_combo_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ca_combo_table.verticalHeader().setVisible(False)
        self.ca_combo_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        combo_layout.addWidget(combo_label)
        combo_layout.addWidget(self.ca_combo_table)
        splitter.addWidget(combo_widget)

        freq_widget = QWidget()
        freq_layout = QVBoxLayout(freq_widget)
        freq_layout.setContentsMargins(0, 0, 0, 0)
        freq_label = QLabel("Diapazonlar CA'da qanchalik faol ishtirok etadi")
        freq_label.setStyleSheet(f"color: {ACCENT['text']}; font-size: 13px; font-weight: 600;")
        self.carrier_freq_table = QTableWidget(0, 4)
        self.carrier_freq_table.setHorizontalHeaderLabels(["Band", "PCC sifatida", "SCC sifatida", "Jami"])
        self.carrier_freq_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.carrier_freq_table.verticalHeader().setVisible(False)
        self.carrier_freq_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.carrier_freq_table)
        splitter.addWidget(freq_widget)

        layout.addWidget(splitter, stretch=1)

        self.scc_dist_bar = CategoryBarPlot("Bir vaqtdagi carrier soni taqsimoti (vaqt ulushi %)", "#48dbfb")
        self.scc_dist_bar.setMinimumHeight(180)
        layout.addWidget(self.scc_dist_bar)

        self.tabs.addTab(tab, "Carrier Aggregation")

    def _build_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        summary_layout = QGridLayout()
        summary_layout.setSpacing(10)
        self.summary_cards = {
            "disconnects": StatCard("Uzilishlar soni", ACCENT["bad"]),
            "avg_session": StatCard("O'rtacha sessiya", ACCENT["info"]),
            "uptime_pct": StatCard("Onlayn ulush", ACCENT["ok"], "%"),
            "handovers": StatCard("Handoverlar soni", ACCENT["band"]),
        }
        for i, key in enumerate(self.summary_cards):
            summary_layout.addWidget(self.summary_cards[key], 0, i)
        layout.addLayout(summary_layout)

        self.events_table = QTableWidget(0, 3)
        self.events_table.setHorizontalHeaderLabels(["Vaqt", "Hodisa", "Tafsilot"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.events_table, stretch=1)

        self.tabs.addTab(tab, "Hodisalar")

    def _make_dual_plot(self, title: str, y_label: str):
        axis = pg.DateAxisItem(orientation="bottom")
        plot = pg.PlotWidget(axisItems={"bottom": axis})
        plot.setBackground(ACCENT["bg"])
        plot.setTitle(title, color=ACCENT["text"], size="11pt")
        plot.setLabel("left", y_label, color=ACCENT["muted"])
        plot.showGrid(x=True, y=True, alpha=0.15)
        plot.getAxis("left").setTextPen(ACCENT["muted"])
        plot.getAxis("bottom").setTextPen(ACCENT["muted"])
        plot.addLegend()
        curve_tx = plot.plot([], [], pen=pg.mkPen(ACCENT["info"], width=2), name="TX (yuklama)")
        curve_rx = plot.plot([], [], pen=pg.mkPen(ACCENT["ok"], width=2), name="RX (yuklab olish)")
        return plot, curve_tx, curve_rx

    def _build_traffic_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        self.plot_traffic_cum, self.curve_tx, self.curve_rx = self._make_dual_plot("Kumulyativ trafik", "MB")
        self.plot_traffic_cum.setMinimumHeight(220)
        layout.addWidget(self.plot_traffic_cum)

        self.plot_traffic_rate, self.curve_rate_tx, self.curve_rate_rx = self._make_dual_plot(
            "Tezlik (baholangan, MB/daqiqa)", "MB/daqiqa"
        )
        self.plot_traffic_rate.setMinimumHeight(220)
        layout.addWidget(self.plot_traffic_rate)

        self.tabs.addTab(tab, "Trafik")

    def _apply_dark_theme(self):
        pg.setConfigOption("background", ACCENT["bg"])
        pg.setConfigOption("foreground", ACCENT["text"])
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background-color: {ACCENT['bg']}; }}
            QTableWidget {{
                background-color: {ACCENT['card']};
                color: {ACCENT['text']};
                gridline-color: #2a2a2e;
                border: none;
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: #202024;
                color: {ACCENT['muted']};
                border: none;
                padding: 6px;
                font-size: 11px;
            }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {ACCENT['card']};
                color: {ACCENT['muted']};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{ background: #26262b; color: {ACCENT['text']}; }}
            QComboBox {{
                background-color: {ACCENT['card']};
                color: {ACCENT['text']};
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QSplitter::handle {{ background-color: #2a2a2e; }}
            QScrollArea {{ border: none; }}
            QScrollBar:vertical {{ background: {ACCENT['bg']}; width: 12px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: #35353a; border-radius: 5px; min-height: 24px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            """
        )

    def _on_window_changed(self, text: str):
        self.stats_window_minutes = WINDOW_OPTIONS.get(text)
        self._update_stats_tab()

    # --------------------------------------------------------------- Poll
    def poll(self):
        new_rows = self.reader.poll_new_rows()
        if not new_rows:
            if self.df.empty:
                self.status_label.setText("● Log fayl topilmadi yoki bo'sh")
                self.status_label.setStyleSheet(f"color: {ACCENT['bad']}; font-size: 13px;")
            else:
                self.status_label.setText(f"● {_now()} (o'zgarish yo'q)")
                self.status_label.setStyleSheet(f"color: {ACCENT['muted']}; font-size: 13px;")
            return

        new_events = []
        records = []
        for row in new_rows:
            rec = analytics.row_to_record(row)
            if rec is None:
                continue
            records.append(rec)
            new_events.extend(self.detector.push(rec))

        if not records:
            return

        self.df = pd.concat([self.df, pd.DataFrame(records)], ignore_index=True)
        if len(self.df) > self.max_stored_rows:
            self.df = self.df.iloc[-self.max_stored_rows :].reset_index(drop=True)

        self.events.extend(new_events)
        self._append_event_rows(new_events)

        last = records[-1]
        self._refresh_cards(last)
        self._refresh_live_plots()
        self._update_stats_tab()
        self._update_band_tab()
        self._update_ca_tab()
        self._update_events_summary()
        self._update_traffic_tab()

        self.status_label.setText(f"● Onlayn — so'nggi o'qish: {_now()}")
        self.status_label.setStyleSheet(f"color: {ACCENT['ok']}; font-size: 13px;")

    # ------------------------------------------------------------ Jonli tab
    def _refresh_cards(self, rec: dict):
        state = rec["state"]
        self.cards["state"].set_value(state, ACCENT["ok"] if rec["connected"] else ACCENT["bad"])
        self.cards["network_type"].set_value(rec["network_type"])
        self.cards["band"].set_value(rec["band"])
        self.cards["rssi"].set_value(fmt(rec["rssi"], 0), quality_color("rssi", rec["rssi"]))
        self.cards["rsrp"].set_value(fmt(rec["rsrp"], 0), quality_color("rsrp", rec["rsrp"]))
        self.cards["rsrq"].set_value(fmt(rec["rsrq"], 0), quality_color("rsrq", rec["rsrq"]))
        self.cards["sinr"].set_value(fmt(rec["sinr"], 0), quality_color("sinr", rec["sinr"]))
        self.cards["scc_count"].set_value(str(rec["scc_count"]))
        self.cards["external_ip"].set_value(rec["external_ip"])
        self.cards["connection_uptime"].set_value(format_duration(rec["uptime_s"]))
        self.cards["bandwidth"].set_value(f"{rec['bandwidth_ul'] or '?'} / {rec['bandwidth_dl'] or '?'}")
        tx, rx = rec["tx_mb"], rec["rx_mb"]
        self.cards["traffic"].set_value(f"{fmt(tx,2)} / {fmt(rx,2)} MB")

        by_role = {role: (band, bw) for role, band, bw in analytics.carrier_components(rec)}
        for role, key in (("PCC", "pcc"), ("SCC1", "scc1"), ("SCC2", "scc2"), ("SCC3", "scc3"), ("SCC4", "scc4")):
            band, bw = by_role.get(role, (None, None))
            self.carrier_cards[key].set_value(f"{band} / {bw}" if band else "—", ACCENT["ok"] if band else ACCENT["muted"])

    def _refresh_live_plots(self):
        tail = self.df.tail(self.live_window_points)
        xs = tail["epoch"].tolist()
        self.plot_rsrp.update_data(xs, tail["rsrp"].tolist())
        self.plot_rsrq.update_data(xs, tail["rsrq"].tolist())
        self.plot_sinr.update_data(xs, tail["sinr"].tolist())

    # ---------------------------------------------------------- Statistika
    def _update_stats_tab(self):
        window_df = analytics.filter_window(self.df, self.stats_window_minutes)
        for row, metric in enumerate(["rssi", "rsrp", "rsrq", "sinr"]):
            s = analytics.compute_stats(window_df, metric)
            values = [
                str(s["count"]),
                fmt(s["min"]),
                fmt(s["max"]),
                fmt(s["mean"]),
                fmt(s["median"]),
                fmt(s["std"]),
                f"{fmt(s['p5'])} / {fmt(s['p95'])}",
            ]
            for col, value in enumerate(values, start=1):
                self.stats_table.setItem(row, col, QTableWidgetItem(value))

        corr = analytics.correlation_matrix(window_df)
        labels = ["rssi", "rsrp", "rsrq", "sinr"]
        for i, ri in enumerate(labels):
            for j, cj in enumerate(labels):
                value = corr.loc[ri, cj] if not corr.empty and ri in corr and cj in corr else np.nan
                item = QTableWidgetItem(fmt(value, 2))
                if i != j and not np.isnan(value):
                    strength = abs(value)
                    color = ACCENT["ok"] if strength > 0.7 else (ACCENT["warning"] if strength > 0.4 else ACCENT["muted"])
                    item.setForeground(QColor(color))
                self.corr_table.setItem(i, j, item)

        self.hist_rsrp.update_data(window_df.get("rsrp", pd.Series(dtype=float)))
        self.hist_rsrq.update_data(window_df.get("rsrq", pd.Series(dtype=float)))
        self.hist_sinr.update_data(window_df.get("sinr", pd.Series(dtype=float)))

    # -------------------------------------------------------- Band tahlili
    def _update_band_tab(self):
        breakdown = analytics.band_breakdown(self.df)
        self.band_table.setRowCount(len(breakdown))
        for row, (_, r) in enumerate(breakdown.iterrows()):
            values = [r["band"], str(int(r["count"])), f"{r['pct']:.1f}", fmt(r["rsrp"]), fmt(r["rsrq"]), fmt(r["sinr"]), fmt(r["rssi"])]
            for col, value in enumerate(values):
                self.band_table.setItem(row, col, QTableWidgetItem(value))
        labels = breakdown["band"].tolist()
        values = [v if not np.isnan(v) else 0 for v in breakdown["rsrp"].tolist()]
        self.band_bar.update_data(labels, values)

    # ------------------------------------------------------ Carrier Aggregation
    def _update_ca_tab(self):
        tail = self.df.tail(self.live_window_points)
        carrier_count = (tail["ca_combo"].str.count(r"\+") + 1).where(tail["ca_combo"] != "", 0)
        self.scc_trend.update_data(tail["epoch"].tolist(), carrier_count.tolist())

        combos = analytics.ca_combo_breakdown(self.df)
        self.ca_combo_table.setRowCount(len(combos))
        for row, (_, r) in enumerate(combos.iterrows()):
            values = [r["combo"], str(int(r["count"])), f"{r['pct']:.1f}", f"{fmt(r['rsrp'])} / {fmt(r['sinr'])}"]
            for col, value in enumerate(values):
                self.ca_combo_table.setItem(row, col, QTableWidgetItem(value))

        freq = analytics.carrier_frequency(self.df)
        self.carrier_freq_table.setRowCount(len(freq))
        for row, (_, r) in enumerate(freq.iterrows()):
            values = [r["band"], str(int(r["as_pcc"])), str(int(r["as_scc"])), str(int(r["total"]))]
            for col, value in enumerate(values):
                self.carrier_freq_table.setItem(row, col, QTableWidgetItem(value))

        dist = analytics.scc_count_distribution(self.df)
        labels = [f"{int(n) + 1} carrier" for n in dist["scc_count"].tolist()]
        self.scc_dist_bar.update_data(labels, dist["pct"].tolist())

    # ----------------------------------------------------------- Hodisalar
    def _append_event_rows(self, new_events: list):
        for e in new_events:
            r = self.events_table.rowCount()
            self.events_table.insertRow(r)
            ts_item = QTableWidgetItem(e["ts"].strftime("%Y-%m-%d %H:%M:%S"))
            title_item = QTableWidgetItem(e["title"])
            detail_item = QTableWidgetItem(e["detail"])
            color = QColor(SEVERITY_COLOR.get(e["severity"], ACCENT["text"]))
            title_item.setForeground(color)
            self.events_table.setItem(r, 0, ts_item)
            self.events_table.setItem(r, 1, title_item)
            self.events_table.setItem(r, 2, detail_item)
        if new_events:
            self.events_table.scrollToBottom()

    def _update_events_summary(self):
        rel = analytics.summarize_reliability(self.df)
        self.summary_cards["disconnects"].set_value(str(rel["disconnects"]))
        self.summary_cards["avg_session"].set_value(format_duration(rel["avg_session_s"]))
        self.summary_cards["uptime_pct"].set_value(fmt(rel["uptime_pct"], 1))
        handovers = sum(1 for e in self.events if "Handover" in e["title"])
        self.summary_cards["handovers"].set_value(str(handovers))

    # -------------------------------------------------------------- Trafik
    def _update_traffic_tab(self):
        tmp = self.df[["epoch", "tx_mb", "rx_mb"]].dropna()
        if tmp.empty:
            return
        xs = tmp["epoch"].tolist()
        self.curve_tx.setData(xs, tmp["tx_mb"].tolist())
        self.curve_rx.setData(xs, tmp["rx_mb"].tolist())

        tmp = tmp.copy()
        tmp["dt_min"] = tmp["epoch"].diff() / 60.0
        tmp["d_tx"] = tmp["tx_mb"].diff()
        tmp["d_rx"] = tmp["rx_mb"].diff()
        valid = tmp[(tmp["dt_min"] > 0) & (tmp["d_tx"] >= 0) & (tmp["d_rx"] >= 0)]
        if not valid.empty:
            self.curve_rate_tx.setData(valid["epoch"].tolist(), (valid["d_tx"] / valid["dt_min"]).tolist())
            self.curve_rate_rx.setData(valid["epoch"].tolist(), (valid["d_rx"] / valid["dt_min"]).tolist())


def _now() -> str:
    from datetime import datetime

    return datetime.now().strftime("%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description="GCOM Signal Monitor dashboard")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--logfile", help="gcom_signal_logger CSV log fayli yo'li")
    parser.add_argument("--poll-interval", type=int, help="So'rovlar orasidagi interval (ms)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    if args.logfile:
        cfg["logfile"] = args.logfile
    if args.poll_interval:
        cfg["poll_interval_ms"] = args.poll_interval

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    icon_path = SCRIPT_DIR / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setFont(QFont("Segoe UI", 9))
    window = MainWindow(cfg)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
