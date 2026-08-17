"""Material catalogue with live stock balances."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QWidget

from app.models.enums import Unit
from app.services import counterparty_service, warehouse_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.dialogs.form_dialog import COMBO, MONEY, NUMBER, TEXT, TEXTAREA, Field, FormDialog
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import COLORS
from app.ui.widgets.common import button
from app.ui.widgets.table import (
    BADGE,
    Col,
    DataTable,
    make_combo,
)
from app.ui.widgets.table import (
    MONEY as C_MONEY,
)
from app.ui.widgets.table import (
    NUMBER as C_NUMBER,
)
from app.utils.formatting import fmt_money
from app.utils.i18n import tr
from app.utils.labels import options, unit_label


class MaterialsView(BasePage):
    """Catalogue table with min-stock warnings."""

    permission = Perm.WAREHOUSE_VIEW

    def __init__(self, parent: QWidget | None = None, show_header: bool = True) -> None:
        super().__init__(
            tr("materials"), "", parent, show_header=show_header, compact=not show_header
        )
        self.new_btn = button(tr("add"), "add", "Primary")
        self.new_btn.clicked.connect(self._create)
        self.new_btn.setEnabled(self.can(Perm.WAREHOUSE_EDIT))
        self.header.add_action(self.new_btn)

        self.table = DataTable(
            [
                Col("sku", tr("sku"), width=110),
                Col("name", tr("name"), stretch=True),
                Col("category", tr("category"), width=150),
                Col("unit", tr("unit"), width=90, formatter=lambda r: unit_label(r["unit"])),
                Col(
                    "balance",
                    tr("stock"),
                    C_NUMBER,
                    width=110,
                    color=lambda r: COLORS.danger if r["is_low"] else COLORS.success,
                ),
                Col("min_stock", tr("min_stock"), C_NUMBER, width=110),
                Col("standard_price", tr("standard_price"), C_MONEY, width=140),
                Col("value", tr("stock_value"), C_MONEY, width=150),
                Col("supplier", tr("supplier"), width=180),
                Col(
                    "flag",
                    "",
                    BADGE,
                    width=140,
                    badge=lambda r: (
                        (tr("low_stock_warning"), "danger") if r["is_low"] else ("", "neutral")
                    ),
                ),
            ]
        )
        self.table.row_activated.connect(lambda _row: self._edit())
        self.table.selection_changed.connect(self._update_actions)

        self.category_filter = make_combo(
            [("", tr("all"))] + [(c, c) for c in warehouse_service.categories()]
        )
        self.category_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.category_filter)
        self.low_box = QCheckBox(tr("low_stock_items"))
        self.low_box.stateChanged.connect(self.refresh)
        self.table.add_filter(self.low_box)
        self.archived_box = QCheckBox(tr("show_archived"))
        self.archived_box.stateChanged.connect(self.refresh)
        self.table.add_filter(self.archived_box)
        if not show_header:
            self.table.add_action(self.new_btn)

        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit)
        self.archive_btn = button(tr("archive"), "archive", "Ghost")
        self.archive_btn.clicked.connect(self._archive)
        for widget in (self.edit_btn, self.archive_btn):
            self.table.add_action(widget)

        self.root.addWidget(self.table, 1)
        self._update_actions(None)

    # -- data ------------------------------------------------------------------ #
    def refresh(self) -> None:
        """Reload the catalogue."""
        rows = warehouse_service.list_materials(
            category=self.category_filter.currentData() or "",
            only_low=self.low_box.isChecked(),
            include_archived=self.archived_box.isChecked(),
        )
        data = [
            {
                "id": row.id,
                "sku": row.sku,
                "name": row.name,
                "category": row.category,
                "unit": row.unit,
                "balance": row.balance,
                "min_stock": row.min_stock,
                "standard_price": row.standard_price,
                "value": row.value,
                "supplier": row.supplier,
                "supplier_id": row.supplier_id,
                "is_low": row.is_low,
                "note": row.note,
                "is_archived": row.is_archived,
                "flag": "",
            }
            for row in rows
        ]
        self.table.set_rows(data)
        total = sum(r["value"] for r in data)
        low = sum(1 for r in data if r["is_low"])
        self.header.set_subtitle(
            f"{tr('stock_value')}: {fmt_money(total)}  ·  {tr('low_stock_items')}: {low}"
        )
        self._update_actions(self.table.current_row())

    def _update_actions(self, row: dict | None) -> None:
        may_edit = self.can(Perm.WAREHOUSE_EDIT)
        self.edit_btn.setEnabled(row is not None and may_edit)
        self.archive_btn.setEnabled(row is not None and may_edit)

    # -- actions --------------------------------------------------------------- #
    def _fields(self) -> list[Field]:
        return [
            Field("sku", tr("sku"), TEXT, required=True),
            Field("name", tr("name"), TEXT, required=True),
            Field("category", tr("category"), TEXT),
            Field("unit", tr("unit"), COMBO, options=options(Unit)),
            Field("min_stock", tr("min_stock"), NUMBER, decimals=2),
            Field("standard_price", tr("standard_price"), MONEY),
            Field(
                "supplier_id",
                tr("supplier"),
                COMBO,
                options=counterparty_service.counterparty_choices("supplier"),
                span=2,
            ),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]

    def _create(self) -> None:
        dialog = FormDialog(tr("material"), self._fields(), {"unit": Unit.PIECE.value}, parent=self)
        if not dialog.exec():
            return
        self._save(dialog.values(), None)

    def _edit(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        dialog = FormDialog(tr("edit"), self._fields(), row, row["name"], parent=self)
        if not dialog.exec():
            return
        self._save(dialog.values(), row["id"])

    def _save(self, values: dict, material_id: int | None) -> None:
        values["supplier_id"] = values.get("supplier_id") or None
        try:
            warehouse_service.save_material(values, self.actor, material_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _archive(self) -> None:
        row = self.table.current_row()
        if row is None or not confirm(self, tr("confirm_question"), tr("archive")):
            return
        try:
            warehouse_service.archive_material(row["id"], self.actor, not row["is_archived"])
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()
