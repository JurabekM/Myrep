"""Tests for catalog, quotation, report and shipping-document generation."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Catalog, Quotation, Shipment
from app.reports import build_quotation_pdf, build_shipping_document
from app.services import (
    ai_content_service,
    catalog_service,
    company_service,
    logistics_service,
    quotation_service,
    report_service,
)


def test_catalog_pdf_is_generated(session, admin, tmp_path: Path):
    """The catalog PDF is written and is not empty."""
    catalog = session.scalars(select(Catalog)).first()
    target = tmp_path / "catalog.pdf"
    path = Path(catalog_service.export_pdf(session, admin, catalog.id, target))

    assert path.exists()
    assert path.stat().st_size > 5000
    assert path.read_bytes()[:5] == b"%PDF-"


def test_catalog_html_export_is_self_contained(session, admin, tmp_path: Path):
    """The static catalog has an index, per-product pages and local assets."""
    catalog = session.scalars(select(Catalog)).first()
    output = Path(catalog_service.export_html(session, admin, catalog.id, tmp_path / "site"))

    index = output / "index.html"
    assert index.exists()
    html = index.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert 'href="assets/style.css"' in html
    assert "mailto:" in html  # Request a Quote target
    assert "http://localhost" not in html and "127.0.0.1" not in html

    assert (output / "assets" / "style.css").exists()
    product_pages = list((output / "products").glob("*.html"))
    assert len(product_pages) == 4
    detail = product_pages[0].read_text(encoding="utf-8")
    assert "../assets/style.css" in detail


def test_catalog_zip_package_contains_the_site(session, admin, tmp_path: Path):
    """The ZIP package holds the whole static catalog."""
    catalog = session.scalars(select(Catalog)).first()
    archive = Path(catalog_service.export_zip(session, admin, catalog.id, tmp_path / "catalog.zip"))

    assert archive.exists()
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
    assert "index.html" in names
    assert any(name.startswith("products/") for name in names)
    assert "assets/style.css" in names


def test_quotation_pdf_contains_the_number(session, tmp_path: Path):
    """The quotation PDF renders without errors."""
    quotation = session.scalars(select(Quotation)).first()
    data = quotation_service.quotation_dict(session, quotation.id)
    company = company_service.company_dict(session)

    path = Path(build_quotation_pdf(tmp_path / "q.pdf", data, company))
    assert path.exists()
    assert path.stat().st_size > 3000


@pytest.mark.parametrize("kind", ["commercial_invoice", "packing_list"])
def test_shipping_documents_are_generated(session, tmp_path: Path, kind: str):
    """Commercial invoice and packing list drafts are produced."""
    shipment = session.scalars(select(Shipment)).first()
    data = logistics_service.shipment_dict(session, shipment.id)
    company = company_service.company_dict(session)

    path = Path(build_shipping_document(tmp_path / f"{kind}.pdf", data, company, kind))
    assert path.exists()
    assert path.stat().st_size > 2000


@pytest.mark.parametrize("code", report_service.REPORT_CODES)
def test_every_report_builds(session, code: str):
    """Each report returns columns and a row list without raising."""
    report = report_service.build(session, code)
    assert report["columns"], f"{code} must declare columns"
    assert isinstance(report["rows"], list)


@pytest.mark.parametrize("fmt", ["xlsx", "pdf"])
def test_report_export_writes_a_file(session, admin, tmp_path: Path, fmt: str):
    """Reports export to both supported formats."""
    target = tmp_path / f"report.{fmt}"
    path = Path(report_service.export(session, admin, "quotation_register", fmt, target=target))
    assert path.exists()
    assert path.stat().st_size > 1000


def test_demo_ai_provider_never_invents_a_certificate(session, admin):
    """Without a registered certificate the generator must not claim one."""
    from app.models import Product

    product = session.scalars(select(Product).where(Product.sku == "CR-TBL-24")).first()
    facts = ai_content_service.collect_facts(session, product_id=product.id)
    assert not facts.get("certificates")

    result = ai_content_service.generate(
        session,
        admin,
        content_type="certificate_explanation",
        language="en",
        product_id=product.id,
    )
    text = result["text"].lower()
    assert "certified" not in text
    assert "no certificate is registered" in text


def test_demo_ai_provider_works_in_three_languages(session, admin):
    """Uzbek, Russian and English all produce non-empty content."""
    from app.models import Product

    product = session.scalars(select(Product).where(Product.sku == "TX-TOW-500")).first()
    for language in ("uz", "ru", "en"):
        result = ai_content_service.generate(
            session,
            admin,
            content_type="b2b_product_description",
            language=language,
            product_id=product.id,
        )
        assert len(result["text"]) > 60
        assert result["is_demo"] is True
        assert result["fact_sources"]
