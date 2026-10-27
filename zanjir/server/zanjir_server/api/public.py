"""Ochiq endpointlar: `/v/{qr_token}` (tekshirish sahifasi), `/v/{qr_token}/pdf`, `/healthz`, `/readyz`, `/metrics`.

Sahifada shaxsiy ma'lumot minimal: imzolovchining F.I.Sh. va tashkiloti (prompt 7-bo'lim). Obyekt manzili, buyurtmachi
va o'lchovlar faqat PDF ichida (protokolning o'zi, QR uni olgan kishiga mo'ljallangan).
"""

from __future__ import annotations

import hmac
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select

from zanjir_server.api.deps import Ctx, fail
from zanjir_server.crypto.protocol import verify_protocol
from zanjir_server.db.models import AppUser, AuditEvent, Device, Organization, Protocol, ProtocolDocument
from zanjir_server.web.i18n import TEXTS

router = APIRouter()
_TOKEN = re.compile(r"^[0-9a-f]{32}$")
_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "web" / "templates"),
    autoescape=select_autoescape(["html"]),
)
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; script-src 'self'; font-src 'self'; "
    "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@dataclass
class PublicProtocol:
    token: str
    number: str
    revoked: bool
    lab: str
    signer: str
    signed_at: str
    payload_sha256: str
    pdf_sha256: str
    signature_ok: bool
    has_pdf: bool


async def load_public(ctx: Ctx, token: str) -> tuple[PublicProtocol, bytes | None] | None:
    if not _TOKEN.fullmatch(token):
        return None
    org_id = await ctx.db.lookup_org("zanjir_org_of_qr", token)
    if org_id is None:
        return None
    async with ctx.db.org_session(org_id) as s:
        p = (await s.execute(select(Protocol).where(Protocol.qr_token == token))).scalar_one_or_none()
        if p is None:
            return None
        org = (await s.execute(select(Organization.name).where(Organization.id == p.org_id))).scalar_one()
        signer = (await s.execute(select(AppUser.full_name).where(AppUser.id == p.signed_by))).scalar_one()
        key = (await s.execute(select(Device.public_key_ed25519).where(Device.id == p.device_id))).scalar_one()
        doc = (
            await s.execute(select(ProtocolDocument).where(ProtocolDocument.protocol_id == p.id))
        ).scalar_one_or_none()
        revoked = (
            await s.execute(
                select(AuditEvent.id).where(
                    AuditEvent.org_id == p.org_id,
                    AuditEvent.entity_id == p.id,
                    AuditEvent.event_type == "PROTOCOL_REVOKED",
                )
            )
        ).first() is not None
    signed_at = ""
    ok = False
    if doc is not None:
        payload = json.loads(doc.payload_json)
        signed_at = str(payload.get("signed_at", ""))[:16].replace("T", " ")
        ok = (
            verify_protocol(
                payload=payload,
                pdf=doc.pdf,
                payload_sha256=p.payload_sha256,
                pdf_sha256=p.pdf_sha256,
                signature_hex=p.signature,
                sig_alg=p.sig_alg,
                public_key_hex=key,
            )
            is None
        )
    info = PublicProtocol(
        token=token,
        number=p.number,
        revoked=revoked,
        lab=org,
        signer=signer,
        signed_at=signed_at,
        payload_sha256=p.payload_sha256,
        pdf_sha256=p.pdf_sha256,
        signature_ok=ok,
        has_pdf=doc is not None,
    )
    return info, (doc.pdf if doc else None)


def _lang(request: Request, lang: str | None) -> str:
    if lang in TEXTS:
        return lang
    accept = request.headers.get("accept-language", "").lower()
    return "ru" if accept.startswith("ru") else "uz"


@router.get("/v/{qr_token}", response_class=HTMLResponse, tags=["public"])
async def verify_page(
    qr_token: str, request: Request, ctx: Ctx, lang: Annotated[str | None, Query(max_length=2)] = None
) -> HTMLResponse:
    found = await load_public(ctx, qr_token)
    code = _lang(request, lang)
    html = _env.get_template("verify.html").render(
        lang=code,
        other_lang="ru" if code == "uz" else "uz",
        t=TEXTS[code],
        p=found[0] if found else None,
    )
    return HTMLResponse(html, status_code=200 if found else 404, headers=SECURITY_HEADERS)


@router.get("/v/{qr_token}/pdf", tags=["public"])
async def verify_pdf(qr_token: str, ctx: Ctx) -> Response:
    found = await load_public(ctx, qr_token)
    if found is None or found[1] is None:
        fail(404, "not_found")
    info, pdf = found
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            **SECURITY_HEADERS,
            "Content-Disposition": f'attachment; filename="ZANJIR-{info.number}.pdf"',
        },
    )


@router.get("/healthz", tags=["ops"])
async def healthz() -> dict[str, str]:
    # Jarayon tirikligi; bazaga murojaat qilmaydi.
    return {"status": "ok"}


@router.get("/readyz", tags=["ops"])
async def readyz(ctx: Ctx) -> dict[str, str]:
    try:
        await ctx.db.ping()
    except Exception:
        fail(503, "database_unavailable")
    return {"status": "ready"}


@router.get("/metrics", tags=["ops"])
async def metrics(request: Request, ctx: Ctx) -> Response:
    """Prometheus — faqat `ZANJIR_METRICS_TOKEN` bilan (berilmasa o'chiq); Caddy ham tashqariga ochmaydi."""
    token = ctx.settings.metrics_token
    if token is None:
        fail(404, "not_found")
    given = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not hmac.compare_digest(given.encode(), token.get_secret_value().encode()):
        fail(401, "metrics_token_required")
    return Response(generate_latest(ctx.metrics.registry), media_type=CONTENT_TYPE_LATEST)
