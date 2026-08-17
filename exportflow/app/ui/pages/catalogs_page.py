"""Catalog studio: compose a catalog and export it to PDF / HTML / ZIP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.controllers.app_context import AppContext
from app.services import catalog_service, product_service
from app.ui.i18n import t
from app.ui.pages.base_page import BasePage
from app.ui.pages.certificates_page import open_path
from app.ui.widgets.common import (
    PageHeader,
    banner,
    button,
    checkbox,
    combo,
    combo_value,
    line_edit,
    section_title,
    text_area,
)
from app.ui.widgets.table import Column, DataTable


class CatalogsPage(BasePage):
    """Catalog list on the left, editor and preview on the right."""

    permission = "catalog.view"
    topics = ("catalog", "product")

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        self._catalog_id: int | None = None
        self._products: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.header = PageHeader()
        root.addWidget(self.header)
        if ctx.can("catalog.edit"):
            self.header.add_action(button(t("catalog.new"), self.on_new, "Primary"))
        if ctx.can("catalog.export"):
            self.header.add_action(button(t("catalog.export_pdf"), self._export_pdf, "Ghost"))
            self.header.add_action(button(t("catalog.export_html"), self._export_html, "Ghost"))
            self.header.add_action(button(t("catalog.export_zip"), self._export_zip, "Ghost"))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = DataTable(self._columns())
        self.table.selection_changed.connect(self._on_selected)
        splitter.addWidget(self.table)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(12, 0, 0, 0)
        editor_layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)
        self.title_field = line_edit(t("catalog.name"))
        self.subtitle_field = line_edit(t("catalog.subtitle"))
        self.language_field = combo(
            [("en", "English"), ("ru", "Русский"), ("uz", "O‘zbekcha")], "en", False
        )
        self.version_field = line_edit(t("catalog.version"), "1.0")
        self.include_certificates = checkbox(t("catalog.include_certificates"), True)
        self.include_prices = checkbox(t("catalog.include_prices"), False)
        form.addRow(t("catalog.name"), self.title_field)
        form.addRow(t("catalog.subtitle"), self.subtitle_field)
        form.addRow(t("common.language"), self.language_field)
        form.addRow(t("catalog.version"), self.version_field)
        form.addRow("", self.include_certificates)
        form.addRow("", self.include_prices)
        editor_layout.addLayout(form)

        self.cover_note = text_area(t("catalog.cover_note"), "", 56)
        self.about_text = text_area(t("catalog.about"), "", 56)
        self.contact_text = text_area(t("catalog.contact"), "", 56)
        editor_layout.addWidget(self.cover_note)
        editor_layout.addWidget(self.about_text)
        editor_layout.addWidget(self.contact_text)

        editor_layout.addWidget(section_title(t("catalog.products")))
        self.product_list = QListWidget()
        self.product_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.product_list.setMinimumHeight(150)
        editor_layout.addWidget(self.product_list, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(button(t("common.save"), self.on_save, "Primary"))
        actions.addWidget(button(t("catalog.new_version"), self._duplicate, "Ghost"))
        actions.addWidget(button(t("catalog.preview"), self._preview, "Ghost"))
        actions.addWidget(button(t("catalog.open_folder"), self._open_export, "Ghost"))
        actions.addStretch(1)
        editor_layout.addLayout(actions)

        editor_layout.addWidget(banner(t("catalog.html_hint"), "info"))

        self.preview_box = QPlainTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setMinimumHeight(120)
        editor_layout.addWidget(self.preview_box)

        splitter.addWidget(editor)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        self.retranslate()

    def _columns(self) -> list[Column]:
        return [
            Column("title", t("catalog.name"), stretch=True),
            Column("language", t("common.language"), width=90),
            Column("version", t("catalog.version"), width=80),
            Column("items", t("catalog.products"), kind="number", decimals=0, width=90),
            Column("updated_at", t("common.updated"), kind="date", width=110),
        ]

    # --------------------------------------------------------------- data
    def refresh(self) -> None:
        """Reload catalogs and the product picker."""

        def _load(session: Session) -> tuple[list, list]:
            return (
                catalog_service.list_catalogs(session),
                product_service.search_products(session, lang=self.ctx.language()),
            )

        try:
            catalogs, products = self.ctx.read(_load)
        except Exception as exc:
            self.handle_error(exc)
            return
        self._products = products
        self.table.set_rows(catalogs)
        self._fill_product_list([])
        if self._catalog_id:
            self.table.select_id(self._catalog_id)

    def _fill_product_list(self, selected_ids: list[int]) -> None:
        self.product_list.clear()
        for product in self._products:
            item = QListWidgetItem(f"{product['sku']} — {product['name']}")
            item.setData(Qt.ItemDataRole.UserRole, product["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if product["id"] in selected_ids else Qt.CheckState.Unchecked
            )
            self.product_list.addItem(item)

    def _selected_products(self) -> list[int]:
        result = []
        for index in range(self.product_list.count()):
            item = self.product_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

    def _on_selected(self, row: dict | None) -> None:
        if row is None:
            return
        self._catalog_id = row["id"]
        data = self.ctx.read(lambda s: catalog_service.catalog_dict(s, row["id"]))
        self.title_field.setText(data["title"])
        self.subtitle_field.setText(data.get("subtitle") or "")
        self.version_field.setText(data.get("version") or "1.0")
        index = self.language_field.findData(data.get("language"))
        self.language_field.setCurrentIndex(max(index, 0))
        self.include_certificates.setChecked(bool(data.get("include_certificates")))
        self.include_prices.setChecked(bool(data.get("include_prices")))
        self.cover_note.setPlainText(data.get("cover_note") or "")
        self.about_text.setPlainText(data.get("about_text") or "")
        self.contact_text.setPlainText(data.get("contact_text") or "")
        self._fill_product_list(data.get("product_ids") or [])
        self._preview()

    def retranslate(self) -> None:
        """Re-apply captions."""
        self.header.set_texts(t("catalog.title"))
        self.table.set_columns(self._columns())
        if self._loaded:
            self.refresh()

    # ------------------------------------------------------------ actions
    def on_new(self) -> None:
        """Start a new catalog."""
        self._catalog_id = None
        self.title_field.setText(t("catalog.new"))
        self.subtitle_field.clear()
        self.version_field.setText("1.0")
        self.cover_note.clear()
        self.about_text.clear()
        self.contact_text.clear()
        self._fill_product_list([])
        self.preview_box.clear()

    def on_save(self) -> None:
        """Persist the catalog currently shown in the editor."""
        if not self.ctx.can("catalog.edit"):
            return
        values: dict[str, Any] = {
            "id": self._catalog_id,
            "title": self.title_field.text().strip(),
            "subtitle": self.subtitle_field.text().strip(),
            "language": combo_value(self.language_field),
            "version": self.version_field.text().strip() or "1.0",
            "cover_note": self.cover_note.toPlainText().strip(),
            "about_text": self.about_text.toPlainText().strip(),
            "contact_text": self.contact_text.toPlainText().strip(),
            "include_certificates": 1 if self.include_certificates.isChecked() else 0,
            "include_prices": 1 if self.include_prices.isChecked() else 0,
        }
        try:
            self._catalog_id = self.ctx.run(
                lambda s: catalog_service.save_catalog(
                    s, self.ctx.user, values, self._selected_products()
                ).id
            )
        except Exception as exc:
            self.handle_error(exc)
            return
        self.ctx.notify("catalog")
        self.info(t("common.saved"))
        self._preview()

    def _duplicate(self) -> None:
        if not self._catalog_id:
            return
        try:
            new_id = self.ctx.run(
                lambda s: catalog_service.duplicate_catalog(s, self.ctx.user, self._catalog_id).id
            )
            self._catalog_id = new_id
            self.ctx.notify("catalog")
        except Exception as exc:
            self.handle_error(exc)

    def _preview(self) -> None:
        if not self._catalog_id:
            return
        try:
            self.preview_box.setPlainText(
                self.ctx.read(lambda s: catalog_service.preview_text(s, self._catalog_id))
            )
        except Exception as exc:
            self.handle_error(exc)

    def _require_catalog(self) -> bool:
        if self._catalog_id:
            return True
        self.ctx.show_toast(t("error.validation"), "warning")
        return False

    def _export_pdf(self) -> None:
        if not self._require_catalog():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("catalog.export_pdf"), "catalog.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(
                lambda s: catalog_service.export_pdf(s, self.ctx.user, self._catalog_id, path)
            )
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)

    def _export_html(self) -> None:
        if not self._require_catalog():
            return
        folder = QFileDialog.getExistingDirectory(self, t("catalog.export_html"))
        if not folder:
            return
        target = Path(folder) / "catalog"
        try:
            written = self.ctx.run(
                lambda s: catalog_service.export_html(s, self.ctx.user, self._catalog_id, target)
            )
            self.info(t("common.exported", path=written))
            open_path(str(Path(written) / "index.html"))
        except Exception as exc:
            self.handle_error(exc)

    def _export_zip(self) -> None:
        if not self._require_catalog():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("catalog.export_zip"), "catalog.zip", "ZIP (*.zip)"
        )
        if not path:
            return
        try:
            written = self.ctx.run(
                lambda s: catalog_service.export_zip(s, self.ctx.user, self._catalog_id, path)
            )
            self.info(t("common.exported", path=written))
        except Exception as exc:
            self.handle_error(exc)

    def _open_export(self) -> None:
        row = self.table.current_row()
        if row and row.get("last_export_path"):
            open_path(row["last_export_path"])

    def on_export(self) -> None:
        """Ctrl+E exports the catalog to PDF."""
        self._export_pdf()
