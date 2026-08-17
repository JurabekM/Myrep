"""Panel 2 — qurilmalar, DC va kalitlar (spec §3)."""
from __future__ import annotations

import time

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...crypto.primitives import (
    ED25519_PK,
    MLDSA65_PK,
    MLKEM768_PK,
    X25519_PK,
)
from ...protocol.identity import fingerprint_words
from .. import theme as T
from ..widgets import Badge, Card, KeyValue, page_header, scroll_page


class DeviceCard(Card):
    def __init__(self, state, getter, parent=None) -> None:
        super().__init__()
        self.state = state
        self.getter = getter

        head = QHBoxLayout()
        self.title = QLabel("—")
        self.title.setObjectName("CardTitle")
        self.badge = Badge("qurilma", T.PRIMARY)
        head.addWidget(self.title)
        head.addWidget(self.badge)
        head.addStretch(1)
        self.add(head)

        self.kv = KeyValue()
        for k in (
            "device_id",
            "fingerprint",
            "xavfsizlik raqami",
            "DC amal qiladi",
            "SPK muddati",
            "OPK zaxirasi",
            "revoke_epoch",
            "ochiq kalit hajmi",
        ):
            self.kv.add_row(k)
        self.add(self.kv)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        for label, slot, obj in [
            ("SPK rotatsiya", self._rotate_spk, "Ghost"),
            ("DIK rotatsiya", self._rotate_dik, "Ghost"),
            ("DC ni yangilash", self._renew_dc, "Ghost"),
            ("OPK to'ldirish", self._refill, "Ghost"),
        ]:
            b = QPushButton(label)
            b.setObjectName(obj)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch(1)
        self.add(btns)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setStyleSheet(f"color:{T.WARN}; font-size:11px;")
        self.add(self.note)

        self._prev_fp: bytes | None = None
        self.refresh()

    # ------------------------------------------------------------------
    def client(self):
        return self.getter(self.state.world)

    def _rotate_spk(self):
        self.client().device.rotate_spk(self.state.cfg)
        self._republish("SPK yangilandi")

    def _rotate_dik(self):
        self.client().device.rotate_dik(self.state.cfg)
        self._republish("DIK yangilandi — fingerprint albatta o'zgaradi")

    def _renew_dc(self):
        self.client().device.renew_dc(self.state.cfg)
        self._republish("DC muddati uzaytirildi (kalitlar O'ZGARMADI)")

    def _refill(self):
        self.client().device.refill_opks(8)
        self._republish("OPK zaxirasi to'ldirildi")

    def _republish(self, msg: str):
        c = self.client()
        self.state.world.server.publish_bundle(c.device_id, c.bundle())
        self.state.trace.info(c.name, msg)
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        c = self.client()
        d = c.device
        fp = c.fingerprint()
        self.title.setText(d.name)
        self.badge.set(
            "bekor qilingan" if d.revoked else "faol",
            T.FAIL if d.revoked else T.OK,
        )
        self.kv.set("device_id", d.device_id.hex())
        self.kv.set("fingerprint", fp.hex())
        self.kv.set("xavfsizlik raqami", fingerprint_words(fp, 6), T.ACCENT)
        now = int(time.time())
        self.kv.set(
            "DC amal qiladi",
            f"{(d.expires_at - now) // 86400} kun",
            T.OK if d.expires_at > now else T.FAIL,
        )
        left = (d.spk_expiry - now) // 86400
        self.kv.set("SPK muddati", f"{left} kun", T.OK if left > 0 else T.FAIL)
        self.kv.set(
            "OPK zaxirasi",
            str(len(d.opks)),
            T.OK if len(d.opks) > 2 else T.WARN,
        )
        self.kv.set("revoke_epoch", str(d.revoke_epoch))
        self.kv.set(
            "ochiq kalit hajmi",
            f"X25519 {X25519_PK}B · Ed25519 {ED25519_PK}B · "
            f"ML-DSA-65 {MLDSA65_PK}B · ML-KEM-768 {MLKEM768_PK}B",
        )

        if self._prev_fp is not None and self._prev_fp != fp:
            self.note.setText(
                "⚠ Xavfsizlik raqami o'zgardi. Agar identity kalitlari "
                "o'zgarmagan bo'lsa — bu Y-7 topilmasi (SPEC rejimda DC "
                "muddati fingerprintga kiradi)."
            )
        self._prev_fp = fp


class DevicesPanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        root.addWidget(
            page_header(
                "Qurilmalar va kalitlar",
                "Spec §3: Device Identity Key, Signed Pre-Key, One-Time Pre-Key "
                "va Device Certificate. `DC ni yangilash` tugmasi Y-7 topilmasini "
                "to'g'ridan-to'g'ri ko'rsatadi.",
            )
        )
        self.cards = []
        for getter in (lambda w: w.alice, lambda w: w.bob, lambda w: w.mallory):
            card = DeviceCard(state, getter)
            self.cards.append(card)
            root.addWidget(card)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))
        self.state.world_changed.connect(self.refresh)

    def refresh(self) -> None:
        for c in self.cards:
            c._prev_fp = None
            c.note.setText("")
            c.refresh()
