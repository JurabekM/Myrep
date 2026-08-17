"""Catalog composition and export to PDF, static HTML and ZIP."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import PATHS
from app.models import Catalog, CatalogItem, Certificate, Product
from app.reports import build_catalog_pdf, build_html_catalog, zip_catalog
from app.services import audit_service, company_service, product_service
from app.services.auth_service import CurrentUser
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import fmt_money, now, slugify


def list_catalogs(session: Session, include_archived: bool = False) -> list[dict]:
    """Catalogs with their product counts."""
    stmt = select(Catalog)
    if not include_archived:
        stmt = stmt.where(Catalog.is_archived.is_(False))
    rows = session.scalars(stmt.order_by(Catalog.id.desc())).unique().all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "language": row.language,
            "version": row.version,
            "subtitle": row.subtitle or "",
            "template": row.template,
            "items": len(row.items),
            "include_certificates": bool(row.include_certificates),
            "include_prices": bool(row.include_prices),
            "last_export_path": row.last_export_path or "",
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


def get_catalog(session: Session, catalog_id: int) -> Catalog:
    """Fetch a catalog or raise :class:`NotFoundError`."""
    catalog = session.get(Catalog, catalog_id)
    if catalog is None:
        raise NotFoundError("Catalog not found")
    return catalog


def catalog_dict(session: Session, catalog_id: int) -> dict:
    """Catalog payload for the editor (metadata plus selected product ids)."""
    catalog = get_catalog(session, catalog_id)
    data = {c.name: getattr(catalog, c.name) for c in Catalog.__table__.columns}
    data["product_ids"] = [item.product_id for item in catalog.items]
    data["highlights"] = {item.product_id: item.highlight or "" for item in catalog.items}
    return data


def save_catalog(
    session: Session, actor: CurrentUser, values: dict, product_ids: list[int] | None = None
) -> Catalog:
    """Create or update a catalog and its product selection."""
    actor.require("catalog.edit")
    title = (values.get("title") or "").strip()
    if not title:
        raise ValidationError("Catalog title is required", key="error.title_required")
    catalog_id = values.get("id")
    if catalog_id:
        catalog = get_catalog(session, catalog_id)
        action = "update"
    else:
        catalog = Catalog(title=title)
        session.add(catalog)
        action = "create"

    for key in (
        "title",
        "language",
        "version",
        "subtitle",
        "cover_note",
        "about_text",
        "contact_text",
        "include_certificates",
        "include_prices",
        "template",
    ):
        if key in values:
            setattr(catalog, key, values[key])
    session.flush()

    if product_ids is not None:
        for item in list(catalog.items):
            session.delete(item)
        session.flush()
        for order, product_id in enumerate(product_ids):
            session.add(CatalogItem(catalog_id=catalog.id, product_id=product_id, sort_order=order))
        session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="catalog",
        entity_id=catalog.id,
        summary=f"Catalog '{catalog.title}' {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    return catalog


def duplicate_catalog(session: Session, actor: CurrentUser, catalog_id: int) -> Catalog:
    """Create a new version of an existing catalog."""
    actor.require("catalog.edit")
    source = get_catalog(session, catalog_id)
    try:
        version = f"{float(source.version) + 0.1:.1f}"
    except ValueError:
        version = f"{source.version}-copy"
    clone = Catalog(
        title=source.title,
        language=source.language,
        version=version,
        subtitle=source.subtitle,
        cover_note=source.cover_note,
        about_text=source.about_text,
        contact_text=source.contact_text,
        include_certificates=source.include_certificates,
        include_prices=source.include_prices,
        template=source.template,
    )
    session.add(clone)
    session.flush()
    for item in source.items:
        session.add(
            CatalogItem(
                catalog_id=clone.id,
                product_id=item.product_id,
                sort_order=item.sort_order,
                highlight=item.highlight,
            )
        )
    session.flush()
    return clone


def archive_catalog(session: Session, actor: CurrentUser, catalog_id: int) -> None:
    """Soft delete a catalog."""
    actor.require("catalog.edit")
    catalog = get_catalog(session, catalog_id)
    catalog.is_archived = True
    session.flush()


def build_payload(session: Session, catalog_id: int) -> dict:
    """Assemble the full render payload used by every export format."""
    catalog = get_catalog(session, catalog_id)
    lang = catalog.language or "en"
    payload = {
        "title": catalog.title,
        "subtitle": catalog.subtitle,
        "version": catalog.version,
        "language": lang,
        "cover_note": catalog.cover_note,
        "about_text": catalog.about_text,
        "contact_text": catalog.contact_text,
        "include_certificates": bool(catalog.include_certificates),
        "include_prices": bool(catalog.include_prices),
        "template": catalog.template,
        "products": [],
        "certificates": [],
    }

    cert_names: set[str] = set()
    for item in sorted(catalog.items, key=lambda i: i.sort_order):
        product = session.get(Product, item.product_id)
        if product is None or product.is_archived:
            continue
        certificates = session.scalars(
            select(Certificate).where(
                Certificate.product_id == product.id, Certificate.is_archived.is_(False)
            )
        ).all()
        photos = [media.file_path for media in product.media if media.kind == "image"]
        primary = [media.file_path for media in product.media if media.is_primary]
        if primary:
            photos = primary + [path for path in photos if path not in primary]

        price_text = ""
        if catalog.include_prices:
            prices = product_service.valid_prices_for_product(session, product.id)
            if prices:
                price = prices[0]
                price_text = (
                    f"{fmt_money(price.unit_price, price.currency)} "
                    f"{price.custom_incoterm or price.incoterm} {price.origin_point or ''}".strip()
                )

        payload["products"].append(
            {
                "id": product.id,
                "sku": product.sku,
                "slug": slugify(f"{product.sku}-{product.display_name(lang)}"),
                "name": product.display_name(lang),
                "short_description": getattr(product, f"short_desc_{lang}", None)
                or product.short_desc_en
                or "",
                "description": getattr(product, f"full_desc_{lang}", None)
                or product.full_desc_en
                or getattr(product, f"short_desc_{lang}", None)
                or product.short_desc_en
                or "",
                "hs_code": product.hs_code,
                "origin_country": product.origin_country,
                "moq": product.moq,
                "unit": product.unit,
                "lead_time_days": product.lead_time_days,
                "capacity_month": product.capacity_month,
                "packaging_type": product.packaging_type,
                "net_weight": product.net_weight,
                "gross_weight": product.gross_weight,
                "shelf_life": product.shelf_life,
                "storage_condition": product.storage_condition,
                "price_text": price_text,
                "photo": photos[0] if photos else None,
                "photos": photos,
                "highlight": item.highlight or "",
                "certificates": [cert.name for cert in certificates],
                "specifications": [
                    {
                        "name": getattr(spec, f"name_{lang}", None) or spec.name_en,
                        "value": getattr(spec, f"value_{lang}", None) or spec.value_en,
                    }
                    for spec in sorted(product.specifications, key=lambda s: s.sort_order)
                    if (getattr(spec, f"name_{lang}", None) or spec.name_en)
                ],
            }
        )
        for cert in certificates:
            if cert.name in cert_names:
                continue
            cert_names.add(cert.name)
            payload["certificates"].append(
                {
                    "name": cert.name,
                    "issuer": cert.issuer,
                    "expiry_date": (
                        cert.expiry_date.strftime("%d.%m.%Y") if cert.expiry_date else ""
                    ),
                }
            )
    return payload


def _export_dir(catalog: Catalog) -> Path:
    stamp = now().strftime("%Y%m%d-%H%M%S")
    folder = PATHS.exports_dir / "catalogs" / f"{slugify(catalog.title)}-{catalog.version}-{stamp}"
    folder.parent.mkdir(parents=True, exist_ok=True)
    return folder


def export_pdf(
    session: Session, actor: CurrentUser, catalog_id: int, target: str | Path | None = None
) -> str:
    """Export the catalog as a PDF file."""
    actor.require("catalog.export")
    catalog = get_catalog(session, catalog_id)
    payload = build_payload(session, catalog_id)
    company = company_service.company_dict(session)
    if target is None:
        # The folder name contains dots (version numbers), so build the file
        # name by appending the extension instead of using ``with_suffix``.
        target = Path(f"{_export_dir(catalog)}.pdf")
    path = build_catalog_pdf(target, payload, company)
    catalog.last_export_path = path
    session.flush()
    audit_service.record(
        session,
        action="export",
        entity_type="catalog",
        entity_id=catalog.id,
        summary=f"Catalog '{catalog.title}' exported to PDF",
        details={"path": path},
        user_id=actor.id,
        username=actor.username,
    )
    return path


def export_html(
    session: Session, actor: CurrentUser, catalog_id: int, target: str | Path | None = None
) -> str:
    """Export the catalog as a static, backend-free HTML site."""
    actor.require("catalog.export")
    catalog = get_catalog(session, catalog_id)
    payload = build_payload(session, catalog_id)
    company = company_service.company_dict(session)
    if target is None:
        target = _export_dir(catalog)
    path = build_html_catalog(target, payload, company)
    catalog.last_export_path = path
    session.flush()
    audit_service.record(
        session,
        action="export",
        entity_type="catalog",
        entity_id=catalog.id,
        summary=f"Catalog '{catalog.title}' exported to static HTML",
        details={"path": path},
        user_id=actor.id,
        username=actor.username,
    )
    return path


def export_zip(
    session: Session, actor: CurrentUser, catalog_id: int, target: str | Path | None = None
) -> str:
    """Export the static catalog and package it as a ZIP archive."""
    actor.require("catalog.export")
    catalog = get_catalog(session, catalog_id)
    html_dir = export_html(session, actor, catalog_id)
    if target is None:
        target = Path(f"{html_dir}.zip")
    path = zip_catalog(html_dir, target)
    catalog.last_export_path = path
    session.flush()
    return path


def preview_text(session: Session, catalog_id: int) -> str:
    """Plain-text preview shown inside the catalog editor."""
    payload = build_payload(session, catalog_id)
    lines = [
        f"{payload['title']} (v{payload['version']}, {payload['language'].upper()})",
        payload.get("subtitle") or "",
        "",
        f"Products: {len(payload['products'])}",
        "",
    ]
    for index, product in enumerate(payload["products"], 1):
        lines.append(f"{index}. [{product['sku']}] {product['name']}")
        if product["short_description"]:
            lines.append(f"    {product['short_description'][:140]}")
        details = []
        if product["moq"]:
            details.append(f"MOQ {product['moq']:g} {product['unit']}")
        if product["hs_code"]:
            details.append(f"HS {product['hs_code']}")
        if product["certificates"]:
            details.append("Cert: " + ", ".join(product["certificates"]))
        if product["price_text"]:
            details.append(product["price_text"])
        if details:
            lines.append("    " + " · ".join(details))
        lines.append("")
    return "\n".join(lines)
