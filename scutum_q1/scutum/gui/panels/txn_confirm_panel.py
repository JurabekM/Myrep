"""ROSTOR panel 2 — Tranzaksiya tasdiqlash (markaziy anti-vishing oqimi)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...rostor.txn_confirm import (
    create_txn_confirm_request,
    create_txn_confirm_response,
    verify_txn_confirm_response,
)
from ...sim.rostor_world import RostorWorld
from .. import theme as T
from ..widgets import Badge, Card, KeyValue, LogView, page_header, scroll_page


class TxnConfirmPanel(QWidget):
    def __init__(self, state=None, parent=None) -> None:
        super().__init__(parent)
        self.world = RostorWorld()
        self.pending_request = None
        self.account_id = b"\xAA" * 16

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        root.addWidget(page_header(
            "Tranzaksiya tasdiqlash — anti-vishing markaziy mexanizmi",
            "Spec §11-12: aytiladigan/yoziladigan kod UMUMAN YO'Q. Foydalanuvchi "
            "faqat ko'rgan (WYSIWYS) ma'lumotni imzolaydi. "
            "'Bank sizdan hech qachon kod SO'RAMAYDI. Agar so'rasa — bu firibgar.'",
        ))

        form = Card("Bank so'rovi yaratish")
        row1 = QHBoxLayout()
        self.inst_box = QComboBox()
        self.amount_box = QSpinBox()
        self.amount_box.setRange(1000, 999_999_999)
        self.amount_box.setValue(350_000)
        self.amount_box.setSuffix(" so'm")
        self.amount_box.setGroupSeparatorShown(True)
        self.recipient_edit = QLineEdit("****1234")
        self.purpose_edit = QLineEdit("Pul o'tkazish")
        row1.addWidget(self.inst_box)
        row1.addWidget(self.amount_box)
        row1.addWidget(self.recipient_edit)
        row1.addWidget(self.purpose_edit)
        form.add(row1)
        btn_send = QPushButton("Bank so'rovni yuboradi")
        btn_send.setObjectName("Primary")
        btn_send.clicked.connect(self.send_request)
        form.add(btn_send)
        root.addWidget(form)

        display = Card(
            "Foydalanuvchi ekranida ko'rinadigan narsa (WYSIWYS)",
            "Bu maydonlar `TxnConfirmRequest.render_for_display()` dan — imzolanadigan "
            "struktura bilan AYNAN bir xil, alohida 'displey matni' yo'q.",
        )
        self.badge = Badge("so'rov yo'q", T.DIM)
        display.add(self.badge)
        self.display_kv = KeyValue()
        for k in ("Institutsiya", "Summa", "Qabul qiluvchi", "Maqsad", "Muddat"):
            self.display_kv.add_row(k)
        display.add(self.display_kv)
        row2 = QHBoxLayout()
        btn_approve = QPushButton("✓ Tasdiqlash")
        btn_approve.setObjectName("Primary")
        btn_approve.clicked.connect(lambda: self.respond("APPROVE"))
        btn_deny = QPushButton("✗ Rad etish")
        btn_deny.setObjectName("Danger")
        btn_deny.clicked.connect(lambda: self.respond("DENY"))
        row2.addWidget(btn_approve)
        row2.addWidget(btn_deny)
        row2.addStretch(1)
        display.add(row2)
        root.addWidget(display)

        attack = Card(
            "Relay hujumi (R7 sinovi)",
            "Kichik, zararsiz operatsiya uchun olingan tasdiqni katta operatsiyaga "
            "'yopishtirish' — request_hash to'liq so'rovni qamragani uchun rad etiladi.",
        )
        btn_relay = QPushButton("Relay hujumini sinash")
        btn_relay.setObjectName("Danger")
        btn_relay.clicked.connect(self.run_relay_attack)
        attack.add(btn_relay)
        root.addWidget(attack)

        log_card = Card("Jurnal")
        self.log = LogView()
        self.log.setMinimumHeight(160)
        log_card.add(self.log)
        root.addWidget(log_card)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))

        self.refresh_institutions()

    # ------------------------------------------------------------------
    def refresh_institutions(self) -> None:
        self.inst_box.clear()
        for name in self.world.institutions:
            self.inst_box.addItem(name)

    def send_request(self) -> None:
        name = self.inst_box.currentText()
        if not name:
            return
        inst = self.world.institutions[name]
        req = create_txn_confirm_request(
            inst.idc, inst.keys.institution_id,
            amount_minor=self.amount_box.value() * 100, currency="UZS",
            recipient_masked=self.recipient_edit.text(), purpose=self.purpose_edit.text(),
        )
        self.pending_request = req
        d = req.render_for_display()
        self.badge.set(f"✓ Tasdiqlangan bank: {name}", T.OK)
        self.display_kv.set("Institutsiya", name, T.OK)
        self.display_kv.set("Summa", f"{d['amount_minor']/100:,.0f} {d['currency']}")
        self.display_kv.set("Qabul qiluvchi", d["recipient_masked"])
        self.display_kv.set("Maqsad", d["purpose"])
        self.display_kv.set("Muddat", f"{req.expires_at} (TTL ~120s)")
        self.log.append_line(
            f"[{name}] TXN_CONFIRM_REQUEST yuborildi: {d['amount_minor']/100:,.0f} so'm "
            f"-> {d['recipient_masked']}", T.INFO,
        )

    def respond(self, decision: str) -> None:
        if self.pending_request is None:
            self.log.append_line("Avval so'rov yuboring.", T.WARN)
            return
        user = self.world.citizens["Alisa"]
        resp = create_txn_confirm_response(user, self.pending_request, decision, self.account_id)
        ok = verify_txn_confirm_response(resp, user.dc(), self.pending_request)
        color = T.OK if decision == "APPROVE" else T.WARN
        self.log.append_line(
            f"Foydalanuvchi javobi: {decision} — device_sig tekshirildi: {ok}", color,
        )
        self.pending_request = None
        self.badge.set("so'rov yo'q", T.DIM)

    def run_relay_attack(self) -> None:
        name = self.inst_box.currentText()
        if not name:
            self.log.append_line("Avval institutsiya tanlang.", T.WARN)
            return
        inst = self.world.institutions[name]
        user = self.world.citizens["Alisa"]

        small = create_txn_confirm_request(
            inst.idc, inst.keys.institution_id, amount_minor=1_000_00,
            currency="UZS", recipient_masked="****0001", purpose="kichik xarid",
        )
        big = create_txn_confirm_request(
            inst.idc, inst.keys.institution_id, amount_minor=35_000_000_00,
            currency="UZS", recipient_masked="****9999 (noma'lum)", purpose="katta o'tkazma",
        )
        resp_for_small = create_txn_confirm_response(user, small, "APPROVE", self.account_id)
        forged_ok = verify_txn_confirm_response(resp_for_small, user.dc(), big)

        self.log.append_line(
            f"Hujumchi: 1,000 so'mlik tasdiqni 350,000,000 so'mlik operatsiyaga "
            f"yopishtirmoqchi -> {'MUVAFFAQIYATLI (XATO!)' if forged_ok else 'RAD ETILDI'}",
            T.FAIL if forged_ok else T.OK,
        )
