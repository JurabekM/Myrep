"""QORAVUL gateway dashboard (PyQt6 + pyqtgraph).

    python -m qoravul.sim.run --export runs/day1
    python -m qoravul.dashboard.app runs/day1 [--lang en] [--screenshot shot.png]
"""
from __future__ import annotations

import argparse
import sys

from .data import DashboardData, load

BG, PANEL, GRID = "#05060a", "#0b0f17", "#16202c"
CYAN, MAGENTA, TEXT, DIM = "#00f0ff", "#ff2bd6", "#d8f7ff", "#5c7a88"
FONT = "DejaVu Sans Mono"

TR = {
    "uz": {
        "title": "QORAVUL // GATEWAY", "nodes": "HISOBLAGICHLAR", "alerts": "ALERTLAR", "active": "FAOL INCIDENT",
        "energy": "ENERGIYA, kWh", "chain": "ZANJIR", "chain_ok": "BUTUN", "chain_bad": "BUZILGAN",
        "ledger": "DALIL REESTRI", "incidents": "INCIDENTLAR", "kwh": "kWh / 15 daqiqa",
        "cols": ["#", "vaqt", "node", "sabab", "ball / chegara", "imzo", "hash"],
        "inc_cols": ["node", "ochilgan", "sabab", "holat"], "open": "FAOL", "closed": "YOPILGAN",
        "fleet": "flot o'rtachasi", "node": "node", "lang": "EN", "sig_bad": "IMZO XATO", "hour": "soat",
    },
    "en": {
        "title": "QORAVUL // GATEWAY", "nodes": "METERS", "alerts": "ALERTS", "active": "ACTIVE INCIDENTS",
        "energy": "ENERGY, kWh", "chain": "CHAIN", "chain_ok": "INTACT", "chain_bad": "BROKEN",
        "ledger": "EVIDENCE LEDGER", "incidents": "INCIDENTS", "kwh": "kWh / 15 min",
        "cols": ["#", "time", "node", "culprit", "score / thr", "sig", "hash"],
        "inc_cols": ["node", "opened", "culprit", "state"], "open": "ACTIVE", "closed": "CLOSED",
        "fleet": "fleet average", "node": "node", "lang": "UZ", "sig_bad": "BAD SIG", "hour": "hour",
    },
}

QSS = f"""
* {{ font-family: '{FONT}'; color: {TEXT}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QFrame#panel {{ background: {PANEL}; border: 1px solid {GRID}; border-radius: 6px; }}
QLabel#h1 {{ color: {CYAN}; font-size: 20px; font-weight: bold; letter-spacing: 4px; }}
QLabel#cap {{ color: {DIM}; font-size: 10px; letter-spacing: 2px; }}
QLabel#kpi {{ color: {CYAN}; font-size: 24px; font-weight: bold; }}
QLabel#kpi_bad {{ color: {MAGENTA}; font-size: 24px; font-weight: bold; }}
QLabel#sect {{ color: {MAGENTA}; font-size: 12px; font-weight: bold; letter-spacing: 3px; }}
QTableWidget {{ background: {PANEL}; gridline-color: {GRID}; border: none; font-size: 11px;
               selection-background-color: #1a2a3a; }}
QHeaderView::section {{ background: {BG}; color: {CYAN}; border: none; border-bottom: 1px solid {CYAN};
                        padding: 4px; font-size: 10px; letter-spacing: 1px; }}
QPushButton, QComboBox {{ background: {BG}; color: {CYAN}; border: 1px solid {CYAN}; border-radius: 4px;
                          padding: 4px 10px; }}
QPushButton:hover {{ color: {MAGENTA}; border-color: {MAGENTA}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT}; }}
QScrollBar:vertical {{ background: {BG}; width: 8px; border: none; }}
QScrollBar::handle:vertical {{ background: {GRID}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {CYAN}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
"""


def hhmm(window: int) -> str:
    return f"{(window // 60) % 24:02d}:{window % 60:02d}"


def build_window(data: DashboardData, lang: str = "uz"):
    import pyqtgraph as pg
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
                                 QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

    pg.setConfigOptions(antialias=True, background=PANEL, foreground=DIM)

    class Dashboard(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.data, self.lang = data, lang
            self.setStyleSheet(QSS)
            self.resize(1280, 760)
            self.render()

        def panel(self) -> tuple[QFrame, QVBoxLayout]:
            f = QFrame()
            f.setObjectName("panel")
            lay = QVBoxLayout(f)
            lay.setContentsMargins(12, 10, 12, 10)
            return f, lay

        def label(self, text: str, name: str) -> QLabel:
            lab = QLabel(text)
            lab.setObjectName(name)
            return lab

        def render(self) -> None:
            t, d = TR[self.lang], self.data
            self.setWindowTitle(t["title"])
            root = QWidget()
            root.setObjectName("root")
            grid = QGridLayout(root)
            grid.setContentsMargins(16, 12, 16, 16)
            grid.setSpacing(12)

            head = QHBoxLayout()
            head.addWidget(self.label(t["title"], "h1"))
            head.addStretch(1)
            self.lang_btn = QPushButton(t["lang"])
            self.lang_btn.clicked.connect(self.toggle_lang)
            head.addWidget(self.lang_btn)
            grid.addLayout(head, 0, 0, 1, 5)

            active = sum(i.active for i in d.incidents)
            chain_good = d.chain_ok and d.sig_failures == 0
            kpis = [
                (t["nodes"], str(len(d.nodes)), True),
                (t["alerts"], str(len(d.rows)), not d.rows),
                (t["active"], str(active), active == 0),
                (t["energy"], f"{d.total_kwh:,.1f}", True),
                (t["chain"], t["chain_ok"] if chain_good else t["chain_bad"], chain_good),
            ]
            self.kpi_labels = {}
            kpi_row = QHBoxLayout()
            kpi_row.setSpacing(12)
            for cap, val, good in kpis:
                f, lay = self.panel()
                lay.addWidget(self.label(cap, "cap"))
                v = self.label(val, "kpi" if good else "kpi_bad")
                lay.addWidget(v)
                self.kpi_labels[cap] = v
                kpi_row.addWidget(f, 1)
            grid.addLayout(kpi_row, 1, 0, 1, 5)

            # ledger table
            f, lay = self.panel()
            lay.addWidget(self.label(t["ledger"], "sect"))
            self.table = QTableWidget(len(d.rows), len(t["cols"]))
            self.table.setHorizontalHeaderLabels(t["cols"])
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setStretchLastSection(True)
            for r, row in enumerate(d.rows):
                cells = [str(row.index), hhmm(row.window), row.node[:10], row.culprit,
                         f"{row.score} / {row.threshold}", "OK" if row.sig_ok else t["sig_bad"],
                         row.hash[:16] + "…"]
                for c, text in enumerate(cells):
                    item = QTableWidgetItem(text)
                    if c == 5:
                        item.setForeground(QColor(CYAN if row.sig_ok else MAGENTA))
                    if c == 3:
                        item.setForeground(QColor(MAGENTA))
                    self.table.setItem(r, c, item)
            lay.addWidget(self.table)
            grid.addWidget(f, 2, 0, 2, 3)

            # kWh chart
            f, lay = self.panel()
            top = QHBoxLayout()
            top.addWidget(self.label(t["kwh"], "sect"))
            top.addStretch(1)
            self.node_box = QComboBox()
            self.node_box.addItems([n[:10] for n in d.nodes])
            alert_nodes = [r.node for r in d.rows]
            if alert_nodes:
                self.node_box.setCurrentIndex(d.nodes.index(alert_nodes[0]))
            self.node_box.currentIndexChanged.connect(self.update_node_curve)
            top.addWidget(self.node_box)
            lay.addLayout(top)
            self.plot = pg.PlotWidget()
            self.plot.showGrid(x=True, y=True, alpha=0.15)
            self.plot.setLabel("bottom", t["hour"])
            self.plot.addLegend(offset=(10, 5), labelTextColor=TEXT)
            hours = [w / 60.0 for w in d.kwh_slots]
            avg = [v / max(1, len(d.nodes)) for v in d.kwh_fleet]  # per-meter average, comparable to one node
            self.plot.plot(hours, avg, pen=pg.mkPen(CYAN, width=2), name=t["fleet"],
                           fillLevel=0, brush=pg.mkBrush(0, 240, 255, 40))
            self.node_curve = self.plot.plot([], [], pen=pg.mkPen(MAGENTA, width=2), name=t["node"])
            for row in d.rows:
                self.plot.addItem(pg.InfiniteLine(row.window / 60.0, angle=90,
                                                  pen=pg.mkPen(MAGENTA, width=1, style=Qt.PenStyle.DashLine)))
            lay.addWidget(self.plot)
            grid.addWidget(f, 2, 3, 1, 2)
            self.update_node_curve()

            # incidents
            f, lay = self.panel()
            lay.addWidget(self.label(t["incidents"], "sect"))
            self.inc_table = QTableWidget(len(d.incidents), 4)
            self.inc_table.setHorizontalHeaderLabels(t["inc_cols"])
            self.inc_table.verticalHeader().setVisible(False)
            self.inc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            for r, inc in enumerate(d.incidents):
                state = QTableWidgetItem(t["open"] if inc.active else t["closed"])
                state.setForeground(QColor(MAGENTA if inc.active else DIM))
                for c, item in enumerate([QTableWidgetItem(inc.node[:10]), QTableWidgetItem(hhmm(inc.opened)),
                                          QTableWidgetItem(inc.culprit), state]):
                    self.inc_table.setItem(r, c, item)
            lay.addWidget(self.inc_table)
            grid.addWidget(f, 3, 3, 1, 2)

            grid.setRowStretch(2, 3)
            grid.setRowStretch(3, 2)
            grid.setColumnStretch(0, 1)
            self.setCentralWidget(root)

        def update_node_curve(self) -> None:
            if not self.data.nodes:
                return
            node = self.data.nodes[self.node_box.currentIndex()]
            self.node_curve.setData([w / 60.0 for w in self.data.kwh_slots], self.data.kwh_node.get(node, []))

        def toggle_lang(self) -> None:
            self.lang = "en" if self.lang == "uz" else "uz"
            self.render()

    return Dashboard()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export_dir", help="directory written by `python -m qoravul.sim.run --export DIR`")
    ap.add_argument("--lang", choices=["uz", "en"], default="uz")
    ap.add_argument("--screenshot", default=None, help="render once, save PNG and exit (works offscreen)")
    args = ap.parse_args(argv)

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    win = build_window(load(args.export_dir), args.lang)
    win.show()
    if args.screenshot:
        app.processEvents()
        win.grab().save(args.screenshot)
        print(f"saved {args.screenshot}")
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
