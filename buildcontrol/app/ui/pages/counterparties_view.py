"""Suppliers and contractors register."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QWidget

from app.models.enums import CounterpartyKind
from app.services import counterparty_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.dialogs.form_dialog import (
    COMBO,
    INT,
    MONEY,
    NUMBER,
    TEXT,
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
    MONEY as C_MONEY,
)
from app.ui.widgets.table import (
    NUMBER as C_NUMBER,
)
from app.utils.i18n import tr
from app.utils.labels import cp_kind_label, options


def _rating_kind(value: float) -> str:
    if value >= 4.2:
        return "success"
    if value >= 3.2:
        return "warning"
    return "danger"


class CounterpartiesView(BasePage):
    """Table of suppliers and contractors with the performance rating."""

    permission = Perm.COUNTERPARTY_VIEW

    def __init__(
        self,
        kind: str = "",
        parent: QWidget | None = None,
        show_header: bool = True,
        locked_kind: bool = False,
    ) -> None:
        super().__init__(
            tr("counterparties"), "", parent, show_header=show_header, compact=not show_header
        )
        self._locked_kind = locked_kind
        self._kind = kind

        self.new_btn = button(tr("new_counterparty"), "add", "Primary")
        self.new_btn.clicked.connect(self._create)
        self.new_btn.setEnabled(self.can(Perm.COUNTERPARTY_EDIT))
        self.header.add_action(self.new_btn)

        self.table = DataTable(self._columns())
        self.table.row_activated.connect(lambda _row: self._edit())
        self.table.selection_changed.connect(self._update_actions)

        if not locked_kind:
            self.kind_filter = make_combo(options(CounterpartyKind, include_all=True))
            self.kind_filter.currentIndexChanged.connect(self.refresh)
            self.table.add_filter(self.kind_filter)
        else:
            self.kind_filter = None
        self.archived_box = QCheckBox(tr("show_archived"))
        self.archived_box.stateChanged.connect(self.refresh)
        self.table.add_filter(self.archived_box)
        if not show_header:
            self.table.add_action(self.new_btn)

        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit)
        self.archive_btn = button(tr("archive"), "archive", "Ghost")
        self.archive_btn.clicked.connect(self._archive)
        self.table.add_action(self.edit_btn)
        self.table.add_action(self.archive_btn)

        self.root.addWidget(self.table, 1)
        self._update_actions(None)

    # -- table -------------------------------------------------------------------- #
    def _columns(self) -> list[Col]:
        columns = [Col("name", tr("name"), stretch=True)]
        if not self._locked_kind:
            columns.append(
                Col("kind", tr("type"), width=150, formatter=lambda r: cp_kind_label(r["kind"]))
            )
        columns += [
            Col("category", tr("category"), width=170),
            Col("tin", tr("tin"), width=110),
            Col("phone", tr("phone"), width=150),
            Col("email", tr("email"), width=180),
            Col("contract_amount", tr("contract_amount"), C_MONEY, width=150),
            Col("paid_amount", tr("paid_amount"), C_MONEY, width=150),
            Col(
                "delay_days",
                tr("delay_days"),
                C_NUMBER,
                width=110,
                color=lambda r: COLORS.danger if (r["delay_days"] or 0) > 10 else None,
            ),
            Col(
                "rating",
                tr("rating"),
                BADGE,
                width=110,
                badge=lambda r: (f"{r['rating']:.2f}", _rating_kind(r["rating"])),
            ),
        ]
        return columns

    # -- data --------------------------------------------------------------------- #
    def refresh(self) -> None:
        """Reload the counterparty list."""
        kind = self._kind
        if self.kind_filter is not None:
            kind = self.kind_filter.currentData() or ""
        rows = counterparty_service.list_counterparties(
            kind=kind, include_archived=self.archived_box.isChecked()
        )
        self.table.set_rows(rows)
        self.header.set_subtitle(f"{tr('total')}: {len(rows)}")
        self._update_actions(self.table.current_row())

    def _update_actions(self, row: dict | None) -> None:
        may_edit = self.can(Perm.COUNTERPARTY_EDIT)
        self.edit_btn.setEnabled(row is not None and may_edit)
        self.archive_btn.setEnabled(row is not None and may_edit)

    # -- actions ------------------------------------------------------------------- #
    def _fields(self) -> list[Field]:
        def is_contractor(values: dict) -> bool:
            """Contractor-only fields are hidden for suppliers."""
            return values.get("kind") == CounterpartyKind.CONTRACTOR.value

        return [
            Field(
                "kind",
                tr("type"),
                COMBO,
                options=options(CounterpartyKind),
                enabled=not self._locked_kind,
            ),
            Field("name", tr("company_name"), TEXT, required=True),
            Field("tin", tr("tin"), TEXT),
            Field("category", tr("category"), TEXT),
            Field("phone", tr("phone"), TEXT),
            Field("email", tr("email"), TEXT),
            Field("address", tr("address"), TEXT, span=2),
            Field("bank_details", tr("bank_details"), TEXTAREA, span=2),
            Field("contract_amount", tr("contract_amount"), MONEY, visible_if=is_contractor),
            Field("paid_amount", tr("paid_amount"), MONEY, visible_if=is_contractor),
            Field(
                "completed_work",
                tr("completed_work"),
                NUMBER,
                decimals=1,
                maximum=100,
                visible_if=is_contractor,
            ),
            Field("delay_days", tr("delay_days"), INT, maximum=3650, visible_if=is_contractor),
            Field(
                "quality_score",
                tr("quality_score"),
                NUMBER,
                decimals=1,
                maximum=5,
                visible_if=is_contractor,
            ),
            Field("disputes", tr("disputes"), INT, maximum=999, visible_if=is_contractor),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]

    def _create(self) -> None:
        default_kind = self._kind or CounterpartyKind.SUPPLIER.value
        dialog = FormDialog(
            tr("new_counterparty"), self._fields(), {"kind": default_kind}, parent=self
        )
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

    def _save(self, values: dict, cp_id: int | None) -> None:
        try:
            counterparty_service.save_counterparty(values, self.actor, cp_id)
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
            counterparty_service.archive_counterparty(row["id"], self.actor, not row["is_archived"])
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()
