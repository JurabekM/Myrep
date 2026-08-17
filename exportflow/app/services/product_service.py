"""Product information management and Incoterm pricing rules."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Certificate,
    Product,
    ProductCategory,
    ProductMedia,
    ProductPrice,
    ProductSpecification,
    ProductVariant,
)
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.enums import PORT_REQUIRED_INCOTERMS
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import today


# ---------------------------------------------------------------- categories
def list_categories(session: Session, include_archived: bool = False) -> list[dict]:
    """Return categories with their parent name resolved."""
    stmt = select(ProductCategory).order_by(ProductCategory.name_en)
    if not include_archived:
        stmt = stmt.where(ProductCategory.is_archived.is_(False))
    rows = session.scalars(stmt).unique().all()
    by_id = {row.id: row for row in rows}
    return [
        {
            "id": row.id,
            "code": row.code,
            "name_uz": row.name_uz,
            "name_ru": row.name_ru,
            "name_en": row.name_en,
            "parent_id": row.parent_id,
            "parent_name": by_id[row.parent_id].name_en if row.parent_id in by_id else "",
        }
        for row in rows
    ]


def save_category(session: Session, actor: CurrentUser, values: dict) -> ProductCategory:
    """Create or update a product category."""
    actor.require("product.edit")
    category_id = values.get("id")
    if category_id:
        category = session.get(ProductCategory, category_id)
        if category is None:
            raise NotFoundError("Category not found")
    else:
        category = ProductCategory(code=values.get("code") or "cat", name_uz="")
        session.add(category)
    for key in ("code", "name_uz", "name_ru", "name_en", "parent_id"):
        if key in values:
            setattr(category, key, values[key])
    if not category.name_en:
        category.name_en = category.name_uz
    session.flush()
    audit_service.record(
        session,
        action="update" if category_id else "create",
        entity_type="product_category",
        entity_id=category.id,
        summary=f"Category {category.name_en}",
        user_id=actor.id,
        username=actor.username,
    )
    return category


# ------------------------------------------------------------------ products
def _product_row(product: Product, certificate_count: int, price_count: int, lang: str) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.display_name(lang),
        "name_uz": product.name_uz,
        "name_ru": product.name_ru,
        "name_en": product.name_en,
        "category_id": product.category_id,
        "category": product.category.display_name(lang) if product.category else "",
        "brand": product.brand or "",
        "status": product.status,
        "hs_code": product.hs_code or "",
        "moq": product.moq,
        "unit": product.unit,
        "lead_time_days": product.lead_time_days,
        "certificates": certificate_count,
        "prices": price_count,
        "export_ready": product.export_ready,
        "is_archived": product.is_archived,
        "updated_at": product.updated_at,
    }


def search_products(
    session: Session,
    *,
    text: str = "",
    category_id: int | None = None,
    status: str | None = None,
    has_certificate: bool | None = None,
    export_ready: bool | None = None,
    min_moq: float | None = None,
    max_moq: float | None = None,
    include_archived: bool = False,
    lang: str = "en",
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Filtered product list used by the products page."""
    stmt = select(Product)
    if not include_archived:
        stmt = stmt.where(Product.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                Product.sku.ilike(pattern),
                Product.name_en.ilike(pattern),
                Product.name_ru.ilike(pattern),
                Product.name_uz.ilike(pattern),
                Product.hs_code.ilike(pattern),
                Product.tags.ilike(pattern),
            )
        )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if status:
        stmt = stmt.where(Product.status == status)
    if export_ready is not None:
        stmt = stmt.where(Product.export_ready.is_(export_ready))
    if min_moq is not None:
        stmt = stmt.where(Product.moq >= min_moq)
    if max_moq is not None:
        stmt = stmt.where(Product.moq <= max_moq)
    stmt = stmt.order_by(Product.sku)
    if limit:
        stmt = stmt.limit(limit).offset(offset)

    products = list(session.scalars(stmt).unique())
    if not products:
        return []
    ids = [p.id for p in products]

    cert_counts = dict(
        session.execute(
            select(Certificate.product_id, func.count(Certificate.id))
            .where(Certificate.product_id.in_(ids), Certificate.is_archived.is_(False))
            .group_by(Certificate.product_id)
        ).all()
    )
    price_counts = dict(
        session.execute(
            select(ProductPrice.product_id, func.count(ProductPrice.id))
            .where(ProductPrice.product_id.in_(ids), ProductPrice.is_archived.is_(False))
            .group_by(ProductPrice.product_id)
        ).all()
    )

    rows = [
        _product_row(p, int(cert_counts.get(p.id, 0)), int(price_counts.get(p.id, 0)), lang)
        for p in products
    ]
    if has_certificate is True:
        rows = [row for row in rows if row["certificates"] > 0]
    elif has_certificate is False:
        rows = [row for row in rows if row["certificates"] == 0]
    return rows


def get_product(session: Session, product_id: int) -> Product:
    """Fetch a product or raise :class:`NotFoundError`."""
    product = session.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    return product


def product_dict(session: Session, product_id: int) -> dict:
    """Full product payload used by the detail editor."""
    product = get_product(session, product_id)
    data: dict[str, Any] = {
        column.name: getattr(product, column.name) for column in Product.__table__.columns
    }
    data["specifications"] = [
        {
            "id": spec.id,
            "name_en": spec.name_en,
            "name_ru": spec.name_ru,
            "name_uz": spec.name_uz,
            "value_en": spec.value_en,
            "value_ru": spec.value_ru,
            "value_uz": spec.value_uz,
        }
        for spec in sorted(product.specifications, key=lambda s: s.sort_order)
    ]
    data["variants"] = [
        {
            "id": v.id,
            "name": v.name,
            "sku_suffix": v.sku_suffix,
            "attribute": v.attribute,
            "value": v.value,
            "extra_price": v.extra_price,
            "moq": v.moq,
        }
        for v in product.variants
        if not v.is_archived
    ]
    data["media"] = [
        {
            "id": m.id,
            "kind": m.kind,
            "file_path": m.file_path,
            "title": m.title,
            "is_primary": m.is_primary,
        }
        for m in sorted(product.media, key=lambda m: (not m.is_primary, m.sort_order))
    ]
    data["prices"] = list_prices(session, product_id)
    data["certificates"] = [
        {
            "id": c.id,
            "name": c.name,
            "cert_type": c.cert_type,
            "expiry_date": c.expiry_date,
            "status": c.status,
        }
        for c in session.scalars(
            select(Certificate).where(
                Certificate.product_id == product_id, Certificate.is_archived.is_(False)
            )
        ).all()
    ]
    return data


def save_product(session: Session, actor: CurrentUser, values: dict) -> Product:
    """Create or update a product from a flat value dictionary."""
    actor.require("product.edit")
    sku = (values.get("sku") or "").strip()
    if not sku:
        raise ValidationError("SKU is required", key="error.sku_required")
    product_id = values.get("id")

    duplicate = session.scalar(
        select(Product).where(
            func.lower(Product.sku) == sku.lower(), Product.id != (product_id or 0)
        )
    )
    if duplicate is not None:
        raise ValidationError("SKU already exists", key="error.sku_duplicate")

    if product_id:
        product = get_product(session, product_id)
        action = "update"
    else:
        product = Product(sku=sku)
        session.add(product)
        action = "create"

    editable = {c.name for c in Product.__table__.columns} - {
        "id",
        "created_at",
        "updated_at",
        "created_by_id",
        "updated_by_id",
        "is_archived",
        "archived_at",
    }
    for key, value in values.items():
        if key in editable:
            setattr(product, key, value)
    if not product.name_en:
        product.name_en = product.name_uz or product.sku
    product.updated_by_id = actor.id
    session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="product",
        entity_id=product.id,
        summary=f"Product {product.sku} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    audit_service.add_activity(
        session,
        entity_type="product",
        entity_id=product.id,
        kind=action,
        title=f"Product {action}d",
        user_id=actor.id,
    )
    return product


def replace_specifications(session: Session, product_id: int, specs: list[dict]) -> None:
    """Replace the whole specification list of a product."""
    product = get_product(session, product_id)
    for spec in list(product.specifications):
        session.delete(spec)
    session.flush()
    for order, spec in enumerate(specs):
        session.add(
            ProductSpecification(
                product_id=product_id,
                name_en=spec.get("name_en") or "",
                name_ru=spec.get("name_ru"),
                name_uz=spec.get("name_uz"),
                value_en=spec.get("value_en") or "",
                value_ru=spec.get("value_ru"),
                value_uz=spec.get("value_uz"),
                sort_order=order,
            )
        )
    session.flush()


def replace_variants(session: Session, product_id: int, variants: list[dict]) -> None:
    """Replace the variant list of a product."""
    product = get_product(session, product_id)
    for variant in list(product.variants):
        session.delete(variant)
    session.flush()
    for variant in variants:
        session.add(
            ProductVariant(
                product_id=product_id,
                name=variant.get("name") or "",
                sku_suffix=variant.get("sku_suffix") or "",
                attribute=variant.get("attribute"),
                value=variant.get("value"),
                extra_price=float(variant.get("extra_price") or 0),
                moq=variant.get("moq"),
            )
        )
    session.flush()


def add_media(
    session: Session, product_id: int, file_path: str, kind: str = "image", title: str = ""
) -> ProductMedia:
    """Attach a media file to a product."""
    product = get_product(session, product_id)
    is_primary = not any(m.is_primary for m in product.media) and kind == "image"
    media = ProductMedia(
        product_id=product_id,
        kind=kind,
        file_path=file_path,
        title=title or None,
        is_primary=is_primary,
        sort_order=len(product.media),
    )
    session.add(media)
    session.flush()
    return media


def remove_media(session: Session, media_id: int) -> None:
    """Detach a media file from its product."""
    media = session.get(ProductMedia, media_id)
    if media is not None:
        session.delete(media)
        session.flush()


def set_primary_media(session: Session, media_id: int) -> None:
    """Mark one image as the product's primary photo."""
    media = session.get(ProductMedia, media_id)
    if media is None:
        return
    for sibling in media.product.media:
        sibling.is_primary = sibling.id == media_id
    session.flush()


def archive_products(
    session: Session, actor: CurrentUser, product_ids: list[int], reason: str = ""
) -> int:
    """Bulk archive products (soft delete)."""
    actor.require("product.archive")
    count = 0
    for product_id in product_ids:
        product = session.get(Product, product_id)
        if product is None or product.is_archived:
            continue
        product.is_archived = True
        product.status = "archived"
        product.archive_reason = reason or None
        count += 1
        audit_service.record(
            session,
            action="archive",
            entity_type="product",
            entity_id=product.id,
            summary=f"Product {product.sku} archived",
            user_id=actor.id,
            username=actor.username,
        )
    session.flush()
    return count


def restore_product(session: Session, actor: CurrentUser, product_id: int) -> None:
    """Restore an archived product back to draft."""
    actor.require("product.archive")
    product = get_product(session, product_id)
    product.is_archived = False
    product.status = "draft"
    session.flush()


# -------------------------------------------------------------------- prices
def list_prices(session: Session, product_id: int, include_archived: bool = False) -> list[dict]:
    """Every price line of a product, newest first."""
    stmt = select(ProductPrice).where(ProductPrice.product_id == product_id)
    if not include_archived:
        stmt = stmt.where(ProductPrice.is_archived.is_(False))
    rows = session.scalars(stmt.order_by(ProductPrice.id.desc())).all()
    return [
        {
            "id": row.id,
            "product_id": row.product_id,
            "incoterm": row.custom_incoterm or row.incoterm,
            "raw_incoterm": row.incoterm,
            "custom_incoterm": row.custom_incoterm,
            "currency": row.currency,
            "origin_point": row.origin_point or "",
            "unit_price": row.unit_price,
            "moq": row.moq,
            "valid_from": row.valid_from,
            "valid_to": row.valid_to,
            "payment_terms": row.payment_terms or "",
            "lead_time_days": row.lead_time_days,
            "status": row.status,
            "notes": row.notes or "",
            "is_valid": is_price_valid(row),
        }
        for row in rows
    ]


def is_price_valid(price: ProductPrice, on_date: dt.date | None = None) -> bool:
    """True when a price is approved and inside its validity window."""
    on_date = on_date or today()
    if price.is_archived or price.status != "approved":
        return False
    if price.valid_from and on_date < price.valid_from:
        return False
    if price.valid_to and on_date > price.valid_to:
        return False
    return True


def validate_price_values(values: dict) -> None:
    """Apply the pricing business rules before persisting."""
    incoterm = values.get("incoterm") or ""
    if not incoterm:
        raise ValidationError("Incoterm is required", key="error.incoterm_required")
    if float(values.get("unit_price") or 0) <= 0:
        raise ValidationError("Unit price must be greater than zero", key="error.price_positive")
    if incoterm in PORT_REQUIRED_INCOTERMS and not (values.get("origin_point") or "").strip():
        raise ValidationError(
            "Port / place of loading is required for this Incoterm",
            key="error.port_required",
            incoterm=incoterm,
        )
    valid_from = values.get("valid_from")
    valid_to = values.get("valid_to")
    if valid_from and valid_to and valid_to < valid_from:
        raise ValidationError("Validity end is before start", key="error.date_range")


def save_price(session: Session, actor: CurrentUser, values: dict) -> ProductPrice:
    """Create or update an Incoterm price line."""
    actor.require("price.edit")
    validate_price_values(values)
    price_id = values.get("id")
    if price_id:
        price = session.get(ProductPrice, price_id)
        if price is None:
            raise NotFoundError("Price not found")
        action = "update"
    else:
        price = ProductPrice(product_id=values["product_id"])
        session.add(price)
        action = "create"

    for key in (
        "product_id",
        "incoterm",
        "custom_incoterm",
        "currency",
        "origin_point",
        "unit_price",
        "moq",
        "valid_from",
        "valid_to",
        "payment_terms",
        "lead_time_days",
        "notes",
    ):
        if key in values:
            setattr(price, key, values[key])

    # Approving a price is a separate, permission-gated action.
    requested_status = values.get("status", price.status or "draft")
    if requested_status == "approved" and price.status != "approved":
        actor.require("price.approve")
    price.status = requested_status
    if price.valid_to and price.valid_to < today():
        price.status = "expired"
    session.flush()

    audit_service.record(
        session,
        action=action,
        entity_type="product_price",
        entity_id=price.id,
        summary=f"Price {price.incoterm} {price.unit_price} {price.currency} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    return price


def approve_price(session: Session, actor: CurrentUser, price_id: int) -> ProductPrice:
    """Approve a draft price so quotations may use it."""
    actor.require("price.approve")
    price = session.get(ProductPrice, price_id)
    if price is None:
        raise NotFoundError("Price not found")
    if price.valid_to and price.valid_to < today():
        raise ValidationError("Cannot approve an expired price", key="error.price_expired")
    price.status = "approved"
    session.flush()
    audit_service.record(
        session,
        action="approve",
        entity_type="product_price",
        entity_id=price.id,
        summary=f"Price approved for product #{price.product_id}",
        user_id=actor.id,
        username=actor.username,
    )
    return price


def archive_price(session: Session, actor: CurrentUser, price_id: int) -> None:
    """Archive a price line."""
    actor.require("price.edit")
    price = session.get(ProductPrice, price_id)
    if price is not None:
        price.is_archived = True
        session.flush()


def valid_prices_for_product(
    session: Session, product_id: int, on_date: dt.date | None = None
) -> list[ProductPrice]:
    """Approved, non-expired prices usable in a quotation."""
    rows = session.scalars(
        select(ProductPrice).where(
            ProductPrice.product_id == product_id,
            ProductPrice.is_archived.is_(False),
            ProductPrice.status == "approved",
        )
    ).all()
    return [row for row in rows if is_price_valid(row, on_date)]


def refresh_expired_prices(session: Session) -> int:
    """Mark approved prices whose validity has passed as ``expired``."""
    rows = session.scalars(
        select(ProductPrice).where(
            ProductPrice.is_archived.is_(False),
            ProductPrice.status == "approved",
            ProductPrice.valid_to.is_not(None),
            ProductPrice.valid_to < today(),
        )
    ).all()
    for row in rows:
        row.status = "expired"
    session.flush()
    return len(rows)


# ------------------------------------------------------------ export readiness
def export_readiness(session: Session, product_id: int) -> dict:
    """Score how ready a product is for export and list what is missing."""
    product = get_product(session, product_id)
    checks: list[tuple[str, bool]] = [
        ("english_name", bool(product.name_en)),
        ("english_description", bool(product.full_desc_en or product.short_desc_en)),
        ("russian_description", bool(product.full_desc_ru or product.short_desc_ru)),
        ("hs_code", bool(product.hs_code)),
        ("moq", bool(product.moq)),
        ("lead_time", bool(product.lead_time_days)),
        ("packaging", bool(product.packaging_type)),
        ("weights", bool(product.net_weight and product.gross_weight)),
        ("photo", any(m.kind == "image" for m in product.media)),
        (
            "certificate",
            bool(
                session.scalar(
                    select(func.count(Certificate.id)).where(
                        Certificate.product_id == product_id,
                        Certificate.is_archived.is_(False),
                    )
                )
            ),
        ),
        ("approved_price", bool(valid_prices_for_product(session, product_id))),
    ]
    passed = [name for name, ok in checks if ok]
    missing = [name for name, ok in checks if not ok]
    score = round(len(passed) * 100.0 / len(checks), 1)
    return {"score": score, "passed": passed, "missing": missing, "total": len(checks)}


def recompute_export_ready(session: Session, product_id: int, threshold: float = 80.0) -> bool:
    """Update the ``export_ready`` flag from the readiness score."""
    result = export_readiness(session, product_id)
    product = get_product(session, product_id)
    product.export_ready = result["score"] >= threshold
    session.flush()
    return product.export_ready
