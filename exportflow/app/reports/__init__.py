"""Report and document generation (PDF, Excel, static HTML)."""

from app.reports.catalog_html import build_html_catalog, zip_catalog
from app.reports.catalog_pdf import build_catalog_pdf
from app.reports.quotation_pdf import build_quotation_pdf, build_shipping_document
from app.reports.tabular import export_excel, export_pdf, read_excel_rows

__all__ = [
    "build_catalog_pdf",
    "build_html_catalog",
    "build_quotation_pdf",
    "build_shipping_document",
    "export_excel",
    "export_pdf",
    "read_excel_rows",
    "zip_catalog",
]
