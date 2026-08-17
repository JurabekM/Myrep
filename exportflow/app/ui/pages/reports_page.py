"""Reports page: pick a report, filter it, export to PDF or Excel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.services import auth_service, buyer_service, product_service, report_service
from app.ui.i18n import t
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import PageHeader, button
from app.ui.widgets.table import Column, DataTable, FilterBar, FilterSpec
from app.utils.enums import INCOTERMS, LEAD_SOURCES, PIPELINE_STAGES


class ReportsPage(BasePage):
    """Report catalogue on the left, the result table on the right."""

    permission = "report.view"
    topics = ("*",)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        self._code = report_service.REPORT_CODES[0]

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        if ctx.can("report.export"):
            self.header.add_action(
                button(t("report.export_excel"), lambda: self._export("xlsx"), "Primary")
            )
            self.header.add_action(
                button(t("report.export_pdf"), lambda: self._export("pdf"), "Ghost")
            )
        self.header.add_action(button(t("common.refresh"), self.refresh, "Ghost"))

        self.filter_bar = FilterBar(
            [
                FilterSpec("date_from", t("common.date_from"), "date", width=120),
                FilterSpec("date_to", t("common.date_to"), "date", width=120),
                FilterSpec("country", t("common.country"), "combo", [], width=130),
                FilterSpec("buyer_id", t("common.buyer"), "combo", [], width=170),
                FilterSpec("product_id", t("common.product"), "combo", [], width=170),
                FilterSpec("manager_id", t("common.manager"), "combo", [], width=140),
                FilterSpec("source", t("common.source"), "enum", LEAD_SOURCES, "lead_source", 130),
                FilterSpec("stage", t("common.stage"), "enum", PIPELINE_STAGES, "lead_status", 150),
                FilterSpec(
                    "incoterm",
                    t("common.incoterm"),
                    "combo",
                    [(i, i) for i in INCOTERMS],
                    width=110,
                ),
                FilterSpec(
                    "currency",
                    t("common.currency"),
                    "combo",
                    [(c, c) for c in SUPPORTED_CURRENCIES],
                    width=100,
                ),
            ]
        )
        self.filter_bar.search.setVisible(False)
        self.filter_bar.changed.connect(self._run_report)
        root.addWidget(self.filter_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.report_list = QListWidget()
        self.report_list.setMaximumWidth(280)
        self.report_list.currentRowChanged.connect(self._on_report_changed)
        splitter.addWidget(self.report_list)

        self.table = DataTable([Column("value", "")])
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        self.retranslate()

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload the filter sources and re-run the selected report."""

        def _load(session: Session) -> tuple[list, list, list, list]:
            return (
                [(name, name) for name in buyer_service.distinct_countries(session)],
                [(row["id"], row["company_name"]) for row in buyer_service.search_buyers(session)],
                [
                    (row["id"], f"{row['sku']} — {row['name']}")
                    for row in product_service.search_products(session, lang=self.ctx.language())
                ],
                [
                    (user["id"], user["full_name"] or user["username"])
                    for user in auth_service.list_users(session)
                ],
            )

        try:
            countries, buyers, products, managers = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.filter_bar.set_options("country", countries, t("common.country"))
        self.filter_bar.set_options("buyer_id", buyers, t("common.buyer"))
        self.filter_bar.set_options("product_id", products, t("common.product"))
        self.filter_bar.set_options("manager_id", managers, t("common.manager"))
        self._run_report()

    def _filters(self) -> dict[str, Any]:
        values = self.filter_bar.values()
        values.pop("text", None)
        return {key: value for key, value in values.items() if value not in (None, "", False)}

    def _run_report(self) -> None:
        try:
            report = self.ctx.read(lambda s: report_service.build(s, self._code, self._filters()))
        except Exception as exc:
            self.handle_error(exc)
            return
        columns = [
            Column(key, title, kind=self._guess_kind(key), stretch=(index == 1))
            for index, (key, title) in enumerate(report["columns"])
        ]
        self.table.set_columns(columns)
        self.table.set_rows(report["rows"])
        self.header.set_texts(t(f"report.{self._code}"), t("report.rows", count=report["count"]))

    @staticmethod
    def _guess_kind(key: str) -> str:
        """Pick a rendering kind from the column key."""
        if key in ("status", "cert_type", "source", "priority", "buyer_type", "alert"):
            return "text"
        if key.endswith("_date") or key in (
            "etd",
            "eta",
            "issue_date",
            "valid_until",
            "record_date",
        ):
            return "date"
        if key in ("conversion", "share", "score", "margin_percent"):
            return "percent"
        if key in (
            "expected",
            "won_value",
            "value",
            "amount",
            "grand_total",
            "expected_amount",
            "actual_amount",
            "delta",
            "potential",
            "planned_cost",
            "actual_cost",
            "cost_delta",
            "commission_value",
            "expected_value",
        ):
            return "money"
        if key in (
            "leads",
            "buyers",
            "quotations",
            "rfqs",
            "samples",
            "won",
            "lost",
            "open",
            "deals",
            "items",
            "days_left",
            "days_overdue",
            "certificates",
            "prices",
            "moq",
            "lead_time_days",
            "avg_cycle",
            "commission_percent",
            "gross_weight",
        ):
            return "number"
        return "text"

    def _on_report_changed(self, index: int) -> None:
        if 0 <= index < len(report_service.REPORT_CODES):
            self._code = report_service.REPORT_CODES[index]
            self._run_report()

    def retranslate(self) -> None:
        """Re-apply captions and refill the report list."""
        self.header.set_texts(t("report.title"), t("report.select"))
        current = self.report_list.currentRow()
        self.report_list.blockSignals(True)
        self.report_list.clear()
        for code in report_service.REPORT_CODES:
            self.report_list.addItem(t(f"report.{code}"))
        self.report_list.setCurrentRow(max(current, 0))
        self.report_list.blockSignals(False)
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def _export(self, fmt: str) -> None:
        suffix = "xlsx" if fmt == "xlsx" else "pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("common.export"),
            f"{self._code}.{suffix}",
            "Excel (*.xlsx)" if fmt == "xlsx" else "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            written = self.ctx.run(
                lambda s: report_service.export(
                    s,
                    self.ctx.user,
                    self._code,
                    fmt,
                    filters=self._filters(),
                    target=path,
                    title=t(f"report.{self._code}"),
                )
            )
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)

    def on_export(self) -> None:
        """Ctrl+E exports the current report to Excel."""
        self._export("xlsx")
