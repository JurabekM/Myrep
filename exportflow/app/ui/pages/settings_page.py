"""Settings page: company, users, roles, integrations, backup and audit log."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.config import SUPPORTED_CURRENCIES
from app.controllers.app_context import AppContext
from app.services import (
    audit_service,
    auth_service,
    checklist_service,
    company_service,
    email_service,
    import_service,
    integration_service,
    product_service,
)
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import (
    PageHeader,
    banner,
    button,
    combo,
    combo_value,
    line_edit,
    section_title,
    text_area,
)
from app.ui.widgets.table import Column, DataTable


class SettingsPage(BasePage):
    """Tabbed settings workspace."""

    permission = "settings.view"
    topics = ("settings", "user", "integration")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        self.header.add_action(button(t("common.refresh"), self.refresh, "Ghost"))

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.company_tab = self._build_company_tab()
        self.users_table = DataTable(self._user_columns())
        self.users_table.row_activated.connect(lambda row: self._edit_user(row))
        self.roles_table = DataTable(self._role_columns())
        self.reference_tab = self._build_reference_tab()
        self.integrations_tab = self._build_integrations_tab()
        self.backup_tab = self._build_backup_tab()
        self.audit_table = DataTable(self._audit_columns())

        self.tabs.addTab(self.company_tab, t("settings.company"))
        self.tabs.addTab(self._wrap_users(), t("settings.users"))
        self.tabs.addTab(self.roles_table, t("settings.roles"))
        self.tabs.addTab(self.reference_tab, t("settings.catalogs"))
        self.tabs.addTab(self.integrations_tab, t("settings.integrations"))
        self.tabs.addTab(self.backup_tab, t("settings.backup"))
        self.tabs.addTab(self.audit_table, t("settings.audit"))

        self.retranslate()

    # ------------------------------------------------------------ company
    def _build_company_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 10, 12, 10)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        self.company_fields: dict[str, QWidget] = {}
        text_fields = [
            ("name", t("buyer.company")),
            ("legal_name", t("settings.legal_name")),
            ("address", t("buyer.address")),
            ("country", t("common.country")),
            ("city", t("common.city")),
            ("tax_id", t("settings.tax_id")),
            ("phone", t("common.phone")),
            ("email", t("common.email")),
            ("website", t("common.website")),
            ("export_contact_name", t("settings.export_contact")),
            ("export_contact_phone", t("settings.export_contact") + " · " + t("common.phone")),
            ("export_contact_email", t("settings.export_contact") + " · " + t("common.email")),
            ("bank_name", t("settings.bank_name")),
            ("bank_account", t("settings.bank_account")),
            ("bank_swift", t("settings.bank_swift")),
            ("correspondent_bank", t("settings.bank")),
        ]
        for key, label in text_fields:
            widget = line_edit()
            self.company_fields[key] = widget
            form.addRow(label, widget)

        self.company_fields["default_currency"] = combo(
            [(c, c) for c in SUPPORTED_CURRENCIES], "USD", False
        )
        form.addRow(t("settings.default_currency"), self.company_fields["default_currency"])
        self.company_fields["timezone"] = line_edit("", "Asia/Tashkent")
        form.addRow(t("settings.timezone"), self.company_fields["timezone"])
        self.company_fields["languages"] = line_edit("", "uz,ru,en")
        form.addRow(t("settings.languages"), self.company_fields["languages"])

        logo_row = QHBoxLayout()
        self.logo_field = line_edit(t("settings.logo"))
        logo_row.addWidget(self.logo_field, 1)
        logo_row.addWidget(button(t("settings.choose_logo"), self._choose_logo, "Ghost"))
        form.addRow(t("settings.logo"), self._wrap_layout(logo_row))
        layout.addLayout(form)

        layout.addWidget(section_title(t("settings.about")))
        for key, label in (("about_en", "EN"), ("about_ru", "RU"), ("about_uz", "UZ")):
            area = text_area(label, "", 70)
            self.company_fields[key] = area
            layout.addWidget(QLabel(label))
            layout.addWidget(area)

        if self.ctx.can("settings.edit"):
            layout.addWidget(button(t("common.save"), self._save_company, "Primary"))
        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    @staticmethod
    def _wrap_layout(layout) -> QWidget:
        """Wrap a layout into a widget so it can be used in a form row."""
        holder = QWidget()
        holder.setLayout(layout)
        return holder

    def _choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("settings.logo"), "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.logo_field.setText(path)

    def _save_company(self) -> None:
        values: dict[str, Any] = {}
        for key, widget in self.company_fields.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text().strip()
            elif hasattr(widget, "toPlainText"):
                values[key] = widget.toPlainText().strip()
            else:
                values[key] = combo_value(widget)
        values["logo_path"] = self.logo_field.text().strip() or None
        try:
            self.ctx.run(lambda s: company_service.save_company(s, self.ctx.user, values))
        except Exception as exc:
            self.handle_error(exc)
            return
        self.ctx.invalidate_company()
        self.ctx.notify("settings")
        self.info(t("common.saved"))

    # -------------------------------------------------------------- users
    def _wrap_users(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        actions = QHBoxLayout()
        if self.ctx.can("user.manage"):
            actions.addWidget(
                button(t("settings.new_user"), lambda: self._edit_user(None), "Primary")
            )
            actions.addWidget(button(t("settings.change_password"), self._change_password, "Ghost"))
            actions.addWidget(button(t("common.archive"), self._archive_user, "Ghost"))
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.users_table, 1)
        return container

    def _user_columns(self) -> list[Column]:
        return [
            Column("username", t("login.username"), width=140),
            Column("full_name", t("login.full_name"), stretch=True),
            Column("role_code", t("settings.role"), kind="status", group="role", width=170),
            Column("email", t("common.email"), width=200),
            Column("phone", t("common.phone"), width=140),
            Column("is_active", t("settings.active"), kind="bool", width=90),
            Column("last_login_at", t("common.date"), kind="datetime", width=150),
        ]

    def _role_columns(self) -> list[Column]:
        return [
            Column("code", t("settings.role"), kind="status", group="role", width=180),
            Column("name", t("common.name"), width=180),
            Column(
                "permission_count", t("settings.permissions"), kind="number", decimals=0, width=130
            ),
            Column("permission_list", t("settings.permissions"), stretch=True),
        ]

    def _edit_user(self, row: dict | None) -> None:
        if not self.ctx.can("user.manage"):
            return
        roles = self.ctx.read(auth_service.list_roles)
        role_options = [(role["id"], te("role", role["code"])) for role in roles]
        values: dict[str, Any] = row.copy() if row else {"is_active": True, "language": "uz"}
        fields = [
            Field("username", t("login.username"), required=True),
            Field("full_name", t("login.full_name"), required=True),
            Field(
                "role_id",
                t("settings.role"),
                "combo",
                role_options,
                required=True,
                with_empty=False,
            ),
            Field("email", t("common.email")),
            Field("phone", t("common.phone")),
            Field("position", t("buyer.position")),
            Field(
                "language",
                t("common.language"),
                "combo",
                [("uz", "O‘zbekcha"), ("ru", "Русский"), ("en", "English")],
                with_empty=False,
            ),
            Field("is_active", t("settings.active"), "check"),
            Field("password", t("settings.password")),
        ]

        def _save(collected: dict[str, Any]) -> int:
            return self.ctx.run(
                lambda s: auth_service.save_user(
                    s,
                    self.ctx.user,
                    user_id=row["id"] if row else None,
                    username=collected["username"],
                    full_name=collected["full_name"],
                    role_id=collected["role_id"],
                    email=collected.get("email"),
                    phone=collected.get("phone"),
                    position=collected.get("position"),
                    language=collected.get("language") or "uz",
                    is_active=bool(collected.get("is_active")),
                    password=collected.get("password"),
                ).id
            )

        dialog = FormDialog(t("settings.new_user"), fields, values, _save, self, width=600)
        if dialog.exec():
            self.ctx.notify("user")
            self.info(t("common.saved"))

    def _change_password(self) -> None:
        row = self.users_table.current_row()
        if row is None:
            return
        fields = [Field("password", t("settings.password"), required=True)]

        def _save(collected: dict[str, Any]) -> None:
            self.ctx.run(
                lambda s: auth_service.change_password(
                    s, self.ctx.user, row["id"], collected["password"]
                )
            )

        dialog = FormDialog(t("settings.change_password"), fields, {}, _save, self, width=460)
        if dialog.exec():
            self.info(t("common.saved"))

    def _archive_user(self) -> None:
        row = self.users_table.current_row()
        if row is None or not self.confirm(t("common.confirm_archive")):
            return
        try:
            self.ctx.run(lambda s: auth_service.archive_user(s, self.ctx.user, row["id"]))
            self.ctx.notify("user")
        except Exception as exc:
            self.handle_error(exc)

    # --------------------------------------------------------- reference
    def _build_reference_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(10)

        layout.addWidget(section_title(t("settings.categories")))
        self.categories_table = DataTable(
            [
                Column("code", t("common.name"), width=140),
                Column("name_uz", "UZ", width=180),
                Column("name_ru", "RU", width=180),
                Column("name_en", "EN", stretch=True),
            ]
        )
        layout.addWidget(self.categories_table, 1)
        if self.ctx.can("product.edit"):
            layout.addWidget(button(t("common.new"), self._new_category, "Ghost"))

        layout.addWidget(section_title(t("settings.email_templates")))
        self.templates_table = DataTable(
            [
                Column("code", t("common.name"), width=180),
                Column("name", t("common.description"), stretch=True),
                Column("language", t("common.language"), width=90),
                Column("purpose", t("common.type"), width=140),
            ]
        )
        self.templates_table.row_activated.connect(self._edit_email_template)
        layout.addWidget(self.templates_table, 1)

        layout.addWidget(section_title(t("settings.checklist_templates")))
        self.checklist_table = DataTable(
            [
                Column("code", t("common.name"), width=180),
                Column("name", t("common.description"), stretch=True),
                Column("scope", t("checklist.scope"), width=110),
                Column("trigger_status", t("checklist.trigger"), width=170),
                Column("item_count", t("checklist.items"), kind="number", decimals=0, width=90),
            ]
        )
        layout.addWidget(self.checklist_table, 1)
        return container

    def _new_category(self) -> None:
        fields = [
            Field("code", t("common.name"), required=True),
            Field("name_uz", "UZ", required=True),
            Field("name_ru", "RU"),
            Field("name_en", "EN"),
        ]

        def _save(values: dict[str, Any]) -> int:
            return self.ctx.run(
                lambda s: product_service.save_category(s, self.ctx.user, values).id
            )

        dialog = FormDialog(t("settings.categories"), fields, {}, _save, self, width=520)
        if dialog.exec():
            self.ctx.notify("settings")

    def _edit_email_template(self, row: dict) -> None:
        if not self.ctx.can("settings.edit"):
            return
        data = self.ctx.read(lambda s: email_service.list_templates(s))
        template = next((item for item in data if item["id"] == row["id"]), row)
        fields = [
            Field("code", t("common.name"), required=True),
            Field("name", t("common.description"), required=True),
            Field(
                "language",
                t("common.language"),
                "combo",
                [("en", "EN"), ("ru", "RU"), ("uz", "UZ")],
                with_empty=False,
            ),
            Field("subject", t("email.subject")),
            Field("body", t("email.body"), "textarea", height=220),
        ]

        def _save(values: dict[str, Any]) -> int:
            payload = dict(values)
            payload["id"] = row["id"]
            return self.ctx.run(lambda s: email_service.save_template(s, self.ctx.user, payload).id)

        dialog = FormDialog(t("settings.email_templates"), fields, template, _save, self, width=760)
        if dialog.exec():
            self.ctx.notify("settings")

    # ------------------------------------------------------- integrations
    def _build_integrations_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(10)
        layout.addWidget(banner(t("settings.credentials_hint"), "info"))
        self.integrations_table = DataTable(
            [
                Column(
                    "kind", t("common.type"), kind="status", group="integration_kind", width=150
                ),
                Column("name", t("settings.provider"), stretch=True),
                Column("provider", "code", width=160),
                Column("status", t("common.status"), kind="status", width=130),
                Column("last_sync_text", t("settings.last_sync"), width=150),
                Column("last_error", t("common.notes"), width=220),
            ]
        )
        self.integrations_table.row_activated.connect(self._configure_integration)
        layout.addWidget(self.integrations_table, 1)

        actions = QHBoxLayout()
        if self.ctx.can("integration.manage"):
            actions.addWidget(
                button(t("settings.test_connection"), self._test_integration, "Primary")
            )
            actions.addWidget(button(t("settings.use_demo"), self._use_demo, "Ghost"))
            actions.addWidget(button(t("settings.import_leads"), self._import_leads, "Ghost"))
        actions.addStretch(1)
        layout.addLayout(actions)

        self.sync_log = text_area(t("settings.sync_log"), "", 120)
        self.sync_log.setReadOnly(True)
        layout.addWidget(self.sync_log)
        return container

    def _configure_integration(self, row: dict) -> None:
        if not self.ctx.can("integration.manage"):
            return
        providers = integration_service.available_providers(row["kind"])
        provider_options = [(item["code"], item["label"]) for item in providers]
        chooser = FormDialog(
            t("settings.provider"),
            [
                Field(
                    "provider",
                    t("settings.provider"),
                    "combo",
                    provider_options,
                    required=True,
                    with_empty=False,
                )
            ],
            {"provider": row["provider"]},
            lambda values: values["provider"],
            self,
            width=460,
        )
        if not chooser.exec():
            return
        provider_code = chooser.result_value
        definition = next((item for item in providers if item["code"] == provider_code), None)
        if definition is None:
            return

        fields = [
            Field(name, label, "text", tooltip=t("settings.credentials_hint") if secret else "")
            for name, label, secret in definition["fields"]
        ]
        current = next(
            (
                cfg
                for cfg in self.ctx.read(lambda s: integration_service.list_configs(s, row["kind"]))
                if cfg["provider"] == provider_code
            ),
            None,
        )
        values = dict(current["settings"]) if current else {}

        def _save(collected: dict[str, Any]) -> None:
            settings = {}
            secrets = {}
            for name, _label, is_secret in definition["fields"]:
                value = collected.get(name) or ""
                if is_secret:
                    secrets[name] = value
                else:
                    settings[name] = value
            self.ctx.run(
                lambda s: integration_service.save_config(
                    s,
                    self.ctx.user,
                    kind=row["kind"],
                    provider=provider_code,
                    settings=settings,
                    secrets=secrets,
                )
            )

        if not fields:
            _save({})
            self.ctx.notify("integration")
            self.info(t("common.saved"))
            return

        dialog = FormDialog(definition["label"], fields, values, _save, self, width=560)
        if dialog.exec():
            self.ctx.notify("integration")
            self.info(t("common.saved"))

    def _test_integration(self) -> None:
        row = self.integrations_table.current_row()
        if row is None:
            return
        try:
            result = self.ctx.run(
                lambda s: integration_service.test_connection(
                    s, self.ctx.user, row["kind"], row["provider"]
                )
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.ctx.show_toast(result.message, "success" if result.ok else "error")
        self.refresh()

    def _use_demo(self) -> None:
        row = self.integrations_table.current_row()
        if row is None:
            return
        try:
            self.ctx.run(
                lambda s: integration_service.switch_to_demo(s, self.ctx.user, row["kind"])
            )
            self.ctx.notify("integration")
        except Exception as exc:
            self.handle_error(exc)

    def _import_leads(self) -> None:
        try:
            result = self.ctx.run(
                lambda s: import_service.import_leads_from_provider(s, self.ctx.user)
            )
            self.ctx.notify("lead")
            self.info(t("lead.imported", leads=result["leads"], provider=result["provider"]))
        except Exception as exc:
            self.handle_error(exc)

    # ------------------------------------------------------------ backup
    def _build_backup_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(10)
        layout.addWidget(banner(t("settings.backup_warning"), "warning"))
        row = QHBoxLayout()
        if self.ctx.can("backup.manage"):
            row.addWidget(button(t("settings.backup_create"), self._backup, "Primary"))
            row.addWidget(button(t("settings.backup_restore"), self._restore, "Danger"))
        row.addWidget(button(t("product.template"), self._download_template, "Ghost"))
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        return container

    def _backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("settings.backup_create"), "exportflow-backup.db", "SQLite (*.db)"
        )
        if not path:
            return
        try:
            written = import_service.backup_database(path)
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)

    def _restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("settings.backup_restore"), "", "SQLite (*.db)"
        )
        if not path or not self.confirm(t("settings.backup_warning")):
            return
        try:
            import_service.restore_database(path)
            self.info(t("common.saved"))
            self.ctx.notify("*")
        except Exception as exc:
            self.handle_error(exc)

    def _download_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("product.template"), "products-template.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            self.info(t("common.exported", path=import_service.export_template("products", path)))
        except Exception as exc:
            self.handle_error(exc)

    # ------------------------------------------------------------- audit
    def _audit_columns(self) -> list[Column]:
        return [
            Column("at", t("common.date"), kind="datetime", width=150),
            Column("username", t("titlebar.user"), width=130),
            Column("action", t("common.actions"), width=130),
            Column("entity_type", t("common.type"), width=150),
            Column("entity_id", "ID", kind="number", decimals=0, width=70),
            Column("summary", t("common.description"), stretch=True),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload every tab."""

        def _load(session: Session) -> dict:
            return {
                "company": company_service.company_dict(session),
                "users": auth_service.list_users(session, include_archived=True),
                "roles": auth_service.list_roles(session),
                "categories": product_service.list_categories(session),
                "email_templates": email_service.list_templates(session),
                "checklists": checklist_service.list_templates(session),
                "integrations": integration_service.list_configs(session),
                "audit": audit_service.search(session, limit=400),
            }

        try:
            data = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return

        company = data["company"]
        for key, widget in self.company_fields.items():
            value = company.get(key)
            if isinstance(widget, QLineEdit):
                widget.setText("" if value is None else str(value))
            elif hasattr(widget, "setPlainText"):
                widget.setPlainText("" if value is None else str(value))
            else:
                index = widget.findData(value)
                widget.setCurrentIndex(index if index >= 0 else 0)
        self.logo_field.setText(company.get("logo_path") or "")

        self.users_table.set_rows(data["users"])
        self.roles_table.set_rows(
            [
                {
                    "code": role["code"],
                    "name": role["name"],
                    "permission_count": len(role["permissions"]),
                    "permission_list": ", ".join(role["permissions"][:14])
                    + (" …" if len(role["permissions"]) > 14 else ""),
                }
                for role in data["roles"]
            ]
        )
        self.categories_table.set_rows(data["categories"])
        self.templates_table.set_rows(data["email_templates"])
        self.checklist_table.set_rows(data["checklists"])
        self.integrations_table.set_rows(data["integrations"])
        self.audit_table.set_rows(data["audit"])
        selected = self.integrations_table.current_row()
        if selected:
            self.sync_log.setPlainText(selected.get("sync_log") or "")

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("settings.title"))
        titles = [
            t("settings.company"),
            t("settings.users"),
            t("settings.roles"),
            t("settings.catalogs"),
            t("settings.integrations"),
            t("settings.backup"),
            t("settings.audit"),
        ]
        for index, title in enumerate(titles):
            self.tabs.setTabText(index, title)
        self.users_table.set_columns(self._user_columns())
        self.roles_table.set_columns(self._role_columns())
        self.audit_table.set_columns(self._audit_columns())
        if self._loaded:
            self.refresh()

    def on_save(self) -> None:
        """Ctrl+S saves the company profile."""
        if self.tabs.currentIndex() == 0:
            self._save_company()
