"""ROSTOR panel 1 — Institutsiyalar va tasdiqlangan jo'natuvchi belgisi."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...crypto.primitives import hybrid_sign
from ...rostor.badge import Badge, derive_badge
from ...sim.rostor_world import RostorWorld
from .. import theme as T
from ..widgets import Badge as BadgeWidget, Card, KeyValue, Table, fmt_hex, page_header, scroll_page


class InstitutionsPanel(QWidget):
    def __init__(self, state=None, parent=None) -> None:
        super().__init__(parent)
        self.world = RostorWorld()

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        root.addWidget(page_header(
            "Institutsiyalar va tasdiqlangan jo'natuvchi",
            "Spec §4, §9, §10: registrator konsorsiumi k-of-n tasdig'i bilan "
            "institutsiya (IC) ro'yxatdan o'tkazadi; IC o'z SCUTUM-Q1 "
            "qurilmasini (IDC) endorsement bilan tasdiqlaydi. `derive_badge` "
            "— deterministik, auditga ochiq funksiya.",
        ))

        bar = QHBoxLayout()
        btn_reset = QPushButton("Dunyoni qayta qurish")
        btn_reset.setObjectName("Primary")
        btn_reset.clicked.connect(self.rebuild)
        btn_add = QPushButton("Yangi institutsiya ro'yxatdan o'tkazish")
        btn_add.clicked.connect(self.add_institution)
        bar.addWidget(btn_reset)
        bar.addWidget(btn_add)
        bar.addStretch(1)
        root.addLayout(bar)

        consort = Card("Registrator konsorsiumi", "§4.1 — genesis anchor, k-of-n alohida gibrid imzo")
        self.consort_kv = KeyValue()
        for k in ("a'zolar soni", "kvorum (k)", "joriy roster_epoch"):
            self.consort_kv.add_row(k)
        consort.add(self.consort_kv)
        root.addWidget(consort)

        inst_card = Card("Ro'yxatdan o'tgan institutsiyalar")
        self.inst_table = Table(["Nom", "Kategoriya", "institution_id", "Holat"])
        self.inst_table.setMinimumHeight(160)
        inst_card.add(self.inst_table)
        root.addWidget(inst_card)

        badge_card = Card(
            "Belgi tekshiruvchisi",
            "Xabarni turli jo'natuvchi nomidan 'imzolab' ko'ring — fishing "
            "hech qachon VERIFIED bo'lolmasligini kuzating.",
        )
        row = QHBoxLayout()
        self.sender_box = QComboBox()
        self.sender_box.addItem("(institutsiyalar hali yuklanmagan)")
        self.msg_edit = QLineEdit("350000 so'mni ****1234 kartaga o'tkazish")
        btn_check = QPushButton("Belgini tekshirish")
        btn_check.setObjectName("Primary")
        btn_check.clicked.connect(self.check_badge)
        row.addWidget(self.sender_box, 1)
        row.addWidget(self.msg_edit, 2)
        row.addWidget(btn_check)
        badge_card.add(row)
        self.badge_result = BadgeWidget("—", T.DIM)
        badge_card.add(self.badge_result)
        root.addWidget(badge_card)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))

        self.refresh()

    # ------------------------------------------------------------------
    def rebuild(self) -> None:
        self.world = RostorWorld()
        self.refresh()

    def add_institution(self) -> None:
        n = len(self.world.institutions) + 1
        self.world.register_institution(f"Yangi-institutsiya-{n}", "marketplace")
        self.refresh()

    def refresh(self) -> None:
        w = self.world
        self.consort_kv.set("a'zolar soni", str(len(w.members)))
        self.consort_kv.set("kvorum (k)", f"{w.k} / {len(w.members)}")
        self.consort_kv.set("joriy roster_epoch", str(w.roster.epoch))

        self.inst_table.clear_rows()
        for name, inst in w.institutions.items():
            revoked = inst.keys.revoked_at is not None
            self.inst_table.add_row(
                [name, inst.keys.category, fmt_hex(inst.keys.institution_id, 8),
                 "BEKOR QILINGAN" if revoked else "faol"],
                [T.TEXT, T.MUTED, T.ACCENT, T.FAIL if revoked else T.OK],
                mono_cols=(2,),
            )
        self.inst_table.resizeColumnsToContents()

        self.sender_box.clear()
        for name in w.institutions:
            self.sender_box.addItem(f"✓ {name} (haqiqiy kalit bilan)")
        self.sender_box.addItem("⚠ Mallory (firibgar, hech qanday IC/IDC yo'q)")

    def check_badge(self) -> None:
        idx = self.sender_box.currentIndex()
        names = list(self.world.institutions)
        msg = self.msg_edit.text().encode("utf-8")
        snap = self.world.snapshot()

        if idx < len(names):
            inst = self.world.institutions[names[idx]]
            idc_dc = inst.idc.dc()
            sig = hybrid_sign(inst.idc.ik_ed, inst.idc.ik_mldsa, msg)
        else:
            fr = self.world.fraudster
            idc_dc = fr.dc()
            sig = hybrid_sign(fr.ik_ed, fr.ik_mldsa, msg)

        result = derive_badge(idc_dc=idc_dc, sig=sig, signed_payload=msg, snapshot=snap)
        color = {
            Badge.VERIFIED: T.OK, Badge.REVOKED: T.FAIL, Badge.INVALID_SIGNATURE: T.FAIL,
            Badge.KNOWN_MALICIOUS: T.FAIL, Badge.FLAGGED: T.WARN, Badge.UNVERIFIED: T.DIM,
        }[result.badge]
        label = result.badge.value
        if result.display_name:
            label = f"✓ Tasdiqlangan: {result.display_name}" if result.badge == Badge.VERIFIED else \
                    f"{result.badge.value}: {result.display_name}"
        self.badge_result.set(label, color)
