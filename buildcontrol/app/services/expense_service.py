"""Expenses, approval workflow and payments."""

from __future__ import annotations

from datetime import date, datetime

from app.database.session import session_scope
from app.models.entities import Expense, User
from app.models.enums import ExpenseStatus
from app.repositories import Repositories
from app.services import audit_service, estimate_service, project_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require


class ExpenseRuleError(Exception):
    """Raised when an expense operation breaks a business rule."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def list_expenses(
    project_id: int | None = None,
    status: str = "",
    category: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    text: str = "",
    include_archived: bool = False,
) -> list[dict]:
    """Return expenses as table rows."""
    with session_scope() as session:
        repos = Repositories(session)
        filters = []
        if project_id:
            filters.append(Expense.project_id == project_id)
        if status:
            filters.append(Expense.status == status)
        if category:
            filters.append(Expense.category == category)
        if date_from:
            filters.append(Expense.pay_date >= date_from)
        if date_to:
            filters.append(Expense.pay_date <= date_to)
        if text:
            pattern = f"%{text}%"
            filters.append(Expense.note.ilike(pattern) | Expense.invoice_no.ilike(pattern))
        rows = []
        for expense in repos.expenses.list(
            filters=filters,
            order_by=Expense.pay_date.desc(),
            include_archived=include_archived,
        ):
            paid = sum(p.amount or 0.0 for p in expense.payments)
            rows.append(
                {
                    "id": expense.id,
                    "project_id": expense.project_id,
                    "project": expense.project.name if expense.project else "",
                    "category": expense.category,
                    "estimate_item_id": expense.estimate_item_id,
                    "estimate_item": expense.estimate_item.name if expense.estimate_item else "",
                    "counterparty_id": expense.counterparty_id,
                    "counterparty": expense.counterparty.name if expense.counterparty else "",
                    "amount": expense.amount or 0.0,
                    "paid": round(paid, 2),
                    "balance": round((expense.amount or 0.0) - paid, 2),
                    "pay_date": expense.pay_date,
                    "method": expense.method,
                    "invoice_no": expense.invoice_no or "",
                    "doc_path": expense.doc_path or "",
                    "note": expense.note or "",
                    "status": expense.status,
                    "created_by": expense.created_by.label if expense.created_by else "",
                    "approved_by": expense.approved_by.label if expense.approved_by else "",
                    "approved_at": expense.approved_at,
                    "is_archived": expense.is_archived,
                }
            )
        return rows


def save_expense(data: dict, actor: CurrentUser, expense_id: int | None = None) -> int:
    """Create or update an expense and refresh the estimate actuals."""
    require(actor.role_code, Perm.EXPENSE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        if expense_id:
            expense = repos.expenses.get_or_raise(expense_id)
            if expense.status in (ExpenseStatus.PAID.value,) and not actor.can(
                Perm.EXPENSE_APPROVE
            ):
                raise ExpenseRuleError("permission_denied")
            before = f"{expense.amount}/{expense.status}"
            repos.expenses.update(expense, **data)
            action = audit_service.Action.UPDATE
        else:
            expense = repos.expenses.create(created_by_id=actor.id, **data)
            before = ""
            action = audit_service.Action.CREATE
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="Expense",
            entity_id=expense.id,
            project_id=expense.project_id,
            description=f"{expense.category}: {expense.note or expense.invoice_no}",
            old_value=before,
            new_value=f"{expense.amount}/{expense.status}",
        )
        estimate_service.recalc_item_actuals(session, expense.project_id)
        return expense.id


def set_status(expense_id: int, status: str, actor: CurrentUser) -> None:
    """Approve, reject or mark an expense as paid.

    Approval requires :data:`Perm.EXPENSE_APPROVE`, so estimators and viewers
    cannot approve their own entries.
    """
    require(actor.role_code, Perm.EXPENSE_APPROVE)
    with session_scope() as session:
        repos = Repositories(session)
        expense = repos.expenses.get_or_raise(expense_id)
        old = expense.status
        expense.status = status
        if status in (ExpenseStatus.APPROVED.value, ExpenseStatus.PAID.value):
            expense.approved_by_id = actor.id
            expense.approved_at = datetime.now()
        action = {
            ExpenseStatus.APPROVED.value: audit_service.Action.APPROVE,
            ExpenseStatus.PAID.value: audit_service.Action.PAYMENT,
            ExpenseStatus.REJECTED.value: audit_service.Action.REJECT,
        }.get(status, audit_service.Action.UPDATE)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="Expense",
            entity_id=expense_id,
            project_id=expense.project_id,
            description=f"{expense.amount} ({expense.category})",
            old_value=old,
            new_value=status,
        )
        estimate_service.recalc_item_actuals(session, expense.project_id)


def archive_expense(expense_id: int, actor: CurrentUser, archived: bool = True) -> None:
    """Archive or restore an expense."""
    require(actor.role_code, Perm.EXPENSE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        expense = repos.expenses.get_or_raise(expense_id)
        repos.expenses.archive(expense, archived)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.ARCHIVE,
            entity_type="Expense",
            entity_id=expense_id,
            project_id=expense.project_id,
            description=str(expense.amount),
            new_value=str(archived),
        )
        estimate_service.recalc_item_actuals(session, expense.project_id)


def add_payment(expense_id: int, data: dict, actor: CurrentUser) -> int:
    """Register a payment against an expense; closes it when fully settled."""
    require(actor.role_code, Perm.EXPENSE_APPROVE)
    with session_scope() as session:
        repos = Repositories(session)
        expense = repos.expenses.get_or_raise(expense_id)
        payment = repos.payments.create(expense_id=expense_id, created_by_id=actor.id, **data)
        total_paid = sum(p.amount or 0.0 for p in expense.payments)
        if total_paid >= (expense.amount or 0.0) - 0.01:
            expense.status = ExpenseStatus.PAID.value
            expense.approved_by_id = expense.approved_by_id or actor.id
            expense.approved_at = expense.approved_at or datetime.now()
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.PAYMENT,
            entity_type="Payment",
            entity_id=payment.id,
            project_id=expense.project_id,
            description=f"payment for expense #{expense_id}",
            new_value=str(payment.amount),
        )
        estimate_service.recalc_item_actuals(session, expense.project_id)
        return payment.id


def list_payments(expense_id: int) -> list[dict]:
    """Return the payments settling an expense."""
    with session_scope() as session:
        expense = Repositories(session).expenses.get_or_raise(expense_id)
        return [
            {
                "id": p.id,
                "amount": p.amount,
                "pay_date": p.pay_date,
                "method": p.method,
                "note": p.note or "",
                "created_by": p.created_by.label if p.created_by else "",
            }
            for p in sorted(expense.payments, key=lambda x: x.pay_date or date.today())
        ]


def would_exceed_budget(project_id: int, amount: float) -> bool:
    """True when approving ``amount`` pushes the project over its budget.

    The system never blocks the operation — the manager decides — but the UI
    surfaces the warning before approval.
    """
    totals = project_service.get_totals(project_id)
    if totals.planned_budget <= 0:
        return False
    return (totals.actual + amount) > totals.planned_budget


def project_payments(project_id: int) -> list[dict]:
    """Return every payment of a project (report source)."""
    with session_scope() as session:
        repos = Repositories(session)
        rows = []
        for expense in repos.expenses.for_project(project_id):
            for payment in expense.payments:
                rows.append(
                    {
                        "pay_date": payment.pay_date,
                        "amount": payment.amount,
                        "method": payment.method,
                        "counterparty": (expense.counterparty.name if expense.counterparty else ""),
                        "category": expense.category,
                        "invoice_no": expense.invoice_no or "",
                        "note": payment.note or expense.note or "",
                    }
                )
        return sorted(rows, key=lambda r: r["pay_date"] or date.today(), reverse=True)
