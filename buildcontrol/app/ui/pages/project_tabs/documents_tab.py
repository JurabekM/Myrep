"""Project documents: attached files and links."""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QWidget

from app.services import attachment_service
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import button
from app.ui.widgets.table import DATETIME, Col, DataTable
from app.utils.files import open_path
from app.utils.i18n import tr

ENTITY = "Project"


class DocumentsTab(BasePage):
    """Attachment register of one project."""

    permission = Perm.PROJECT_VIEW

    def __init__(self, project_id: int, parent: QWidget | None = None) -> None:
        super().__init__("", "", parent, show_header=False, compact=True)
        self.project_id = project_id

        self.table = DataTable(
            [
                Col("title", tr("name"), stretch=True),
                Col("file_path", tr("document"), stretch=True),
                Col("created_at", tr("created_at"), DATETIME, width=160),
                Col("user", tr("author"), width=150),
            ],
            paginated=False,
        )
        self.table.row_activated.connect(lambda row: open_path(row["file_path"]))

        self.add_btn = button(tr("add"), "attach", "Primary")
        self.add_btn.clicked.connect(self._attach)
        self.add_btn.setEnabled(self.can(Perm.PROJECT_EDIT))
        self.open_btn = button(tr("open"), "open")
        self.open_btn.clicked.connect(self._open)
        self.del_btn = button(tr("delete"), "delete", "Ghost")
        self.del_btn.clicked.connect(self._delete)
        self.del_btn.setEnabled(self.can(Perm.PROJECT_EDIT))
        for widget in (self.add_btn, self.open_btn, self.del_btn):
            self.table.add_action(widget)

        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the attachment list."""
        self.table.set_rows(attachment_service.list_attachments(ENTITY, self.project_id))

    def _attach(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, tr("attachments"))
        if not paths:
            return
        for path in paths:
            try:
                attachment_service.attach(
                    ENTITY, self.project_id, path, self.actor, project_id=self.project_id
                )
            except Exception as exc:
                self.handle(exc)
                return
        self.notify(tr("saved"))
        self.refresh()

    def _open(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        if not open_path(row["file_path"]):
            self.notify(tr("no_data"), "warning")

    def _delete(self) -> None:
        row = self.table.current_row()
        if row is None or not confirm(self, tr("confirm_question"), tr("delete")):
            return
        try:
            attachment_service.remove(row["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()
