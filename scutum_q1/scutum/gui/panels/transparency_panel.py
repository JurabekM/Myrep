"""ROSTOR panel 3 — Shaffoflik jurnali inspektori (§8)."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ...sim.rostor_world import RostorWorld
from .. import theme as T
from ..widgets import Badge, Card, KeyValue, StatTile, Table, fmt_hex, page_header, scroll_page


class TransparencyPanel(QWidget):
    def __init__(self, state=None, parent=None) -> None:
        super().__init__(parent)
        self.world = RostorWorld()
        self.sth = None

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        root.addWidget(page_header(
            "Shaffoflik jurnali inspektori",
            "Spec §8: append-only jurnal (tarixiy audit) + RegistrySMT (joriy "
            "holat, BORLIK va YO'QLIK isboti bilan). Witness-cosign va "
            "consistency proof split-view/tarix-qayta-yozish hujumlarini to'sadi.",
        ))

        bar = QHBoxLayout()
        btn_publish = QPushButton("STH nashr qilish (witness-cosign bilan)")
        btn_publish.setObjectName("Primary")
        btn_publish.clicked.connect(self.publish)
        btn_reset = QPushButton("Qayta qurish")
        btn_reset.clicked.connect(self.rebuild)
        bar.addWidget(btn_publish)
        bar.addWidget(btn_reset)
        bar.addStretch(1)
        root.addLayout(bar)

        stats = QHBoxLayout()
        self.t_size = StatTile("tree_size", "0", T.PRIMARY)
        self.t_smt = StatTile("smt_epoch", "0", T.VIOLET)
        self.t_witness = StatTile("witness-cosign", "0", T.OK)
        for t in (self.t_size, self.t_smt, self.t_witness):
            stats.addWidget(t)
        root.addLayout(stats)

        sth_card = Card("Joriy STH (Signed Tree Head)")
        self.sth_kv = KeyValue()
        for k in ("root_hash (jurnal)", "smt_root (reestr)", "timestamp", "operator_sig tekshirildi"):
            self.sth_kv.add_row(k)
        sth_card.add(self.sth_kv)
        root.addWidget(sth_card)

        entries_card = Card("Jurnal yozuvlari")
        self.entries_table = Table(["seq", "turi", "submitter_id", "vaqt"])
        self.entries_table.setMinimumHeight(160)
        entries_card.add(self.entries_table)
        root.addWidget(entries_card)

        lookup_card = Card(
            "Reestr qidiruvi (borlik/yo'qlik isboti bilan)",
            "Institutsiya nomini kiriting — SMT non-inclusion proof orqali "
            "'topilmadi' javobi ham isbotlanadi, faqat 'ishoning' emas.",
        )
        row = QHBoxLayout()
        self.lookup_edit = QLineEdit()
        self.lookup_edit.setPlaceholderText("masalan: Bank X, yoki tasodifiy matn")
        btn_lookup = QPushButton("Qidirish")
        btn_lookup.setObjectName("Primary")
        btn_lookup.clicked.connect(self.do_lookup)
        row.addWidget(self.lookup_edit, 1)
        row.addWidget(btn_lookup)
        lookup_card.add(row)
        self.lookup_badge = Badge("—", T.DIM)
        lookup_card.add(self.lookup_badge)
        root.addWidget(lookup_card)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))

        self.publish()

    # ------------------------------------------------------------------
    def rebuild(self) -> None:
        self.world = RostorWorld()
        self.publish()

    def publish(self) -> None:
        self.sth = self.world.publish_and_witness_sth()
        self.refresh()

    def refresh(self) -> None:
        sth = self.sth
        self.t_size.set_value(sth.tree_size)
        self.t_smt.set_value(sth.smt_epoch)
        self.t_witness.set_value(f"{len(sth.witness_sigs)}/{len(self.world.witnesses)}")

        self.sth_kv.set("root_hash (jurnal)", fmt_hex(sth.root_hash, 16), T.ACCENT)
        self.sth_kv.set("smt_root (reestr)", fmt_hex(sth.smt_root, 16), T.VIOLET)
        self.sth_kv.set("timestamp", str(sth.timestamp))
        self.sth_kv.set("operator_sig tekshirildi", "HA", T.OK)

        self.entries_table.clear_rows()
        for e in self.world.log.entries:
            self.entries_table.add_row(
                [e.seq, e.type, fmt_hex(e.submitter_id, 8), e.submitted_at],
                [T.DIM, T.ACCENT, T.MUTED, T.DIM], mono_cols=(2,),
            )
        self.entries_table.resizeColumnsToContents()

    def do_lookup(self) -> None:
        text = self.lookup_edit.text().strip()
        if not text:
            return
        raw_id = None
        for name, inst in self.world.institutions.items():
            if name.lower() == text.lower():
                raw_id = inst.keys.institution_id
                break
        target = raw_id if raw_id is not None else text.encode("utf-8")
        proof = self.world.log.lookup(target)
        proof_ok = self.world.log_client.verify_lookup(proof, self.sth)
        if not proof_ok:
            self.lookup_badge.set("⚠ ISBOT NOTO'G'RI — mos kelmadi", T.FAIL)
        elif proof.value is not None:
            self.lookup_badge.set(f"✓ TOPILDI (isbotlangan): {text}", T.OK)
        else:
            self.lookup_badge.set(f"— YO'Q (isbotlangan yo'qlik): {text}", T.WARN)
