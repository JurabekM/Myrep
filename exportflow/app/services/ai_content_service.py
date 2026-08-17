"""AI Content Studio: fact collection, generation and version history.

The service is deliberately strict about facts. Whatever the provider is, it
only ever receives data that exists in the database, and the fact sources are
stored alongside the generated text so a reviewer can verify every claim.
"""

from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.llm.base import GenerationRequest
from app.models import AIGeneration, Buyer, Certificate, Lead, Product, Quotation
from app.services import audit_service, company_service, integration_service, product_service
from app.services.auth_service import CurrentUser
from app.utils.errors import IntegrationError
from app.utils.logging_setup import get_logger

log = get_logger(__name__)


def collect_facts(
    session: Session,
    *,
    product_id: int | None = None,
    buyer_id: int | None = None,
    lead_id: int | None = None,
    quotation_id: int | None = None,
    sender: str = "",
) -> dict:
    """Gather the authoritative facts the generator is allowed to use."""
    facts: dict = {"company": company_service.company_dict(session), "sender": sender}
    facts["company"] = {
        key: value
        for key, value in facts["company"].items()
        if key
        in {
            "name",
            "country",
            "city",
            "phone",
            "email",
            "website",
            "about_en",
            "about_ru",
            "about_uz",
        }
    }

    if product_id:
        product = session.get(Product, product_id)
        if product is not None:
            facts["product"] = {
                "sku": product.sku,
                "name_en": product.name_en,
                "name_ru": product.name_ru,
                "name_uz": product.name_uz,
                "short_desc_en": product.short_desc_en,
                "short_desc_ru": product.short_desc_ru,
                "short_desc_uz": product.short_desc_uz,
                "full_desc_en": product.full_desc_en,
                "full_desc_ru": product.full_desc_ru,
                "full_desc_uz": product.full_desc_uz,
                "hs_code": product.hs_code,
                "origin_country": product.origin_country,
                "moq": product.moq,
                "unit": product.unit,
                "lead_time_days": product.lead_time_days,
                "capacity_month": product.capacity_month,
                "packaging_type": product.packaging_type,
                "shelf_life": product.shelf_life,
                "storage_condition": product.storage_condition,
                "brand": product.brand,
            }
            facts["specifications"] = [
                {
                    "name_en": spec.name_en,
                    "name_ru": spec.name_ru,
                    "name_uz": spec.name_uz,
                    "value_en": spec.value_en,
                    "value_ru": spec.value_ru,
                    "value_uz": spec.value_uz,
                }
                for spec in product.specifications
            ]
            certificates = session.scalars(
                select(Certificate).where(
                    Certificate.product_id == product_id, Certificate.is_archived.is_(False)
                )
            ).all()
            facts["certificates"] = [
                {
                    "name": cert.name,
                    "type": cert.cert_type,
                    "number": cert.number,
                    "expiry_date": str(cert.expiry_date) if cert.expiry_date else None,
                }
                for cert in certificates
            ]
            prices = product_service.valid_prices_for_product(session, product_id)
            if prices:
                price = prices[0]
                facts["price"] = {
                    "incoterm": price.custom_incoterm or price.incoterm,
                    "currency": price.currency,
                    "unit_price": price.unit_price,
                    "origin_point": price.origin_point,
                    "moq": price.moq,
                    "payment_terms": price.payment_terms,
                }

    if buyer_id:
        buyer = session.get(Buyer, buyer_id)
        if buyer is not None:
            facts["buyer"] = {
                "company_name": buyer.company_name,
                "contact_person": buyer.contact_person,
                "country": buyer.country,
                "city": buyer.city,
                "buyer_type": buyer.buyer_type,
                "language": buyer.language,
                "interested_categories": buyer.interested_categories,
                "target_market": buyer.target_market,
            }

    if lead_id:
        lead = session.get(Lead, lead_id)
        if lead is not None:
            facts["lead"] = {
                "title": lead.title,
                "status": lead.status,
                "source": lead.source,
                "incoterm": lead.incoterm,
                "destination": lead.destination,
                "expected_value": lead.expected_value,
                "currency": lead.currency,
                "next_step": lead.next_step,
            }

    if quotation_id:
        quotation = session.get(Quotation, quotation_id)
        if quotation is not None:
            facts["quotation"] = {
                "number": quotation.number,
                "currency": quotation.currency,
                "incoterm": quotation.incoterm,
                "loading_port": quotation.loading_port,
                "destination": quotation.destination,
                "payment_terms": quotation.payment_terms,
                "valid_until": str(quotation.valid_until) if quotation.valid_until else None,
                "grand_total": quotation.grand_total,
                "items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "unit_price": item.unit_price,
                    }
                    for item in quotation.items
                ],
            }
    return facts


def fact_source_lines(facts: dict) -> list[str]:
    """Human-readable list of the facts shown in the right-hand panel."""
    lines: list[str] = []
    product = facts.get("product") or {}
    for key in (
        "sku",
        "hs_code",
        "origin_country",
        "moq",
        "unit",
        "lead_time_days",
        "packaging_type",
    ):
        if product.get(key):
            lines.append(f"product.{key} = {product[key]}")
    price = facts.get("price") or {}
    for key in ("incoterm", "unit_price", "currency", "origin_point"):
        if price.get(key):
            lines.append(f"price.{key} = {price[key]}")
    for cert in facts.get("certificates") or []:
        lines.append(f"certificate = {cert['name']} (exp: {cert.get('expiry_date') or '-'})")
    if not (facts.get("certificates") or []):
        lines.append("certificate = NONE (do not claim certification)")
    buyer = facts.get("buyer") or {}
    for key in ("company_name", "country", "buyer_type"):
        if buyer.get(key):
            lines.append(f"buyer.{key} = {buyer[key]}")
    return lines


def generate(
    session: Session,
    actor: CurrentUser,
    *,
    content_type: str,
    language: str = "en",
    tone: str = "professional",
    instruction: str = "",
    product_id: int | None = None,
    buyer_id: int | None = None,
    lead_id: int | None = None,
    quotation_id: int | None = None,
) -> dict:
    """Generate content and store it in the history table."""
    actor.require("ai.use")
    facts = collect_facts(
        session,
        product_id=product_id,
        buyer_id=buyer_id,
        lead_id=lead_id,
        quotation_id=quotation_id,
        sender=actor.full_name,
    )
    provider = integration_service.build_provider(session, "llm")
    request = GenerationRequest(
        content_type=content_type,
        language=language,
        tone=tone,
        instruction=instruction,
        facts=facts,
    )
    started = time.perf_counter()
    result = provider.generate(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 1)

    if not result.ok:
        # A remote failure must never block the user: fall back to the offline
        # template engine so content generation always produces something.
        from app.integrations.llm.demo_provider import DemoRuleBasedProvider

        log.warning("LLM provider failed (%s), falling back to demo", result.message)
        fallback = DemoRuleBasedProvider()
        result = fallback.generate(request)
        provider_code = f"{provider.code}->demo"
        if not result.ok:
            raise IntegrationError(result.message, key="error.ai_failed")
    else:
        provider_code = provider.code

    record = AIGeneration(
        content_type=content_type,
        language=language,
        tone=tone,
        provider=provider_code,
        product_id=product_id,
        buyer_id=buyer_id,
        lead_id=lead_id,
        quotation_id=quotation_id,
        instruction=instruction or None,
        fact_sources=json.dumps(fact_source_lines(facts), ensure_ascii=False),
        output_text=result.data or "",
        user_id=actor.id,
        duration_ms=duration_ms,
    )
    session.add(record)
    session.flush()

    audit_service.record(
        session,
        action="create",
        entity_type="ai_generation",
        entity_id=record.id,
        summary=f"AI content '{content_type}' generated in {language} via {provider_code}",
        user_id=actor.id,
        username=actor.username,
    )
    return {
        "id": record.id,
        "text": record.output_text,
        "provider": provider_code,
        "is_demo": provider_code.startswith("demo") or provider_code.endswith("demo"),
        "duration_ms": duration_ms,
        "fact_sources": fact_source_lines(facts),
        "facts": facts,
    }


def approve(
    session: Session, actor: CurrentUser, generation_id: int, edited_text: str
) -> AIGeneration:
    """Store the reviewed text and mark the generation as approved."""
    actor.require("ai.use")
    record = session.get(AIGeneration, generation_id)
    if record is None:
        raise IntegrationError("Generation not found", key="error.not_found")
    record.output_text = edited_text
    record.approved = True
    session.flush()
    audit_service.record(
        session,
        action="approve",
        entity_type="ai_generation",
        entity_id=record.id,
        summary=f"AI content '{record.content_type}' approved",
        user_id=actor.id,
        username=actor.username,
    )
    return record


def history(
    session: Session,
    *,
    content_type: str | None = None,
    product_id: int | None = None,
    buyer_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """Recent generations, newest first."""
    stmt = select(AIGeneration).order_by(AIGeneration.id.desc()).limit(limit)
    if content_type:
        stmt = stmt.where(AIGeneration.content_type == content_type)
    if product_id:
        stmt = stmt.where(AIGeneration.product_id == product_id)
    if buyer_id:
        stmt = stmt.where(AIGeneration.buyer_id == buyer_id)
    return [
        {
            "id": row.id,
            "content_type": row.content_type,
            "language": row.language,
            "tone": row.tone,
            "provider": row.provider,
            "created_at": row.created_at,
            "approved": row.approved,
            "text": row.output_text,
            "fact_sources": json.loads(row.fact_sources) if row.fact_sources else [],
        }
        for row in session.scalars(stmt).all()
    ]


def apply_to_product(
    session: Session,
    actor: CurrentUser,
    generation_id: int,
    target_field: str,
) -> Product:
    """Write approved copy back into a product description field."""
    actor.require("product.edit")
    record = session.get(AIGeneration, generation_id)
    if record is None or not record.product_id:
        raise IntegrationError("Generation is not linked to a product", key="error.not_found")
    product = session.get(Product, record.product_id)
    if product is None:
        raise IntegrationError("Product not found", key="error.not_found")
    if not hasattr(product, target_field):
        raise IntegrationError(f"Unknown field '{target_field}'", key="error.validation")
    setattr(product, target_field, record.output_text)
    session.flush()
    audit_service.record(
        session,
        action="update",
        entity_type="product",
        entity_id=product.id,
        summary=f"AI content applied to {target_field}",
        user_id=actor.id,
        username=actor.username,
    )
    return product
