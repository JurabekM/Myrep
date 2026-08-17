"""Soliq kalkulyatori sahifasi — deterministik hisob + AI tushuntirish."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.services.calculators.tax_calculator import TaxRegime, TaxResult
from app.ui.widgets.common import Card, PageHeader
from app.ui.widgets.markdown_view import MarkdownView
from app.ui.widgets.workers import CallableRunnable


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


class TaxPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._pool = QThreadPool.globalInstance()

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
            "Soliq Kalkulyatori",
            "Raqamlar deterministik hisoblanadi — AI faqat tushuntiradi",
        ))

        # --- Rejim taqqoslash ---
        compare_card = Card()
        compare_card.layout().addWidget(QLabel("Soliq rejimini taqqoslash"))
        form = QHBoxLayout()
        self._revenue = QLineEdit()
        self._revenue.setPlaceholderText("Yillik aylanma, so'm")
        self._expenses = QLineEdit()
        self._expenses.setPlaceholderText("Yillik xarajatlar, so'm")
        form.addWidget(self._revenue)
        form.addWidget(self._expenses)
        compare_card.layout().addLayout(form)

        btn_row = QHBoxLayout()
        calc_btn = QPushButton("Hisoblash")
        calc_btn.setObjectName("Primary")
        calc_btn.clicked.connect(self._compare)
        btn_row.addWidget(calc_btn)
        self._explain_btn = QPushButton("AI tushuntirishi")
        self._explain_btn.clicked.connect(self._explain)
        self._explain_btn.setEnabled(False)
        btn_row.addWidget(self._explain_btn)
        btn_row.addStretch(1)
        compare_card.layout().addLayout(btn_row)

        self._result_label = QLabel("")
        self._result_label.setTextFormat(Qt.TextFormat.RichText)
        self._result_label.setWordWrap(True)
        compare_card.layout().addWidget(self._result_label)

        self._explanation = MarkdownView()
        self._explanation.setFixedHeight(0)
        compare_card.layout().addWidget(self._explanation)
        root.addWidget(compare_card)

        # --- Ish haqi ---
        payroll_card = Card()
        payroll_card.layout().addWidget(QLabel("Ish haqi soliqlari"))
        payroll_row = QHBoxLayout()
        self._salary = QLineEdit()
        self._salary.setPlaceholderText("Oylik ish haqi (gross), so'm")
        payroll_row.addWidget(self._salary)
        payroll_btn = QPushButton("Hisoblash")
        payroll_btn.setObjectName("Primary")
        payroll_btn.clicked.connect(self._payroll)
        payroll_row.addWidget(payroll_btn)
        payroll_card.layout().addLayout(payroll_row)
        self._payroll_label = QLabel("")
        self._payroll_label.setTextFormat(Qt.TextFormat.RichText)
        payroll_card.layout().addWidget(self._payroll_label)
        root.addWidget(payroll_card)
        root.addStretch(1)

    # ---------------------------------------------------------------- logic

    def _parse(self, field: QLineEdit) -> float:
        text = field.text().strip().replace(" ", "").replace(",", "")
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _compare(self) -> None:
        revenue = self._parse(self._revenue)
        expenses = self._parse(self._expenses)
        if revenue <= 0:
            self._result_label.setText("<span style='color:#f59e0b'>Yillik aylanmani kiriting</span>")
            return
        comparison = self._container.tax_service.compare_regimes(revenue, expenses)
        self._result_label.setText(_format_comparison(comparison))
        self._explain_btn.setEnabled(True)

    def _explain(self) -> None:
        revenue = self._parse(self._revenue)
        expenses = self._parse(self._expenses)
        self._explain_btn.setEnabled(False)
        self._explain_btn.setText("Tushuntirilmoqda…")
        runnable = CallableRunnable(
            self._container.tax_service.explain_comparison, revenue, expenses
        )
        runnable.signals.finished.connect(self._on_explain)
        runnable.signals.error.connect(self._on_explain_error)
        self._pool.start(runnable)

    def _on_explain(self, content: str) -> None:
        self._explanation.set_markdown(content)
        self._explanation.setFixedHeight(300)
        self._explain_btn.setEnabled(True)
        self._explain_btn.setText("AI tushuntirishi")

    def _on_explain_error(self, message: str) -> None:
        self._explanation.set_markdown(f"⚠️ Xatolik: {message}")
        self._explanation.setFixedHeight(120)
        self._explain_btn.setEnabled(True)
        self._explain_btn.setText("AI tushuntirishi")

    def _payroll(self) -> None:
        salary = self._parse(self._salary)
        if salary <= 0:
            self._payroll_label.setText("<span style='color:#f59e0b'>Ish haqini kiriting</span>")
            return
        result = self._container.tax_service.payroll(salary)
        self._payroll_label.setText(
            f"JShDS (12%): <b>{_fmt(result['income_tax'])}</b> so'm &nbsp;|&nbsp; "
            f"Ijtimoiy soliq (12%): <b>{_fmt(result['social_tax'])}</b> so'm<br>"
            f"Qo'lga tegadigan: <b>{_fmt(result['net_salary'])}</b> so'm &nbsp;|&nbsp; "
            f"Ish beruvchi xarajati: <b>{_fmt(result['employer_total_cost'])}</b> so'm"
        )


def _format_comparison(comparison: dict) -> str:
    turnover: TaxResult = comparison["turnover"]
    general: TaxResult = comparison["general"]
    recommended: TaxRegime = comparison["recommended"]

    def block(name: str, result: TaxResult, recommended_flag: bool) -> str:
        mark = " ✅ tavsiya" if recommended_flag else ""
        lines = "".join(
            f"&nbsp;&nbsp;{ln.name} ({ln.rate*100:.0f}%): <b>{_fmt(ln.amount)}</b> so'm<br>"
            for ln in result.lines
        )
        warns = "".join(
            f"<span style='color:#f59e0b'>⚠️ {w}</span><br>" for w in result.warnings
        )
        return (
            f"<div style='margin:6px 0'><b>{name}{mark}</b><br>{lines}"
            f"Jami: <b>{_fmt(result.total_tax)}</b> so'm "
            f"(samarali {result.effective_rate*100:.1f}%)<br>{warns}</div>"
        )

    return (
        block("Aylanma soliq", turnover, recommended is TaxRegime.TURNOVER)
        + block("Umumiy rejim (QQS + foyda)", general, recommended is TaxRegime.GENERAL)
        + f"<div>Farq: <b>{_fmt(comparison['savings'])}</b> so'm/yil</div>"
    )
