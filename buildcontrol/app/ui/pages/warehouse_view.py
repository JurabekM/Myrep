"""Warehouse movements: receipts, issues, returns, adjustments and losses."""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.models.enums import TxKind
from app.services import estimate_service, project_service, warehouse_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.dialogs.form_dialog import (
    COMBO,
    DATE,
    FILE,
    MONEY,
    NUMBER,
    TEXTAREA,
    Field,
    FormDialog,
)
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
    DATE as C_DATE,
)
from app.ui.widgets.table import (
    MONEY as C_MONEY,
)
from app.ui.widgets.table import (
    NUMBER as C_NUMBER,
)
from app.utils.files import open_path
from app.utils.formatting import fmt_money
from app.utils.i18n import tr
from app.utils.labels import options, tx_kind_label

_KIND_BADGE = {
    TxKind.IN.value: "success",
    TxKind.OUT.value: "info",
    TxKind.RETURN.value: "accent",
    TxKind.ADJUST.value: "warning",
    TxKind.LOSS.value: "danger",
}


class WarehouseView(BasePage):
    """Stock movement register."""

    permission = Perm.WAREHOUSE_VIEW

    def __init__(
        self,
        project_id: int | None = None,
        parent: QWidget | None = None,
        show_header: bool = True,
    ) -> None:
        super().__init__(
            tr("transactions"), "", parent, show_header=show_header, compact=not show_header
        )
        self.project_id = project_id

        self.new_btn = button(tr("new_transaction"), "add", "Primary")
        self.new_btn.clicked.connect(self._create)
        self.new_btn.setEnabled(self.can(Perm.WAREHOUSE_EDIT))
        self.header.add_action(self.new_btn)

        self.table = DataTable(self._columns())
        self.kind_filter = make_combo(options(TxKind, include_all=True))
        self.kind_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.kind_filter)
        if project_id is None:
            self.project_filter = make_combo(project_service.project_choices())
            self.project_filter.currentIndexChanged.connect(self.refresh)
            self.table.add_filter(self.project_filter)
        else:
            self.project_filter = None
        if not show_header:
            self.table.add_action(self.new_btn)

        self.doc_btn = button(tr("open"), "open", "Ghost")
        self.doc_btn.clicked.connect(self._open_doc)
        self.delete_btn = button(tr("delete"), "delete", "Danger")
        self.delete_btn.clicked.connect(self._delete)
        self.delete_btn.setEnabled(self.can(Perm.WAREHOUSE_EDIT))
        self.table.add_action(self.doc_btn)
        self.table.add_action(self.delete_btn)

        self.root.addWidget(self.table, 1)

    # -- table ------------------------------------------------------------------ #
    def _columns(self) -> list[Col]:
        columns = [
            Col("tx_date", tr("date"), C_DATE, width=110),
            Col(
                "kind",
                tr("type"),
                BADGE,
                width=140,
                badge=lambda r: (tx_kind_label(r["kind"]), _KIND_BADGE.get(r["kind"], "neutral")),
            ),
            Col("sku", tr("sku"), width=110),
            Col("material", tr("material"), stretch=True),
            Col(
                "signed_quantity",
                tr("quantity"),
                C_NUMBER,
                width=110,
                color=lambda r: COLORS.success if r["signed_quantity"] > 0 else COLORS.warning,
            ),
            Col("unit_price", tr("unit_price"), C_MONEY, width=140),
            Col("total", tr("total"), C_MONEY, width=150),
        ]
        if self.project_id is None:
            columns.append(Col("project", tr("project"), width=180))
        columns += [
            Col("estimate_item", tr("estimate_item"), width=180),
            Col("user", tr("responsible"), width=140),
            Col("note", tr("note"), width=160),
        ]
        return columns

    # -- data -------------------------------------------------------------------- #
    def refresh(self) -> None:
        """Reload movements."""
        project_id = self.project_id
        if project_id is None and self.project_filter is not None:
            project_id = self.project_filter.currentData() or None
        rows = warehouse_service.list_transactions(
            project_id=project_id, kind=self.kind_filter.currentData() or ""
        )
        self.table.set_rows(rows)
        incoming = sum(r["total"] for r in rows if r["signed_quantity"] > 0)
        outgoing = sum(r["total"] for r in rows if r["signed_quantity"] < 0)
        self.header.set_subtitle(
            f"{tr('enum.tx.in')}: {fmt_money(incoming)}  ·  "
            f"{tr('enum.tx.out')}: {fmt_money(outgoing)}"
        )

    # -- actions ------------------------------------------------------------------ #
    def _fields(self) -> list[Field]:
        projects = project_service.project_choices()
        return [
            Field("tx_date", tr("date"), DATE, default=date.today()),
            Field("kind", tr("type"), COMBO, options=options(TxKind), required=True),
            Field(
                "material_id",
                tr("material"),
                COMBO,
                required=True,
                options=warehouse_service.material_choices(),
                span=2,
            ),
            Field("quantity", tr("quantity"), NUMBER, required=True, decimals=2),
            Field("unit_price", tr("unit_price"), MONEY),
            Field(
                "project_id",
                tr("project"),
                COMBO,
                options=projects,
                default=self.project_id or "",
            ),
            Field("estimate_item_id", tr("estimate_item"), COMBO, options=self._item_choices()),
            Field("doc_path", tr("document"), FILE, span=2),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]

    def _item_choices(self) -> list[tuple]:
        if self.project_id:
            return estimate_service.item_choices(self.project_id)
        rows: list[tuple] = [("", "—")]
        for project_id, name in project_service.project_choices(include_all=False):
            for item_id, label in estimate_service.item_choices(int(project_id))[1:]:
                rows.append((item_id, f"{name.split('—')[0].strip()} · {label}"))
        return rows

    def _create(self) -> None:
        dialog = FormDialog(
            tr("new_transaction"),
            self._fields(),
            {"kind": TxKind.IN.value, "project_id": self.project_id or ""},
            parent=self,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        values["project_id"] = values.get("project_id") or None
        values["estimate_item_id"] = values.get("estimate_item_id") or None
        try:
            warehouse_service.register_transaction(values, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _delete(self) -> None:
        row = self.table.current_row()
        if row is None or not confirm(self, tr("confirm_question"), tr("delete")):
            return
        try:
            warehouse_service.delete_transaction(row["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("deleted"))
        self.refresh()

    def _open_doc(self) -> None:
        row = self.table.current_row()
        if row is None or not row.get("doc_path"):
            self.notify(tr("no_data"), "warning")
            return
        if not open_path(row["doc_path"]):
            self.notify(tr("no_data"), "warning")
