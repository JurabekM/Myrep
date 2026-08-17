"""Panel 1 — umumiy ko'rinish, rejim va tuzatish bayroqlari."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...config import FLAG_CATALOG, Mode
from .. import theme as T
from ..widgets import Badge, Card, StatTile, Table, page_header, scroll_page

PROFILE_ROWS = [
    ("Klassik kalit kelishuvi", "X25519", "256-bit"),
    ("Post-kvant KEM", "ML-KEM-768", "FIPS 203, NIST L3"),
    ("Klassik imzo", "Ed25519", "128-bit"),
    ("Post-kvant imzo", "ML-DSA-65", "FIPS 204, NIST L3"),
    ("AEAD", "ChaCha20-Poly1305", "256-bit kalit, 96-bit nonce"),
    ("KDF", "HKDF-SHA-512", "kontekstga bog'langan"),
    ("Xesh", "SHA-3-256", "identifikator va Merkle"),
    ("Parol KDF", "Argon2id", "m=64 MiB, t=3, p=1"),
]


class OverviewPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        root.addWidget(
            page_header(
                "SCUTUM-Q1 — protokol simulyatori",
                "S-MSG va S-FILE spetsifikatsiyasining ijro etiladigan modeli. "
                "Rejimni almashtirib, auditda topilgan kamchiliklarning ta'sirini "
                "jonli ko'rish mumkin.",
            )
        )

        # ---------------- rejim ----------------
        mode_card = Card("Protokol rejimi",
                         "SPEC — hujjatdagidek, aynan. HARDENED — audit tuzatishlari bilan.")
        row = QHBoxLayout()
        row.setSpacing(0)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        for i, (mode, label) in enumerate(
            [(Mode.SPEC, "SPEC"), (Mode.HARDENED, "HARDENED"), (Mode.CUSTOM, "CUSTOM")]
        ):
            b = QPushButton(label)
            b.setObjectName("Seg")
            if i == 0:
                b.setProperty("class", "first")
                b.setObjectName("Seg")
                b.setStyleSheet("border-top-left-radius:8px;border-bottom-left-radius:8px;")
            if i == 2:
                b.setStyleSheet("border-top-right-radius:8px;border-bottom-right-radius:8px;")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mode_group.addButton(b, i)
            row.addWidget(b)
        row.addSpacing(16)
        self.mode_badge = Badge("—", T.PRIMARY)
        row.addWidget(self.mode_badge)
        row.addStretch(1)
        mode_card.add(row)
        self.mode_group.idClicked.connect(self._mode_clicked)
        root.addWidget(mode_card)

        # ---------------- statistika ----------------
        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.tile_fixed = StatTile("Tuzatishlar yoqilgan", "0/14", T.PRIMARY)
        self.tile_crit = StatTile("Kritik topilma", "4", T.FAIL)
        self.tile_high = StatTile("Yuqori topilma", "8", "#FF9E64")
        self.tile_attacks = StatTile("Hujum ssenariysi", "17", T.VIOLET)
        for t in (self.tile_fixed, self.tile_crit, self.tile_high, self.tile_attacks):
            stats.addWidget(t)
        root.addLayout(stats)

        # ---------------- profil ----------------
        prof = Card("Kriptografik profil SCUTUM-Q1",
                    "Barcha algoritmlar `cryptography` (OpenSSL) va `argon2-cffi` "
                    "kutubxonalaridan — o'z qo'lda yozilgan kripto yo'q (spec §2).")
        tbl = Table(["Vazifa", "Algoritm", "Parametr"])
        for r in PROFILE_ROWS:
            tbl.add_row(list(r), [T.MUTED, T.ACCENT, T.DIM], mono_cols=(1,))
        tbl.setMinimumHeight(280)
        tbl.resizeColumnsToContents()
        prof.add(tbl)
        root.addWidget(prof)

        # ---------------- bayroqlar ----------------
        flags = Card(
            "Audit tuzatishlari",
            "Har bir bayroq bitta topilmaga mos keladi. Belgini olib tashlang — "
            "hujum laboratoriyasida tegishli hujum yana ishlay boshlaydi.",
        )
        grid = QGridLayout()
        grid.setSpacing(10)
        self.checks: dict[str, QCheckBox] = {}
        for i, f in enumerate(FLAG_CATALOG):
            box = QWidget()
            box.setObjectName("FlagBox")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(10, 8, 10, 8)
            bl.setSpacing(3)
            head = QHBoxLayout()
            head.setSpacing(8)
            cb = QCheckBox(f.title)
            cb.setStyleSheet("font-weight:600;")
            sev = "KRITIK" if f.finding.startswith("K") else (
                "YUQORI" if f.finding.startswith("Y") else "O'RTA")
            head.addWidget(Badge(f.finding, T.SEVERITY[sev]))
            head.addWidget(cb, 1)
            det = QLabel(f.detail)
            det.setWordWrap(True)
            det.setStyleSheet(f"color:{T.DIM}; font-size:11px;")
            bl.addLayout(head)
            bl.addWidget(det)
            box.setStyleSheet(
                f"QWidget#FlagBox {{ background:{T.SURFACE_2};"
                f" border:1px solid {T.BORDER_SOFT}; border-radius:10px; }}"
            )
            cb.toggled.connect(lambda v, k=f.key: self._flag_toggled(k, v))
            self.checks[f.key] = cb
            grid.addWidget(box, i // 2, i % 2)
        flags.add(grid)
        root.addWidget(flags)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))

        self.state.config_changed.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------------
    def _mode_clicked(self, idx: int) -> None:
        self.state.set_mode([Mode.SPEC, Mode.HARDENED, Mode.CUSTOM][idx])

    def _flag_toggled(self, key: str, value: bool) -> None:
        if getattr(self.state.cfg, key) != value:
            self.state.set_flag(key, value)

    def refresh(self) -> None:
        cfg = self.state.cfg
        idx = {Mode.SPEC: 0, Mode.HARDENED: 1, Mode.CUSTOM: 2}[cfg.mode]
        btn = self.mode_group.button(idx)
        if btn:
            btn.setChecked(True)
        n = self.state.fixed_count
        total = self.state.total_flags
        self.tile_fixed.set_value(
            f"{n}/{total}", T.OK if n == total else (T.FAIL if n == 0 else T.WARN)
        )
        color = {Mode.SPEC: T.FAIL, Mode.HARDENED: T.OK, Mode.CUSTOM: T.WARN}[cfg.mode]
        self.mode_badge.set(cfg.describe(), color)
        for key, cb in self.checks.items():
            cb.blockSignals(True)
            cb.setChecked(getattr(cfg, key))
            cb.blockSignals(False)
