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

from distribos.app_context import AppContext
from distribos.i18n import tr
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

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, tr("Hisobotlar"), tr("Davrni tanlang va eksport qiling."),
        )
        self._build = primary_button(tr("Shakllantirish"))
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
        # DIQQAT: hisobot nomlari (`title`) `reports/builders.py` dan
        # keladi — bu fayl hozircha tarjima qamroviga KIRMAYDI (u
        # eksport qilinadigan CSV/PDF matnini ham belgilaydi, alohida
        # qaror talab qiladi).
        for key, title, _ in builders.AVAILABLE_REPORTS:
            self._choice.addItem(title, key)

        self._start = QDateEdit(QDate.currentDate().addMonths(-1))
        self._start.setCalendarPopup(True)
        self._end = QDateEdit(QDate.currentDate())
        self._end.setCalendarPopup(True)

        row.addWidget(QLabel(tr("Hisobot:")))
        row.addWidget(self._choice, 2)
        row.addWidget(QLabel(tr("dan:")))
        row.addWidget(self._start)
        row.addWidget(QLabel(tr("gacha:")))
        row.addWidget(self._end)
        row.addStretch(1)
        self.add(filters)

        self.table = DataTable([], placeholder=tr("Natijalar ichida qidirish…"))
        self.add(self.table, 1)

        self._report: builders.Report | None = None

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
            self.report_error(exc, tr("Hisobotni shakllantirish"))
            return

        self._report = report
        self._rebuild_table(report)
        self.header.set_subtitle(
            tr("{description} · {n} qator").format(
                description=report.description, n=report.row_count
            )
        )

    def _rebuild_table(self, report: builders.Report) -> None:
        """Ustunlar hisobotdan hisobotga o'zgargani uchun jadval qayta quriladi."""
        layout = self._layout
        layout.removeWidget(self.table)
        self.table.deleteLater()

        self.table = DataTable(report.columns, placeholder=tr("Natijalar ichida qidirish…"))
        layout.addWidget(self.table, 1)
        rows = list(report.rows)
        if report.footer:
            rows.append(report.footer)
        self.table.set_rows(rows)

    @Slot()
    def _on_export_csv(self) -> None:
        if self._report is None:
            self.warn(tr("Avval hisobotni shakllantiring."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("CSV saqlash"),
            str(Path.home() / f"{self._report.key}-{dt.date.today():%Y%m%d}.csv"),
            tr("CSV (*.csv)"),
        )
        if not path:
            return
        try:
            self._report.to_csv(Path(path))
        except OSError as exc:
            self.report_error(exc, tr("CSV saqlash"))
            return
        self.notify(tr("Saqlandi: {name}").format(name=Path(path).name), tr("Eksport"))

    @Slot()
    def _on_export_pdf(self) -> None:
        if self._report is None:
            self.warn(tr("Avval hisobotni shakllantiring."))
            return
        from distribos.reports.documents import render_report, write_pdf

        path, _ = QFileDialog.getSaveFileName(
            self, tr("PDF saqlash"),
            str(Path.home() / f"{self._report.key}-{dt.date.today():%Y%m%d}.pdf"),
            tr("PDF (*.pdf)"),
        )
        if not path:
            return
        try:
            result = write_pdf(
                render_report(self._report), Path(path), title=self._report.title
            )
        except Exception as exc:
            self.report_error(exc, tr("PDF saqlash"))
            return
        self.notify(
            tr("Saqlandi: {name} ({pages} bet)").format(
                name=result.path.name, pages=result.page_count
            ),
            tr("Eksport"),
        )


class DocumentsPage(BasePage):
    """Bosma hujjatlar — buyurtmadan PDF."""

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, tr("Hujjatlar"),
            tr("Buyurtmani tanlang va kerakli hujjatni chiqaring."),
        )
        self._print = primary_button(tr("PDF chiqarish"))
        self._print.clicked.connect(self._on_print)
        self.header.add_action(self._print)

        filters = QWidget()
        row = QHBoxLayout(filters)
        row.setContentsMargins(0, 0, 0, 0)
        self._kind = QComboBox()
        from distribos.reports.documents import ORDER_DOCUMENTS

        # DIQQAT: hujjat turi nomlari `reports/documents.py` dan keladi
        # — u hozircha tarjima qamroviga kirmaydi (chiqadigan PDF
        # matnini ham belgilaydi).
        for key, title in ORDER_DOCUMENTS:
            self._kind.addItem(title, key)
        row.addWidget(QLabel(tr("Hujjat turi:")))
        row.addWidget(self._kind)
        row.addStretch(1)
        self.add(filters)

        self.table = DataTable(
            [tr("Raqam"), tr("Mijoz"), tr("Sana"), tr("Holat"), tr("Summa")],
            placeholder=tr("Buyurtma raqami yoki mijoz…"),
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
        self.header.set_subtitle(tr("{n} ta buyurtma").format(n=len(orders)))

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
            self.warn(tr("Avval jadvaldan buyurtmani tanlang."))
            return

        number = selected[0]
        kind = self._kind.currentData()
        title = self._kind.currentText()

        path, _ = QFileDialog.getSaveFileName(
            self, tr("Hujjatni saqlash"),
            str(Path.home() / default_document_name(kind, number)), tr("PDF (*.pdf)"),
        )
        if not path:
            return

        try:
            with self.context.database.session() as session:
                order = session.query(Order).filter_by(number=number).one_or_none()
                if order is None:
                    self.warn(tr("Buyurtma topilmadi."))
                    return
                body = render_order(session, order.id, title=title)
            result = write_pdf(body, Path(path), title=title)
        except Exception as exc:
            self.report_error(exc, tr("Hujjat chiqarish"))
            return

        self.notify(
            tr("{title} tayyor: {name} ({pages} bet)").format(
                title=title, name=result.path.name, pages=result.page_count
            ),
            tr("Hujjat saqlandi"),
        )


class AssistantPage(BasePage):
    """AI yordamchi — tavsiyalar, tasdiqlash bilan."""

    def __init__(self, context: AppContext) -> None:
        super().__init__(
            context, tr("AI yordamchi"),
            tr(
                "Tavsiyalar. Hech qanday amal siz tasdiqlamaguningizcha "
                "bajarilmaydi."
            ),
        )
        self._analyse = primary_button(tr("Tahlil qilish"))
        self._analyse.clicked.connect(self._on_analyse)
        self.header.add_action(self._analyse)

        note = QLabel(tr(
            "AI buyurtmani yakuniy tasdiqlamaydi, to'lov yaratmaydi, "
            "qoldiqni o'zgartirmaydi va moliyaviy yozuvga tegmaydi. "
            "U faqat tavsiya beradi."
        ))
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE.text_muted};")
        self.add(note)

        self.table = DataTable(
            [tr("Ahamiyat"), tr("Tavsiya"), tr("Sabab"), tr("Nima qilish kerak")],
            placeholder=tr("Tavsiyalar ichida qidirish…"),
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
            self.report_error(exc, tr("Tahlil"))
            return

        self.table.set_rows([
            (item.severity_label, item.title, item.reason, item.action)
            for item in suggestions
        ])
        for index, item in enumerate(suggestions):
            self.table.set_row_tone(index, item.tone)

        self.header.set_subtitle(tr("{n} ta tavsiya").format(n=len(suggestions)))
        self._detail.setPlainText(tr(
            "Bu tavsiyalar shu kompyuterdagi ma'lumotlar asosida, "
            "internetsiz hisoblandi. Tashqi AI xizmatiga hech narsa "
            "yuborilmadi."
        ) if suggestions else tr("Hozircha e'tibor talab qiladigan holat topilmadi."))
