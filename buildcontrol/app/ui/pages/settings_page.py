"""Settings: company profile, users, roles, dictionaries, backup and export."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import BACKUP_DIR
from app.controllers.sync_controller import get_sync_controller
from app.models.enums import RoleCode
from app.services import auth_service, settings_service
from app.services.auth_service import AuthError
from app.services.permissions import ROLE_PERMISSIONS, Perm
from app.ui.dialogs.base_dialog import confirm, show_info
from app.ui.dialogs.form_dialog import (
    CHECK,
    COMBO,
    FILE,
    PASSWORD,
    TEXT,
    TEXTAREA,
    Field,
    FormDialog,
)
from app.ui.pages.base_page import BasePage
from app.ui.pages.sync_tab import SyncTab
from app.ui.styles.theme import SPACING, SPACING_LG, SPACING_SM
from app.ui.widgets.common import Card, button, field_label
from app.ui.widgets.table import BADGE, DATETIME, Col, DataTable, make_combo
from app.utils.files import open_path
from app.utils.i18n import tr
from app.utils.labels import role_label


class SettingsPage(QWidget):
    """Tabbed settings screen."""

    permission = Perm.SETTINGS_MANAGE

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING, SPACING_LG, SPACING)
        self.tabs = QTabWidget()
        self.company_tab = CompanyTab()
        self.users_tab = UsersTab()
        self.roles_tab = RolesTab()
        self.dict_tab = DictionariesTab()
        self.sync_tab = SyncTab(get_sync_controller())
        self.backup_tab = BackupTab()
        self.tabs.addTab(self.company_tab, tr("company"))
        self.tabs.addTab(self.users_tab, tr("users"))
        self.tabs.addTab(self.roles_tab, tr("roles"))
        self.tabs.addTab(self.dict_tab, tr("dictionaries"))
        self.tabs.addTab(self.sync_tab, tr("sync"))
        self.tabs.addTab(self.backup_tab, tr("backup"))
        layout.addWidget(self.tabs)

    def refresh(self) -> None:
        """Refresh the visible tab."""
        widget = self.tabs.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()


class CompanyTab(BasePage):
    """Company profile used in report headers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("company"), "", parent, show_header=False, compact=True)
        self.card = Card(tr("company"))
        self.root.addWidget(self.card, 0)
        self._build_inline()
        self.root.addStretch(1)

    def _fields(self) -> list[Field]:
        return [
            Field("name", tr("company_name"), TEXT, required=True, span=2),
            Field("address", tr("address"), TEXT, span=2),
            Field("phone", tr("phone"), TEXT),
            Field("logo_path", tr("logo"), FILE),
            Field("requisites", tr("requisites"), TEXTAREA, span=2),
        ]

    def _build_inline(self) -> None:
        """Render the company form directly inside the tab."""
        self.inline = FormDialog(
            tr("company"), self._fields(), settings_service.get_company(), parent=self
        )
        inner = self.inline.body()
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        while inner.count():
            item = inner.takeAt(0)
            if item.layout() is not None:
                holder_layout.addLayout(item.layout())
            elif item.widget() is not None:
                holder_layout.addWidget(item.widget())
        self.card.body().addWidget(holder)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_btn = button(tr("save"), "save", "Primary")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(self.can(Perm.SETTINGS_MANAGE))
        save_row.addWidget(self.save_btn)
        self.card.body().addLayout(save_row)

    def _save(self) -> None:
        values = self.inline.values()
        try:
            settings_service.save_company(values, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))

    def refresh(self) -> None:
        """No-op: values are loaded when the tab is created."""


class UsersTab(BasePage):
    """User administration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("users"), "", parent, show_header=False, compact=True)
        self.table = DataTable(
            [
                Col("username", tr("username"), width=150),
                Col("full_name", tr("full_name"), stretch=True),
                Col(
                    "role_code",
                    tr("role"),
                    BADGE,
                    width=170,
                    badge=lambda r: (role_label(r["role_code"]), _role_kind(r["role_code"])),
                ),
                Col("email", tr("email"), width=200),
                Col("phone", tr("phone"), width=150),
                Col("last_login", tr("login"), DATETIME, width=150),
                Col(
                    "is_active",
                    tr("is_active"),
                    BADGE,
                    width=110,
                    badge=lambda r: (
                        (tr("yes"), "success") if r["is_active"] else (tr("no"), "danger")
                    ),
                ),
            ]
        )
        self.new_btn = button(tr("new_user"), "add", "Primary")
        self.new_btn.clicked.connect(self._create)
        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit)
        self.password_btn = button(tr("reset_password"), "user")
        self.password_btn.clicked.connect(self._reset_password)
        for widget in (self.new_btn, self.edit_btn, self.password_btn):
            self.table.add_action(widget)
            widget.setEnabled(self.can(Perm.USER_MANAGE))
        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the user list."""
        self.table.set_rows(auth_service.list_users())

    def _role_options(self) -> list[tuple[str, str]]:
        return [(role.value, role_label(role.value)) for role in RoleCode]

    def _create(self) -> None:
        fields = [
            Field("username", tr("username"), TEXT, required=True),
            Field("full_name", tr("full_name"), TEXT, required=True),
            Field("role_code", tr("role"), COMBO, options=self._role_options()),
            Field("email", tr("email"), TEXT),
            Field("phone", tr("phone"), TEXT),
            Field("password", tr("password"), PASSWORD, required=True),
        ]
        dialog = FormDialog(
            tr("new_user"), fields, {"role_code": RoleCode.VIEWER.value}, parent=self
        )
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            auth_service.create_user(
                username=values["username"],
                password=values["password"],
                full_name=values["full_name"],
                role_code=values["role_code"],
                email=values["email"],
                phone=values["phone"],
            )
        except AuthError as exc:
            self.handle(exc)
            return
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _edit(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        fields = [
            Field("full_name", tr("full_name"), TEXT, required=True),
            Field("role_code", tr("role"), COMBO, options=self._role_options()),
            Field("email", tr("email"), TEXT),
            Field("phone", tr("phone"), TEXT),
            Field("is_active", tr("is_active"), CHECK),
        ]
        dialog = FormDialog(tr("edit"), fields, row, row["username"], parent=self)
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            auth_service.update_user(
                row["id"],
                full_name=values["full_name"],
                role_code=values["role_code"],
                email=values["email"],
                phone=values["phone"],
                is_active=values["is_active"],
                actor=self.actor,
            )
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _reset_password(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        dialog = FormDialog(
            tr("reset_password"),
            [Field("password", tr("password"), PASSWORD, required=True, span=2)],
            {},
            row["username"],
            parent=self,
            width=460,
        )
        if not dialog.exec():
            return
        try:
            auth_service.set_password(row["id"], dialog.values()["password"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))


class RolesTab(BasePage):
    """Read-only permission matrix of the built-in roles."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("roles"), "", parent, show_header=False, compact=True)
        self.table = DataTable(
            [
                Col("role", tr("role"), width=190),
                Col("permission", tr("actions"), stretch=True),
            ],
            paginated=False,
        )
        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Rebuild the permission matrix."""
        rows = []
        for role_code, perms in ROLE_PERMISSIONS.items():
            listing = tr("all") if "*" in perms else ", ".join(sorted(perms))
            rows.append({"role": role_label(role_code), "permission": listing})
        self.table.set_rows(rows)


class DictionariesTab(BasePage):
    """Editable reference dictionaries."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("dictionaries"), "", parent, show_header=False, compact=True)
        self.kind_box = make_combo(
            [(kind, tr(_dict_label(kind))) for kind in settings_service.REF_KINDS]
        )
        self.kind_box.currentIndexChanged.connect(self.refresh)
        top = QHBoxLayout()
        top.addWidget(field_label(tr("dictionaries")))
        top.addWidget(self.kind_box)
        top.addStretch(1)
        self.root.addLayout(top)

        self.table = DataTable(
            [
                Col("code", tr("code"), width=160),
                Col("name_uz", "O'zbekcha", stretch=True),
                Col("name_en", "English", stretch=True),
                Col(
                    "is_system",
                    tr("type"),
                    BADGE,
                    width=120,
                    badge=lambda r: (
                        ("system", "neutral") if r["is_system"] else (tr("edit"), "accent")
                    ),
                ),
            ],
            paginated=False,
        )
        self.add_btn = button(tr("add"), "add", "Primary")
        self.add_btn.clicked.connect(self._create)
        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit)
        self.del_btn = button(tr("delete"), "delete", "Ghost")
        self.del_btn.clicked.connect(self._delete)
        for widget in (self.add_btn, self.edit_btn, self.del_btn):
            self.table.add_action(widget)
            widget.setEnabled(self.can(Perm.SETTINGS_MANAGE))
        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the selected dictionary."""
        kind = str(self.kind_box.currentData())
        self.table.set_rows(settings_service.list_refs(kind))

    def _fields(self) -> list[Field]:
        return [
            Field("code", tr("code"), TEXT, required=True),
            Field("name_uz", "O'zbekcha", TEXT, required=True),
            Field("name_en", "English", TEXT, required=True),
        ]

    def _create(self) -> None:
        dialog = FormDialog(tr("add"), self._fields(), {}, parent=self, width=520)
        if not dialog.exec():
            return
        values = dialog.values()
        values["kind"] = str(self.kind_box.currentData())
        try:
            settings_service.save_ref(values, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()

    def _edit(self) -> None:
        row = self.table.current_row()
        if row is None:
            return
        dialog = FormDialog(tr("edit"), self._fields(), row, parent=self, width=520)
        if not dialog.exec():
            return
        try:
            settings_service.save_ref(dialog.values(), self.actor, row["id"])
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()

    def _delete(self) -> None:
        row = self.table.current_row()
        if row is None or not confirm(self, tr("confirm_question"), tr("delete")):
            return
        try:
            settings_service.delete_ref(row["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.refresh()


class BackupTab(BasePage):
    """Database backup, restore and CSV export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("backup"), "", parent, show_header=False, compact=True)
        buttons = QHBoxLayout()
        buttons.setSpacing(SPACING_SM)
        self.create_btn = button(tr("create_backup"), "save", "Primary")
        self.create_btn.clicked.connect(self._create)
        self.restore_btn = button(tr("restore_backup"), "refresh", "Danger")
        self.restore_btn.clicked.connect(self._restore)
        self.export_btn = button(tr("export_data"), "excel")
        self.export_btn.clicked.connect(self._export)
        self.folder_btn = button(tr("open_folder"), "open", "Ghost")
        self.folder_btn.clicked.connect(lambda: open_path(BACKUP_DIR))
        for widget in (self.create_btn, self.restore_btn, self.export_btn, self.folder_btn):
            buttons.addWidget(widget)
            widget.setEnabled(self.can(Perm.SETTINGS_MANAGE))
        buttons.addStretch(1)
        self.root.addLayout(buttons)

        self.table = DataTable(
            [
                Col("name", tr("name"), stretch=True),
                Col("created", tr("created_at"), DATETIME, width=170),
                Col(
                    "size",
                    tr("total"),
                    width=140,
                    formatter=lambda r: f"{r['size'] / 1024:,.0f} KB".replace(",", " "),
                ),
            ],
            paginated=False,
        )
        self.root.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Reload the backup list."""
        self.table.set_rows(settings_service.list_backups())

    def _create(self) -> None:
        try:
            path = settings_service.create_backup(self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(f"{tr('backup_created')}: {path.name}")
        self.refresh()

    def _restore(self) -> None:
        row = self.table.current_row()
        path = row["path"] if row else ""
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("restore_backup"), str(BACKUP_DIR))
        if not path:
            return
        if not confirm(self, tr("restore_warning"), tr("restore_backup")):
            return
        try:
            settings_service.restore_backup(path, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, tr("restart_required"))

    def _export(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("export_data"))
        try:
            paths = settings_service.export_tables(self.actor, folder or None)
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{paths[0].parent}")
        open_path(paths[0].parent)


def _role_kind(role_code: str) -> str:
    return {
        RoleCode.ADMIN.value: "danger",
        RoleCode.MANAGER.value: "accent",
        RoleCode.ESTIMATOR.value: "info",
        RoleCode.STOREKEEPER.value: "warning",
        RoleCode.VIEWER.value: "neutral",
    }.get(role_code, "neutral")


def _dict_label(kind: str) -> str:
    return {
        "estimate_category": "category",
        "unit": "unit",
        "project_status": "status",
        "expense_category": "nav_expenses",
    }.get(kind, kind)
