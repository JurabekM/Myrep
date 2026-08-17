"""End-to-end walk through the main Demo-mode flows.

Mirrors the acceptance scenario: create a product, export the catalog, create a
buyer, register an RFQ, prepare a quotation for sending, complete a checklist,
create a shipment and export a report.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import select

from app.models import Catalog
from app.services import (
    buyer_service,
    catalog_service,
    checklist_service,
    contract_service,
    email_service,
    integration_service,
    lead_service,
    logistics_service,
    product_service,
    quotation_service,
    report_service,
)
from app.utils.formatting import today


def test_full_demo_flow(session, admin, tmp_path: Path):
    """Every core flow works end to end without any external credentials."""
    # 1) Product ------------------------------------------------------------
    product = product_service.save_product(
        session,
        admin,
        {
            "sku": "E2E-TOWEL-01",
            "name_en": "E2E Cotton Towel",
            "name_uz": "E2E paxta sochiq",
            "short_desc_en": "Test towel for the end-to-end flow.",
            "hs_code": "6302600000",
            "moq": 1000,
            "unit": "pcs",
            "lead_time_days": 25,
            "net_weight": 0.5,
            "gross_weight": 0.55,
            "packaging_type": "20 pcs per carton",
            "units_per_carton": 20,
            "status": "active",
        },
    )
    assert product.id

    price = product_service.save_price(
        session,
        admin,
        {
            "product_id": product.id,
            "incoterm": "FOB",
            "currency": "USD",
            "origin_point": "Tashkent",
            "unit_price": 2.75,
            "moq": 1000,
            "valid_from": today() - dt.timedelta(days=1),
            "valid_to": today() + dt.timedelta(days=90),
            "lead_time_days": 25,
            "status": "approved",
        },
    )
    assert product_service.is_price_valid(price)

    readiness = product_service.export_readiness(session, product.id)
    assert 0 <= readiness["score"] <= 100

    # 2) Catalog exports ----------------------------------------------------
    catalog = catalog_service.save_catalog(
        session,
        admin,
        {"title": "E2E catalog", "language": "en", "version": "1.0", "include_prices": 1},
        [product.id],
    )
    pdf_path = Path(catalog_service.export_pdf(session, admin, catalog.id, tmp_path / "e2e.pdf"))
    html_dir = Path(catalog_service.export_html(session, admin, catalog.id, tmp_path / "e2e-site"))
    zip_path = Path(catalog_service.export_zip(session, admin, catalog.id, tmp_path / "e2e.zip"))
    assert pdf_path.exists() and (html_dir / "index.html").exists() and zip_path.exists()

    # 3) Buyer --------------------------------------------------------------
    buyer = buyer_service.save_buyer(
        session,
        admin,
        {
            "company_name": "E2E Import Partners Ltd",
            "contact_person": "Test Buyer",
            "country": "Poland",
            "city": "Gdansk",
            "email": "buyer@e2e.example",
            "phone": "+48 22 000 11 22",
            "buyer_type": "importer",
            "source": "manual",
        },
    )
    lead = lead_service.save_lead(
        session,
        admin,
        {
            "title": "E2E towel programme",
            "buyer_id": buyer.id,
            "product_id": product.id,
            "status": "new",
            "expected_value": 27500,
            "currency": "USD",
        },
    )

    # 4) RFQ ----------------------------------------------------------------
    rfq = quotation_service.save_rfq(
        session,
        admin,
        {
            "buyer_id": buyer.id,
            "lead_id": lead.id,
            "received_at": today(),
            "deadline": today() + dt.timedelta(days=7),
            "target_incoterm": "FOB",
            "destination": "Gdansk",
            "certificate_requirements": "Certificate of Origin",
            "currency": "USD",
            "status": "in_review",
        },
        [
            {
                "product_id": product.id,
                "description": "E2E Cotton Towel",
                "quantity": 10000,
                "unit": "pcs",
                "target_price": 2.6,
            }
        ],
    )
    assert quotation_service.rfq_dict(session, rfq.id)["items"]

    # 5) Quotation ready to be sent ----------------------------------------
    line = quotation_service.suggest_line_from_price(session, product.id, price.id, 10000)
    quotation = quotation_service.save_quotation(
        session,
        admin,
        {
            "buyer_id": buyer.id,
            "lead_id": lead.id,
            "rfq_id": rfq.id,
            "issue_date": today(),
            "valid_until": today() + dt.timedelta(days=30),
            "incoterm": "FOB",
            "loading_port": "Tashkent",
            "destination": "Gdansk",
            "currency": "USD",
            "payment_terms": "30% advance, 70% against B/L copy",
            "freight_cost": 1500,
            "insurance_cost": 200,
            "discount": 0,
        },
        [line],
    )
    assert quotation.subtotal == 27500.0
    assert quotation.grand_total == 27500.0 + 1500 + 200

    quotation_service.submit_for_review(session, admin, quotation.id)
    quotation_service.approve_quotation(session, admin, quotation.id)
    sent = quotation_service.mark_sent(session, admin, quotation.id)
    assert sent.status == "sent"

    # The lead follows the quotation into the pipeline.
    assert lead_service.lead_dict(session, lead.id)["status"] == "quotation_sent"

    # 6) Email through the demo outbox --------------------------------------
    provider = integration_service.build_provider(session, "email")
    assert provider.is_demo is True
    draft = email_service.save_draft(
        session,
        admin,
        {
            "buyer_id": buyer.id,
            "lead_id": lead.id,
            "quotation_id": quotation.id,
            "to_address": "buyer@e2e.example",
            "subject": f"Quotation {quotation.number}",
            "body": "Please find our offer attached.",
        },
    )
    message = email_service.send(session, admin, draft.id)
    assert message.status == "sent"
    assert message.provider == "demo_outbox"

    # 7) Checklist ----------------------------------------------------------
    checklists = checklist_service.list_checklists(session, scope="lead", entity_id=lead.id)
    assert checklists, "the quotation_sent stage applies a checklist"
    items = checklist_service.checklist_items(session, checklists[0]["id"])
    for item in items:
        checklist_service.toggle_item(session, admin, item["id"], True)
    assert (
        checklist_service.list_checklists(session, scope="lead", entity_id=lead.id)[0]["completion"]
        == 100.0
    )

    # 8) Contract, shipment and revenue -------------------------------------
    contract = contract_service.create_from_quotation(session, admin, quotation.id)
    lead_service.change_status(session, admin, lead.id, "closed_won", contract_id=contract.id)
    assert lead_service.lead_dict(session, lead.id)["status"] == "closed_won"

    shipment = logistics_service.save_shipment(
        session,
        admin,
        {
            "buyer_id": buyer.id,
            "lead_id": lead.id,
            "contract_id": contract.id,
            "quotation_id": quotation.id,
            "incoterm": "FOB",
            "loading_port": "Tashkent",
            "destination": "Gdansk",
            "container_type": "40HC",
            "etd": today() + dt.timedelta(days=10),
            "eta": today() + dt.timedelta(days=35),
            "currency": "USD",
            "planned_freight_cost": 1500,
        },
        logistics_service.build_items_from_quotation(session, quotation.id),
    )
    assert shipment.package_count == 500  # 10000 pcs / 20 per carton

    for target in (
        "booking_requested",
        "booked",
        "ready_to_ship",
        "in_transit",
        "arrived",
        "delivered",
    ):
        logistics_service.change_status(session, admin, shipment.id, target)
    assert logistics_service.shipment_dict(session, shipment.id)["status"] == "delivered"

    contract_service.record_revenue(
        session,
        admin,
        {
            "shipment_id": shipment.id,
            "lead_id": lead.id,
            "contract_id": contract.id,
            "buyer_id": buyer.id,
            "expected_amount": quotation.grand_total,
            "actual_amount": quotation.grand_total,
            "currency": "USD",
        },
    )

    # 9) Reports ------------------------------------------------------------
    xlsx = Path(
        report_service.export(
            session, admin, "won_lost_deals", "xlsx", target=tmp_path / "won-lost.xlsx"
        )
    )
    pdf = Path(
        report_service.export(
            session, admin, "shipment_status", "pdf", target=tmp_path / "shipments.pdf"
        )
    )
    assert xlsx.exists() and pdf.exists()

    counters = report_service.dashboard_counters(session)
    assert counters["revenue_actual"] >= quotation.grand_total

    # The demo catalog seeded at start-up is still intact.
    assert session.scalars(select(Catalog)).first() is not None
