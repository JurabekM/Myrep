"""Moliyaviy kalkulyatorlar sahifasi — sof Python, darhol natija."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.core.exceptions import ValidationError
from app.ui.widgets.common import Card, PageHeader


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


class FinancePage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._finance = container.finance_service

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(PageHeader(
            "Moliyaviy Kalkulyatorlar", "Kredit, zararsizlik nuqtasi, NPV va IRR"
        ))

        root.addWidget(self._build_loan_card())
        root.addWidget(self._build_break_even_card())
        root.addWidget(self._build_npv_card())
        root.addStretch(1)

    def _num(self, field: QLineEdit) -> float:
        text = field.text().strip().replace(" ", "").replace(",", "")
        try:
            return float(text)
        except ValueError:
            return 0.0

    # ------------------------------------------------------------------ loan

    def _build_loan_card(self) -> Card:
        card = Card()
        card.layout().addWidget(QLabel("Kredit kalkulyatori (annuitet)"))
        row = QHBoxLayout()
        self._loan_principal = QLineEdit(); self._loan_principal.setPlaceholderText("Summa, so'm")
        self._loan_rate = QLineEdit(); self._loan_rate.setPlaceholderText("Yillik stavka, %")
        self._loan_months = QLineEdit(); self._loan_months.setPlaceholderText("Muddat, oy")
        for w in (self._loan_principal, self._loan_rate, self._loan_months):
            row.addWidget(w)
        card.layout().addLayout(row)

        btn = QPushButton("Hisoblash"); btn.setObjectName("Primary")
        btn.clicked.connect(self._calc_loan)
        card.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._loan_summary = QLabel(""); self._loan_summary.setTextFormat(Qt.TextFormat.RichText)
        card.layout().addWidget(self._loan_summary)

        self._loan_table = QTableWidget(0, 5)
        self._loan_table.setHorizontalHeaderLabels(
            ["Oy", "To'lov", "Asosiy qarz", "Foiz", "Qoldiq"]
        )
        self._loan_table.setMaximumHeight(220)
        self._loan_table.hide()
        card.layout().addWidget(self._loan_table)
        return card

    def _calc_loan(self) -> None:
        try:
            payment, schedule = self._finance.loan(
                self._num(self._loan_principal),
                self._num(self._loan_rate) / 100,
                int(self._num(self._loan_months)),
            )
        except ValidationError as exc:
            self._loan_summary.setText(f"<span style='color:#f59e0b'>{exc}</span>")
            return
        total = payment * len(schedule)
        self._loan_summary.setText(
            f"Oylik to'lov: <b>{_fmt(payment)}</b> so'm &nbsp;|&nbsp; "
            f"Jami to'lov: <b>{_fmt(total)}</b> so'm &nbsp;|&nbsp; "
            f"Jami foiz: <b>{_fmt(total - self._num(self._loan_principal))}</b> so'm"
        )
        self._loan_table.setRowCount(len(schedule))
        for i, r in enumerate(schedule):
            for j, value in enumerate(
                [str(r.month), _fmt(r.payment), _fmt(r.principal), _fmt(r.interest), _fmt(r.balance)]
            ):
                item = QTableWidgetItem(value)
                if j > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._loan_table.setItem(i, j, item)
        self._loan_table.show()

    # ------------------------------------------------------------ break-even

    def _build_break_even_card(self) -> Card:
        card = Card()
        card.layout().addWidget(QLabel("Zararsizlik nuqtasi (Break-even)"))
        row = QHBoxLayout()
        self._be_fixed = QLineEdit(); self._be_fixed.setPlaceholderText("Doimiy xarajatlar, so'm")
        self._be_price = QLineEdit(); self._be_price.setPlaceholderText("Birlik narxi, so'm")
        self._be_var = QLineEdit(); self._be_var.setPlaceholderText("O'zgaruvchan xarajat/birlik")
        for w in (self._be_fixed, self._be_price, self._be_var):
            row.addWidget(w)
        card.layout().addLayout(row)
        btn = QPushButton("Hisoblash"); btn.setObjectName("Primary")
        btn.clicked.connect(self._calc_break_even)
        card.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._be_result = QLabel(""); self._be_result.setTextFormat(Qt.TextFormat.RichText)
        card.layout().addWidget(self._be_result)
        return card

    def _calc_break_even(self) -> None:
        try:
            result = self._finance.break_even(
                self._num(self._be_fixed), self._num(self._be_price), self._num(self._be_var)
            )
        except ValidationError as exc:
            self._be_result.setText(f"<span style='color:#f59e0b'>{exc}</span>")
            return
        self._be_result.setText(
            f"Zararsizlik hajmi: <b>{_fmt(result.units)}</b> dona/oy &nbsp;|&nbsp; "
            f"Aylanma: <b>{_fmt(result.revenue)}</b> so'm &nbsp;|&nbsp; "
            f"Marja/birlik: <b>{_fmt(result.contribution_margin)}</b> so'm"
        )

    # ------------------------------------------------------------- npv / irr

    def _build_npv_card(self) -> Card:
        card = Card()
        card.layout().addWidget(QLabel("Investitsiya bahosi (NPV / IRR)"))
        self._npv_flows = QLineEdit()
        self._npv_flows.setPlaceholderText(
            "Pul oqimlari, vergul bilan (birinchisi manfiy investitsiya)"
        )
        self._npv_flows.setText("-100000000, 30000000, 40000000, 50000000, 60000000")
        card.layout().addWidget(self._npv_flows)
        row = QHBoxLayout()
        self._npv_rate = QLineEdit(); self._npv_rate.setPlaceholderText("Diskont stavkasi, %")
        self._npv_rate.setText("15")
        self._npv_rate.setFixedWidth(160)
        row.addWidget(self._npv_rate)
        btn = QPushButton("Hisoblash"); btn.setObjectName("Primary")
        btn.clicked.connect(self._calc_npv)
        row.addWidget(btn)
        row.addStretch(1)
        card.layout().addLayout(row)
        self._npv_result = QLabel(""); self._npv_result.setTextFormat(Qt.TextFormat.RichText)
        card.layout().addWidget(self._npv_result)
        return card

    def _calc_npv(self) -> None:
        try:
            flows = [
                float(x.strip()) for x in self._npv_flows.text().split(",") if x.strip()
            ]
        except ValueError:
            self._npv_result.setText("<span style='color:#f59e0b'>Oqimlar noto'g'ri formatda</span>")
            return
        if len(flows) < 2:
            self._npv_result.setText("<span style='color:#f59e0b'>Kamida 2 ta oqim kerak</span>")
            return
        rate = self._num(self._npv_rate) / 100
        npv_value = self._finance.npv(rate, flows)
        try:
            irr_value = f"{self._finance.irr(flows) * 100:.1f}% yillik"
        except ValidationError:
            irr_value = "hisoblab bo'lmadi"
        color = "#22c55e" if npv_value >= 0 else "#ef4444"
        verdict = "foydali" if npv_value >= 0 else "zarar"
        self._npv_result.setText(
            f"NPV: <b style='color:{color}'>{_fmt(npv_value)}</b> so'm ({verdict}) "
            f"&nbsp;|&nbsp; IRR: <b>{irr_value}</b>"
        )
