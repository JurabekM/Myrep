"""Prices and Incoterms page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.services import product_service
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import banner, button
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import INCOTERMS, PAYMENT_TERMS, PRICE_STATUSES
from app.utils.formatting import fmt_date


class PricesPage(RecordPage):
    """All price lines across every product, with approval actions."""

    permission = "price.view"
    title_key = "price.title"
    subtitle_key = "price.only_approved"
    topics = ("price", "product")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._products: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        if ctx.can("price.edit"):
            self.header.add_action(button(t("price.new"), self.on_new, "Primary"))

    def columns(self) -> list[Column]:
        """Column layout of the price table."""
        return [
            Column("product", t("common.product"), stretch=True),
            Column("incoterm", t("price.incoterm"), width=90),
            Column("origin_point", t("price.origin_point"), width=180),
            Column("unit_price", t("price.unit_price"), kind="money", width=110),
            Column("moq", t("product.moq"), kind="number", decimals=0, width=80),
            Column("lead_time_days", t("product.lead_time"), kind="number", decimals=0, width=90),
            Column("valid_from", t("price.valid_from"), kind="date", width=100),
            Column("valid_to", t("price.valid_to"), kind="date", width=100),
            Column("status", t("common.status"), kind="status", group="price_status", width=110),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the price table."""
        return [
            FilterSpec("product_id", t("common.product"), "combo", [], width=200),
            FilterSpec(
                "incoterm", t("price.incoterm"), "combo", [(i, i) for i in INCOTERMS], width=110
            ),
            FilterSpec("status", t("common.status"), "enum", PRICE_STATUSES, "price_status", 130),
            FilterSpec(
                "currency",
                t("common.currency"),
                "combo",
                [(c, c) for c in SUPPORTED_CURRENCIES],
                width=100,
            ),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload the product list and the prices."""
        self._products = self.ctx.read(
            lambda s: [
                (row["id"], f"{row['sku']} — {row['name']}")
                for row in product_service.search_products(s, lang=self.ctx.language())
            ]
        )
        self.filter_bar.set_options("product_id", self._products, t("common.product"))
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Collect price lines from every (or one) product."""
        names = dict(self._products)

        def _load(session: Session) -> list[dict]:
            product_ids = [filters["product_id"]] if filters.get("product_id") else list(names)
            rows: list[dict] = []
            for product_id in product_ids:
                for price in product_service.list_prices(session, product_id):
                    price["product"] = names.get(product_id, "")
                    price["product_id"] = product_id
                    rows.append(price)
            return rows

        rows = self.ctx.read(_load)
        text = (filters.get("text") or "").lower()
        if text:
            rows = [
                row
                for row in rows
                if text in row["product"].lower() or text in (row["origin_point"] or "").lower()
            ]
        if filters.get("incoterm"):
            rows = [row for row in rows if row["incoterm"] == filters["incoterm"]]
        if filters.get("status"):
            rows = [row for row in rows if row["status"] == filters["status"]]
        if filters.get("currency"):
            rows = [row for row in rows if row["currency"] == filters["currency"]]
        return rows

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Show one price line with its approval actions."""
        self.detail.set_header(
            f"{row['incoterm']} · {row['unit_price']:,.2f} {row['currency']}",
            row["product"],
            "price_status",
            row["status"],
        )
        if self.ctx.can("price.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row), "Primary")
        if self.ctx.can("price.approve") and row["status"] == "draft":
            self.detail.add_action(t("price.approve"), lambda: self._approve(row["id"]), "Success")
        if self.ctx.can("price.edit"):
            self.detail.add_action(t("common.archive"), lambda: self._archive(row["id"]))

        rows = [
            (t("common.product"), row["product"]),
            (t("price.incoterm"), row["incoterm"]),
            (t("price.origin_point"), row["origin_point"]),
            (t("price.unit_price"), f"{row['unit_price']:,.2f} {row['currency']}"),
            (t("product.moq"), row["moq"]),
            (t("product.lead_time"), row["lead_time_days"]),
            (t("price.valid_from"), fmt_date(row["valid_from"])),
            (t("price.valid_to"), fmt_date(row["valid_to"])),
            (t("price.payment_terms"), row["payment_terms"]),
            (t("common.notes"), row["notes"]),
        ]
        self.detail.add_fields_tab(t("common.details"), rows)
        if not row["is_valid"]:
            self.detail.add_tab(t("common.status"), banner(t("price.only_approved"), "warning"))

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("price.edit"):
            self.open_editor(row)

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new price line."""
        self.open_editor(None)

    def open_editor(self, row: dict | None) -> None:
        """Show the price editor dialog."""
        values: dict[str, Any] = (
            row.copy()
            if row
            else {
                "currency": "USD",
                "incoterm": "FOB",
                "status": "draft",
            }
        )
        if row:
            values["incoterm"] = row.get("raw_incoterm") or row["incoterm"]
        fields = [
            Field(
                "product_id",
                t("common.product"),
                "combo",
                self._products,
                required=True,
                with_empty=False,
            ),
            Field(
                "incoterm",
                t("price.incoterm"),
                "combo",
                [(i, i) for i in INCOTERMS],
                required=True,
                with_empty=False,
            ),
            Field("custom_incoterm", t("price.custom_incoterm")),
            Field("origin_point", t("price.origin_point")),
            Field(
                "currency",
                t("common.currency"),
                "combo",
                [(c, c) for c in SUPPORTED_CURRENCIES],
                with_empty=False,
            ),
            Field("unit_price", t("price.unit_price"), "money", required=True, decimals=4),
            Field("moq", t("product.moq"), "float", decimals=0),
            Field("lead_time_days", t("product.lead_time"), "int", maximum=1000),
            Field("valid_from", t("price.valid_from"), "date"),
            Field("valid_to", t("price.valid_to"), "date"),
            Field(
                "payment_terms", t("price.payment_terms"), "combo", [(p, p) for p in PAYMENT_TERMS]
            ),
            Field(
                "status",
                t("common.status"),
                "enum",
                PRICE_STATUSES,
                "price_status",
                with_empty=False,
            ),
            Field("notes", t("common.notes"), "textarea", height=70),
        ]

        def _save(collected: dict[str, Any]) -> int:
            payload = dict(collected)
            payload["id"] = row["id"] if row else None
            return self.ctx.run(lambda s: product_service.save_price(s, self.ctx.user, payload).id)

        dialog = FormDialog(t("price.new"), fields, values, _save, self, width=640)
        if dialog.exec():
            self.ctx.notify("price")
            self.info(t("common.saved"))

    def _approve(self, price_id: int) -> None:
        try:
            self.ctx.run(lambda s: product_service.approve_price(s, self.ctx.user, price_id))
            self.ctx.notify("price")
            self.info(t("price.approved"))
        except Exception as exc:
            self.handle_error(exc)

    def _archive(self, price_id: int) -> None:
        if not self.confirm(t("common.confirm_archive")):
            return
        try:
            self.ctx.run(lambda s: product_service.archive_price(s, self.ctx.user, price_id))
            self.ctx.notify("price")
        except Exception as exc:
            self.handle_error(exc)
