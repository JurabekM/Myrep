"""Excel import/export of master data and lead import through adapters."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PATHS
from app.reports import export_excel, read_excel_rows
from app.services import (
    audit_service,
    buyer_service,
    integration_service,
    lead_service,
    product_service,
)
from app.services.auth_service import CurrentUser
from app.utils.errors import ValidationError
from app.utils.formatting import now, parse_date
from app.utils.logging_setup import get_logger

log = get_logger(__name__)

PRODUCT_COLUMNS = [
    ("sku", "SKU"),
    ("name_en", "Name EN"),
    ("name_ru", "Name RU"),
    ("name_uz", "Name UZ"),
    ("short_desc_en", "Short description EN"),
    ("full_desc_en", "Full description EN"),
    ("brand", "Brand"),
    ("hs_code", "HS code"),
    ("origin_country", "Origin"),
    ("moq", "MOQ"),
    ("unit", "Unit"),
    ("lead_time_days", "Lead time days"),
    ("packaging_type", "Packaging"),
    ("net_weight", "Net weight"),
    ("gross_weight", "Gross weight"),
    ("status", "Status"),
]

BUYER_COLUMNS = [
    ("company_name", "Company"),
    ("contact_person", "Contact"),
    ("position", "Position"),
    ("country", "Country"),
    ("city", "City"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("website", "Website"),
    ("linkedin", "LinkedIn"),
    ("buyer_type", "Buyer type"),
    ("interested_categories", "Interested in"),
    ("annual_potential", "Annual potential"),
    ("source", "Source"),
    ("risk_level", "Risk"),
    ("tags", "Tags"),
]

LEAD_COLUMNS = [
    ("title", "Title"),
    ("buyer", "Buyer"),
    ("country", "Country"),
    ("product", "Product"),
    ("source", "Source"),
    ("status", "Status"),
    ("temperature", "Temperature"),
    ("expected_value", "Expected value"),
    ("currency", "Currency"),
    ("next_step", "Next step"),
    ("next_follow_up", "Next follow-up"),
    ("manager", "Manager"),
]


def _export_path(prefix: str) -> Path:
    folder = PATHS.exports_dir / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{prefix}-{now().strftime('%Y%m%d-%H%M%S')}.xlsx"


# ------------------------------------------------------------------ exports
def export_products(session: Session, actor: CurrentUser, target: str | Path | None = None) -> str:
    """Export the product master data to Excel."""
    actor.require("report.export")
    rows = []
    for row in product_service.search_products(session, include_archived=True):
        data = product_service.product_dict(session, row["id"])
        rows.append({key: data.get(key) for key, _ in PRODUCT_COLUMNS})
    return export_excel(target or _export_path("products"), "Products", PRODUCT_COLUMNS, rows)


def export_buyers(session: Session, actor: CurrentUser, target: str | Path | None = None) -> str:
    """Export the buyer register to Excel."""
    actor.require("report.export")
    rows = buyer_service.search_buyers(session, include_archived=True)
    return export_excel(target or _export_path("buyers"), "Buyers", BUYER_COLUMNS, rows)


def export_leads(session: Session, actor: CurrentUser, target: str | Path | None = None) -> str:
    """Export leads to Excel."""
    actor.require("report.export")
    rows = lead_service.search_leads(session, include_archived=True)
    return export_excel(target or _export_path("leads"), "Leads", LEAD_COLUMNS, rows)


def export_template(kind: str, target: str | Path | None = None) -> str:
    """Write an empty import template with the expected headers."""
    columns = {"products": PRODUCT_COLUMNS, "buyers": BUYER_COLUMNS}.get(kind)
    if columns is None:
        raise ValidationError(f"Unknown template '{kind}'", key="error.validation")
    return export_excel(target or _export_path(f"{kind}-template"), f"{kind} template", columns, [])


# ------------------------------------------------------------------ imports
def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _to_int(value) -> int | None:
    number = _to_float(value)
    return int(number) if number is not None else None


def import_products(session: Session, actor: CurrentUser, path: str | Path) -> dict:
    """Import or update products from an Excel file."""
    actor.require("product.edit")
    raw_rows = read_excel_rows(path)
    created = updated = skipped = 0
    errors: list[str] = []
    header_map = {header: key for key, header in PRODUCT_COLUMNS}

    for index, raw in enumerate(raw_rows, 2):
        values = {
            header_map[header]: value for header, value in raw.items() if header in header_map
        }
        sku = str(values.get("sku") or "").strip()
        if not sku:
            skipped += 1
            continue
        existing = product_service.search_products(session, text=sku, include_archived=True)
        match = next((row for row in existing if row["sku"].lower() == sku.lower()), None)
        payload = {
            "sku": sku,
            "name_en": values.get("name_en") or sku,
            "name_ru": values.get("name_ru") or "",
            "name_uz": values.get("name_uz") or "",
            "short_desc_en": values.get("short_desc_en"),
            "full_desc_en": values.get("full_desc_en"),
            "brand": values.get("brand"),
            "hs_code": values.get("hs_code"),
            "origin_country": values.get("origin_country") or "Uzbekistan",
            "moq": _to_float(values.get("moq")),
            "unit": values.get("unit") or "pcs",
            "lead_time_days": _to_int(values.get("lead_time_days")),
            "packaging_type": values.get("packaging_type"),
            "net_weight": _to_float(values.get("net_weight")),
            "gross_weight": _to_float(values.get("gross_weight")),
            "status": values.get("status") or "draft",
        }
        if match:
            payload["id"] = match["id"]
        try:
            product_service.save_product(session, actor, payload)
            if match:
                updated += 1
            else:
                created += 1
        except Exception as exc:
            errors.append(f"Row {index}: {exc}")
            skipped += 1

    audit_service.record(
        session,
        action="import",
        entity_type="product",
        summary=f"Product import: {created} created, {updated} updated, {skipped} skipped",
        user_id=actor.id,
        username=actor.username,
    )
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


def import_buyers(session: Session, actor: CurrentUser, path: str | Path) -> dict:
    """Import buyers from Excel, skipping duplicates."""
    actor.require("buyer.edit")
    raw_rows = read_excel_rows(path)
    created = duplicates = skipped = 0
    errors: list[str] = []
    header_map = {header: key for key, header in BUYER_COLUMNS}

    for index, raw in enumerate(raw_rows, 2):
        values = {
            header_map[header]: value for header, value in raw.items() if header in header_map
        }
        company_name = str(values.get("company_name") or "").strip()
        if not company_name:
            skipped += 1
            continue
        matches = buyer_service.find_duplicates(
            session,
            email=values.get("email"),
            phone=values.get("phone"),
            company_name=company_name,
        )
        if matches:
            duplicates += 1
            continue
        payload = {
            "company_name": company_name,
            "contact_person": values.get("contact_person"),
            "position": values.get("position"),
            "country": values.get("country") or "",
            "city": values.get("city"),
            "email": values.get("email"),
            "phone": str(values.get("phone")) if values.get("phone") else None,
            "website": values.get("website"),
            "linkedin": values.get("linkedin"),
            "buyer_type": values.get("buyer_type") or "importer",
            "interested_categories": values.get("interested_categories"),
            "annual_potential": _to_float(values.get("annual_potential")),
            "source": values.get("source") or "manual",
            "risk_level": values.get("risk_level") or "medium",
            "tags": values.get("tags"),
        }
        try:
            buyer_service.save_buyer(session, actor, payload)
            created += 1
        except Exception as exc:
            errors.append(f"Row {index}: {exc}")
            skipped += 1

    audit_service.record(
        session,
        action="import",
        entity_type="buyer",
        summary=f"Buyer import: {created} created, {duplicates} duplicates, {skipped} skipped",
        user_id=actor.id,
        username=actor.username,
    )
    return {"created": created, "duplicates": duplicates, "skipped": skipped, "errors": errors}


def import_leads_from_provider(session: Session, actor: CurrentUser, limit: int = 50) -> dict:
    """Fetch leads through the active lead import adapter and store them.

    Buyers that already exist are reused; new enquiries always create a lead so
    nothing gets lost.
    """
    actor.require("lead.edit")
    provider = integration_service.build_provider(session, "lead_import")
    result = provider.fetch_leads(limit)
    if not result.ok:
        integration_service.append_sync_log(
            session, "lead_import", provider.code, f"ERROR: {result.message}"
        )
        raise ValidationError(result.message, key="error.integration")

    created_buyers = created_leads = matched = 0
    for record in result.data or []:
        company_name = (record.get("company_name") or "").strip()
        if not company_name:
            continue
        matches = buyer_service.find_duplicates(
            session,
            email=record.get("email"),
            phone=record.get("phone"),
            company_name=company_name,
        )
        if matches:
            buyer_id = matches[0]["id"]
            matched += 1
        else:
            buyer = buyer_service.save_buyer(
                session,
                actor,
                {
                    "company_name": company_name,
                    "contact_person": record.get("contact_person"),
                    "country": record.get("country") or "",
                    "city": record.get("city"),
                    "email": record.get("email"),
                    "phone": record.get("phone"),
                    "website": record.get("website"),
                    "linkedin": record.get("linkedin"),
                    "buyer_type": record.get("buyer_type") or "importer",
                    "source": record.get("source") or provider.code,
                },
                allow_duplicate=True,
            )
            buyer_id = buyer.id
            created_buyers += 1

        lead_service.save_lead(
            session,
            actor,
            {
                "title": f"{company_name} - {record.get('product_interest') or 'enquiry'}",
                "buyer_id": buyer_id,
                "country": record.get("country") or "",
                "source": record.get("source") or provider.code,
                "source_detail": record.get("external_ref") or "",
                "status": "new",
                "temperature": "warm",
                "notes": record.get("message") or "",
            },
        )
        created_leads += 1

    integration_service.append_sync_log(
        session,
        "lead_import",
        provider.code,
        f"{created_leads} lead(s), {created_buyers} new buyer(s), {matched} matched",
    )
    audit_service.record(
        session,
        action="import",
        entity_type="lead",
        summary=f"Lead import via {provider.code}: {created_leads} leads",
        user_id=actor.id,
        username=actor.username,
    )
    return {
        "provider": provider.code,
        "leads": created_leads,
        "buyers": created_buyers,
        "matched": matched,
    }


def backup_database(target: str | Path | None = None) -> str:
    """Copy the SQLite database file to a timestamped backup."""
    import shutil

    source = PATHS.database_file
    if not source.exists():
        raise ValidationError("Database file not found", key="error.file_missing")
    if target is None:
        folder = PATHS.exports_dir / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"exportflow-{now().strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(source, target)
    log.info("Database backup written")
    return str(target)


def restore_database(source: str | Path) -> str:
    """Replace the working database with a backup copy."""
    import shutil

    from app.database.engine import reset_engine

    path = Path(source)
    if not path.exists():
        raise ValidationError("Backup file not found", key="error.file_missing")
    reset_engine()
    shutil.copy2(path, PATHS.database_file)
    log.info("Database restored from backup")
    return str(PATHS.database_file)


def parse_import_date(value) -> object:
    """Helper used by import routines to accept several date formats."""
    if hasattr(value, "date"):
        return value.date()
    return parse_date(str(value) if value is not None else "")
