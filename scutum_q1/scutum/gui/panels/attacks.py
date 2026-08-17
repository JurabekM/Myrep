"""Panel 6 — hujum laboratoriyasi: SPEC ⇄ HARDENED yonma-yon."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from ...config import hardened_config, spec_config
from ...sim.attacks import ATTACKS, Outcome, run_attack
from .. import theme as T
from ..widgets import Badge, Card, LogView, StatTile, Table, page_header


class Runner(QThread):
    progress = Signal(int, int, str)
    result = Signal(str, object, object)
    done = Signal()

    def __init__(self, cfg, keys, compare: bool) -> None:
        super().__init__()
        self.cfg = cfg
        self.keys = keys
        self.compare = compare

    def run(self) -> None:
        total = len(self.keys)
        for i, key in enumerate(self.keys, 1):
            self.progress.emit(i, total, ATTACKS[key].title)
            if self.compare:
                rs = run_attack(key, spec_config())
                rh = run_attack(key, hardened_config())
            else:
                rs = run_attack(key, self.cfg)
                rh = None
            self.result.emit(key, rs, rh)
        self.done.emit()


class AttacksPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.results: dict[str, tuple] = {}
        self._runner: Runner | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        root.addWidget(
            page_header(
                "Hujum laboratoriyasi",
                "Har bir hujum haqiqatan ishga tushiriladi. BROKEN — hujumchi "
                "maqsadiga erishdi; STRUCTURAL — buzilish ijro etilmadi, lekin "
                "tuzilmaviy zaiflik o'lchandi; NAZORAT — himoya ishlashini "
                "tasdiqlovchi musbat sinov.",
            )
        )

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_cmp = QPushButton("SPEC ⇄ HARDENED taqqoslash")
        self.btn_cmp.setObjectName("Primary")
        self.btn_cmp.clicked.connect(lambda: self.start(compare=True))
        self.btn_cur = QPushButton("Joriy rejimda ishga tushirish")
        self.btn_cur.clicked.connect(lambda: self.start(compare=False))
        self.btn_sel = QPushButton("Tanlanganini qayta ishga tushirish")
        self.btn_sel.setObjectName("Ghost")
        self.btn_sel.clicked.connect(self.run_selected)
        bar.addWidget(self.btn_cmp)
        bar.addWidget(self.btn_cur)
        bar.addWidget(self.btn_sel)
        bar.addStretch(1)
        self.tile_broken = StatTile("Buzilgan", "—", T.FAIL)
        self.tile_safe = StatTile("Himoyalangan", "—", T.OK)
        self.tile_struct = StatTile("Tuzilmaviy", "—", T.WARN)
        for t in (self.tile_broken, self.tile_safe, self.tile_struct):
            t.setMinimumWidth(140)
            bar.addWidget(t)
        root.addLayout(bar)

        self.prog = QProgressBar()
        self.prog.setVisible(False)
        root.addWidget(self.prog)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = Card("Ssenariylar")
        self.table = Table(
            ["hujum", "topilma", "jiddiylik", "SPEC", "HARDENED", "ms"]
        )
        self.table.itemSelectionChanged.connect(self.show_detail)
        left.add(self.table)
        split.addWidget(left)

        right = Card("Tafsilot")
        self.head = QLabel("Ro'yxatdan hujum tanlang.")
        self.head.setWordWrap(True)
        self.head.setStyleSheet(f"color:{T.MUTED}; font-size:12px;")
        right.add(self.head)
        self.badges = QHBoxLayout()
        self.badge_spec = Badge("SPEC —", T.DIM)
        self.badge_hard = Badge("HARDENED —", T.DIM)
        self.badges.addWidget(self.badge_spec)
        self.badges.addWidget(self.badge_hard)
        self.badges.addStretch(1)
        right.add(self.badges)
        self.log = LogView()
        right.add(self.log)
        split.addWidget(right)
        split.setSizes([720, 560])
        root.addWidget(split, 1)

        self._fill_empty()

    # ------------------------------------------------------------------
    def _fill_empty(self) -> None:
        self.table.clear_rows()
        self.row_of: dict[str, int] = {}
        for key, atk in ATTACKS.items():
            r = self.table.add_row(
                [atk.title, atk.finding, atk.severity, "—", "—", "—"],
                [T.TEXT, T.MUTED, T.SEVERITY.get(atk.severity, T.DIM),
                 T.DIM, T.DIM, T.DIM],
            )
            self.row_of[key] = r
        self.table.resizeColumnsToContents()

    def start(self, compare: bool) -> None:
        if self._runner and self._runner.isRunning():
            return
        self.results.clear()
        self._fill_empty()
        keys = list(ATTACKS)
        self._launch(keys, compare)

    def run_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        key = next(k for k, v in self.row_of.items() if v == r)
        self._launch([key], True)

    def _launch(self, keys, compare: bool) -> None:
        self.prog.setVisible(True)
        self.prog.setRange(0, len(keys))
        for b in (self.btn_cmp, self.btn_cur, self.btn_sel):
            b.setEnabled(False)
        self._runner = Runner(self.state.cfg, keys, compare)
        self._runner.progress.connect(self._on_progress)
        self._runner.result.connect(self._on_result)
        self._runner.done.connect(self._on_done)
        self._runner.start()

    def _on_progress(self, i: int, total: int, title: str) -> None:
        self.prog.setValue(i)
        self.head.setText(f"Bajarilmoqda: {title} ({i}/{total})")

    def _on_result(self, key: str, rs, rh) -> None:
        self.results[key] = (rs, rh)
        r = self.row_of[key]
        self.table.item(r, 3).setText(rs.outcome)
        self.table.item(r, 3).setForeground(_c(T.OUTCOME.get(rs.outcome, T.DIM)))
        if rh is not None:
            self.table.item(r, 4).setText(rh.outcome)
            self.table.item(r, 4).setForeground(_c(T.OUTCOME.get(rh.outcome, T.DIM)))
        self.table.item(r, 5).setText(f"{rs.elapsed_ms:.0f}")
        self._update_tiles()

    def _on_done(self) -> None:
        self.prog.setVisible(False)
        for b in (self.btn_cmp, self.btn_cur, self.btn_sel):
            b.setEnabled(True)
        self.head.setText("Tugadi. Tafsilot uchun qatorni tanlang.")
        self.table.resizeColumnsToContents()

    def _update_tiles(self) -> None:
        vals = [rs.outcome for rs, _ in self.results.values()]
        self.tile_broken.set_value(vals.count(Outcome.BROKEN))
        self.tile_safe.set_value(vals.count(Outcome.SAFE))
        self.tile_struct.set_value(vals.count(Outcome.STRUCTURAL))

    # ------------------------------------------------------------------
    def show_detail(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        key = next((k for k, v in self.row_of.items() if v == r), None)
        if key is None:
            return
        atk = ATTACKS[key]
        self.log.clear()
        self.head.setText(
            f"<b style='font-size:14px'>{atk.title}</b> "
            f"<span style='color:{T.DIM}'>({atk.finding} · {atk.severity})</span>"
            f"<br><span style='color:{T.MUTED}'>Maqsad: {atk.goal}</span>"
        )
        pair = self.results.get(key)
        if pair is None:
            self.badge_spec.set("SPEC —", T.DIM)
            self.badge_hard.set("HARDENED —", T.DIM)
            self.log.append_line("Hali ishga tushirilmagan.", T.DIM)
            return
        rs, rh = pair
        self.badge_spec.set(f"SPEC · {rs.outcome}", T.OUTCOME.get(rs.outcome, T.DIM))
        if rh:
            self.badge_hard.set(
                f"HARDENED · {rh.outcome}", T.OUTCOME.get(rh.outcome, T.DIM)
            )
        for label, res in (("SPEC", rs), ("HARDENED", rh)):
            if res is None:
                continue
            self.log.append_line(f"\n── {label} ─────────────────────", T.VIOLET)
            self.log.append_line(f"natija: {res.outcome} — {res.summary}",
                                 T.OUTCOME.get(res.outcome, T.TEXT))
            for line in res.evidence:
                self.log.append_line("  " + line, T.MUTED)


def _c(hexcolor: str):
    from PySide6.QtGui import QColor

    return QColor(hexcolor)
