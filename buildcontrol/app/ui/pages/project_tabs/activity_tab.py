"""Per-project audit trail."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.services import project_service
from app.services.audit_service import Action
from app.services.permissions import Perm
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import button
from app.ui.widgets.table import BADGE, DATETIME, Col, DataTable
from app.utils.formatting import short
from app.utils.i18n import tr
from app.utils.labels import audit_action_label

_KIND = {
    Action.CREATE: "success",
    Action.UPDATE: "info",
    Action.DELETE: "danger",
    Action.ARCHIVE: "neutral",
    Action.APPROVE: "success",
    Action.REJECT: "danger",
    Action.PAYMENT: "accent",
    Action.STOCK: "info",
}


class ActivityTab(BasePage):
    """Everything that happened inside one project."""

    permission = Perm.PROJECT_VIEW

    def __init__(self, project_id: int, parent: QWidget | None = None) -> None:
        super().__init__("", "", parent, show_header=False, compact=True)
        self.project_id = project_id
        self.table = DataTable(
            [
                Col("ts", tr("date"), DATETIME, width=155),
                Col("username", tr("user"), width=140),
                Col(
                    "action",
                    tr("action"),
                    BADGE,
                    width=150,
                    badge=lambda r: (
                        audit_action_label(r["action"]),
                        _KIND.get(r["action"], "neutral"),
                    ),
                ),
                Col("entity_type", tr("entity"), width=160),
                Col(
                    "description",
                    tr("description"),
                    stretch=True,
                    formatter=lambda r: short(r["description"], 100),
                ),
                Col("old_value", "←", width=160, formatter=lambda r: short(r["old_value"], 36)),
                Col("new_value", "→", width=160, formatter=lambda r: short(r["new_value"], 36)),
            ]
        )
        self.refresh_btn = button(tr("refresh"), "refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        self.table.add_action(self.refresh_btn)
        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the project activity."""
        self.table.set_rows(project_service.project_activity(self.project_id, limit=500))
