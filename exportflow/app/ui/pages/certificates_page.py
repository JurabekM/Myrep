"""Certificates and export documents page."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QWidget
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import document_service, product_service
from app.ui.dialogs.form_dialog import Field, FormDialog
from app.ui.i18n import t, te
from app.ui.pages.base_page import RecordPage
from app.ui.widgets.common import banner, button
from app.ui.widgets.table import Column, FilterSpec
from app.utils.enums import (
    CERTIFICATE_STATUSES,
    CERTIFICATE_TYPES,
    DOCUMENT_TYPES,
    VERIFICATION_STATUSES,
)
from app.utils.formatting import fmt_date


def open_path(path: str) -> None:
    """Open a file with the operating system's default application."""
    target = Path(path)
    if not target.exists():
        return
    if sys.platform.startswith("win"):
        os.startfile(str(target))  # noqa: S606 - intentional shell-less open
    elif sys.platform == "darwin":  # pragma: no cover - not the target platform
        subprocess.run(["open", str(target)], check=False)
    else:  # pragma: no cover - not the target platform
        subprocess.run(["xdg-open", str(target)], check=False)


class CertificatesPage(RecordPage):
    """Certificate register with expiry alerts and file preview."""

    permission = "certificate.view"
    title_key = "certificate.title"
    topics = ("certificate", "product", "document")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        self._products: list[tuple[int, str]] = []
        super().__init__(ctx, parent)
        if ctx.can("certificate.edit"):
            self.header.add_action(button(t("certificate.new"), self.on_new, "Primary"))
            self.header.add_action(
                button(t("certificate.new_document"), self._new_document, "Ghost")
            )
        self.header.add_action(button(t("common.export"), self.on_export, "Ghost"))

    def columns(self) -> list[Column]:
        """Column layout of the certificate table."""
        return [
            Column("name", t("common.name"), stretch=True),
            Column(
                "cert_type",
                t("certificate.type"),
                kind="status",
                group="certificate_type",
                width=170,
            ),
            Column("product", t("common.product"), width=180),
            Column("issuer", t("certificate.issuer"), width=170),
            Column("number", t("certificate.number"), width=120),
            Column("issue_date", t("certificate.issue_date"), kind="date", width=110),
            Column("expiry_date", t("certificate.expiry_date"), kind="date", width=110),
            Column("days_left", t("certificate.days_left"), kind="number", decimals=0, width=90),
            Column(
                "status", t("common.status"), kind="status", group="certificate_status", width=120
            ),
        ]

    def filter_specs(self) -> list[FilterSpec]:
        """Filters for the certificate table."""
        return [
            FilterSpec(
                "cert_type",
                t("certificate.type"),
                "enum",
                CERTIFICATE_TYPES,
                "certificate_type",
                180,
            ),
            FilterSpec("product_id", t("common.product"), "combo", [], width=180),
            FilterSpec(
                "status",
                t("common.status"),
                "enum",
                CERTIFICATE_STATUSES,
                "certificate_status",
                140,
            ),
            FilterSpec("archived", t("common.show_archived"), "check"),
        ]

    def refresh(self) -> None:
        """Reload the product list and the certificates."""
        self._products = self.ctx.read(
            lambda s: [
                (row["id"], f"{row['sku']} — {row['name']}")
                for row in product_service.search_products(s, lang=self.ctx.language())
            ]
        )
        self.filter_bar.set_options("product_id", self._products, t("common.product"))
        super().refresh()

    def load_rows(self, filters: dict[str, Any]) -> list[dict]:
        """Fetch certificates matching the filter bar."""

        def _load(session: Session) -> list[dict]:
            return document_service.list_certificates(
                session,
                text=filters.get("text", ""),
                cert_type=filters.get("cert_type"),
                product_id=filters.get("product_id"),
                status=filters.get("status"),
                include_archived=bool(filters.get("archived")),
            )

        return self.ctx.read(_load)

    # ------------------------------------------------------------- detail
    def fill_detail(self, row: dict) -> None:
        """Populate the certificate detail panel."""
        self.detail.set_header(
            row["name"],
            te("certificate_type", row["cert_type"]),
            "certificate_status",
            row["status"],
        )
        if self.ctx.can("certificate.edit"):
            self.detail.add_action(t("common.edit"), lambda: self.open_editor(row), "Primary")
            self.detail.add_action(t("common.archive"), lambda: self._archive(row["id"]))
        if row.get("file_path"):
            self.detail.add_action(t("certificate.open_file"), lambda: open_path(row["file_path"]))

        self.detail.add_fields_tab(
            t("common.details"),
            [
                (t("certificate.type"), te("certificate_type", row["cert_type"])),
                (t("common.product"), row["product"]),
                (t("certificate.issuer"), row["issuer"]),
                (t("certificate.number"), row["number"]),
                (t("certificate.issue_date"), fmt_date(row["issue_date"])),
                (t("certificate.expiry_date"), fmt_date(row["expiry_date"])),
                (t("certificate.days_left"), row["days_left"]),
                (t("certificate.target_market"), row["target_market"]),
                (t("certificate.verification"), row["verification_status"]),
                (t("certificate.file"), row["file_path"]),
                (t("common.notes"), row["notes"]),
            ],
        )
        days_left = row.get("days_left")
        if days_left is not None and days_left <= 60:
            level = "error" if days_left < 0 else "warning"
            self.detail.add_tab(
                t("certificate.expiring_soon"),
                banner(f"{t('certificate.days_left')}: {days_left}", level),
            )
        documents = self.ctx.read(lambda s: document_service.list_documents(s))
        self.detail.add_list_tab(
            t("certificate.documents"),
            [
                f"{doc['title']} · {te('certificate_type', doc['doc_type'])}"
                for doc in documents[:40]
            ],
        )

    def on_row_activated(self, row: dict) -> None:
        """Open the editor on double click."""
        if self.ctx.can("certificate.edit"):
            self.open_editor(row)

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Create a new certificate."""
        self.open_editor(None)

    def open_editor(self, row: dict | None) -> None:
        """Show the certificate editor."""
        values: dict[str, Any] = (
            row.copy()
            if row
            else {
                "cert_type": "other",
                "verification_status": "unverified",
                "status": "valid",
            }
        )
        fields = [
            Field("name", t("common.name"), required=True),
            Field(
                "cert_type",
                t("certificate.type"),
                "enum",
                CERTIFICATE_TYPES,
                "certificate_type",
                with_empty=False,
            ),
            Field("product_id", t("common.product"), "combo", self._products),
            Field("issuer", t("certificate.issuer")),
            Field("number", t("certificate.number")),
            Field("issue_date", t("certificate.issue_date"), "date"),
            Field("expiry_date", t("certificate.expiry_date"), "date"),
            Field("target_market", t("certificate.target_market")),
            Field(
                "verification_status",
                t("certificate.verification"),
                "combo",
                [(v, v) for v in VERIFICATION_STATUSES],
                with_empty=False,
            ),
            Field("notes", t("common.notes"), "textarea", height=70),
        ]

        def _save(collected: dict[str, Any]) -> int:
            payload = dict(collected)
            payload["id"] = row["id"] if row else None
            payload.pop("status", None)
            return self.ctx.run(
                lambda s: document_service.save_certificate(s, self.ctx.user, payload).id
            )

        dialog = FormDialog(t("certificate.new"), fields, values, _save, self, width=620)
        if dialog.exec():
            certificate_id = dialog.result_value
            path, _ = QFileDialog.getOpenFileName(
                self,
                t("certificate.file"),
                "",
                "Documents (*.pdf *.jpg *.png *.docx);;All files (*.*)",
            )
            if path and certificate_id:
                stored = document_service.store_file(path, "certificates")
                self.ctx.run(
                    lambda s: document_service.save_certificate(
                        s, self.ctx.user, {"id": certificate_id, "file_path": stored}
                    )
                )
            self.ctx.notify("certificate")
            self.info(t("common.saved"))

    def _archive(self, certificate_id: int) -> None:
        if not self.confirm(t("common.confirm_archive")):
            return
        try:
            self.ctx.run(
                lambda s: document_service.archive_certificate(s, self.ctx.user, certificate_id)
            )
            self.ctx.notify("certificate")
        except Exception as exc:
            self.handle_error(exc)

    def _new_document(self) -> None:
        """Register a generic export document."""
        fields = [
            Field("title", t("common.name"), required=True),
            Field(
                "doc_type",
                t("certificate.doc_type"),
                "combo",
                [(d, te("certificate_type", d)) for d in DOCUMENT_TYPES],
                with_empty=False,
            ),
            Field("doc_date", t("common.date"), "date"),
            Field("notes", t("common.notes"), "textarea", height=70),
        ]

        def _save(values: dict[str, Any]) -> int:
            return self.ctx.run(
                lambda s: document_service.save_document(s, self.ctx.user, values).id
            )

        dialog = FormDialog(
            t("certificate.new_document"), fields, {"doc_type": "other"}, _save, self, 560
        )
        if dialog.exec():
            self.ctx.notify("document")

    def on_export(self) -> None:
        """Export the certificate expiry report."""
        from app.services import report_service

        path, _ = QFileDialog.getSaveFileName(
            self, t("common.export"), "certificates.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(
                lambda s: report_service.export(
                    s, self.ctx.user, "certificate_expiry", "xlsx", target=path
                )
            )
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)
