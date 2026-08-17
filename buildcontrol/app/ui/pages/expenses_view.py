"""Expenses and payments (reused by the global page and the project tab)."""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.models.enums import ExpenseCategory, ExpenseStatus, PaymentMethod
from app.services import (
    counterparty_service,
    estimate_service,
    expense_service,
    project_service,
)
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.dialogs.form_dialog import (
    COMBO,
    DATE,
    FILE,
    MONEY,
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
    DATE as C_DATE,
)
from app.ui.widgets.table import (
    MONEY as C_MONEY,
)
from app.utils.formatting import fmt_money
from app.utils.i18n import tr
from app.utils.labels import expense_category_label, expense_status_label, method_label, options

_STATUS_KIND = {
    ExpenseStatus.PENDING.value: "warning",
    ExpenseStatus.APPROVED.value: "info",
    ExpenseStatus.PAID.value: "success",
    ExpenseStatus.REJECTED.value: "danger",
}


class ExpensesView(BasePage):
    """Expense register with the approval and payment workflow."""

    permission = Perm.EXPENSE_VIEW

    def __init__(
        self,
        project_id: int | None = None,
        parent: QWidget | None = None,
        show_header: bool = True,
    ) -> None:
        super().__init__(
            tr("expenses"), "", parent, show_header=show_header, compact=not show_header
        )
        self.project_id = project_id

        self.new_btn = button(tr("new_expense"), "add", "Primary")
        self.new_btn.clicked.connect(self._create)
        self.new_btn.setEnabled(self.can(Perm.EXPENSE_EDIT))
        (self.header.add_action if show_header else lambda w: None)(self.new_btn)

        self.table = DataTable(self._columns())
        self.table.selection_changed.connect(self._update_actions)
        self.table.row_activated.connect(lambda _row: self._edit())

        self.status_filter = make_combo(options(ExpenseStatus, include_all=True))
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.status_filter)
        self.category_filter = make_combo(options(ExpenseCategory, include_all=True))
        self.category_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.category_filter)
        if project_id is None:
            self.project_filter = make_combo(project_service.project_choices())
            self.project_filter.currentIndexChanged.connect(self.refresh)
            self.table.add_filter(self.project_filter)
        else:
            self.project_filter = None
        if not show_header:
            self.table.add_action(self.new_btn)

        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit)
        self.approve_btn = button(tr("approve"), "approve", "Success")
        self.approve_btn.clicked.connect(lambda: self._set_status(ExpenseStatus.APPROVED.value))
        self.paid_btn = button(tr("mark_paid"), "money")
        self.paid_btn.clicked.connect(self._add_payment)
        self.reject_btn = button(tr("reject"), "reject", "Danger")
        self.reject_btn.clicked.connect(lambda: self._set_status(ExpenseStatus.REJECTED.value))
        self.archive_btn = button(tr("archive"), "archive", "Ghost")
        self.archive_btn.clicked.connect(self._archive)
        for widget in (
            self.edit_btn,
            self.approve_btn,
            self.paid_btn,
            self.reject_btn,
            self.archive_btn,
        ):
            self.table.add_action(widget)

        self.root.addWidget(self.table, 1)
        self._update_actions(None)

    # -- table ----------------------------------------------------------------- #
    def _columns(self) -> list[Col]:
        columns = [Col("pay_date", tr("pay_date"), C_DATE, width=110)]
        if self.project_id is None:
            columns.append(Col("project", tr("project"), width=180))
        columns += [
            Col(
                "category",
                tr("category"),
                width=130,
                formatter=lambda r: expense_category_label(r["category"]),
            ),
            Col("counterparty", tr("counterparty"), width=190),
            Col("estimate_item", tr("estimate_item"), stretch=True),
            Col("amount", tr("amount"), C_MONEY, width=150),
            Col("paid", tr("paid_amount"), C_MONEY, width=140),
            Col(
                "balance",
                tr("remaining_funds"),
                C_MONEY,
                width=140,
                color=lambda r: COLORS.warning if r["balance"] > 0 else COLORS.success,
            ),
            Col("method", tr("method"), width=130, formatter=lambda r: method_label(r["method"])),
            Col("invoice_no", tr("invoice_no"), width=120),
            Col(
                "status",
                tr("status"),
                BADGE,
                width=140,
                badge=lambda r: (
                    expense_status_label(r["status"]),
                    _STATUS_KIND.get(r["status"], "neutral"),
                ),
            ),
        ]
        return columns

    # -- data ------------------------------------------------------------------ #
    def refresh(self) -> None:
        """Reload the expense register."""
        project_id = self.project_id
        if project_id is None and self.project_filter is not None:
            project_id = self.project_filter.currentData() or None
        rows = expense_service.list_expenses(
            project_id=project_id,
            status=self.status_filter.currentData() or "",
            category=self.category_filter.currentData() or "",
        )
        self.table.set_rows(rows)
        total = sum(r["amount"] for r in rows)
        paid = sum(r["paid"] for r in rows)
        self.header.set_subtitle(
            f"{tr('total')}: {fmt_money(total)}  ·  {tr('paid_amount')}: {fmt_money(paid)}"
        )
        self._update_actions(self.table.current_row())

    def _update_actions(self, row: dict | None) -> None:
        has = row is not None
        may_edit = self.can(Perm.EXPENSE_EDIT)
        may_approve = self.can(Perm.EXPENSE_APPROVE)
        pending = has and row["status"] == ExpenseStatus.PENDING.value
        self.edit_btn.setEnabled(has and may_edit)
        self.approve_btn.setEnabled(bool(pending and may_approve))
        self.reject_btn.setEnabled(bool(pending and may_approve))
        self.paid_btn.setEnabled(
            has and may_approve and row["status"] != ExpenseStatus.REJECTED.value
        )
        self.archive_btn.setEnabled(has and may_edit)

    # -- form ------------------------------------------------------------------ #
    def _fields(self, project_id: int | None) -> list[Field]:
        items = estimate_service.item_choices(project_id) if project_id else [("", "—")]
        fields = []
        if self.project_id is None:
            fields.append(
                Field(
                    "project_id",
                    tr("project"),
                    COMBO,
                    required=True,
                    options=project_service.project_choices(include_all=False),
                    span=2,
                )
            )
        fields += [
            Field("category", tr("category"), COMBO, options=options(ExpenseCategory)),
            Field(
                "counterparty_id",
                tr("counterparty"),
                COMBO,
                options=counterparty_service.counterparty_choices(),
            ),
            Field("estimate_item_id", tr("estimate_item"), COMBO, options=items, span=2),
            Field("amount", tr("amount"), MONEY, required=True),
            Field("pay_date", tr("pay_date"), DATE),
            Field("method", tr("method"), COMBO, options=options(PaymentMethod)),
            Field("invoice_no", tr("invoice_no"), TEXT),
            Field("doc_path", tr("document"), FILE, span=2),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]
        return fields

    def _create(self) -> None:
        dialog = FormDialog(
            tr("new_expense"),
            self._fields(self.project_id),
            {
                "pay_date": date.today(),
                "status": ExpenseStatus.PENDING.value,
                "method": PaymentMethod.TRANSFER.value,
            },
            parent=self,
        )
        if not dialog.exec():
            return
        self._save(dialog.values(), None)

    def _edit(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        dialog = FormDialog(
            tr("edit"), self._fields(row["project_id"]), row, row["counterparty"], parent=self
        )
        if not dialog.exec():
            return
        self._save(dialog.values(), row["id"])

    def _save(self, values: dict, expense_id: int | None) -> None:
        values["project_id"] = values.get("project_id") or self.project_id
        values["estimate_item_id"] = values.get("estimate_item_id") or None
        values["counterparty_id"] = values.get("counterparty_id") or None
        if expense_id is None:
            values["status"] = ExpenseStatus.PENDING.value
        try:
            expense_service.save_expense(values, self.actor, expense_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    # -- workflow -------------------------------------------------------------- #
    def _set_status(self, status: str) -> None:
        row = self.table.current_row()
        if row is None:
            return
        if status == ExpenseStatus.APPROVED.value:
            over = expense_service.would_exceed_budget(row["project_id"], row["amount"])
            question = tr("approve_expense_q")
            if over:
                question = f"{tr('budget_exceed_warning')}\n\n{question}"
            if not confirm(self, question, tr("approve")):
                return
        try:
            expense_service.set_status(row["id"], status, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _add_payment(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        dialog = FormDialog(
            tr("add_payment"),
            [
                Field("amount", tr("amount"), MONEY, required=True, default=row["balance"]),
                Field("pay_date", tr("pay_date"), DATE, default=date.today()),
                Field("method", tr("method"), COMBO, options=options(PaymentMethod)),
                Field("note", tr("note"), TEXT, span=2),
            ],
            {"method": row["method"]},
            f"{tr('amount')}: {fmt_money(row['amount'])} · "
            f"{tr('paid_amount')}: {fmt_money(row['paid'])}",
            parent=self,
            width=520,
        )
        if not dialog.exec():
            return
        try:
            expense_service.add_payment(row["id"], dialog.values(), self.actor)
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
            expense_service.archive_expense(row["id"], self.actor, not row["is_archived"])
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()
