"""Audit trail page."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.services import project_service
from app.services.audit_service import Action
from app.services.permissions import Perm
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import button
from app.ui.widgets.table import BADGE, DATETIME, Col, DataTable, make_combo
from app.utils.formatting import short
from app.utils.i18n import tr
from app.utils.labels import audit_action_label

_ACTION_KIND = {
    Action.CREATE: "success",
    Action.UPDATE: "info",
    Action.DELETE: "danger",
    Action.ARCHIVE: "neutral",
    Action.APPROVE: "success",
    Action.REJECT: "danger",
    Action.PAYMENT: "accent",
    Action.STOCK: "info",
    Action.LOGIN: "neutral",
    Action.LOGOUT: "neutral",
    Action.BACKUP: "warning",
}


class AuditPage(BasePage):
    """Read-only audit log with action and text filters."""

    permission = Perm.AUDIT_VIEW

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("audit"), "", parent)
        self.table = DataTable(
            [
                Col("ts", tr("date"), DATETIME, width=150),
                Col("username", tr("user"), width=140),
                Col(
                    "action",
                    tr("action"),
                    BADGE,
                    width=150,
                    badge=lambda r: (
                        audit_action_label(r["action"]),
                        _ACTION_KIND.get(r["action"], "neutral"),
                    ),
                ),
                Col("entity_type", tr("entity"), width=150),
                Col("entity_id", "ID", width=70),
                Col(
                    "description",
                    tr("description"),
                    stretch=True,
                    formatter=lambda r: short(r["description"], 90),
                ),
                Col("old_value", "←", width=170, formatter=lambda r: short(r["old_value"], 40)),
                Col("new_value", "→", width=170, formatter=lambda r: short(r["new_value"], 40)),
            ]
        )
        actions = [("", tr("all"))] + [
            (value, audit_action_label(value))
            for value in sorted({v for k, v in vars(Action).items() if not k.startswith("_")})
        ]
        self.action_filter = make_combo(actions)
        self.action_filter.currentIndexChanged.connect(self.refresh)
        self.table.add_filter(self.action_filter)

        self.refresh_btn = button(tr("refresh"), "refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        self.table.add_action(self.refresh_btn)

        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the audit entries."""
        rows = project_service.global_activity(
            limit=1000, action=self.action_filter.currentData() or ""
        )
        self.table.set_rows(rows)
        self.header.set_subtitle(f"{tr('total')}: {len(rows)}")
