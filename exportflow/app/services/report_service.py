"""Report definitions, data assembly and PDF/Excel export."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import PATHS
from app.models import Buyer, Contract, Lead, Product, RevenueRecord, SalesAgent, User
from app.reports import export_excel, export_pdf
from app.services import (
    audit_service,
    checklist_service,
    company_service,
    contract_service,
    document_service,
    logistics_service,
    product_service,
    quotation_service,
)
from app.services.auth_service import CurrentUser
from app.utils.errors import ValidationError
from app.utils.formatting import now, slugify

#: Report identifiers exposed in the reports page.
REPORT_CODES = (
    "product_catalog",
    "product_export_readiness",
    "buyer_register",
    "buyers_by_country",
    "lead_source_performance",
    "rfq_register",
    "quotation_register",
    "quotation_conversion",
    "pipeline_by_product",
    "pipeline_by_country",
    "manager_performance",
    "agent_performance",
    "certificate_expiry",
    "shipment_status",
    "overdue_checklists",
    "won_lost_deals",
    "lost_reasons",
    "revenue_expected_vs_actual",
)


class ReportFilters(dict):
    """Loose filter container; unknown keys are simply ignored."""


def _leads(session: Session, filters: dict) -> list[dict]:
    from app.services import lead_service

    rows = lead_service.search_leads(
        session,
        country=filters.get("country"),
        product_id=filters.get("product_id"),
        category_id=filters.get("category_id"),
        source=filters.get("source"),
        manager_id=filters.get("manager_id"),
        status=filters.get("stage") or filters.get("status"),
    )
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        filtered = []
        for row in rows:
            created = row.get("created_at")
            created_date = created.date() if isinstance(created, dt.datetime) else created
            if date_from and created_date and created_date < date_from:
                continue
            if date_to and created_date and created_date > date_to:
                continue
            filtered.append(row)
        rows = filtered
    if filters.get("buyer_id"):
        rows = [row for row in rows if row["buyer_id"] == filters["buyer_id"]]
    return rows


# --------------------------------------------------------------- builders
def _product_catalog(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    rows = product_service.search_products(
        session,
        category_id=filters.get("category_id"),
        status=filters.get("status"),
        lang=filters.get("lang", "en"),
    )
    columns = [
        ("sku", "SKU"),
        ("name", "Product"),
        ("category", "Category"),
        ("brand", "Brand"),
        ("hs_code", "HS code"),
        ("moq", "MOQ"),
        ("unit", "Unit"),
        ("lead_time_days", "Lead time, days"),
        ("certificates", "Certificates"),
        ("prices", "Prices"),
        ("status", "Status"),
    ]
    return columns, rows


def _product_export_readiness(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    products = product_service.search_products(session, category_id=filters.get("category_id"))
    rows = []
    for product in products:
        readiness = product_service.export_readiness(session, product["id"])
        rows.append(
            {
                "sku": product["sku"],
                "name": product["name"],
                "category": product["category"],
                "score": readiness["score"],
                "missing": ", ".join(readiness["missing"]),
                "export_ready": "yes" if readiness["score"] >= 80 else "no",
            }
        )
    rows.sort(key=lambda row: row["score"])
    columns = [
        ("sku", "SKU"),
        ("name", "Product"),
        ("category", "Category"),
        ("score", "Readiness, %"),
        ("export_ready", "Export ready"),
        ("missing", "Missing"),
    ]
    return columns, rows


def _buyer_register(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    from app.services import buyer_service

    rows = buyer_service.search_buyers(
        session,
        country=filters.get("country"),
        source=filters.get("source"),
        manager_id=filters.get("manager_id"),
    )
    columns = [
        ("company_name", "Buyer"),
        ("country", "Country"),
        ("city", "City"),
        ("contact_person", "Contact"),
        ("email", "Email"),
        ("phone", "Phone"),
        ("buyer_type", "Type"),
        ("source", "Source"),
        ("manager", "Manager"),
        ("leads", "Leads"),
        ("quotations", "Quotations"),
        ("risk_level", "Risk"),
    ]
    return columns, rows


def _buyers_by_country(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    from app.services import buyer_service

    buyers = buyer_service.search_buyers(session)
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"buyers": 0, "leads": 0, "quotations": 0, "potential": 0.0}
    )
    for buyer in buyers:
        bucket = grouped[buyer["country"] or "-"]
        bucket["buyers"] += 1
        bucket["leads"] += buyer["leads"]
        bucket["quotations"] += buyer["quotations"]
        bucket["potential"] += buyer["annual_potential"] or 0
    rows = [
        {"country": country, **values, "potential": round(values["potential"], 2)}
        for country, values in sorted(grouped.items(), key=lambda kv: -kv[1]["buyers"])
    ]
    columns = [
        ("country", "Country"),
        ("buyers", "Buyers"),
        ("leads", "Leads"),
        ("quotations", "Quotations"),
        ("potential", "Annual potential"),
    ]
    return columns, rows


def _lead_source_performance(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    leads = _leads(session, filters)
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"leads": 0, "won": 0, "lost": 0, "expected": 0.0, "won_value": 0.0}
    )
    for lead in leads:
        bucket = grouped[lead["source"]]
        bucket["leads"] += 1
        bucket["expected"] += lead["expected_value"] or 0
        if lead["status"] == "closed_won":
            bucket["won"] += 1
            bucket["won_value"] += lead["expected_value"] or 0
        elif lead["status"] == "closed_lost":
            bucket["lost"] += 1
    rows = []
    for source, values in sorted(grouped.items(), key=lambda kv: -kv[1]["leads"]):
        rows.append(
            {
                "source": source,
                "leads": values["leads"],
                "won": values["won"],
                "lost": values["lost"],
                "expected": round(values["expected"], 2),
                "won_value": round(values["won_value"], 2),
                "conversion": (
                    round(values["won"] * 100.0 / values["leads"], 1) if values["leads"] else 0.0
                ),
            }
        )
    columns = [
        ("source", "Source"),
        ("leads", "Leads"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("conversion", "Conversion, %"),
        ("expected", "Expected value"),
        ("won_value", "Won value"),
    ]
    return columns, rows


def _rfq_register(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    rows = quotation_service.list_rfqs(
        session, buyer_id=filters.get("buyer_id"), status=filters.get("status")
    )
    columns = [
        ("number", "RFQ"),
        ("buyer", "Buyer"),
        ("received_at", "Received"),
        ("deadline", "Deadline"),
        ("target_incoterm", "Incoterm"),
        ("destination", "Destination"),
        ("items", "Items"),
        ("currency", "Currency"),
        ("status", "Status"),
    ]
    return columns, rows


def _quotation_register(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    rows = quotation_service.list_quotations(
        session,
        buyer_id=filters.get("buyer_id"),
        status=filters.get("status"),
        manager_id=filters.get("manager_id"),
        incoterm=filters.get("incoterm"),
        currency=filters.get("currency"),
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
    )
    columns = [
        ("number", "Quotation"),
        ("buyer", "Buyer"),
        ("country", "Country"),
        ("issue_date", "Issued"),
        ("valid_until", "Valid until"),
        ("incoterm", "Incoterm"),
        ("destination", "Destination"),
        ("currency", "Currency"),
        ("grand_total", "Grand total"),
        ("status", "Status"),
        ("manager", "Manager"),
    ]
    return columns, rows


def _quotation_conversion(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    quotations = quotation_service.list_quotations(
        session, date_from=filters.get("date_from"), date_to=filters.get("date_to")
    )
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "sent": 0,
            "accepted": 0,
            "rejected": 0,
            "value": 0.0,
            "won_value": 0.0,
        }
    )
    for quotation in quotations:
        bucket = grouped[quotation["manager"] or "-"]
        bucket["total"] += 1
        bucket["value"] += quotation["grand_total"] or 0
        if quotation["status"] in (
            "sent",
            "viewed",
            "buyer_replied",
            "under_negotiation",
            "accepted",
            "rejected",
        ):
            bucket["sent"] += 1
        if quotation["status"] == "accepted":
            bucket["accepted"] += 1
            bucket["won_value"] += quotation["grand_total"] or 0
        if quotation["status"] == "rejected":
            bucket["rejected"] += 1
    rows = []
    for manager, values in sorted(grouped.items(), key=lambda kv: -kv[1]["total"]):
        rows.append(
            {
                "manager": manager,
                "total": values["total"],
                "sent": values["sent"],
                "accepted": values["accepted"],
                "rejected": values["rejected"],
                "conversion": (
                    round(values["accepted"] * 100.0 / values["sent"], 1) if values["sent"] else 0.0
                ),
                "value": round(values["value"], 2),
                "won_value": round(values["won_value"], 2),
            }
        )
    columns = [
        ("manager", "Manager"),
        ("total", "Quotations"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("conversion", "Conversion, %"),
        ("value", "Total value"),
        ("won_value", "Accepted value"),
    ]
    return columns, rows


def _pipeline_grouped(session: Session, filters: dict, key: str, label: str):
    leads = _leads(session, filters)
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"leads": 0, "open": 0, "won": 0, "lost": 0, "expected": 0.0}
    )
    for lead in leads:
        bucket = grouped[lead.get(key) or "-"]
        bucket["leads"] += 1
        bucket["expected"] += lead["expected_value"] or 0
        if lead["status"] == "closed_won":
            bucket["won"] += 1
        elif lead["status"] == "closed_lost":
            bucket["lost"] += 1
        else:
            bucket["open"] += 1
    rows = [
        {key: name, **values, "expected": round(values["expected"], 2)}
        for name, values in sorted(grouped.items(), key=lambda kv: -kv[1]["expected"])
    ]
    columns = [
        (key, label),
        ("leads", "Deals"),
        ("open", "Open"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("expected", "Expected value"),
    ]
    return columns, rows


def _pipeline_by_product(session: Session, filters: dict):
    return _pipeline_grouped(session, filters, "product", "Product")


def _pipeline_by_country(session: Session, filters: dict):
    return _pipeline_grouped(session, filters, "country", "Country")


def _manager_performance(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    leads = _leads(session, filters)
    quotations = quotation_service.list_quotations(session)
    rfqs = quotation_service.list_rfqs(session)
    users = {
        u.id: (u.full_name or u.username) for u in session.scalars(select(User)).unique().all()
    }

    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "leads": 0,
            "rfqs": 0,
            "quotations": 0,
            "samples": 0,
            "won": 0,
            "lost": 0,
            "expected": 0.0,
            "won_value": 0.0,
            "cycle_days": [],
        }
    )
    lead_manager = {}
    for lead in leads:
        name = lead["manager"] or "-"
        lead_manager[lead["id"]] = name
        bucket = stats[name]
        bucket["leads"] += 1
        bucket["expected"] += lead["expected_value"] or 0
        if lead["status"] == "closed_won":
            bucket["won"] += 1
            bucket["won_value"] += lead["expected_value"] or 0
        elif lead["status"] == "closed_lost":
            bucket["lost"] += 1
        if lead["status"] == "sample_sent":
            bucket["samples"] += 1

    for rfq in rfqs:
        name = lead_manager.get(rfq.get("lead_id"), "-")
        stats[name]["rfqs"] += 1
    for quotation in quotations:
        stats[quotation["manager"] or "-"]["quotations"] += 1

    for lead in session.scalars(select(Lead).where(Lead.is_archived.is_(False))).unique().all():
        if lead.closed_at and lead.created_at:
            name = users.get(lead.manager_id, "-")
            stats[name]["cycle_days"].append((lead.closed_at - lead.created_at).days)

    rows = []
    for manager, values in sorted(stats.items(), key=lambda kv: -kv[1]["leads"]):
        closed = values["won"] + values["lost"]
        rows.append(
            {
                "manager": manager,
                "leads": values["leads"],
                "rfqs": values["rfqs"],
                "quotations": values["quotations"],
                "samples": values["samples"],
                "won": values["won"],
                "lost": values["lost"],
                "conversion": round(values["won"] * 100.0 / closed, 1) if closed else 0.0,
                "expected": round(values["expected"], 2),
                "won_value": round(values["won_value"], 2),
                "avg_cycle": (
                    round(sum(values["cycle_days"]) / len(values["cycle_days"]), 1)
                    if values["cycle_days"]
                    else 0.0
                ),
            }
        )
    columns = [
        ("manager", "Manager"),
        ("leads", "Leads"),
        ("rfqs", "RFQ"),
        ("quotations", "Quotations"),
        ("samples", "Samples"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("conversion", "Conversion, %"),
        ("expected", "Expected value"),
        ("won_value", "Won value"),
        ("avg_cycle", "Avg cycle, days"),
    ]
    return columns, rows


def _agent_performance(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    agents = (
        session.scalars(select(SalesAgent).where(SalesAgent.is_archived.is_(False))).unique().all()
    )
    buyers = session.scalars(select(Buyer).where(Buyer.is_archived.is_(False))).unique().all()
    leads = session.scalars(select(Lead).where(Lead.is_archived.is_(False))).unique().all()
    rows = []
    for agent in agents:
        agent_buyers = [b.id for b in buyers if b.agent_id == agent.id]
        agent_leads = [
            lead for lead in leads if lead.agent_id == agent.id or lead.buyer_id in agent_buyers
        ]
        won = [lead for lead in agent_leads if lead.status == "closed_won"]
        lost = [lead for lead in agent_leads if lead.status == "closed_lost"]
        won_value = sum(lead.expected_value or 0 for lead in won)
        rows.append(
            {
                "name": agent.name,
                "country": agent.country or "",
                "market": agent.market or "",
                "buyers": len(agent_buyers),
                "leads": len(agent_leads),
                "won": len(won),
                "lost": len(lost),
                "won_value": round(won_value, 2),
                "commission_percent": agent.commission_percent,
                "commission_value": round(won_value * agent.commission_percent / 100.0, 2),
                "commission_status": agent.commission_status,
            }
        )
    columns = [
        ("name", "Agent"),
        ("country", "Country"),
        ("market", "Market"),
        ("buyers", "Buyers"),
        ("leads", "Deals"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("won_value", "Won value"),
        ("commission_percent", "Commission, %"),
        ("commission_value", "Commission value"),
        ("commission_status", "Status"),
    ]
    return columns, rows


def _certificate_expiry(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    rows = document_service.certificate_register_rows(session)
    columns = [
        ("name", "Certificate"),
        ("cert_type", "Type"),
        ("product", "Product"),
        ("issuer", "Issuer"),
        ("number", "Number"),
        ("issue_date", "Issued"),
        ("expiry_date", "Expires"),
        ("days_left", "Days left"),
        ("status", "Status"),
        ("alert", "Alert"),
    ]
    return columns, rows


def _shipment_status(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    rows = logistics_service.list_shipments(
        session,
        buyer_id=filters.get("buyer_id"),
        status=filters.get("status"),
        incoterm=filters.get("incoterm"),
    )
    columns = [
        ("number", "Shipment"),
        ("buyer", "Buyer"),
        ("incoterm", "Incoterm"),
        ("loading_port", "Loading port"),
        ("destination", "Destination"),
        ("etd", "ETD"),
        ("eta", "ETA"),
        ("actual_arrival", "Arrived"),
        ("status", "Status"),
        ("customs_status", "Customs"),
        ("gross_weight", "Gross, kg"),
        ("planned_cost", "Planned cost"),
        ("actual_cost", "Actual cost"),
        ("cost_delta", "Delta"),
    ]
    return columns, rows


def _overdue_checklists(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    rows = checklist_service.overdue_summary(session)
    columns = [
        ("checklist", "Checklist"),
        ("scope", "Scope"),
        ("entity_id", "Entity"),
        ("category", "Category"),
        ("title", "Task"),
        ("due_date", "Due"),
        ("days_overdue", "Days overdue"),
        ("priority", "Priority"),
    ]
    return columns, rows


def _won_lost_deals(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    leads = [
        lead for lead in _leads(session, filters) if lead["status"] in ("closed_won", "closed_lost")
    ]
    columns = [
        ("title", "Deal"),
        ("buyer", "Buyer"),
        ("country", "Country"),
        ("product", "Product"),
        ("source", "Source"),
        ("manager", "Manager"),
        ("expected_value", "Value"),
        ("currency", "Currency"),
        ("status", "Result"),
        ("lost_reason", "Loss reason"),
    ]
    return columns, leads


def _lost_reasons(session: Session, filters: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    leads = [lead for lead in _leads(session, filters) if lead["status"] == "closed_lost"]
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"deals": 0, "value": 0.0})
    for lead in leads:
        bucket = grouped[lead["lost_reason"] or "unspecified"]
        bucket["deals"] += 1
        bucket["value"] += lead["expected_value"] or 0
    total = sum(values["deals"] for values in grouped.values()) or 1
    rows = [
        {
            "reason": reason,
            "deals": values["deals"],
            "value": round(values["value"], 2),
            "share": round(values["deals"] * 100.0 / total, 1),
        }
        for reason, values in sorted(grouped.items(), key=lambda kv: -kv[1]["deals"])
    ]
    columns = [
        ("reason", "Loss reason"),
        ("deals", "Deals"),
        ("share", "Share, %"),
        ("value", "Lost value"),
    ]
    return columns, rows


def _revenue_expected_vs_actual(
    session: Session, filters: dict
) -> tuple[list[tuple[str, str]], list[dict]]:
    records = contract_service.list_revenue(session)
    buyers = {b.id: b.company_name for b in session.scalars(select(Buyer)).unique().all()}
    contracts = {c.id: c.number for c in session.scalars(select(Contract)).unique().all()}
    rows = []
    for record in records:
        rows.append(
            {
                "record_date": record["record_date"],
                "buyer": buyers.get(record["buyer_id"], ""),
                "contract": contracts.get(record["contract_id"], ""),
                "currency": record["currency"],
                "expected_amount": record["expected_amount"],
                "actual_amount": record["actual_amount"],
                "delta": record["delta"],
                "kind": record["kind"],
            }
        )
    open_pipeline = sum(
        lead["expected_value"] or 0
        for lead in _leads(session, filters)
        if lead["status"] not in ("closed_won", "closed_lost")
    )
    if open_pipeline:
        rows.append(
            {
                "record_date": None,
                "buyer": "OPEN PIPELINE",
                "contract": "",
                "currency": "USD",
                "expected_amount": round(open_pipeline, 2),
                "actual_amount": 0.0,
                "delta": round(-open_pipeline, 2),
                "kind": "pipeline",
            }
        )
    columns = [
        ("record_date", "Date"),
        ("buyer", "Buyer"),
        ("contract", "Contract"),
        ("currency", "Currency"),
        ("expected_amount", "Expected"),
        ("actual_amount", "Actual"),
        ("delta", "Delta"),
        ("kind", "Kind"),
    ]
    return columns, rows


BUILDERS: dict[str, Callable[[Session, dict], tuple[list[tuple[str, str]], list[dict]]]] = {
    "product_catalog": _product_catalog,
    "product_export_readiness": _product_export_readiness,
    "buyer_register": _buyer_register,
    "buyers_by_country": _buyers_by_country,
    "lead_source_performance": _lead_source_performance,
    "rfq_register": _rfq_register,
    "quotation_register": _quotation_register,
    "quotation_conversion": _quotation_conversion,
    "pipeline_by_product": _pipeline_by_product,
    "pipeline_by_country": _pipeline_by_country,
    "manager_performance": _manager_performance,
    "agent_performance": _agent_performance,
    "certificate_expiry": _certificate_expiry,
    "shipment_status": _shipment_status,
    "overdue_checklists": _overdue_checklists,
    "won_lost_deals": _won_lost_deals,
    "lost_reasons": _lost_reasons,
    "revenue_expected_vs_actual": _revenue_expected_vs_actual,
}


def build(session: Session, code: str, filters: dict | None = None) -> dict:
    """Build one report and return its columns, rows and metadata."""
    if code not in BUILDERS:
        raise ValidationError(f"Unknown report '{code}'", key="error.unknown_report")
    filters = dict(filters or {})
    columns, rows = BUILDERS[code](session, filters)
    return {"code": code, "columns": columns, "rows": rows, "filters": filters, "count": len(rows)}


def _meta(session: Session, filters: dict) -> dict[str, str]:
    meta: dict[str, str] = {}
    labels = {
        "date_from": "From",
        "date_to": "To",
        "country": "Country",
        "status": "Status",
        "incoterm": "Incoterm",
        "currency": "Currency",
        "source": "Source",
        "stage": "Stage",
    }
    for key, label in labels.items():
        value = filters.get(key)
        if value:
            meta[label] = str(value)
    if filters.get("buyer_id"):
        buyer = session.get(Buyer, filters["buyer_id"])
        if buyer is not None:
            meta["Buyer"] = buyer.company_name
    if filters.get("product_id"):
        product = session.get(Product, filters["product_id"])
        if product is not None:
            meta["Product"] = product.display_name("en")
    if filters.get("manager_id"):
        user = session.get(User, filters["manager_id"])
        if user is not None:
            meta["Manager"] = user.full_name or user.username
    return meta


def export(
    session: Session,
    actor: CurrentUser,
    code: str,
    fmt: str = "xlsx",
    filters: dict | None = None,
    target: str | Path | None = None,
    title: str | None = None,
) -> str:
    """Export a report to Excel or PDF and return the written file path."""
    actor.require("report.export")
    report = build(session, code, filters)
    company = company_service.company_dict(session)
    display_title = title or code.replace("_", " ").title()
    if target is None:
        stamp = now().strftime("%Y%m%d-%H%M%S")
        folder = PATHS.exports_dir / "reports"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{slugify(code)}-{stamp}.{fmt}"

    if fmt == "xlsx":
        path = export_excel(
            target,
            display_title,
            report["columns"],
            report["rows"],
            meta=_meta(session, report["filters"]),
            sheet_name=code[:31],
        )
    elif fmt == "pdf":
        path = export_pdf(
            target,
            display_title,
            report["columns"],
            report["rows"],
            meta=_meta(session, report["filters"]),
            company_name=company.get("name", ""),
        )
    else:
        raise ValidationError(f"Unsupported format '{fmt}'", key="error.unknown_format")

    audit_service.record(
        session,
        action="export",
        entity_type="report",
        summary=f"Report '{code}' exported to {fmt.upper()} ({report['count']} rows)",
        details={"path": path},
        user_id=actor.id,
        username=actor.username,
    )
    return path


def dashboard_counters(session: Session) -> dict[str, Any]:
    """Small aggregate numbers used by the workspace headers."""
    from app.services import lead_service

    leads = lead_service.search_leads(session, include_closed=False)
    quotations = quotation_service.list_quotations(session)
    return {
        "open_leads": len(leads),
        "overdue_follow_ups": sum(1 for lead in leads if lead["overdue"]),
        "pipeline_value": round(sum(lead["expected_value"] or 0 for lead in leads), 2),
        "quotations_sent": sum(1 for q in quotations if q["status"] in ("sent", "viewed")),
        "expiring_certificates": len(
            [alert for alert in document_service.expiry_alerts(session) if alert["level"] != "info"]
        ),
        "delayed_shipments": len(logistics_service.delay_alerts(session)),
        "overdue_checklists": len(checklist_service.overdue_summary(session)),
        "revenue_actual": round(
            sum(record.actual_amount for record in session.scalars(select(RevenueRecord)).all()), 2
        ),
    }
