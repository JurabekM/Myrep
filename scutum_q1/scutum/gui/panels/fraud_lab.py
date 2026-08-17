"""ROSTOR panel 4 — Firibgarlik hujum laboratoriyasi: T1-T6 real ssenariylar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSplitter, QVBoxLayout, QWidget

from ...sim.fraud_attacks import ATTACKS, Outcome, run_attack
from .. import theme as T
from ..widgets import Badge, Card, LogView, StatTile, Table, page_header

OUTCOME_COLOR = {Outcome.BROKEN: T.FAIL, Outcome.SAFE: T.OK, Outcome.STRUCTURAL: T.WARN}


class FraudLabPanel(QWidget):
    def __init__(self, state=None, parent=None) -> None:
        super().__init__(parent)
        self.results: dict[str, object] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        root.addWidget(page_header(
            "Firibgarlik hujum laboratoriyasi",
            "O'zbekistonda haqiqatda ishlaydigan 6 ta tahdid vektori (IIV/Gazeta.uz "
            "va Group-IB statistikasi asosida). Har biri UNPROTECTED (bugungi oddiy "
            "oqim) va PROTECTED (ROSTOR-1) holatida HAQIQATAN ijro etiladi.",
        ))

        bar = QHBoxLayout()
        btn_run = QPushButton("Barcha T1-T6 ssenariylarini ishga tushirish")
        btn_run.setObjectName("Primary")
        btn_run.clicked.connect(self.run_all)
        bar.addWidget(btn_run)
        bar.addStretch(1)
        self.t_broken = StatTile("UNPROTECTED buzilgan", "—", T.FAIL)
        self.t_safe = StatTile("PROTECTED himoyalangan", "—", T.OK)
        for t in (self.t_broken, self.t_safe):
            t.setMinimumWidth(180)
            bar.addWidget(t)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = Card("Ssenariylar")
        self.table = Table(["Tahdid", "Nom", "UNPROTECTED", "PROTECTED"])
        self.table.itemSelectionChanged.connect(self.show_detail)
        left.add(self.table)
        split.addWidget(left)

        right = Card("Tafsilot")
        self.summary = Badge("Ro'yxatdan ssenariy tanlang", T.DIM)
        right.add(self.summary)
        self.log = LogView()
        right.add(self.log)
        split.addWidget(right)
        split.setSizes([680, 640])
        root.addWidget(split, 1)

        self._fill_empty()

    # ------------------------------------------------------------------
    def _fill_empty(self) -> None:
        self.table.clear_rows()
        self.row_of: dict[str, int] = {}
        for key, atk in ATTACKS.items():
            r = self.table.add_row(
                [atk.threat, atk.title, "—", "—"],
                [T.VIOLET, T.TEXT, T.DIM, T.DIM],
            )
            self.row_of[key] = r
        self.table.resizeColumnsToContents()

    def run_all(self) -> None:
        self.results.clear()
        self._fill_empty()
        for key in ATTACKS:
            r = run_attack(key)
            self.results[key] = r
            row = self.row_of[key]
            self.table.item(row, 2).setText(r.unprotected)
            self.table.item(row, 2).setForeground(_qcolor(OUTCOME_COLOR.get(r.unprotected, T.DIM)))
            self.table.item(row, 3).setText(r.protected)
            self.table.item(row, 3).setForeground(_qcolor(OUTCOME_COLOR.get(r.protected, T.DIM)))
        self.table.resizeColumnsToContents()
        n_broken = sum(1 for r in self.results.values() if r.unprotected == Outcome.BROKEN)
        n_safe = sum(1 for r in self.results.values() if r.protected == Outcome.SAFE)
        self.t_broken.set_value(f"{n_broken}/{len(self.results)}")
        self.t_safe.set_value(f"{n_safe}/{len(self.results)}")

    def show_detail(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        key = next((k for k, v in self.row_of.items() if v == row), None)
        if key is None or key not in self.results:
            return
        r = self.results[key]
        atk = ATTACKS[key]
        self.log.clear()
        self.summary.set(
            f"{r.threat} · UNPROTECTED={r.unprotected} · PROTECTED={r.protected}",
            T.FAIL if r.protected != Outcome.SAFE else T.OK,
        )
        self.log.append_line(f"Real dunyo: {atk.real_world_note}", T.MUTED)
        self.log.append_line("\n── UNPROTECTED (bugungi oddiy oqim) ──", T.FAIL)
        for e in r.unprotected_evidence:
            self.log.append_line("  " + e, T.MUTED)
        self.log.append_line("\n── PROTECTED (ROSTOR-1) ──", T.OK)
        for e in r.protected_evidence:
            self.log.append_line("  " + e, T.MUTED)


def _qcolor(hexcolor: str):
    from PySide6.QtGui import QColor

    return QColor(hexcolor)
