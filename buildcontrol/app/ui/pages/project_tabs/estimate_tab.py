"""Estimate tree with versioning, drag & drop, Excel/PDF exchange."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from app.models.enums import EstimateItemStatus, EstimateStatus, Unit
from app.reports import excel_reports, pdf_reports
from app.services import estimate_service, project_service, report_service
from app.services.estimate_service import EstimateLocked, SectionNode
from app.services.permissions import Perm
from app.ui.dialogs.base_dialog import confirm, show_info
from app.ui.dialogs.form_dialog import (
    COMBO,
    NUMBER,
    PERCENT,
    TEXT,
    TEXTAREA,
    Field,
    FormDialog,
)
from app.ui.pages.base_page import BasePage
from app.ui.styles.theme import COLORS, SPACING_SM
from app.ui.widgets.common import Badge, button
from app.utils.files import open_path
from app.utils.formatting import fmt_money, fmt_percent, fmt_qty
from app.utils.i18n import tr
from app.utils.labels import estimate_status_label, item_status_label, options, unit_label

ITEM_ROLE = int(Qt.ItemDataRole.UserRole) + 1

_STATUS_KIND = {
    EstimateStatus.DRAFT.value: "neutral",
    EstimateStatus.SUBMITTED.value: "warning",
    EstimateStatus.APPROVED.value: "success",
    EstimateStatus.REVISION.value: "info",
}


class EstimateTreeWidget(QTreeWidget):
    """Tree widget emitting a signal after an internal drag & drop move."""

    item_dropped = Signal(object, object, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(False)

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt naming
        dragged = self.currentItem()
        payload = dragged.data(0, ITEM_ROLE) if dragged else None
        if payload is None or payload.get("type") != "item":
            event.ignore()
            return
        super().dropEvent(event)
        parent = dragged.parent()
        if parent is None:
            return
        target = parent.data(0, ITEM_ROLE)
        if not target or target.get("type") != "section":
            return
        self.item_dropped.emit(payload, target, parent.indexOfChild(dragged))


class EstimateTab(BasePage):
    """Full estimate workspace of one project."""

    permission = Perm.ESTIMATE_VIEW

    COLUMNS = [
        "code",
        "name",
        "unit",
        "quantity",
        "plan_unit_price",
        "plan_total",
        "actual_unit_price",
        "actual_total",
        "variance",
        "variance_percent",
        "progress_percent",
        "responsible",
        "status",
        "note",
    ]

    def __init__(self, project_id: int, parent: QWidget | None = None) -> None:
        super().__init__("", "", parent, show_header=False, compact=True)
        self.project_id = project_id
        self.tree_data = None

        self._build_toolbar()
        self.tree = EstimateTreeWidget()
        self.tree.setHeaderLabels(
            [
                tr("code"),
                tr("name"),
                tr("unit"),
                tr("quantity"),
                tr("plan_unit_price"),
                tr("plan_total"),
                tr("actual_unit_price"),
                tr("actual_total"),
                tr("variance"),
                tr("variance_percent"),
                tr("percent_done"),
                tr("responsible"),
                tr("status"),
                tr("note"),
            ]
        )
        self.tree.item_dropped.connect(self._on_dropped)
        self.tree.itemDoubleClicked.connect(lambda *_: self._edit_selected())
        self.tree.itemSelectionChanged.connect(self._update_actions)
        self.root.addWidget(self.tree, 1)

        self.totals_label = QLabel("")
        self.totals_label.setObjectName("SectionTitle")
        self.root.addWidget(self.totals_label)

    # -- toolbar -------------------------------------------------------------------- #
    def _build_toolbar(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(SPACING_SM)

        row.addWidget(QLabel(tr("estimate_version")))
        self.version_box = QComboBox()
        self.version_box.setMinimumWidth(190)
        self.version_box.currentIndexChanged.connect(self._on_version_changed)
        row.addWidget(self.version_box)

        self.status_badge = Badge("—", "neutral")
        self.status_badge.setMinimumWidth(160)
        self.status_badge.setMinimumHeight(24)
        row.addWidget(self.status_badge)
        row.addStretch(1)

        self.add_section_btn = button(tr("add_section"), "add")
        self.add_section_btn.clicked.connect(lambda: self._add_section(False))
        self.add_sub_btn = button(tr("add_subsection"), "add")
        self.add_sub_btn.clicked.connect(lambda: self._add_section(True))
        self.add_item_btn = button(tr("add_item"), "add", "Primary")
        self.add_item_btn.clicked.connect(self._add_item)
        self.edit_btn = button(tr("edit"), "edit")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.delete_btn = button(tr("delete"), "delete", "Ghost")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.up_btn = button("", "up", "Ghost", tr("move_up"))
        self.up_btn.setFixedWidth(34)
        self.up_btn.clicked.connect(lambda: self._move_section(-1))
        self.down_btn = button("", "down", "Ghost", tr("move_down"))
        self.down_btn.setFixedWidth(34)
        self.down_btn.clicked.connect(lambda: self._move_section(1))
        for widget in (
            self.add_section_btn,
            self.add_sub_btn,
            self.add_item_btn,
            self.edit_btn,
            self.delete_btn,
            self.up_btn,
            self.down_btn,
        ):
            row.addWidget(widget)

        second = QHBoxLayout()
        second.setSpacing(SPACING_SM)
        self.submit_btn = button(tr("submit_for_approval"), "up")
        self.submit_btn.clicked.connect(lambda: self._set_status(EstimateStatus.SUBMITTED.value))
        self.approve_btn = button(tr("approve"), "approve", "Success")
        self.approve_btn.clicked.connect(lambda: self._set_status(EstimateStatus.APPROVED.value))
        self.revision_btn = button(tr("send_to_revision"), "refresh")
        self.revision_btn.clicked.connect(lambda: self._set_status(EstimateStatus.REVISION.value))
        self.version_btn = button(tr("new_version"), "copy")
        self.version_btn.clicked.connect(self._new_version)
        self.compare_btn = button(tr("compare_versions"), "compare")
        self.compare_btn.clicked.connect(self._compare)
        self.import_btn = button(tr("import_excel"), "excel")
        self.import_btn.clicked.connect(self._import_excel)
        self.export_btn = button(tr("export_excel"), "excel")
        self.export_btn.clicked.connect(self._export_excel)
        self.pdf_btn = button(tr("export_pdf"), "pdf")
        self.pdf_btn.clicked.connect(self._export_pdf)
        for widget in (
            self.submit_btn,
            self.approve_btn,
            self.revision_btn,
            self.version_btn,
            self.compare_btn,
        ):
            second.addWidget(widget)
        second.addStretch(1)
        for widget in (self.import_btn, self.export_btn, self.pdf_btn):
            second.addWidget(widget)

        self.root.addLayout(row)
        self.root.addLayout(second)

    # -- data ----------------------------------------------------------------------- #
    def refresh(self) -> None:
        """Reload versions and rebuild the tree."""
        versions = estimate_service.list_versions(self.project_id)
        self.version_box.blockSignals(True)
        self.version_box.clear()
        for version in versions:
            label = f"v{version['version_no']} · {estimate_status_label(version['status'])}"
            if version["is_current"]:
                label += " ★"
            self.version_box.addItem(label, version["id"])
        current = next((v for v in versions if v["is_current"]), None)
        if current:
            index = self.version_box.findData(current["id"])
            self.version_box.setCurrentIndex(max(0, index))
        self.version_box.blockSignals(False)
        self._load_tree()

    def _on_version_changed(self) -> None:
        self._load_tree()

    def _load_tree(self) -> None:
        version_id = self.version_box.currentData()
        try:
            data = estimate_service.load_tree(self.project_id, version_id)
        except Exception as exc:
            self.handle(exc)
            return
        self.tree_data = data
        self.status_badge.setText(estimate_status_label(data.status))
        self.status_badge.set_kind(_STATUS_KIND.get(data.status, "neutral"))
        self._populate(data)
        self.totals_label.setText(
            f"{tr('plan_total')}: {fmt_money(data.plan_total)}    "
            f"{tr('actual_total')}: {fmt_money(data.actual_total)}    "
            f"{tr('variance')}: {fmt_money(data.variance)}"
        )
        self._update_actions()

    def _populate(self, data) -> None:
        self.tree.clear()
        for node in data.roots:
            self.tree.addTopLevelItem(self._section_item(node))
        self.tree.expandAll()
        for index in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(index)

    def _section_item(self, node: SectionNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setText(0, node.code)
        item.setText(1, node.name)
        item.setText(5, fmt_money(node.plan_total, with_suffix=False))
        item.setText(7, fmt_money(node.actual_total, with_suffix=False))
        item.setText(8, fmt_money(node.variance, with_suffix=False))
        font = QFont()
        font.setBold(True)
        for column in range(self.tree.columnCount()):
            item.setFont(column, font)
        if node.variance > 0:
            item.setForeground(8, QBrush(QColor(COLORS.danger)))
        item.setData(0, ITEM_ROLE, {"type": "section", "id": node.id, "name": node.name})
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled
        )
        for child in node.children:
            item.addChild(self._section_item(child))
        for row in node.items:
            item.addChild(self._line_item(row))
        return item

    def _line_item(self, row) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        values = [
            row.code,
            row.name,
            unit_label(row.unit),
            fmt_qty(row.quantity),
            fmt_money(row.plan_unit_price, with_suffix=False),
            fmt_money(row.plan_total, with_suffix=False),
            fmt_money(row.actual_unit_price, with_suffix=False),
            fmt_money(row.actual_total, with_suffix=False),
            fmt_money(row.variance, with_suffix=False),
            fmt_percent(row.variance_percent),
            fmt_percent(row.progress_percent, 0),
            row.responsible,
            item_status_label(row.status),
            row.note,
        ]
        for index, value in enumerate(values):
            item.setText(index, value)
            if index in (3, 4, 5, 6, 7, 8, 9, 10):
                item.setTextAlignment(
                    index, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                )
        if row.variance > 0:
            brush = QBrush(QColor(COLORS.danger))
            item.setForeground(8, brush)
            item.setForeground(9, brush)
            item.setForeground(7, brush)
        elif row.status == EstimateItemStatus.NEEDS_PURCHASE.value:
            item.setForeground(12, QBrush(QColor(COLORS.warning)))
        if row.actual_total == 0 and row.plan_total > 0:
            item.setForeground(7, QBrush(QColor(COLORS.text_faint)))
        item.setData(0, ITEM_ROLE, {"type": "item", "id": row.id, "row": row})
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        )
        return item

    # -- selection ------------------------------------------------------------------- #
    def _selected(self) -> dict | None:
        item = self.tree.currentItem()
        return item.data(0, ITEM_ROLE) if item else None

    def _update_actions(self) -> None:
        data = self.tree_data
        editable = bool(data and data.editable and self.can(Perm.ESTIMATE_EDIT))
        selection = self._selected()
        is_section = bool(selection and selection["type"] == "section")
        for widget in (self.add_section_btn, self.add_item_btn, self.import_btn):
            widget.setEnabled(editable)
        self.add_sub_btn.setEnabled(editable and is_section)
        self.add_item_btn.setEnabled(editable and is_section)
        self.edit_btn.setEnabled(editable and selection is not None)
        self.delete_btn.setEnabled(editable and selection is not None)
        self.up_btn.setEnabled(editable and is_section)
        self.down_btn.setEnabled(editable and is_section)
        self.submit_btn.setEnabled(
            editable and data is not None and data.status == EstimateStatus.DRAFT.value
        )
        self.approve_btn.setEnabled(
            self.can(Perm.ESTIMATE_APPROVE)
            and data is not None
            and data.status == EstimateStatus.SUBMITTED.value
        )
        self.revision_btn.setEnabled(
            self.can(Perm.ESTIMATE_APPROVE)
            and data is not None
            and data.status in (EstimateStatus.SUBMITTED.value, EstimateStatus.APPROVED.value)
        )
        self.version_btn.setEnabled(self.can(Perm.ESTIMATE_EDIT))
        self.tree.setDragEnabled(editable)

    def _guard(self) -> bool:
        if self.tree_data is None:
            return False
        if not self.tree_data.editable:
            show_info(self, tr("estimate_locked"))
            return False
        if not self.can(Perm.ESTIMATE_EDIT):
            show_info(self, tr("permission_denied"))
            return False
        return True

    # -- editing ---------------------------------------------------------------------- #
    def _add_section(self, as_child: bool) -> None:
        if not self._guard():
            return
        parent_id = None
        if as_child:
            selection = self._selected()
            if not selection or selection["type"] != "section":
                self.notify(tr("select_row_first"), "warning")
                return
            parent_id = selection["id"]
        dialog = FormDialog(
            tr("add_subsection") if as_child else tr("add_section"),
            [
                Field("name", tr("name"), TEXT, required=True, span=2),
                Field("code", tr("code"), TEXT),
            ],
            {},
            parent=self,
            width=520,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            estimate_service.add_section(
                int(self.version_box.currentData()),
                values["name"],
                self.actor,
                parent_id,
                values["code"],
            )
        except EstimateLocked:
            show_info(self, tr("estimate_locked"))
            return
        except Exception as exc:
            self.handle(exc)
            return
        self._load_tree()

    def _item_fields(self) -> list[Field]:
        return [
            Field("code", tr("code"), TEXT),
            Field("category", tr("category"), TEXT),
            Field("name", tr("name"), TEXT, required=True, span=2),
            Field("unit", tr("unit"), COMBO, options=options(Unit)),
            Field("quantity", tr("quantity"), NUMBER, required=True, decimals=2),
            Field("plan_unit_price", tr("plan_unit_price"), NUMBER, decimals=0, maximum=1e15),
            Field("progress_percent", tr("percent_done"), PERCENT),
            Field(
                "responsible_id",
                tr("responsible"),
                COMBO,
                options=project_service.user_choices(),
            ),
            Field("status", tr("status"), COMBO, options=options(EstimateItemStatus)),
            Field("note", tr("note"), TEXTAREA, span=2),
        ]

    def _add_item(self) -> None:
        if not self._guard():
            return
        selection = self._selected()
        if not selection or selection["type"] != "section":
            self.notify(tr("select_row_first"), "warning")
            return
        dialog = FormDialog(
            tr("add_item"),
            self._item_fields(),
            {"unit": Unit.PIECE.value, "status": EstimateItemStatus.PLANNED.value},
            selection["name"],
            parent=self,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        values["section_id"] = selection["id"]
        values["responsible_id"] = values.get("responsible_id") or None
        try:
            estimate_service.save_item(values, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self._load_tree()

    def _edit_selected(self) -> None:
        selection = self._selected()
        if selection is None or not self._guard():
            return
        if selection["type"] == "section":
            dialog = FormDialog(
                tr("section"),
                [
                    Field("name", tr("name"), TEXT, required=True, span=2),
                    Field("code", tr("code"), TEXT),
                ],
                {"name": selection["name"]},
                parent=self,
                width=520,
            )
            if not dialog.exec():
                return
            values = dialog.values()
            try:
                estimate_service.update_section(
                    selection["id"], values["name"], values["code"], self.actor
                )
            except Exception as exc:
                self.handle(exc)
                return
        else:
            row = selection["row"]
            data = {
                "code": row.code,
                "category": row.category,
                "name": row.name,
                "unit": row.unit,
                "quantity": row.quantity,
                "plan_unit_price": row.plan_unit_price,
                "progress_percent": row.progress_percent,
                "status": row.status,
                "note": row.note,
            }
            dialog = FormDialog(tr("item"), self._item_fields(), data, row.name, parent=self)
            if not dialog.exec():
                return
            values = dialog.values()
            values["responsible_id"] = values.get("responsible_id") or None
            try:
                estimate_service.save_item(values, self.actor, selection["id"])
            except Exception as exc:
                self.handle(exc)
                return
        self._load_tree()

    def _delete_selected(self) -> None:
        selection = self._selected()
        if selection is None or not self._guard():
            return
        if not confirm(self, tr("confirm_question"), tr("delete")):
            return
        try:
            if selection["type"] == "section":
                estimate_service.delete_section(selection["id"], self.actor)
            else:
                estimate_service.delete_item(selection["id"], self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self._load_tree()

    def _move_section(self, direction: int) -> None:
        selection = self._selected()
        if selection is None or selection["type"] != "section" or not self._guard():
            return
        try:
            estimate_service.move_section(selection["id"], direction, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self._load_tree()

    def _on_dropped(self, payload: dict, target: dict, position: int) -> None:
        try:
            estimate_service.move_item(payload["id"], target["id"], position, self.actor)
        except Exception as exc:
            self.handle(exc)
        self._load_tree()

    # -- workflow ---------------------------------------------------------------------- #
    def _set_status(self, status: str) -> None:
        version_id = self.version_box.currentData()
        if version_id is None:
            return
        if status == EstimateStatus.APPROVED.value and not confirm(
            self, tr("confirm_question"), tr("approve")
        ):
            return
        try:
            estimate_service.set_status(int(version_id), status, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _new_version(self) -> None:
        if not confirm(self, tr("confirm_question"), tr("new_version")):
            return
        try:
            estimate_service.create_new_version(self.project_id, self.actor)
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(tr("saved"))
        self.refresh()

    def _compare(self) -> None:
        versions = estimate_service.list_versions(self.project_id)
        if len(versions) < 2:
            self.notify(tr("no_data"), "warning")
            return
        pairs = [(v["id"], f"v{v['version_no']}") for v in versions]
        dialog = FormDialog(
            tr("compare_versions"),
            [
                Field("left", tr("estimate_version"), COMBO, options=pairs, default=pairs[-1][0]),
                Field("right", tr("estimate_version"), COMBO, options=pairs, default=pairs[0][0]),
            ],
            {},
            parent=self,
            width=520,
        )
        if not dialog.exec():
            return
        values = dialog.values()
        rows = estimate_service.compare_versions(int(values["left"]), int(values["right"]))
        changed = [r for r in rows if r["change"] != "same"]
        if not changed:
            show_info(self, tr("no_data"))
            return
        lines = [
            f"{r['code']} {r['name']}: {fmt_money(r['old_total'])} → {fmt_money(r['new_total'])}"
            f"  ({r['change']})"
            for r in changed[:40]
        ]
        show_info(self, "\n".join(lines), tr("version_diff"))

    # -- exchange ------------------------------------------------------------------------ #
    def _import_excel(self) -> None:
        if not self._guard():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("import_excel"), "", "Excel (*.xlsx *.xlsm)")
        if not path:
            return
        try:
            rows = excel_reports.read_estimate_rows(path)
            count = estimate_service.bulk_import(
                int(self.version_box.currentData()), rows, self.actor
            )
        except Exception as exc:
            self.handle(exc)
            return
        self.notify(f"{tr('saved')}: {count}")
        self._load_tree()

    def _report(self):
        return report_service.build(
            "estimate", report_service.ReportFilters(project_id=self.project_id)
        )

    def _export_excel(self) -> None:
        try:
            path = excel_reports.render_report(self._report())
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)

    def _export_pdf(self) -> None:
        try:
            path = pdf_reports.render_report(self._report())
        except Exception as exc:
            self.handle(exc)
            return
        show_info(self, f"{tr('report_saved')}:\n{path}")
        open_path(path)
