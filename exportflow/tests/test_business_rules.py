"""Tests for the core export business rules."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.models import Certificate, Contract, Lead, Product, Quotation, Shipment
from app.services import (
    buyer_service,
    checklist_service,
    document_service,
    lead_service,
    logistics_service,
    product_service,
    quotation_service,
    task_service,
)
from app.utils.errors import PermissionDenied, ValidationError, WorkflowError
from app.utils.formatting import today


# --------------------------------------------------------------- quotation
def test_quotation_totals_follow_the_documented_formula():
    """Line total, subtotal and grand total are computed as specified."""
    items = [
        {"quantity": 100, "unit_price": 2.5, "cost_price": 1.5},
        {"quantity": 30, "unit_price": 10, "cost_price": 6},
    ]
    totals = quotation_service.compute_totals(items, freight=200, insurance=50, discount=25)

    assert items[0]["line_total"] == 250.0
    assert items[1]["line_total"] == 300.0
    assert totals["subtotal"] == 550.0
    assert totals["grand_total"] == 550.0 + 200 + 50 - 25
    assert totals["cost"] == 330.0
    assert totals["margin"] == 220.0


def test_quotation_totals_handle_empty_input():
    """An empty quotation has zero totals instead of raising."""
    totals = quotation_service.compute_totals([], 0, 0, 0)
    assert totals["subtotal"] == 0
    assert totals["grand_total"] == 0
    assert totals["margin_percent"] == 0.0


# ------------------------------------------------------------------ prices
def test_price_validity_requires_approval_and_a_live_window(session):
    """Only approved prices inside their validity window may be used."""
    product = session.scalars(select(Product)).first()
    prices = product_service.list_prices(session, product.id)
    assert prices, "demo data must contain prices"

    approved = [row for row in prices if row["status"] == "approved"]
    expired = [row for row in prices if row["status"] == "expired"]
    assert approved and expired

    from app.models import ProductPrice

    approved_row = session.get(ProductPrice, approved[0]["id"])
    expired_row = session.get(ProductPrice, expired[0]["id"])
    assert product_service.is_price_valid(approved_row) is True
    assert product_service.is_price_valid(expired_row) is False

    draft = product_service.save_price(
        session,
        _admin(),
        {
            "product_id": product.id,
            "incoterm": "EXW",
            "currency": "USD",
            "origin_point": "Factory",
            "unit_price": 1.11,
            "status": "draft",
        },
    )
    assert product_service.is_price_valid(draft) is False


def test_port_is_mandatory_for_sea_incoterms():
    """FOB/CIF/CFR prices require a port or place of loading."""
    with pytest.raises(ValidationError) as info:
        product_service.validate_price_values(
            {"incoterm": "FOB", "unit_price": 5, "origin_point": ""}
        )
    assert info.value.key == "error.port_required"

    product_service.validate_price_values({"incoterm": "EXW", "unit_price": 5, "origin_point": ""})


def test_expired_price_cannot_be_used_in_a_quotation(session, admin):
    """Saving a quotation with an expired price line is rejected."""
    product = session.scalars(select(Product)).first()
    expired = [
        row
        for row in product_service.list_prices(session, product.id)
        if row["status"] == "expired"
    ]
    buyer = buyer_service.search_buyers(session)[0]

    with pytest.raises(ValidationError) as info:
        quotation_service.save_quotation(
            session,
            admin,
            {"buyer_id": buyer["id"], "issue_date": today(), "incoterm": "FOB", "currency": "USD"},
            [
                {
                    "product_id": product.id,
                    "price_id": expired[0]["id"],
                    "description": "Expired price line",
                    "quantity": 100,
                    "unit_price": 2.8,
                }
            ],
        )
    assert info.value.key == "error.price_not_usable"


# ------------------------------------------------------------- permissions
def test_sales_manager_cannot_approve_a_quotation(session, sales_manager, admin):
    """Approving a quotation requires the ``quotation.approve`` permission."""
    quotation = _draft_quotation(session, admin)
    with pytest.raises(PermissionDenied):
        quotation_service.approve_quotation(session, sales_manager, quotation.id)

    approved = quotation_service.approve_quotation(session, admin, quotation.id)
    assert approved.status == "approved"


def test_quotation_must_be_approved_before_it_is_sent(session, admin):
    """A draft quotation can never be marked as sent."""
    quotation = _draft_quotation(session, admin)
    with pytest.raises(WorkflowError) as info:
        quotation_service.mark_sent(session, admin, quotation.id)
    assert info.value.key == "error.quotation_not_approved"

    quotation_service.approve_quotation(session, admin, quotation.id)
    sent = quotation_service.mark_sent(session, admin, quotation.id)
    assert sent.status == "sent"
    assert sent.sent_at is not None


def test_viewer_role_has_no_write_permissions(viewer):
    """The viewer role can look but never change anything."""
    assert viewer.can("product.view") is True
    assert viewer.can("product.edit") is False
    assert viewer.can("quotation.approve") is False
    with pytest.raises(PermissionDenied):
        viewer.require("buyer.edit")


# --------------------------------------------------------------- buyer CRM
def test_duplicate_buyer_detection_matches_email_phone_and_name(session):
    """Duplicates are found by normalised email, phone tail and company name."""
    buyer = buyer_service.search_buyers(session)[0]

    by_email = buyer_service.find_duplicates(session, email=buyer["email"].upper())
    by_name = buyer_service.find_duplicates(session, company_name=buyer["company_name"].lower())
    by_phone = buyer_service.find_duplicates(session, phone=buyer["phone"])

    assert buyer["id"] in {row["id"] for row in by_email}
    assert buyer["id"] in {row["id"] for row in by_name}
    assert buyer["id"] in {row["id"] for row in by_phone}
    assert buyer_service.find_duplicates(session, email="nobody@example.org") == []


def test_saving_a_duplicate_buyer_is_blocked_unless_forced(session, admin):
    """``save_buyer`` refuses duplicates but allows an explicit override."""
    existing = buyer_service.search_buyers(session)[0]
    payload = {
        "company_name": existing["company_name"],
        "country": existing["country"],
        "email": existing["email"],
    }
    with pytest.raises(ValidationError) as info:
        buyer_service.save_buyer(session, admin, payload)
    assert info.value.key == "error.buyer_duplicate"

    forced = buyer_service.save_buyer(session, admin, payload, allow_duplicate=True)
    assert forced.id != existing["id"]


# -------------------------------------------------------------------- lead
def test_losing_a_deal_requires_a_reason(session, admin):
    """``closed_lost`` without a reason is rejected."""
    lead = session.scalars(
        select(Lead).where(Lead.status == "in_review", Lead.is_archived.is_(False))
    ).first()
    with pytest.raises(ValidationError) as info:
        lead_service.change_status(session, admin, lead.id, "closed_lost")
    assert info.value.key == "error.lost_reason_required"

    closed = lead_service.change_status(
        session, admin, lead.id, "closed_lost", lost_reason="price_too_high"
    )
    assert closed.status == "closed_lost"
    assert closed.lost_reason == "price_too_high"
    assert closed.closed_at is not None


def test_winning_a_deal_requires_a_contract(session, admin):
    """``closed_won`` is only possible with a contract on file."""
    buyer = buyer_service.search_buyers(session)[0]
    lead = lead_service.save_lead(
        session,
        admin,
        {
            "title": "Contract rule test",
            "buyer_id": buyer["id"],
            "status": "negotiation",
            "expected_value": 1000,
        },
    )
    with pytest.raises(ValidationError) as info:
        lead_service.change_status(session, admin, lead.id, "closed_won")
    assert info.value.key == "error.contract_required"

    contract = Contract(number="C-TEST-0001", buyer_id=buyer["id"], lead_id=lead.id, amount=1000)
    session.add(contract)
    session.flush()

    won = lead_service.change_status(session, admin, lead.id, "closed_won")
    assert won.status == "closed_won"
    assert won.won_at is not None


def test_stage_change_applies_the_matching_checklist_template(session, admin):
    """Moving a lead to ``rfq_received`` auto-applies the RFQ checklist."""
    buyer = buyer_service.search_buyers(session)[0]
    lead = lead_service.save_lead(
        session,
        admin,
        {"title": "Checklist automation test", "buyer_id": buyer["id"], "status": "new"},
    )
    assert checklist_service.list_checklists(session, scope="lead", entity_id=lead.id) == []

    lead_service.change_status(session, admin, lead.id, "rfq_received")
    checklists = checklist_service.list_checklists(session, scope="lead", entity_id=lead.id)
    assert checklists, "a checklist must be created for the rfq_received stage"
    assert checklists[0]["total"] > 0

    # Re-entering the same stage must not duplicate the checklist.
    lead_service.change_status(session, admin, lead.id, "qualified")
    lead_service.change_status(session, admin, lead.id, "rfq_received")
    assert len(checklist_service.list_checklists(session, scope="lead", entity_id=lead.id)) == 1


def test_checklist_completion_is_tracked(session, admin):
    """Ticking every item moves the checklist to ``completed``."""
    buyer = buyer_service.search_buyers(session)[0]
    lead = lead_service.save_lead(
        session, admin, {"title": "Completion test", "buyer_id": buyer["id"], "status": "new"}
    )
    templates = checklist_service.list_templates(session, scope="lead")
    checklist = checklist_service.apply_template(
        session, admin, templates[0]["id"], "lead", lead.id
    )
    items = checklist_service.checklist_items(session, checklist.id)
    assert items

    for item in items:
        checklist_service.toggle_item(session, admin, item["id"], True)
    summary = checklist_service.list_checklists(session, scope="lead", entity_id=lead.id)[0]
    assert summary["completion"] == 100.0
    assert summary["status"] == "completed"


# ------------------------------------------------------------- certificates
def test_certificate_expiry_alerts_use_the_60_30_7_thresholds(session):
    """Certificates inside a threshold produce an alert with the right level."""
    alerts = {row["name"]: row for row in document_service.expiry_alerts(session)}

    halal = alerts.get("Halal certificate")
    phyto = alerts.get("Phytosanitary certificate")
    assert halal is not None and halal["level"] == "info"  # 45 days -> 60-day threshold
    assert phyto is not None and phyto["level"] == "warning"  # 25 days -> 30-day threshold
    assert "ISO 9001:2015" not in alerts  # 620 days left, no alert

    # A certificate expiring within a week is escalated to critical.
    urgent = session.scalars(
        select(Certificate).where(Certificate.name == "Certificate of Origin (Form A)")
    ).first()
    urgent.expiry_date = today() + dt.timedelta(days=5)
    session.flush()
    refreshed = {row["name"]: row for row in document_service.expiry_alerts(session)}
    assert refreshed["Certificate of Origin (Form A)"]["level"] == "critical"


def test_certificate_status_reflects_the_expiry_date():
    """The derived status is valid / expiring / expired."""
    assert document_service.certificate_status(None) == "valid"
    assert document_service.certificate_status(today() + dt.timedelta(days=400)) == "valid"
    assert document_service.certificate_status(today() + dt.timedelta(days=20)) == "expiring"
    assert document_service.certificate_status(today() - dt.timedelta(days=1)) == "expired"


def test_missing_certificates_are_reported_for_a_quotation(session):
    """A requirement without a matching certificate is reported as missing."""
    product = session.scalars(select(Product).where(Product.sku == "FD-APR-ORG")).first()
    missing = document_service.missing_certificates(
        session, [product.id], "Halal, Kosher certificate"
    )
    assert any("kosher" in item for item in missing)
    assert not any("halal" in item for item in missing)


# ---------------------------------------------------------------- shipment
def test_shipment_status_transitions_are_validated(session, admin):
    """Only the transitions declared in the state machine are allowed."""
    assert logistics_service.can_transition("planning", "booking_requested") is True
    assert logistics_service.can_transition("planning", "delivered") is False
    assert logistics_service.can_transition("delivered", "in_transit") is False

    shipment = session.scalars(select(Shipment)).first()
    with pytest.raises(WorkflowError) as info:
        logistics_service.change_status(session, admin, shipment.id, "delivered")
    assert info.value.key == "error.shipment_transition"

    logistics_service.change_status(session, admin, shipment.id, "ready_to_ship")
    logistics_service.change_status(session, admin, shipment.id, "in_transit")
    arrived = logistics_service.change_status(session, admin, shipment.id, "arrived")
    assert arrived.actual_arrival is not None


def test_revenue_can_only_be_recorded_for_a_delivered_shipment(session, admin):
    """Recording actual revenue requires a delivered shipment."""
    from app.services import contract_service

    shipment = session.scalars(select(Shipment)).first()
    shipment.status = "in_transit"
    session.flush()
    with pytest.raises(ValidationError) as info:
        contract_service.record_revenue(
            session, admin, {"shipment_id": shipment.id, "actual_amount": 100}
        )
    assert info.value.key == "error.shipment_not_delivered"

    shipment.status = "delivered"
    session.flush()
    record = contract_service.record_revenue(
        session, admin, {"shipment_id": shipment.id, "actual_amount": 100, "expected_amount": 90}
    )
    assert record.actual_amount == 100


# ------------------------------------------------------------- follow-ups
def test_follow_up_task_is_created_when_a_quotation_is_sent(session, admin):
    """Sending a quotation schedules a follow-up three days later."""
    quotation = _draft_quotation(session, admin)
    quotation_service.approve_quotation(session, admin, quotation.id)
    quotation_service.mark_sent(session, admin, quotation.id)

    tasks = task_service.list_tasks(
        session, entity_type="quotation", entity_id=quotation.id, status="open"
    )
    assert tasks, "a follow-up task must exist"
    assert tasks[0]["due_date"] == today() + dt.timedelta(days=3)
    assert tasks[0]["rule_code"] == "quotation.followup"


def test_certificate_expiry_rule_creates_a_task(session):
    """The scan creates one task per certificate/threshold combination."""
    certificate = session.scalars(
        select(Certificate).where(Certificate.name == "Phytosanitary certificate")
    ).first()
    task_service.run_follow_up_rules(session)

    tasks = task_service.list_tasks(
        session, entity_type="certificate", entity_id=certificate.id, status="open"
    )
    assert tasks
    assert any(task["rule_code"].startswith("certificate.expiry") for task in tasks)

    # Running the rules twice must not duplicate the tasks.
    before = len(tasks)
    task_service.run_follow_up_rules(session)
    after = len(
        task_service.list_tasks(
            session, entity_type="certificate", entity_id=certificate.id, status="open"
        )
    )
    assert after == before


# ------------------------------------------------------------------ helpers
def _admin():
    from app.services.auth_service import CurrentUser
    from app.services.permissions import PERMISSIONS
    from app.utils.enums import ROLE_ADMIN

    return CurrentUser(
        id=1,
        username="admin",
        full_name="System Administrator",
        role_code=ROLE_ADMIN,
        role_name="Administrator",
        language="en",
        permissions=frozenset(PERMISSIONS),
    )


def _draft_quotation(session, actor) -> Quotation:
    """Create a small approved-price quotation used by several tests."""
    product = session.scalars(select(Product).where(Product.sku == "TX-TOW-500")).first()
    price = product_service.valid_prices_for_product(session, product.id)[0]
    buyer = buyer_service.search_buyers(session)[0]
    return quotation_service.save_quotation(
        session,
        actor,
        {
            "buyer_id": buyer["id"],
            "issue_date": today(),
            "valid_until": today() + dt.timedelta(days=30),
            "incoterm": price.incoterm,
            "loading_port": price.origin_point,
            "currency": price.currency,
            "status": "draft",
        },
        [
            {
                "product_id": product.id,
                "price_id": price.id,
                "description": product.display_name("en"),
                "quantity": 5000,
                "unit": product.unit,
                "unit_price": price.unit_price,
            }
        ],
    )
