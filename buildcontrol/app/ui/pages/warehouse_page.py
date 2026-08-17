"""Global warehouse movements page."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.services.permissions import Perm
from app.ui.pages.warehouse_view import WarehouseView


class WarehousePage(WarehouseView):
    """Stock movements across every project."""

    permission = Perm.WAREHOUSE_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(project_id=None, parent=parent, show_header=True)
