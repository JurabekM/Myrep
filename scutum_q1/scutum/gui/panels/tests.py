"""Panel 8 — majburiy testlar (spec §10)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...selftest import TESTS, run_all
from .. import theme as T
from ..widgets import Badge, Card, StatTile, Table, page_header

CHECKLIST = [
    ("1. Har kriptografik funksiya uchun KAT/test vektorlari", "KAT"),
    ("2. INIT, ratchet, noto'g'ri imzo, replay, out-of-order testlari", "Sessiya"),
    ("3. Fayl bo'lagi, truncation, duplicate, manifest testlari", "S-FILE"),
    ("4. Fuzzing: parser, envelope, manifest, handlerlar", "Fuzz"),
    ("5. Maxfiy kalit/plaintext loglarda yo'qligini tekshirish", "Gigiyena"),
    ("6. Mustaqil kriptografik dizayn va implementatsiya auditi", None),
    ("7. Versiyalararo migratsiya va algoritm almashtirish sinovi", None),
]


class TestRunner(QThread):
    one = Signal(object)
    done = Signal(list)

    def __init__(self, cfg) -> None:
        super().__init__()
        self.cfg = cfg

    def run(self) -> None:
        out = run_all(self.cfg, on_result=lambda r: self.one.emit(r))
        self.done.emit(out)


class TestsPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self._runner: TestRunner | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        root.addWidget(
            page_header(
                "Majburiy testlar",
                "Spec §10 — chiqarish mezoni. Testlar joriy rejim "
                "konfiguratsiyasi ostida bajariladi.",
            )
        )

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn = QPushButton("Testlarni ishga tushirish")
        self.btn.setObjectName("Primary")
        self.btn.clicked.connect(self.start)
        bar.addWidget(self.btn)
        bar.addStretch(1)
        self.t_pass = StatTile("O'tdi", "—", T.OK)
        self.t_fail = StatTile("Yiqildi", "—", T.FAIL)
        self.t_time = StatTile("Vaqt", "—", T.MUTED)
        for t in (self.t_pass, self.t_fail, self.t_time):
            t.setMinimumWidth(130)
            bar.addWidget(t)
        root.addLayout(bar)

        self.prog = QProgressBar()
        self.prog.setVisible(False)
        root.addWidget(self.prog)

        self.table = Table(["", "guruh", "test", "ms", "natija"])
        root.addWidget(self.table, 1)

        cl = Card("Spec §10 chiqarish mezoni")
        self.check_labels: list[tuple[QLabel, str | None]] = []
        for text, group in CHECKLIST:
            lbl = QLabel("○  " + text)
            lbl.setStyleSheet(f"color:{T.DIM}; font-size:12px;")
            cl.add(lbl)
            self.check_labels.append((lbl, group))
        root.addWidget(cl)

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._runner and self._runner.isRunning():
            return
        self.table.clear_rows()
        self.results: list = []
        self.btn.setEnabled(False)
        self.prog.setVisible(True)
        self.prog.setRange(0, len(TESTS))
        self.prog.setValue(0)
        self._runner = TestRunner(self.state.cfg)
        self._runner.one.connect(self._on_one)
        self._runner.done.connect(self._on_done)
        self._runner.start()

    def _on_one(self, r) -> None:
        self.results.append(r)
        self.prog.setValue(len(self.results))
        self.table.add_row(
            ["✔" if r.ok else "✘", r.group, r.name, f"{r.ms:.0f}", r.detail],
            [T.OK if r.ok else T.FAIL, T.MUTED, T.TEXT, T.DIM,
             T.MUTED if r.ok else T.FAIL],
        )
        self.table.scrollToBottom()
        n_ok = sum(1 for x in self.results if x.ok)
        self.t_pass.set_value(n_ok)
        self.t_fail.set_value(len(self.results) - n_ok)

    def _on_done(self, results) -> None:
        self.prog.setVisible(False)
        self.btn.setEnabled(True)
        total_ms = sum(r.ms for r in results)
        self.t_time.set_value(f"{total_ms / 1000:.1f}s")
        self.table.resizeColumnsToContents()
        by_group: dict[str, bool] = {}
        for r in results:
            by_group[r.group] = by_group.get(r.group, True) and r.ok
        for lbl, group in self.check_labels:
            text = lbl.text()[3:]
            if group is None:
                lbl.setText("—  " + text + "   (qo'lda / tashqi jarayon)")
                lbl.setStyleSheet(f"color:{T.DIM}; font-size:12px;")
            elif by_group.get(group):
                lbl.setText("✔  " + text)
                lbl.setStyleSheet(f"color:{T.OK}; font-size:12px;")
            else:
                lbl.setText("✘  " + text)
                lbl.setStyleSheet(f"color:{T.FAIL}; font-size:12px;")
