"""Audit log worksheet."""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit, QFileDialog, QHBoxLayout, QLabel, QPushButton, QWidget

from app.controllers.app_context import AppContext
from app.database.engine import session_scope
from app.models.enums import Permission as Perm
from app.reports import excel_export
from app.services import audit_service, auth_service
from app.ui.i18n import tr
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import DataTable, Panel, SearchBox, combo, show_error, show_info
from app.utils.dates import end_of_day, fmt_datetime, start_of_day
from app.utils.formatting import truncate

COLUMNS = [
    "common.date",
    "common.user",
    "audit.action",
    "audit.entity",
    "common.name",
    "audit.old",
    "audit.new",
    "common.comment",
]


class AuditPage(BasePage):
    """Immutable record of every important action."""

    title_key = "audit.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._build()

    def _build(self) -> None:
        """Assemble the filters and the table."""
        self.export_button = QPushButton(tr("common.export_excel"))
        self.export_button.setIcon(theme.icon("fa6s.file-excel", theme.SUCCESS))
        self.export_button.clicked.connect(self._export)
        self.header().addWidget(self.export_button)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self.reload)
        row.addWidget(self.search_box, 2)

        self.action_box = combo([(tr("common.all"), "")])
        self.action_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.action_box)

        users = auth_service.list_users(include_archived=True)
        self.user_box = combo([(tr("common.all"), None)] + [(u.full_name, u.id) for u in users])
        self.user_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.user_box)

        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.dateChanged.connect(self.reload)
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.dateChanged.connect(self.reload)
        row.addWidget(QLabel(tr("common.from")))
        row.addWidget(self.date_from)
        row.addWidget(QLabel(tr("common.to")))
        row.addWidget(self.date_to)
        row.addStretch(1)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=4)
        panel.body().addWidget(self.table, 1)
        self.body().addWidget(panel, 1)

    def reload(self) -> None:
        """Reload the audit table."""
        if not self.user.can(Perm.AUDIT_VIEW):
            return
        with session_scope() as session:
            current_action = self.action_box.currentData()
            actions = audit_service.distinct_actions(session)
            self.action_box.blockSignals(True)
            self.action_box.clear()
            self.action_box.addItem(tr("common.all"), "")
            for action in actions:
                self.action_box.addItem(action, action)
            index = self.action_box.findData(current_action)
            self.action_box.setCurrentIndex(index if index >= 0 else 0)
            self.action_box.blockSignals(False)

            entries = audit_service.search(
                session,
                query=self.search_box.text(),
                action=self.action_box.currentData() or "",
                user_id=self.user_box.currentData(),
                date_from=start_of_day(self.date_from.date().toPython()),
                date_to=end_of_day(self.date_to.date().toPython()),
            )
            rows = [
                [
                    fmt_datetime(entry.created_at),
                    entry.username or "system",
                    entry.action,
                    entry.entity_type,
                    entry.entity_label,
                    truncate(entry.old_value, 40),
                    truncate(entry.new_value, 40),
                    truncate(entry.detail, 60),
                ]
                for entry in entries
            ]
            ids = [entry.id for entry in entries]
        self.table.fill(rows, ids=ids)

    def _export(self) -> None:
        """Export the audit log to Excel."""
        if not self.require(Perm.REPORT_EXPORT):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("common.export_excel"), "audit_log.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        with session_scope() as session:
            entries = audit_service.search(
                session,
                query=self.search_box.text(),
                action=self.action_box.currentData() or "",
                user_id=self.user_box.currentData(),
                date_from=start_of_day(self.date_from.date().toPython()),
                date_to=end_of_day(self.date_to.date().toPython()),
                limit=20000,
            )
            rows = [
                [
                    fmt_datetime(entry.created_at),
                    entry.username,
                    entry.action,
                    entry.entity_type,
                    entry.entity_label,
                    entry.old_value,
                    entry.new_value,
                    entry.detail,
                ]
                for entry in entries
            ]
        try:
            excel_export.export_generic(path, "Audit log", [tr(key) for key in COLUMNS], rows)
        except Exception as exc:
            show_error(self, tr("err.export_failed", detail=str(exc)))
            return
        show_info(self, tr("rep.saved_to", path=path))

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.export_button.setText(tr("common.export_excel"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.reload()
