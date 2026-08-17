"""AI Content Studio page (three-column workspace)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import ai_content_service, buyer_service, lead_service, product_service
from app.ui.i18n import t, te
from app.ui.pages.base_page import BasePage
from app.ui.widgets.common import (
    PageHeader,
    banner,
    button,
    combo,
    combo_value,
    section_title,
    text_area,
)
from app.utils.enums import AI_CONTENT_TYPES, AI_TONES
from app.utils.formatting import fmt_datetime

#: Product fields the generated text can be written back into.
TARGET_FIELDS = (
    "short_desc_en",
    "short_desc_ru",
    "short_desc_uz",
    "full_desc_en",
    "full_desc_ru",
    "full_desc_uz",
)


class AIStudioPage(BasePage):
    """Left: parameters. Centre: editor. Right: facts and history."""

    permission = "ai.use"
    topics = ("product", "buyer", "lead")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        self._generation_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        self.header.add_action(button(t("ai.generate"), self._generate, "Primary"))
        self.header.add_action(button(t("ai.approve"), self._approve, "Success"))
        self.header.add_action(button(t("ai.copy"), self._copy, "Ghost"))
        self.header.add_action(button(t("ai.apply_to_product"), self._apply_to_product, "Ghost"))

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ------------------------------------------------------------ left
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(8)
        form = QFormLayout()
        form.setSpacing(8)
        self.content_type = combo(
            [(code, te("ai_content_type", code)) for code in AI_CONTENT_TYPES],
            "b2b_product_description",
            False,
        )
        self.language = combo(
            [("en", "English"), ("ru", "Русский"), ("uz", "O‘zbekcha")], ctx.language(), False
        )
        self.tone = combo([(tone, te("tone", tone)) for tone in AI_TONES], "professional", False)
        self.product_combo = combo([], None, True)
        self.buyer_combo = combo([], None, True)
        self.lead_combo = combo([], None, True)
        form.addRow(t("ai.content_type"), self.content_type)
        form.addRow(t("common.language"), self.language)
        form.addRow(t("ai.tone"), self.tone)
        form.addRow(t("common.product"), self.product_combo)
        form.addRow(t("common.buyer"), self.buyer_combo)
        form.addRow(t("nav.leads"), self.lead_combo)
        left_layout.addLayout(form)
        left_layout.addWidget(QLabel(t("ai.instruction")))
        self.instruction = text_area(t("ai.instruction"), "", 90)
        left_layout.addWidget(self.instruction)
        self.provider_label = QLabel("")
        self.provider_label.setObjectName("Hint")
        left_layout.addWidget(self.provider_label)
        left_layout.addStretch(1)
        splitter.addWidget(left)

        # ---------------------------------------------------------- centre
        centre = QWidget()
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(10, 0, 10, 0)
        centre_layout.setSpacing(8)
        centre_layout.addWidget(section_title(t("common.preview")))
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(t("ai.generate"))
        centre_layout.addWidget(self.editor, 1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("Hint")
        centre_layout.addWidget(self.status_label)
        splitter.addWidget(centre)

        # ----------------------------------------------------------- right
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.addWidget(banner(t("ai.rules"), "info"))
        right_layout.addWidget(section_title(t("ai.fact_sources")))
        self.facts_list = QListWidget()
        right_layout.addWidget(self.facts_list, 2)
        right_layout.addWidget(section_title(t("ai.version_history")))
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._load_history_item)
        right_layout.addWidget(self.history_list, 3)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 2)
        root.addWidget(splitter, 1)

        self._history: list[dict] = []
        self.retranslate()

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload the reference combos and the generation history."""

        def _load(session: Session) -> tuple[list, list, list, list]:
            return (
                [
                    (row["id"], f"{row['sku']} — {row['name']}")
                    for row in product_service.search_products(session, lang=self.ctx.language())
                ],
                [
                    (row["id"], f"{row['company_name']} ({row['country']})")
                    for row in buyer_service.search_buyers(session)
                ],
                [(row["id"], row["title"]) for row in lead_service.search_leads(session)],
                ai_content_service.history(session, limit=60),
            )

        try:
            products, buyers, leads, history = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return

        for widget, items in (
            (self.product_combo, products),
            (self.buyer_combo, buyers),
            (self.lead_combo, leads),
        ):
            current = widget.currentData()
            widget.blockSignals(True)
            widget.clear()
            widget.addItem(t("common.none"), None)
            for value, label in items:
                widget.addItem(label, value)
            index = widget.findData(current)
            widget.setCurrentIndex(index if index >= 0 else 0)
            widget.blockSignals(False)

        self._history = history
        self.history_list.clear()
        for item in history:
            self.history_list.addItem(
                f"{fmt_datetime(item['created_at'])} · {te('ai_content_type', item['content_type'])} "
                f"[{item['language'].upper()}]{' ✓' if item['approved'] else ''}"
            )

        states = {state["kind"]: state for state in self.ctx.integration_states()}
        llm = states.get("llm", {})
        self.provider_label.setText(
            f"{t('ai.provider')}: {llm.get('label', '—')}"
            + (f" · {t('common.demo_mode')}" if llm.get("is_demo") else "")
        )

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("ai.title"))
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def _generate(self) -> None:
        try:
            result = self.ctx.run(
                lambda s: ai_content_service.generate(
                    s,
                    self.ctx.user,
                    content_type=combo_value(self.content_type),
                    language=combo_value(self.language),
                    tone=combo_value(self.tone),
                    instruction=self.instruction.toPlainText().strip(),
                    product_id=combo_value(self.product_combo),
                    buyer_id=combo_value(self.buyer_combo),
                    lead_id=combo_value(self.lead_combo),
                )
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self._generation_id = result["id"]
        self.editor.setPlainText(result["text"])
        self.facts_list.clear()
        for line in result["fact_sources"]:
            self.facts_list.addItem(line)
        self.status_label.setText(
            t("ai.generated", ms=result["duration_ms"]) + f" · {result['provider']}"
        )
        self.refresh()

    def _approve(self) -> None:
        if not self._generation_id:
            return
        try:
            self.ctx.run(
                lambda s: ai_content_service.approve(
                    s, self.ctx.user, self._generation_id, self.editor.toPlainText()
                )
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.info(t("common.saved"))
        self.refresh()

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.ctx.show_toast(t("ai.copy"), "success")

    def _apply_to_product(self) -> None:
        if not self._generation_id or not combo_value(self.product_combo):
            self.ctx.show_toast(t("error.validation"), "warning")
            return
        choice, ok = QInputDialog.getItem(
            self, t("ai.apply_to_product"), t("ai.target_field"), list(TARGET_FIELDS), 0, False
        )
        if not ok:
            return
        try:
            self.ctx.run(
                lambda s: ai_content_service.approve(
                    s, self.ctx.user, self._generation_id, self.editor.toPlainText()
                )
            )
            self.ctx.run(
                lambda s: ai_content_service.apply_to_product(
                    s, self.ctx.user, self._generation_id, choice
                )
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.ctx.notify("product")
        self.info(t("common.saved"))

    def _load_history_item(self) -> None:
        index = self.history_list.currentRow()
        if 0 <= index < len(self._history):
            item = self._history[index]
            self._generation_id = item["id"]
            self.editor.setPlainText(item["text"])
            self.facts_list.clear()
            for line in item["fact_sources"]:
                self.facts_list.addItem(line)

    def on_new(self) -> None:
        """Ctrl+N clears the editor."""
        self.editor.clear()
        self._generation_id = None

    def on_save(self) -> None:
        """Ctrl+S approves the current text."""
        self._approve()

    def on_export(self) -> None:
        """Ctrl+E copies the text to the clipboard."""
        self._copy()
