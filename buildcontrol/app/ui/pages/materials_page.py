"""Global material catalogue page."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.services.permissions import Perm
from app.ui.pages.materials_view import MaterialsView


class MaterialsPage(MaterialsView):
    """Material catalogue with stock balances."""

    permission = Perm.WAREHOUSE_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, show_header=True)
