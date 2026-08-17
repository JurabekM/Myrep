"""Email composer with template, AI draft and quotation attachment support."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.reports import build_quotation_pdf
from app.services import ai_content_service, buyer_service, email_service, quotation_service
from app.ui.i18n import t
from app.ui.widgets.common import (
    banner,
    button,
    checkbox,
    combo,
    combo_value,
    line_edit,
    text_area,
)
from app.utils.errors import ExportFlowError


class EmailComposer(QDialog):
    """Compose, save or send one message to a buyer."""

    def __init__(
        self,
        ctx: AppContext,
        parent: QWidget | None = None,
        buyer_id: int | None = None,
        lead_id: int | None = None,
        quotation_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.buyer_id = buyer_id
        self.lead_id = lead_id
        self.quotation_id = quotation_id
        self.message_id: int | None = None
        self.setModal(True)
        self.setWindowTitle(t("email.new"))
        self.resize(860, 700)

        def _reference(session: Session) -> dict:
            return {
                "buyers": [
                    (row["id"], f"{row['company_name']} ({row['country']})")
                    for row in buyer_service.search_buyers(session)
                ],
                "templates": email_service.list_templates(session),
                "provider": None,
            }

        self.reference = ctx.read(_reference)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        heading = QLabel(t("email.new"))
        heading.setObjectName("PageTitle")
        root.addWidget(heading)

        states = {state["kind"]: state for state in ctx.integration_states()}
        if states.get("email", {}).get("is_demo", True):
            root.addWidget(banner(t("email.provider_demo"), "info"))

        form = QFormLayout()
        form.setSpacing(8)
        self.buyer_combo = combo(self.reference["buyers"], buyer_id, True)
        self.buyer_combo.currentIndexChanged.connect(self._on_buyer_changed)
        self.to_field = line_edit("buyer@example.com")
        self.cc_field = line_edit("")
        self.subject_field = line_edit("")
        self.template_combo = combo(
            [
                (tpl["id"], f"{tpl['name']} [{tpl['language'].upper()}]")
                for tpl in self.reference["templates"]
            ],
            None,
            True,
        )
        form.addRow(t("common.buyer"), self.buyer_combo)
        form.addRow(t("email.to"), self.to_field)
        form.addRow(t("email.cc"), self.cc_field)
        form.addRow(t("email.subject"), self.subject_field)
        form.addRow(t("email.template"), self.template_combo)
        root.addLayout(form)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        tools.addWidget(button(t("email.apply_template"), self._apply_template, "Ghost"))
        if ctx.can("ai.use"):
            tools.addWidget(button(t("email.ai_draft"), self._ai_draft, "Ghost"))
        self.attach_quotation = checkbox(t("email.attach_quotation"), bool(quotation_id))
        self.attach_quotation.setEnabled(bool(quotation_id))
        tools.addWidget(self.attach_quotation)
        tools.addStretch(1)
        root.addLayout(tools)

        self.body_field = text_area(t("email.body"), "", 260)
        root.addWidget(self.body_field, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(button(t("common.cancel"), self.reject, "Ghost"))
        buttons.addWidget(button(t("email.save_draft"), self._save_draft))
        buttons.addWidget(button(t("email.send"), self._send, "Primary"))
        root.addLayout(buttons)

        self._on_buyer_changed()

    # ------------------------------------------------------------- helpers
    def _on_buyer_changed(self) -> None:
        buyer_id = combo_value(self.buyer_combo) or self.buyer_id
        if not buyer_id:
            return
        self.buyer_id = buyer_id
        data = self.ctx.read(lambda s: buyer_service.buyer_dict(s, buyer_id))
        if data.get("email"):
            self.to_field.setText(data["email"])

    def _context(self) -> dict[str, Any]:
        return self.ctx.read(
            lambda s: email_service.template_context(
                s, self.buyer_id, self.quotation_id, self.ctx.user.full_name
            )
        )

    def _apply_template(self) -> None:
        template_id = combo_value(self.template_combo)
        if not template_id:
            return
        rendered = self.ctx.read(
            lambda s: email_service.render_template(s, template_id, self._context())
        )
        self.subject_field.setText(rendered["subject"])
        self.body_field.setPlainText(rendered["body"])

    def _ai_draft(self) -> None:
        try:
            result = self.ctx.run(
                lambda s: ai_content_service.generate(
                    s,
                    self.ctx.user,
                    content_type="follow_up_email" if self.quotation_id else "buyer_email",
                    language=self.ctx.language(),
                    buyer_id=self.buyer_id,
                    lead_id=self.lead_id,
                    quotation_id=self.quotation_id,
                )
            )
        except ExportFlowError as exc:
            self.ctx.show_toast(t(exc.key), "warning")
            return
        self.body_field.setPlainText(result["text"])
        if not self.subject_field.text():
            context = self._context()
            self.subject_field.setText(
                f"{context['company']} — {context.get('quotation_number') or t('email.new')}"
            )

    def _collect(self) -> dict[str, Any]:
        attachment = None
        if self.quotation_id and self.attach_quotation.isChecked():
            attachment = self._ensure_quotation_pdf()
        return {
            "id": self.message_id,
            "buyer_id": self.buyer_id,
            "lead_id": self.lead_id,
            "quotation_id": self.quotation_id,
            "template_id": combo_value(self.template_combo),
            "to_address": self.to_field.text().strip(),
            "cc_address": self.cc_field.text().strip(),
            "subject": self.subject_field.text().strip(),
            "body": self.body_field.toPlainText(),
            "attachment_path": attachment,
        }

    def _ensure_quotation_pdf(self) -> str | None:
        """Render the quotation PDF into the exports folder for attaching."""
        from app.config import PATHS

        data = self.ctx.read(lambda s: quotation_service.quotation_dict(s, self.quotation_id))
        if data.get("last_pdf_path"):
            return data["last_pdf_path"]
        folder = PATHS.exports_dir / "quotations"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{data['number']}.pdf"
        written = build_quotation_pdf(path, data, self.ctx.company())

        def _store(session: Session) -> None:
            quotation = quotation_service.get_quotation(session, self.quotation_id)
            quotation.last_pdf_path = written

        self.ctx.run(_store)
        return written

    def _save_draft(self) -> None:
        try:
            self.message_id = self.ctx.run(
                lambda s: email_service.save_draft(s, self.ctx.user, self._collect()).id
            )
        except Exception as exc:
            self._error(exc)
            return
        self.ctx.show_toast(t("common.saved"), "success")
        self.accept()

    def _send(self) -> None:
        try:
            self.message_id = self.ctx.run(
                lambda s: email_service.save_draft(s, self.ctx.user, self._collect()).id
            )
            message = self.ctx.run(lambda s: email_service.send(s, self.ctx.user, self.message_id))
        except Exception as exc:
            self._error(exc)
            return
        if message.status == "sent":
            self.ctx.show_toast(t("email.sent_ok"), "success")
            self.accept()
        else:
            self.ctx.show_toast(t("email.sent_failed", error=message.error_message or ""), "error")

    def _error(self, exc: Exception) -> None:
        from app.ui.pages.quotations_page import show_error

        show_error(self, exc)


def open_email_composer(
    parent: QWidget,
    ctx: AppContext,
    buyer_id: int | None = None,
    lead_id: int | None = None,
    quotation_id: int | None = None,
) -> bool:
    """Open the composer and report whether a message was saved or sent."""
    dialog = EmailComposer(ctx, parent, buyer_id, lead_id, quotation_id)
    return bool(dialog.exec())
