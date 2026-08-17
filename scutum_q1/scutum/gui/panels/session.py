"""Panel 3 — S-MSG sessiya: INIT -> ACK -> MSG jonli oqimi (spec §11.2)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...protocol.envelope import Envelope
from .. import theme as T
from ..widgets import Badge, Card, KeyValue, Table, page_header


class Bubble(QFrame):
    def __init__(self, who: str, text: str, meta: str, ok: bool, mine: bool):
        super().__init__()
        color = T.PRIMARY if mine else T.ACCENT
        if who == "sim":
            color = T.VIOLET
        if not ok:
            color = T.FAIL
        self.setObjectName("Bubble")
        # DIQQAT: selektor obyekt nomi bilan cheklanadi, aks holda uslub
        # ichkaridagi QLabel'larga ham tarqaladi va soxta ramkalar chiqadi.
        self.setStyleSheet(
            f"QFrame#Bubble {{ background:{T.SURFACE_2};"
            f" border:1px solid {T.BORDER_SOFT};"
            f" border-left:3px solid {color}; border-radius:8px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(11, 8, 11, 8)
        lay.setSpacing(3)
        head = QHBoxLayout()
        n = QLabel(who)
        n.setStyleSheet(f"color:{color}; font-weight:600; font-size:11px;")
        m = QLabel(meta)
        m.setStyleSheet(f"color:{T.DIM}; font-size:10px;")
        head.addWidget(n)
        head.addStretch(1)
        head.addWidget(m)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setStyleSheet(f"color:{T.TEXT if ok else T.FAIL}; font-size:12px;")
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addLayout(head)
        lay.addWidget(body)


class ChatColumn(QWidget):
    def __init__(self, title: str, accent: str):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{accent}; font-weight:700; font-size:14px;")
        self.badge = Badge("sessiya yo'q", T.DIM)
        head.addWidget(t)
        head.addStretch(1)
        head.addWidget(self.badge)
        lay.addLayout(head)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.holder = QWidget()
        self.vbox = QVBoxLayout(self.holder)
        self.vbox.setContentsMargins(2, 2, 2, 2)
        self.vbox.setSpacing(7)
        self.vbox.addStretch(1)
        self.area.setWidget(self.holder)
        self.area.setObjectName("ChatArea")
        self.area.setStyleSheet(
            f"QScrollArea#ChatArea {{ background:{T.SURFACE};"
            f" border:1px solid {T.BORDER_SOFT}; border-radius:10px; }}"
        )
        lay.addWidget(self.area, 1)

    def add(self, w: QWidget) -> None:
        self.vbox.insertWidget(self.vbox.count() - 1, w)
        bar = self.area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear(self) -> None:
        while self.vbox.count() > 1:
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class SessionPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        root.addWidget(
            page_header(
                "S-MSG sessiyasi",
                "Spec §5–§6: INIT → ACK → MSG. Server o'rtada turadi va faqat "
                "shifrlangan Envelope'ni ko'radi.",
            )
        )

        # ---------------- toolbar ----------------
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_hs = QPushButton("Handshake (INIT → ACK)")
        self.btn_hs.setObjectName("Primary")
        self.btn_hs.clicked.connect(self.do_handshake)
        self.btn_pq = QPushButton("PQ ratchet")
        self.btn_pq.clicked.connect(self.do_pq)
        self.btn_pq.setEnabled(False)
        self.btn_burst = QPushButton("10 ta xabar")
        self.btn_burst.clicked.connect(self.do_burst)
        self.btn_burst.setEnabled(False)
        self.btn_reset = QPushButton("Qayta boshlash")
        self.btn_reset.setObjectName("Ghost")
        self.btn_reset.clicked.connect(lambda: self.state.rebuild())
        for b in (self.btn_hs, self.btn_pq, self.btn_burst, self.btn_reset):
            bar.addWidget(b)
        bar.addStretch(1)
        self.sess_badge = Badge("sessiya ochilmagan", T.DIM)
        bar.addWidget(self.sess_badge)
        root.addLayout(bar)

        # ---------------- 3 ustun ----------------
        split = QSplitter(Qt.Orientation.Horizontal)
        self.col_a = ChatColumn("Alisa", T.PRIMARY)
        self.col_b = ChatColumn("Bobur", T.ACCENT)

        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(8)
        h = QLabel("Ishonchsiz server")
        h.setStyleSheet(f"color:{T.WARN}; font-weight:700; font-size:14px;")
        ml.addWidget(h)
        note = QLabel("Server faqat quyidagilarni ko'radi:")
        note.setStyleSheet(f"color:{T.DIM}; font-size:11px;")
        ml.addWidget(note)
        self.wire = Table(["turi", "yo'n.", "no", "bayt"])
        self.wire.setMinimumWidth(260)
        ml.addWidget(self.wire, 1)
        self.srv_kv = KeyValue()
        for k in ("navbatda", "yetkazildi", "ushlangan", "bundle"):
            self.srv_kv.add_row(k)
        ml.addWidget(self.srv_kv)

        split.addWidget(self.col_a)
        split.addWidget(mid)
        split.addWidget(self.col_b)
        split.setSizes([420, 300, 420])
        root.addWidget(split, 1)

        # ---------------- input ----------------
        inp = QHBoxLayout()
        inp.setSpacing(8)
        self.who = QPushButton("Alisa →")
        self.who.setCheckable(True)
        self.who.setChecked(True)
        self.who.clicked.connect(self._toggle_who)
        self.who.setFixedWidth(110)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Xabar matni…")
        self.edit.returnPressed.connect(self.do_send)
        self.edit.setEnabled(False)
        self.btn_send = QPushButton("Yuborish")
        self.btn_send.setObjectName("Primary")
        self.btn_send.clicked.connect(self.do_send)
        self.btn_send.setEnabled(False)
        inp.addWidget(self.who)
        inp.addWidget(self.edit, 1)
        inp.addWidget(self.btn_send)
        root.addLayout(inp)

        self.state.world_changed.connect(self.reset_view)
        self.refresh_server()

    # ------------------------------------------------------------------
    @property
    def w(self):
        return self.state.world

    def _toggle_who(self) -> None:
        self.who.setText("Alisa →" if self.who.isChecked() else "Bobur →")

    def reset_view(self) -> None:
        self.col_a.clear()
        self.col_b.clear()
        self.wire.clear_rows()
        self.sess_badge.set("sessiya ochilmagan", T.DIM)
        for b in (self.btn_pq, self.btn_burst, self.btn_send):
            b.setEnabled(False)
        self.edit.setEnabled(False)
        self.btn_hs.setEnabled(True)
        self.refresh_server()

    # ------------------------------------------------------------------
    def do_handshake(self) -> None:
        try:
            sid = self.w.handshake()
        except Exception as exc:  # noqa: BLE001
            self._sys(f"Handshake muvaffaqiyatsiz: {exc}", ok=False)
            return
        self.sess_badge.set(f"sessiya {sid.hex()[:8]}", T.OK)
        self._sys(f"INIT → ACK bajarildi · sessiya {sid.hex()[:8]}")
        self.col_a.badge.set("initiator", T.PRIMARY)
        self.col_b.badge.set("responder", T.ACCENT)
        for b in (self.btn_pq, self.btn_burst, self.btn_send):
            b.setEnabled(True)
        self.edit.setEnabled(True)
        self.btn_hs.setEnabled(False)
        self.edit.setFocus()
        self.refresh_server()

    def do_send(self) -> None:
        text = self.edit.text().strip()
        if not text:
            return
        sender = self.w.alice if self.who.isChecked() else self.w.bob
        self._send_one(sender, text)
        self.edit.clear()

    def do_burst(self) -> None:
        for i in range(10):
            sender = self.w.alice if i % 2 == 0 else self.w.bob
            self._send_one(sender, f"avtomatik xabar #{i}")

    def _send_one(self, sender, text: str) -> None:
        before = len(self.w.server.metadata_log)
        try:
            line = self.w.send(sender, text)
        except Exception as exc:  # noqa: BLE001
            self._sys(f"Yuborib bo'lmadi: {exc}", ok=False)
            return
        rec = self.w.server.metadata_log[before] if len(
            self.w.server.metadata_log) > before else {}
        meta = f"no={rec.get('no')} · {rec.get('bytes', 0)} bayt"
        mine_col = self.col_a if sender is self.w.alice else self.col_b
        peer_col = self.col_b if sender is self.w.alice else self.col_a
        mine_col.add(Bubble(sender.name, text, meta, True, True))
        if line.ok:
            peer_col.add(Bubble(sender.name, line.text, meta, True, False))
        else:
            peer_col.add(Bubble(sender.name, f"❌ {line.detail}", meta, False, False))
        self.refresh_server()

    def do_pq(self) -> None:
        try:
            self.w.pq_ratchet(self.w.alice)
        except Exception as exc:  # noqa: BLE001
            self._sys(f"PQ ratchet xatosi: {exc}", ok=False)
            return
        st = self.w.alice.sessions[self.w.session_id].state
        self._sys(
            f"🔄 Post-kvant ratchet bajarildi — ML-KEM siri root-key'ga "
            f"aralashtirildi (PQ qadam #{st.pq_steps})"
        )
        self.refresh_server()

    def _sys(self, text: str, ok: bool = True) -> None:
        for col in (self.col_a, self.col_b):
            col.add(Bubble("sim", text, "", ok, False))

    # ------------------------------------------------------------------
    def refresh_server(self) -> None:
        s = self.w.server
        self.wire.clear_rows()
        for r in s.metadata_log[-40:]:
            self.wire.add_row(
                [r["type"], f"{r['snd']}→{r['rcv']}", r["no"], r["bytes"]],
                [T.ACCENT, T.MUTED, T.DIM, T.DIM],
                mono_cols=(1,),
            )
        self.wire.resizeColumnsToContents()
        st = s.stats()
        self.srv_kv.set("navbatda", str(st["queued"]))
        self.srv_kv.set("yetkazildi", str(st["delivered"]))
        self.srv_kv.set("ushlangan", str(st["captured"]))
        self.srv_kv.set("bundle", str(st["bundles"]))
