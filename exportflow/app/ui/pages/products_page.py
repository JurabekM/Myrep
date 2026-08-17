"""Product information management page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QWidget
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import import_service, product_service
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import key_value_row
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import PRODUCT_STATUSES, UNITS
from app.utils.formatting import fmt_date, fmt_number


class ProductsPage(RecordPage):
    """Table of products with a full multi-tab editor."""

    permission = "product.view"
    title_key = "product.title"
    topics = ("product", "price", "certificate")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._categories: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        self._build_actions()

    # ------------------------------------------------------------- layout
    def _build_actions(self) -> None:
        from app.ui.widgets.common import button

        if self.ctx.can("product.edit"):
            self.header.add_action(button(t("product.new"), self.on_new, "Primary"))
        if self.ctx.can("product.archive"):
            self.header.add_action(button(t("product.bulk_archive"), self._bulk_archive, "Ghost"))
        if self.ctx.can("product.edit"):
            self.header.add_action(button(t("common.import"), self._import_excel, "Ghost"))
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the product table."""
        return [
            Column("sku", t("product.sku"), width=110),
            Column("name", t("common.name"), stretch=True),
            Column("category", t("common.category"), width=130),
            Column("brand", t("product.brand"), width=110),
            Column("hs_code", t("product.hs_code"), width=100),
            Column("moq", t("product.moq"), kind="number", decimals=0, width=80),
            Column("unit", t("common.unit"), width=60),
            Column(
                "certificates", t("product.tab_certificates"), kind="number", decimals=0, width=70
            ),
            Column("prices", t("product.tab_prices"), kind="number", decimals=0, width=70),
            Column("export_ready", t("product.export_ready"), kind="bool", width=90),
            Column("status", t("common.status"), kind="status", group="product_status", width=100),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters above the product table."""
        return [
            FilterSpec("category_id", t("common.category"), "combo", [], width=150),
            FilterSpec(
                "status", t("common.status"), "enum", PRODUCT_STATUSES, "product_status", 130
            ),
            FilterSpec(
                "certificate",
                t("product.filter_certificate"),
                "combo",
                [(1, t("product.filter_has_certificate")), (0, t("product.filter_no_certificate"))],
                width=150,
            ),
            FilterSpec(
                "ready",
                t("product.export_ready"),
                "combo",
                [(1, t("product.filter_export_ready")), (0, t("product.filter_not_ready"))],
                width=140,
            ),
            FilterSpec("archived", t("common.show_archived"), "check"),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload categories and the product list."""
        self._categories = self.ctx.read(
            lambda s: [
                (row["id"], row["name_en"] or row["name_uz"])
                for row in product_service.list_categories(s)
            ]
        )
        self.filter_bar.set_options("category_id", self._categories, t("common.category"))
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch products matching the filter bar."""
        certificate = filters.get("certificate")
        ready = filters.get("ready")

        def _load(session: Session) -> list[dict]:
            return product_service.search_products(
                session,
                text=filters.get("text", ""),
                category_id=filters.get("category_id"),
                status=filters.get("status"),
                has_certificate=None if certificate is None else bool(certificate),
                export_ready=None if ready is None else bool(ready),
                include_archived=bool(filters.get("archived")),
                lang=self.ctx.language(),
            )

        return self.ctx.read(_load)

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Populate the right-hand product detail panel."""
        data = self.ctx.read(lambda s: product_service.product_dict(s, row["id"]))
        readiness = self.ctx.read(lambda s: product_service.export_readiness(s, row["id"]))
        lang = self.ctx.language()

        self.detail.set_header(
            data.get(f"name_{lang}") or data.get("name_en") or data["sku"],
            f"{data['sku']} · {row.get('category', '')}",
            "product_status",
            data["status"],
        )
        if self.ctx.can("product.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row["id"]), "Primary")
        if self.ctx.can("product.archive"):
            if data.get("is_archived"):
                self.detail.add_action(t("common.restore"), lambda: self._restore(row["id"]))
            else:
                self.detail.add_action(t("common.archive"), lambda: self._archive(row["id"]))

        self.detail.add_fields_tab(
            t("product.tab_general"),
            [
                (t("product.sku"), data["sku"]),
                (t("product.brand"), data.get("brand")),
                (t("product.manufacturer"), data.get("manufacturer")),
                (t("product.hs_code"), data.get("hs_code")),
                (t("product.origin"), data.get("origin_country")),
                (t("product.moq"), f"{fmt_number(data.get('moq'), 0)} {data.get('unit', '')}"),
                (t("product.lead_time"), data.get("lead_time_days")),
                (t("product.capacity_month"), fmt_number(data.get("capacity_month"), 0)),
                (t("common.tags"), data.get("tags")),
            ],
        )
        self.detail.add_fields_tab(
            t("product.tab_packaging"),
            [
                (t("product.packaging_type"), data.get("packaging_type")),
                (t("product.units_per_carton"), fmt_number(data.get("units_per_carton"), 0)),
                (t("product.cartons_per_pallet"), fmt_number(data.get("cartons_per_pallet"), 0)),
                (t("product.carton_dimensions"), data.get("carton_dimensions")),
                (t("product.net_weight"), fmt_number(data.get("net_weight"))),
                (t("product.gross_weight"), fmt_number(data.get("gross_weight"))),
                (t("product.shelf_life"), data.get("shelf_life")),
                (t("product.storage"), data.get("storage_condition")),
            ],
        )
        self.detail.add_list_tab(
            t("product.tab_prices"),
            [
                f"{price['incoterm']} · {price['unit_price']:,.2f} {price['currency']} · "
                f"{price['origin_point']} · {te('price_status', price['status'])}"
                f"{' · ' + fmt_date(price['valid_to']) if price['valid_to'] else ''}"
                for price in data.get("prices", [])
            ],
        )
        self.detail.add_list_tab(
            t("product.tab_certificates"),
            [
                f"{cert['name']} · {te('certificate_type', cert['cert_type'])} · "
                f"{fmt_date(cert['expiry_date'])}"
                for cert in data.get("certificates", [])
            ],
        )
        self.detail.add_list_tab(
            t("product.tab_media"),
            [
                f"{'★ ' if media['is_primary'] else ''}{Path(media['file_path']).name}"
                for media in data.get("media", [])
            ],
        )

        readiness_widget = QWidget()
        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(readiness_widget)
        layout.setContentsMargins(2, 6, 2, 6)
        layout.setSpacing(4)
        layout.addWidget(key_value_row(t("product.readiness_score"), f"{readiness['score']}%"))
        layout.addWidget(
            key_value_row(
                t("product.missing"),
                ", ".join(readiness["missing"]) if readiness["missing"] else "—",
            )
        )
        layout.addStretch(1)
        self.detail.add_tab(t("product.tab_readiness"), readiness_widget)

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("product.edit"):
            self.open_editor(row["id"])

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new product."""
        if self.ctx.can("product.edit"):
            self.open_editor(None)

    def open_editor(self, product_id: int | None) -> None:
        """Show the multi-tab product editor."""
        values: dict[str, Any] = {"status": "draft", "origin_country": "Uzbekistan", "unit": "pcs"}
        if product_id:
            values = self.ctx.read(lambda s: product_service.product_dict(s, product_id))

        tab_general = t("product.tab_general")
        tab_desc = t("product.tab_descriptions")
        tab_pack = t("product.tab_packaging")
        fields = [
            Field("sku", t("product.sku"), tab=tab_general, required=True),
            Field(
                "status",
                t("common.status"),
                "enum",
                PRODUCT_STATUSES,
                "product_status",
                tab_general,
                with_empty=False,
            ),
            Field("category_id", t("common.category"), "combo", self._categories, tab=tab_general),
            Field("brand", t("product.brand"), tab=tab_general),
            Field("manufacturer", t("product.manufacturer"), tab=tab_general),
            Field("hs_code", t("product.hs_code"), tab=tab_general),
            Field("origin_country", t("product.origin"), tab=tab_general),
            Field(
                "unit",
                t("common.unit"),
                "combo",
                [(u, u) for u in UNITS],
                tab=tab_general,
                with_empty=False,
            ),
            Field("moq", t("product.moq"), "float", tab=tab_general, decimals=0),
            Field("lead_time_days", t("product.lead_time"), "int", tab=tab_general, maximum=1000),
            Field(
                "capacity_month", t("product.capacity_month"), "float", tab=tab_general, decimals=0
            ),
            Field(
                "capacity_year", t("product.capacity_year"), "float", tab=tab_general, decimals=0
            ),
            Field("tags", t("common.tags"), tab=tab_general),
            Field(
                "internal_notes",
                t("product.internal_notes"),
                "textarea",
                tab=tab_general,
                height=70,
            ),
            Field("name_uz", t("common.name") + " (UZ)", tab=tab_desc),
            Field("name_ru", t("common.name") + " (RU)", tab=tab_desc),
            Field("name_en", t("common.name") + " (EN)", tab=tab_desc, required=True),
            Field(
                "short_desc_uz",
                t("product.short_desc") + " (UZ)",
                "textarea",
                tab=tab_desc,
                height=60,
            ),
            Field(
                "short_desc_ru",
                t("product.short_desc") + " (RU)",
                "textarea",
                tab=tab_desc,
                height=60,
            ),
            Field(
                "short_desc_en",
                t("product.short_desc") + " (EN)",
                "textarea",
                tab=tab_desc,
                height=60,
            ),
            Field(
                "full_desc_uz",
                t("product.full_desc") + " (UZ)",
                "textarea",
                tab=tab_desc,
                height=90,
            ),
            Field(
                "full_desc_ru",
                t("product.full_desc") + " (RU)",
                "textarea",
                tab=tab_desc,
                height=90,
            ),
            Field(
                "full_desc_en",
                t("product.full_desc") + " (EN)",
                "textarea",
                tab=tab_desc,
                height=90,
            ),
            Field("packaging_type", t("product.packaging_type"), tab=tab_pack),
            Field(
                "units_per_carton", t("product.units_per_carton"), "float", tab=tab_pack, decimals=0
            ),
            Field(
                "cartons_per_pallet",
                t("product.cartons_per_pallet"),
                "float",
                tab=tab_pack,
                decimals=0,
            ),
            Field("carton_dimensions", t("product.carton_dimensions"), tab=tab_pack),
            Field("pallet_dimensions", t("product.pallet_dimensions"), tab=tab_pack),
            Field("net_weight", t("product.net_weight"), "float", tab=tab_pack, decimals=3),
            Field("gross_weight", t("product.gross_weight"), "float", tab=tab_pack, decimals=3),
            Field("length_cm", t("product.dimensions") + " L", "float", tab=tab_pack),
            Field("width_cm", t("product.dimensions") + " W", "float", tab=tab_pack),
            Field("height_cm", t("product.dimensions") + " H", "float", tab=tab_pack),
            Field("shelf_life", t("product.shelf_life"), tab=tab_pack),
            Field("storage_condition", t("product.storage"), "textarea", tab=tab_pack, height=60),
        ]

        def _save(collected: dict[str, Any]) -> int:
            payload = dict(collected)
            payload["id"] = product_id

            def _run(session: Session) -> int:
                product = product_service.save_product(session, self.ctx.user, payload)
                product_service.recompute_export_ready(session, product.id)
                return product.id

            return self.ctx.run(_run)

        dialog = FormDialog(
            t("product.new") if not product_id else values.get("sku", ""),
            fields,
            values,
            _save,
            self,
        )
        if dialog.exec():
            self.ctx.notify("product")
            self.info(t("common.saved"))
            if dialog.result_value:
                self.table.select_id(dialog.result_value)

    def _archive(self, product_id: int) -> None:
        if not self.confirm(t("common.confirm_archive")):
            return
        try:
            self.ctx.run(lambda s: product_service.archive_products(s, self.ctx.user, [product_id]))
            self.ctx.notify("product")
        except Exception as exc:
            self.handle_error(exc)

    def _restore(self, product_id: int) -> None:
        try:
            self.ctx.run(lambda s: product_service.restore_product(s, self.ctx.user, product_id))
            self.ctx.notify("product")
        except Exception as exc:
            self.handle_error(exc)

    def _bulk_archive(self) -> None:
        rows = self.table.selected_rows()
        if not rows:
            return
        if not self.confirm(t("common.confirm_archive")):
            return
        ids = [row["id"] for row in rows]
        try:
            count = self.ctx.run(lambda s: product_service.archive_products(s, self.ctx.user, ids))
            self.ctx.notify("product")
            self.info(t("common.rows", count=count))
        except Exception as exc:
            self.handle_error(exc)

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("product.import_excel"), "", "Excel (*.xlsx *.xlsm)"
        )
        if not path:
            return
        try:
            result = self.ctx.run(lambda s: import_service.import_products(s, self.ctx.user, path))
            self.ctx.notify("product")
            self.info(f"+{result['created']} / ~{result['updated']} / −{result['skipped']}")
            if result["errors"]:
                self.ctx.show_toast(result["errors"][0], "warning")
        except Exception as exc:
            self.handle_error(exc)

    def on_export(self) -> None:
        """Export the product master data to Excel."""
        path, _ = QFileDialog.getSaveFileName(
            self, t("product.export_excel"), "products.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(lambda s: import_service.export_products(s, self.ctx.user, path))
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)
