"""Asosiy oyna: chap navigatsiya + panellar + jonli log."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import Mode
from . import theme as T
from .panels import (
    AttacksPanel,
    DevicesPanel,
    FraudLabPanel,
    InspectorPanel,
    InstitutionsPanel,
    OverviewPanel,
    SFilePanel,
    RatchetPanel,
    SessionPanel,
    TestsPanel,
    TransparencyPanel,
    TxnConfirmPanel,
)
from .state import AppState
from .widgets import Badge, LogView

NAV = [
    ("Institutsiyalar", InstitutionsPanel),
    ("Tranzaksiya tasdiqlash", TxnConfirmPanel),
    ("Shaffoflik jurnali", TransparencyPanel),
    ("Firibgarlik lab (T1-T6)", FraudLabPanel),
    ("Umumiy ko'rinish (transport)", OverviewPanel),
    ("Qurilmalar (transport)", DevicesPanel),
    ("S-MSG sessiya (transport)", SessionPanel),
    ("Ratchet holati (transport)", RatchetPanel),
    ("S-FILE (transport)", SFilePanel),
    ("Transport hujumlari", AttacksPanel),
    ("Paket inspektori (transport)", InspectorPanel),
    ("Testlar", TestsPanel),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(
            "ROSTOR-1 — kiberfiribgarlikka qarshi ishonch protokoli "
            "(SCUTUM-Q1 transporti ustida)"
        )
        self.resize(1560, 960)
        self.setMinimumSize(1180, 760)

        self.state = AppState()

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- sidebar ----------------
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(238)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 12)
        sl.setSpacing(0)

        title = QLabel("SCUTUM")
        title.setObjectName("SidebarTitle")
        sub = QLabel(f"protokol simulyatori · v{__version__}")
        sub.setObjectName("SidebarSub")
        sl.addWidget(title)
        sl.addWidget(sub)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for i, (label, _cls) in enumerate(NAV):
            b = QPushButton(label)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(b, i)
            sl.addWidget(b)
        sl.addStretch(1)

        modebox = QWidget()
        mb = QVBoxLayout(modebox)
        mb.setContentsMargins(18, 8, 18, 8)
        mb.setSpacing(6)
        mb.addWidget(QLabel("<span style='color:%s;font-size:11px'>REJIM</span>" % T.DIM))
        self.mode_badge = Badge("SPEC", T.FAIL)
        mb.addWidget(self.mode_badge)
        self.flags_lbl = QLabel("")
        self.flags_lbl.setStyleSheet(f"color:{T.DIM}; font-size:11px;")
        self.flags_lbl.setWordWrap(True)
        mb.addWidget(self.flags_lbl)
        sl.addWidget(modebox)
        root.addWidget(side)

        # ---------------- content + log ----------------
        vsplit = QSplitter(Qt.Orientation.Vertical)
        self.stack = QStackedWidget()
        self.panels = []
        for _label, cls in NAV:
            p = cls(self.state)
            self.panels.append(p)
            self.stack.addWidget(p)
        vsplit.addWidget(self.stack)

        logbox = QWidget()
        ll = QVBoxLayout(logbox)
        ll.setContentsMargins(18, 8, 18, 8)
        ll.setSpacing(6)
        head = QHBoxLayout()
        h = QLabel("Voqealar jurnali")
        h.setStyleSheet(f"color:{T.MUTED}; font-weight:600; font-size:12px;")
        clear = QPushButton("Tozalash")
        clear.setObjectName("Ghost")
        clear.setFixedWidth(96)
        head.addWidget(h)
        head.addStretch(1)
        head.addWidget(clear)
        ll.addLayout(head)
        self.log = LogView()
        clear.clicked.connect(self.log.clear)
        ll.addWidget(self.log)
        vsplit.addWidget(logbox)
        vsplit.setSizes([720, 210])
        root.addWidget(vsplit, 1)

        self.setCentralWidget(central)
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)
        self.nav_group.button(0).setChecked(True)

        self.state.event_logged.connect(self.log.append_event)
        self.state.config_changed.connect(self._refresh_mode)
        self._refresh_mode()

        sb = self.statusBar()
        sb.showMessage(
            "Tayyor · SPEC rejimi — hujjatdagi protokol aynan modellashtirilgan"
        )

    # ------------------------------------------------------------------
    def _refresh_mode(self) -> None:
        cfg = self.state.cfg
        color = {Mode.SPEC: T.FAIL, Mode.HARDENED: T.OK, Mode.CUSTOM: T.WARN}[cfg.mode]
        self.mode_badge.set(cfg.mode.value, color)
        self.flags_lbl.setText(
            f"{self.state.fixed_count}/{self.state.total_flags} tuzatish yoqilgan"
        )
        self.statusBar().showMessage(cfg.describe())
