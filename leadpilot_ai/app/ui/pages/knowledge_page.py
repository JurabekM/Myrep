"""Knowledge base worksheet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QPushButton,
    QSplitter,
    QTextEdit,
    QWidget,
)

from app.controllers.app_context import AppContext
from app.models.enums import Permission as Perm
from app.services import knowledge_service
from app.ui.dialogs.misc_dialogs import KnowledgeDialog
from app.ui.i18n import tr, translator
from app.ui.pages.base_page import BasePage
from app.ui.styles import theme
from app.ui.widgets.common import (
    DataTable,
    FilterChip,
    Panel,
    SearchBox,
    colored_item,
    combo,
    confirm,
    show_error,
    show_info,
)
from app.ui.widgets.labels import kb_type_items, kb_type_label
from app.utils.dates import fmt_date, fmt_datetime
from app.utils.formatting import fmt_money

COLUMNS = [
    "common.title",
    "common.type",
    "common.category",
    "common.price",
    "kb.valid_from",
    "kb.valid_to",
    "kb.ai_usable",
    "common.updated",
]


class KnowledgePage(BasePage):
    """Company knowledge the AI is allowed to quote."""

    title_key = "kb.title"
    subtitle_key = "app.subtitle"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._build()

    def _build(self) -> None:
        """Assemble the toolbar, table and preview."""
        self.new_button = QPushButton(tr("kb.new"))
        self.new_button.setObjectName("Primary")
        self.new_button.setIcon(theme.icon("fa6s.plus", "#FFFFFF"))
        self.new_button.clicked.connect(self._create)
        self.header().addWidget(self.new_button)

        self.attach_button = QPushButton(tr("kb.attachments"))
        self.attach_button.clicked.connect(self._attach)
        self.header().addWidget(self.attach_button)

        filters = Panel(padding=10, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_box = SearchBox(tr("common.search"))
        self.search_box.textChanged.connect(self.reload)
        row.addWidget(self.search_box, 2)

        self.type_box = combo(kb_type_items())
        self.type_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.type_box)

        self.category_box = combo([(tr("common.all"), "")])
        self.category_box.currentIndexChanged.connect(self.reload)
        row.addWidget(self.category_box)

        self.chip_ai = FilterChip(tr("kb.ai_usable"))
        self.chip_ai.clicked.connect(self.reload)
        row.addWidget(self.chip_ai)
        self.chip_archived = FilterChip(tr("leads.archived_only"))
        self.chip_archived.clicked.connect(self.reload)
        row.addWidget(self.chip_archived)
        row.addStretch(1)
        filters.body().addLayout(row)
        self.body().addWidget(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        table_panel = Panel(padding=8, spacing=6)
        self.table = DataTable([tr(key) for key in COLUMNS], stretch_column=0)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)
        table_panel.body().addWidget(self.table, 1)
        splitter.addWidget(table_panel)

        preview = Panel(padding=12, spacing=8)
        self.preview_title = QLabel(tr("common.details"))
        self.preview_title.setObjectName("SectionTitle")
        preview.body().addWidget(self.preview_title)
        self.preview_body = QTextEdit()
        self.preview_body.setReadOnly(True)
        preview.body().addWidget(self.preview_body, 1)
        self.attachments_label = QLabel(tr("kb.attachments"))
        self.attachments_label.setObjectName("SectionTitle")
        preview.body().addWidget(self.attachments_label)
        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(110)
        preview.body().addWidget(self.attachments_list)
        preview.setMinimumWidth(330)
        splitter.addWidget(preview)
        splitter.setSizes([880, 340])
        self.body().addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Reload the knowledge base table."""
        try:
            items = knowledge_service.list_items(
                search=self.search_box.text(),
                item_type=self.type_box.currentData() or "",
                category=self.category_box.currentData() or "",
                only_ai_usable=self.chip_ai.isChecked(),
                include_archived=self.chip_archived.isChecked(),
            )
        except Exception as exc:
            self.handle_error(exc)
            return

        current_category = self.category_box.currentData()
        self.category_box.blockSignals(True)
        self.category_box.clear()
        self.category_box.addItem(tr("common.all"), "")
        for category in knowledge_service.categories():
            self.category_box.addItem(category, category)
        index = self.category_box.findData(current_category)
        self.category_box.setCurrentIndex(index if index >= 0 else 0)
        self.category_box.blockSignals(False)

        russian = translator.language == "ru"
        rows = []
        ids = []
        for item in items:
            ids.append(item.id)
            title = item.title_ru if russian and item.title_ru else item.title
            rows.append(
                [
                    title,
                    kb_type_label(item.item_type),
                    item.category or "—",
                    fmt_money(item.price) if item.price else "—",
                    fmt_date(item.valid_from) if item.valid_from else "—",
                    fmt_date(item.valid_to) if item.valid_to else "—",
                    colored_item(
                        tr("common.yes") if item.ai_usable else tr("common.no"),
                        theme.SUCCESS if item.ai_usable else theme.TEXT_DISABLED,
                    ),
                    fmt_datetime(item.updated_at),
                ]
            )
        self.table.fill(rows, ids=ids)

    def _selected_item(self):
        """Return the selected knowledge base item."""
        item_id = self.table.selected_id()
        return knowledge_service.get_item(item_id) if item_id else None

    def _on_selection(self) -> None:
        """Show the body of the selected article."""
        item = self._selected_item()
        if item is None:
            return
        russian = translator.language == "ru"
        title = item.title_ru if russian and item.title_ru else item.title
        body = item.body_ru if russian and item.body_ru else item.body
        self.preview_body.setPlainText(f"{title}\n\n{body}\n\n#{item.keywords}")
        self.attachments_list.clear()
        for attachment in item.attachments:
            self.attachments_list.addItem(f"📎 {attachment.file_name}")

    def _create(self) -> None:
        """Create a knowledge base article."""
        if not self.require(Perm.KB_MANAGE):
            return
        dialog = KnowledgeDialog(self.user, parent=self)
        if dialog.exec():
            self.reload()

    def _edit(self) -> None:
        """Edit the selected article."""
        item = self._selected_item()
        if item is None:
            show_error(self, tr("err.select_row"))
            return
        dialog = KnowledgeDialog(self.user, item, parent=self)
        if dialog.exec():
            self.reload()
            self._on_selection()

    def _show_menu(self, position) -> None:
        """Row context menu."""
        item = self._selected_item()
        if item is None:
            return
        menu = QMenu(self)
        menu.addAction(tr("common.edit"), self._edit)
        menu.addAction(tr("kb.ai_usable"), lambda: self._toggle_ai(item.id, not item.ai_usable))
        menu.addAction(tr("kb.attachments"), self._attach)
        menu.addSeparator()
        menu.addAction(tr("common.archive"), lambda: self._archive(item.id))
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _toggle_ai(self, item_id: int, value: bool) -> None:
        """Allow or forbid AI usage of an article."""
        try:
            knowledge_service.toggle_ai_usable(item_id, value, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _archive(self, item_id: int) -> None:
        """Archive an article."""
        if not confirm(self, tr("common.confirm")):
            return
        try:
            knowledge_service.archive_item(item_id, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        self.reload()

    def _attach(self) -> None:
        """Attach a document to the selected article."""
        item = self._selected_item()
        if item is None:
            show_error(self, tr("err.select_row"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("kb.attachments"), "", "Documents (*.pdf *.docx *.txt *.md);;All files (*.*)"
        )
        if not path:
            return
        try:
            knowledge_service.add_attachment(item.id, path, actor=self.user)
        except Exception as exc:
            self.handle_error(exc)
            return
        show_info(self, tr("common.saved"))
        self._on_selection()

    def retranslate(self) -> None:
        """Reapply translated captions."""
        super().retranslate()
        self.new_button.setText(tr("kb.new"))
        self.attach_button.setText(tr("kb.attachments"))
        self.chip_ai.setText(tr("kb.ai_usable"))
        self.chip_archived.setText(tr("leads.archived_only"))
        self.preview_title.setText(tr("common.details"))
        self.attachments_label.setText(tr("kb.attachments"))
        self.table.set_headers([tr(key) for key in COLUMNS])
        self.reload()
