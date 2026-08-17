"""Export readiness checklist page."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import auth_service, checklist_service, lead_service, product_service
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.styles.theme import COLORS
from app.ui.widgets.common import button, section_title
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import CHECKLIST_CATEGORIES, CHECKLIST_SCOPES, PRIORITIES
from app.utils.formatting import fmt_date


class ChecklistsPage(RecordPage):
    """Checklists with an inline item editor in the detail panel."""

    permission = "checklist.view"
    title_key = "checklist.title"
    topics = ("checklist", "lead", "product")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._users: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        if ctx.can("checklist.edit"):
            self.header.add_action(
                button(t("checklist.apply_template"), self._apply_template, "Primary")
            )
            self.header.add_action(button(t("checklist.templates"), self._show_templates, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the checklist table."""
        return [
            Column("name", t("common.name"), stretch=True),
            Column("scope", t("checklist.scope"), width=100),
            Column("entity_label", t("common.details"), width=220),
            Column("done", t("common.total"), kind="number", decimals=0, width=70),
            Column("total", t("checklist.items"), kind="number", decimals=0, width=80),
            Column("completion", t("checklist.completion"), kind="percent", decimals=0, width=110),
            Column("overdue", t("common.overdue"), kind="number", decimals=0, width=90),
            Column("status", t("common.status"), kind="status", group="task_status", width=110),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the checklist table."""
        return [
            FilterSpec(
                "scope",
                t("checklist.scope"),
                "combo",
                [(scope, scope) for scope in CHECKLIST_SCOPES],
                width=130,
            ),
            FilterSpec(
                "category",
                t("checklist.category"),
                "enum",
                CHECKLIST_CATEGORIES,
                "checklist_category",
                180,
            ),
            FilterSpec("overdue", t("checklist.overdue_only"), "check"),
        ]

    def refresh(self) -> None:
        """Reload the user list and the checklists."""
        self._users = self.ctx.read(
            lambda s: [
                (user["id"], user["full_name"] or user["username"])
                for user in auth_service.list_users(s)
            ]
        )
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch checklists and resolve the entity each belongs to."""

        def _load(session: Session) -> list[dict]:
            rows = checklist_service.list_checklists(
                session,
                scope=filters.get("scope"),
                category=filters.get("category"),
                only_overdue=bool(filters.get("overdue")),
            )
            leads = {row["id"]: row["title"] for row in lead_service.search_leads(session)}
            products = {
                row["id"]: f"{row['sku']} — {row['name']}"
                for row in product_service.search_products(session)
            }
            for row in rows:
                if row["scope"] == "lead":
                    row["entity_label"] = leads.get(row["entity_id"], f"#{row['entity_id']}")
                elif row["scope"] == "product":
                    row["entity_label"] = products.get(row["entity_id"], f"#{row['entity_id']}")
                else:
                    row["entity_label"] = f"#{row['entity_id']}"
            return rows

        rows = self.ctx.read(_load)
        text = (filters.get("text") or "").lower()
        if text:
            rows = [
                row
                for row in rows
                if text in row["name"].lower() or text in row["entity_label"].lower()
            ]
        return rows

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Show the checklist items with tick boxes."""
        items = self.ctx.read(lambda s: checklist_service.checklist_items(s, row["id"]))
        self.detail.set_header(
            row["name"],
            f"{row['entity_label']} · {row['completion']}%",
            "task_status",
            row["status"],
        )
        if self.ctx.can("checklist.edit"):
            self.detail.add_action(
                t("checklist.new_item"), lambda: self._add_item(row["id"]), "Primary"
            )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 6, 2, 6)
        layout.setSpacing(4)

        current_category = ""
        for item in items:
            if item["category"] != current_category:
                current_category = item["category"]
                layout.addWidget(section_title(te("checklist_category", current_category)))
            line = QWidget()
            line_layout = QHBoxLayout(line)
            line_layout.setContentsMargins(0, 0, 0, 0)
            line_layout.setSpacing(8)
            box = QCheckBox(item["title"])
            box.setChecked(item["is_done"])
            box.setEnabled(self.ctx.can("checklist.edit"))
            box.toggled.connect(lambda checked, item_id=item["id"]: self._toggle(item_id, checked))
            line_layout.addWidget(box, 1)
            meta = QLabel(
                f"{fmt_date(item['due_date'])}"
                + (f" · {item['assignee']}" if item["assignee"] else "")
            )
            meta.setObjectName("Hint")
            if item["overdue"]:
                meta.setStyleSheet(f"color: {COLORS['danger']}; font-weight: 600;")
            line_layout.addWidget(meta)
            layout.addWidget(line)
        layout.addStretch(1)

        scroll_host = QScrollArea()
        scroll_host.setWidgetResizable(True)
        scroll_host.setWidget(container)
        self.detail.tabs.addTab(scroll_host, t("checklist.items"))

    # ------------------------------------------------------------ actions
    def _toggle(self, item_id: int, done: bool) -> None:
        try:
            self.ctx.run(lambda s: checklist_service.toggle_item(s, self.ctx.user, item_id, done))
            self.ctx.notify("checklist")
        except Exception as exc:
            self.handle_error(exc)

    def _add_item(self, checklist_id: int) -> None:
        fields = [
            Field("title", t("common.name"), required=True),
            Field(
                "category",
                t("checklist.category"),
                "enum",
                CHECKLIST_CATEGORIES,
                "checklist_category",
                with_empty=False,
            ),
            Field(
                "priority", t("common.priority"), "enum", PRIORITIES, "priority", with_empty=False
            ),
            Field("due_date", t("common.due_date"), "date"),
            Field("assignee_id", t("common.assignee"), "combo", self._users),
            Field("description", t("common.description"), "textarea", height=60),
        ]

        def _save(values: dict[str, Any]) -> int:
            payload = dict(values)
            payload["checklist_id"] = checklist_id
            return self.ctx.run(lambda s: checklist_service.save_item(s, self.ctx.user, payload).id)

        dialog = FormDialog(
            t("checklist.new_item"), fields, {"priority": "normal"}, _save, self, 560
        )
        if dialog.exec():
            self.ctx.notify("checklist")

    def _apply_template(self) -> None:
        """Apply a checklist template to a lead or a product."""
        templates = self.ctx.read(checklist_service.list_templates)
        if not templates:
            return
        labels = [f"{tpl['name']} ({tpl['scope']})" for tpl in templates]
        choice, ok = QInputDialog.getItem(
            self, t("checklist.apply_template"), t("checklist.templates"), labels, 0, False
        )
        if not ok:
            return
        template = templates[labels.index(choice)]
        scope = template["scope"]

        def _entities(session: Session) -> list[tuple[int, str]]:
            if scope == "product":
                return [
                    (row["id"], f"{row['sku']} — {row['name']}")
                    for row in product_service.search_products(session)
                ]
            return [(row["id"], row["title"]) for row in lead_service.search_leads(session)]

        entities = self.ctx.read(_entities)
        if not entities:
            return
        entity_labels = [name for _id, name in entities]
        entity_choice, ok = QInputDialog.getItem(
            self, t("checklist.apply_template"), t("checklist.scope"), entity_labels, 0, False
        )
        if not ok:
            return
        entity_id = entities[entity_labels.index(entity_choice)][0]
        try:
            self.ctx.run(
                lambda s: checklist_service.apply_template(
                    s, self.ctx.user, template["id"], scope, entity_id
                )
            )
            self.ctx.notify("checklist")
            self.info(t("common.saved"))
        except Exception as exc:
            self.handle_error(exc)

    def _show_templates(self) -> None:
        """List the available templates and their items."""
        templates = self.ctx.read(checklist_service.list_templates)
        lines = []
        for template in templates:
            trigger = (
                f" → {te('lead_status', template['trigger_status'])}"
                if template["trigger_status"]
                else ""
            )
            lines.append(
                f"{template['name']} ({template['scope']}, {template['item_count']}){trigger}"
            )
            lines.extend(
                f"    · {te('checklist_category', item['category'])}: {item['title']}"
                for item in template["items"]
            )
        dialog = FormDialog(
            t("checklist.templates"),
            [Field("templates", t("checklist.templates"), "textarea", height=420)],
            {"templates": "\n".join(lines)},
            lambda _values: None,
            self,
            width=700,
        )
        dialog.exec()
