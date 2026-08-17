"""Panel 4 — Double Ratchet holati vizualizatori (spec §6)."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import theme as T
from ..widgets import Badge, Card, KeyValue, StatTile, fmt_hex, page_header, scroll_page

FIELDS = [
    ("RK", "root key (64 bayt)"),
    ("CKs", "yuborish chain key"),
    ("CKr", "qabul chain key"),
    ("DHs_pk", "bizning ratchet ochiq kalitimiz"),
    ("DHr_pk", "peer ratchet ochiq kaliti"),
    ("Ns", "chain ichidagi yuborish tartibi"),
    ("Nr", "chain ichidagi qabul tartibi"),
    ("PN", "oldingi chain uzunligi"),
    ("message_no", "envelope tartib raqami (global)"),
    ("skipped", "saqlangan o'tkazib yuborilgan kalitlar"),
]


class SideCard(Card):
    def __init__(self, title: str, accent: str, getter):
        super().__init__()
        self.getter = getter
        head = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{accent}; font-weight:700; font-size:15px;")
        self.badge = Badge("—", T.DIM)
        head.addWidget(t)
        head.addStretch(1)
        head.addWidget(self.badge)
        self.add(head)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.t_dh = StatTile("DH qadam", "0", T.PRIMARY)
        self.t_pq = StatTile("PQ qadam", "0", T.VIOLET)
        self.t_skip = StatTile("Skipped", "0", T.WARN)
        for s in (self.t_dh, self.t_pq, self.t_skip):
            stats.addWidget(s)
        self.add(stats)

        self.kv = KeyValue()
        for name, hint in FIELDS:
            row = self.kv.add_row(name)
            row.setToolTip(hint)
        self.add(self.kv)

    def refresh(self, state) -> None:
        snap = self.getter(state)
        if snap is None:
            self.badge.set("sessiya yo'q", T.DIM)
            for name, _ in FIELDS:
                self.kv.set(name, "—", T.DIM)
            return
        self.badge.set(snap["role"], T.OK)
        self.t_dh.set_value(snap["dh_steps"])
        self.t_pq.set_value(snap["pq_steps"], T.VIOLET if snap["pq_steps"] else T.DIM)
        self.t_skip.set_value(snap["skipped"])
        for name, _ in FIELDS:
            v = snap.get(name)
            if isinstance(v, (bytes, bytearray)):
                self.kv.set(name, fmt_hex(bytes(v), 14), T.ACCENT)
            elif v is None:
                self.kv.set(name, "—", T.DIM)
            else:
                self.kv.set(name, str(v), T.TEXT)


class RatchetPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        root.addWidget(
            page_header(
                "Double Ratchet holati",
                "Spec §6. SPEC rejimda `CKs`/`CKr` xabar yuborilganda O'ZGARMAYDI "
                "— aynan shu K-3 topilmasi. HARDENED rejimda har xabarda siljiydi.",
            )
        )

        warn = Card()
        self.warn_lbl = QLabel()
        self.warn_lbl.setWordWrap(True)
        warn.add(self.warn_lbl)
        root.addWidget(warn)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        for label, slot in [
            ("Alisa → Bobur xabar", lambda: self._send(True)),
            ("Bobur → Alisa xabar", lambda: self._send(False)),
            ("PQ ratchet (Alisa)", self._pq),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        root.addLayout(bar)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        self.card_a = SideCard("Alisa", T.PRIMARY, lambda s: self._snap(s.world.alice))
        self.card_b = SideCard("Bobur", T.ACCENT, lambda s: self._snap(s.world.bob))
        cols.addWidget(self.card_a)
        cols.addWidget(self.card_b)
        root.addLayout(cols)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))

        self.state.world_changed.connect(self.refresh)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(1200)
        self.refresh()

    # ------------------------------------------------------------------
    def _snap(self, client):
        sid = self.state.world.session_id
        if sid is None or sid not in client.sessions:
            return None
        return client.sessions[sid].state.snapshot()

    def _ensure(self) -> bool:
        if self.state.world.session_id is None:
            try:
                self.state.world.handshake()
            except Exception:
                return False
        return True

    def _send(self, from_alice: bool) -> None:
        if not self._ensure():
            return
        w = self.state.world
        try:
            w.send(w.alice if from_alice else w.bob, "ratchet sinovi")
        except Exception as exc:  # noqa: BLE001
            self.state.trace.fail("sim", str(exc))
        self.refresh()

    def _pq(self) -> None:
        if not self._ensure():
            return
        try:
            self.state.world.pq_ratchet(self.state.world.alice)
        except Exception as exc:  # noqa: BLE001
            self.state.trace.fail("sim", str(exc))
        self.refresh()

    def refresh(self) -> None:
        self.card_a.refresh(self.state)
        self.card_b.refresh(self.state)
        if self.state.cfg.advance_chain_key:
            self.warn_lbl.setText(
                "✅ <b>advance_chain_key</b> yoqilgan: "
                "MK = HMAC(CK,0x01), CK ← HMAC(CK,0x02). Zanjir bir tomonlama — "
                "o'g'irlangan CK o'tgan xabarlarni ochmaydi."
            )
            self.warn_lbl.setStyleSheet(f"color:{T.OK}; font-size:12px;")
        else:
            self.warn_lbl.setText(
                "⚠ <b>SPEC formulasi</b>: MK = HKDF(CK, salt=\"SCUTUM-Q1/MSG\", "
                "info=session_id‖message_no). <b>CK o'zgarmaydi</b> — pastdagi "
                "CKs/CKr qiymatlari xabar yuborilganda ham o'sha bo'lib qolishini "
                "kuzating. Bu chain ichida forward secrecy'ning yo'qligini "
                "bildiradi (topilma K-3)."
            )
            self.warn_lbl.setStyleSheet(f"color:{T.WARN}; font-size:12px;")
