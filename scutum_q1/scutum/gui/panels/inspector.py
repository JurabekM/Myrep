"""Panel 7 — paket inspektori: Envelope, AAD va hex dump."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...crypto import canonical
from ...protocol.envelope import Envelope
from .. import theme as T
from ..widgets import (
    Badge,
    Card,
    HexView,
    KeyValue,
    Table,
    fmt_hex,
    page_header,
    scroll_page,
)

AAD_HINT = {
    "v": "protokol versiyasi",
    "suite": "kripto profil nomi",
    "type": "xabar turi",
    "snd": "yuboruvchi device_id",
    "rcv": "qabul qiluvchi device_id",
    "sid": "session_id",
    "no": "message_no",
    "ts": "timestamp",
    "hdr": "ratchet sarlavhasi (spec Envelope'ida YO'Q — K-4)",
}


class InspectorPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        root.addWidget(
            page_header(
                "Paket inspektori",
                "Serverda ushlangan har bir Envelope. Spec §4: v, suite, type, "
                "yuboruvchi/qabul qiluvchi, session_id, message_no va timestamp "
                "AAD ichiga kiritiladi — shuning uchun server ularni "
                "almashtira olmaydi (lekin O'QIY OLADI).",
            )
        )

        bar = QHBoxLayout()
        btn = QPushButton("Yangilash")
        btn.setObjectName("Primary")
        btn.clicked.connect(self.refresh)
        bar.addWidget(btn)
        bar.addStretch(1)
        self.count = Badge("0 paket", T.DIM)
        bar.addWidget(self.count)
        root.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = Card("Ushlangan paketlar")
        self.table = Table(["#", "turi", "yo'nalish", "no", "bayt"])
        self.table.itemSelectionChanged.connect(self.show_detail)
        left.add(self.table)
        split.addWidget(left)

        right_inner = QWidget()
        rl = QVBoxLayout(right_inner)
        rl.setContentsMargins(0, 0, 8, 0)
        rl.setSpacing(12)

        aad_card = Card("AAD maydonlari",
                        "Bu maydonlar autentifikatsiyalangan — o'zgartirilsa "
                        "AEAD tegi buziladi.")
        self.aad = KeyValue()
        aad_card.add(self.aad)
        aad_card.setMinimumHeight(270)
        rl.addWidget(aad_card, 0)

        hdr_card = Card("Ratchet sarlavhasi",
                        "Simulyator qo'shgan maydonlar (spec §4 sxemasida yo'q).")
        self.hdr = KeyValue()
        for k in ("dh", "pn", "n", "pq_ct", "pq_pk", "AAD ichidami"):
            self.hdr.add_row(k)
        hdr_card.add(self.hdr)
        hdr_card.setMinimumHeight(215)
        rl.addWidget(hdr_card, 0)

        body_card = Card("Body (ciphertext)")
        self.hex = HexView()
        self.hex.setMinimumHeight(150)
        body_card.add(self.hex)
        rl.addWidget(body_card, 1)

        split.addWidget(scroll_page(right_inner))
        split.setSizes([560, 720])
        root.addWidget(split, 1)

        self.state.world_changed.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------------
    def _packets(self):
        return self.state.world.server.captured

    def refresh(self) -> None:
        self.table.clear_rows()
        cfg = self.state.cfg
        for i, (_ts, _rcv, wire) in enumerate(self._packets()):
            try:
                env = Envelope.from_wire(wire, cfg)
            except Exception:
                continue
            self.table.add_row(
                [
                    i,
                    env.type,
                    f"{env.sender_device_id.hex()[:6]}→"
                    f"{(env.recipient_device_id or b'').hex()[:6] or '—'}",
                    env.message_no if env.message_no is not None else "—",
                    len(wire),
                ],
                [T.DIM, T.ACCENT, T.MUTED, T.DIM, T.DIM],
                mono_cols=(2,),
            )
        self.table.resizeColumnsToContents()
        self.count.set(f"{self.table.rowCount()} paket",
                       T.PRIMARY if self.table.rowCount() else T.DIM)

    def show_detail(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        packets = self._packets()
        if idx >= len(packets):
            return
        cfg = self.state.cfg
        wire = packets[idx][2]
        try:
            env = Envelope.from_wire(wire, cfg)
        except Exception as exc:  # noqa: BLE001
            self.hex.setPlainText(f"parse xatosi: {exc}")
            return

        d = canonical.decode(wire, cfg.encoding)
        for k in list(self.aad._rows):
            self.aad.set(k, "—", T.DIM)
        for k, v in env.aad_fields(cfg).items():
            if k == "hdr":
                continue
            txt = fmt_hex(v, 8) if isinstance(v, (bytes, bytearray)) else str(v)
            row = self.aad._rows.get(k) or self.aad.add_row(k)
            row.setToolTip(AAD_HINT.get(k, ""))
            self.aad.set(k, txt, T.ACCENT if isinstance(v, bytes) else T.TEXT)

        h = d.get("hdr")
        if h:
            self.hdr.set("dh", fmt_hex(h["dh"], 12), T.ACCENT)
            self.hdr.set("pn", str(h["pn"]))
            self.hdr.set("n", str(h["n"]))
            self.hdr.set("pq_ct", fmt_hex(h.get("pq_ct"), 10) +
                         (f"  ({len(h['pq_ct'])} B)" if h.get("pq_ct") else ""),
                         T.VIOLET if h.get("pq_ct") else T.DIM)
            self.hdr.set("pq_pk", fmt_hex(h.get("pq_pk"), 10), T.VIOLET)
            self.hdr.set(
                "AAD ichidami",
                "HA — himoyalangan" if cfg.header_in_aad else "YO'Q — o'zgartirsa bo'ladi",
                T.OK if cfg.header_in_aad else T.FAIL,
            )
        else:
            for k in ("dh", "pn", "n", "pq_ct", "pq_pk", "AAD ichidami"):
                self.hdr.set(k, "—", T.DIM)

        self.hex.show_bytes(env.body)
