"""Hisobot, hujjat va AI yordamchi sahifalari."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from PySide6.QtCore import QDate, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QWidget,
)

from distribos.presentation.pages.base import BasePage
from distribos.presentation.theme import PALETTE, SPACE_SM
from distribos.presentation.widgets import (
    DataTable,
    ghost_button,
    primary_button,
)
from distribos.reports import builders


class ReportsPage(BasePage):
    """Filtrlanadigan, eksport qilinadigan hisobotlar."""

    def __init__(self, context) -> None:
        super().__init__(
            context, "Hisobotlar", "Davrni tanlang va eksport qiling.",
        )
        self._build = primary_button("Shakllantirish")
        self._build.clicked.connect(self._on_build)
        self.header.add_action(self._build)

        self._csv = ghost_button("CSV")
        self._csv.clicked.connect(self._on_export_csv)
        self.header.add_action(self._csv)

        self._pdf = ghost_button("PDF")
        self._pdf.clicked.connect(self._on_export_pdf)
        self.header.add_action(self._pdf)

        filters = QWidget()
        row = QHBoxLayout(filters)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE_SM)

        self._choice = QComboBox()
        for key, title, _ in builders.AVAILABLE_REPORTS:
            self._choice.addItem(title, key)

        self._start = QDateEdit(QDate.currentDate().addMonths(-1))
        self._start.setCalendarPopup(True)
        self._end = QDateEdit(QDate.currentDate())
        self._end.setCalendarPopup(True)

        row.addWidget(QLabel("Hisobot:"))
        row.addWidget(self._choice, 2)
        row.addWidget(QLabel("dan:"))
        row.addWidget(self._start)
        row.addWidget(QLabel("gacha:"))
        row.addWidget(self._end)
        row.addStretch(1)
        self.add(filters)

        self.table = DataTable([], placeholder="Natijalar ichida qidirish…")
        self.add(self.table, 1)

        self._report = None

    def refresh(self) -> None:
        if self._report is None:
            self._on_build()

    @Slot()
    def _on_build(self) -> None:
        key = self._choice.currentData()
        builder = next(
            (fn for report_key, _, fn in builders.AVAILABLE_REPORTS if report_key == key),
            None,
        )
        if builder is None:
            return

        start = self._start.date().toPython()
        end = self._end.date().toPython()

        try:
            with self.context.database.session() as session:
                report = builder(session, start=start, end=end)
        except TypeError:
            with self.context.database.session() as session:
                report = builder(session)
        except Exception as exc:
            self.report_error(exc, "Hisobotni shakllantirish")
            return

        self._report = report
        self._rebuild_table(report)
        self.header.set_subtitle(f"{report.description} · {report.row_count} qator")

    def _rebuild_table(self, report) -> None:
        """Ustunlar hisobotdan hisobotga o'zgargani uchun jadval qayta quriladi."""
        layout = self._layout
        layout.removeWidget(self.table)
        self.table.deleteLater()

        self.table = DataTable(report.columns, placeholder="Natijalar ichida qidirish…")
        layout.addWidget(self.table, 1)
        rows = list(report.rows)
        if report.footer:
            rows.append(report.footer)
        self.table.set_rows(rows)

    @Slot()
    def _on_export_csv(self) -> None:
        if self._report is None:
            self.warn("Avval hisobotni shakllantiring.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV saqlash",
            str(Path.home() / f"{self._report.key}-{dt.date.today():%Y%m%d}.csv"),
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            self._report.to_csv(Path(path))
        except OSError as exc:
            self.report_error(exc, "CSV saqlash")
            return
        self.notify(f"Saqlandi: {Path(path).name}", "Eksport")

    @Slot()
    def _on_export_pdf(self) -> None:
        if self._report is None:
            self.warn("Avval hisobotni shakllantiring.")
            return
        from distribos.reports.documents import render_report, write_pdf

        path, _ = QFileDialog.getSaveFileName(
            self, "PDF saqlash",
            str(Path.home() / f"{self._report.key}-{dt.date.today():%Y%m%d}.pdf"),
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            result = write_pdf(
                render_report(self._report), Path(path), title=self._report.title
            )
        except Exception as exc:
            self.report_error(exc, "PDF saqlash")
            return
        self.notify(
            f"Saqlandi: {result.path.name} ({result.page_count} bet)", "Eksport"
        )


class DocumentsPage(BasePage):
    """Bosma hujjatlar — buyurtmadan PDF."""

    def __init__(self, context) -> None:
        super().__init__(
            context, "Hujjatlar",
            "Buyurtmani tanlang va kerakli hujjatni chiqaring.",
        )
        self._print = primary_button("PDF chiqarish")
        self._print.clicked.connect(self._on_print)
        self.header.add_action(self._print)

        filters = QWidget()
        row = QHBoxLayout(filters)
        row.setContentsMargins(0, 0, 0, 0)
        self._kind = QComboBox()
        from distribos.reports.documents import ORDER_DOCUMENTS

        for key, title in ORDER_DOCUMENTS:
            self._kind.addItem(title, key)
        row.addWidget(QLabel("Hujjat turi:"))
        row.addWidget(self._kind)
        row.addStretch(1)
        self.add(filters)

        self.table = DataTable(
            ["Raqam", "Mijoz", "Sana", "Holat", "Summa"],
            placeholder="Buyurtma raqami yoki mijoz…",
        )
        self.add(self.table, 1)

    def refresh(self) -> None:
        from distribos.application import queries
        from distribos.presentation.status import money, order_state

        with self.context.database.session() as session:
            orders = queries.list_orders(session)
        self.table.set_rows([
            (row.number, row.customer_name, row.ordered_at.strftime("%d.%m.%Y"),
             order_state(row.state), money(row.total))
            for row in orders
        ])
        self.header.set_subtitle(f"{len(orders)} ta buyurtma")

    @Slot()
    def _on_print(self) -> None:
        from distribos.persistence.models import Order
        from distribos.reports.documents import (
            default_document_name,
            render_order,
            write_pdf,
        )

        selected = self.table.selected_row()
        if selected is None:
            self.warn("Avval jadvaldan buyurtmani tanlang.")
            return

        number = selected[0]
        kind = self._kind.currentData()
        title = self._kind.currentText()

        path, _ = QFileDialog.getSaveFileName(
            self, "Hujjatni saqlash",
            str(Path.home() / default_document_name(kind, number)), "PDF (*.pdf)",
        )
        if not path:
            return

        try:
            with self.context.database.session() as session:
                order = session.query(Order).filter_by(number=number).one_or_none()
                if order is None:
                    self.warn("Buyurtma topilmadi.")
                    return
                body = render_order(session, order.id, title=title)
            result = write_pdf(body, Path(path), title=title)
        except Exception as exc:
            self.report_error(exc, "Hujjat chiqarish")
            return

        self.notify(
            f"{title} tayyor: {result.path.name} ({result.page_count} bet)",
            "Hujjat saqlandi",
        )


class AssistantPage(BasePage):
    """AI yordamchi — tavsiyalar, tasdiqlash bilan."""

    def __init__(self, context) -> None:
        super().__init__(
            context, "AI yordamchi",
            "Tavsiyalar. Hech qanday amal siz tasdiqlamaguningizcha "
            "bajarilmaydi.",
        )
        self._analyse = primary_button("Tahlil qilish")
        self._analyse.clicked.connect(self._on_analyse)
        self.header.add_action(self._analyse)

        note = QLabel(
            "AI buyurtmani yakuniy tasdiqlamaydi, to'lov yaratmaydi, "
            "qoldiqni o'zgartirmaydi va moliyaviy yozuvga tegmaydi. "
            "U faqat tavsiya beradi."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE.text_muted};")
        self.add(note)

        self.table = DataTable(
            ["Ahamiyat", "Tavsiya", "Sabab", "Nima qilish kerak"],
            placeholder="Tavsiyalar ichida qidirish…",
        )
        self.add(self.table, 1)

        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setMaximumHeight(110)
        self.add(self._detail)

    def refresh(self) -> None:
        self._on_analyse()

    @Slot()
    def _on_analyse(self) -> None:
        from distribos.ai.advisor import LocalAdvisor

        try:
            with self.context.database.session() as session:
                suggestions = LocalAdvisor().analyse(session)
        except Exception as exc:
            self.report_error(exc, "Tahlil")
            return

        self.table.set_rows([
            (item.severity_label, item.title, item.reason, item.action)
            for item in suggestions
        ])
        for index, item in enumerate(suggestions):
            self.table.set_row_tone(index, item.tone)

        self.header.set_subtitle(f"{len(suggestions)} ta tavsiya")
        self._detail.setPlainText(
            "Bu tavsiyalar shu kompyuterdagi ma'lumotlar asosida, "
            "internetsiz hisoblandi. Tashqi AI xizmatiga hech narsa "
            "yuborilmadi."
            if suggestions else
            "Hozircha e'tibor talab qiladigan holat topilmadi."
        )
