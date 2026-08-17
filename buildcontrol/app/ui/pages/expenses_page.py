"""Global expenses page."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.services.permissions import Perm
from app.ui.pages.expenses_view import ExpensesView


class ExpensesPage(ExpensesView):
    """Expense register across every project."""

    permission = Perm.EXPENSE_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(project_id=None, parent=parent, show_header=True)
