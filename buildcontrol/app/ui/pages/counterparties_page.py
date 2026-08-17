"""Global counterparties page."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.services.permissions import Perm
from app.ui.pages.counterparties_view import CounterpartiesView


class CounterpartiesPage(CounterpartiesView):
    """Suppliers and contractors register."""

    permission = Perm.COUNTERPARTY_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(kind="", parent=parent, show_header=True)
