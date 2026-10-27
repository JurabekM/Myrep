"""Ochiq tekshirish sahifasi `/v/{qr_token}`, PDF yuklash, kuzatuv va himoya middleware'lari."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import make_settings
from tests.support.field import rows
from tests.test_sync import Env, env, signable  # noqa: F401 — fixture
from zanjir_server.main import create_app


async def signed(env: Env) -> tuple[dict[str, Any], dict[str, Any], bytes]:  # noqa: F811
    g, ms, inst = await signable(env)
    f = env.field
    payload = f.protocol_payload(g["ses"], ms, [inst])
    ops = f.protocol(g["ses"]["id"], payload)
    await env.ok(ops)
    proto = rows(ops, "protocol")[0]
    pdf = base64.b64decode(rows(ops, "protocol_document")[0]["pdf"])
    return proto, payload, pdf


async def test_verify_page_active_then_revoked(env: Env) -> None:  # noqa: F811
    proto, _, pdf = await signed(env)
    r = await env.api.c.get(f"/v/{proto['qr_token']}")
    assert r.status_code == 200
    html = r.text
    assert proto["number"] in html
    assert proto["payload_sha256"] in html and proto["pdf_sha256"] in html
    assert "Amalda" in html and "Imzo va hash&#39;lar to&#39;g&#39;ri" in html
    assert "Yangi xodim" in html  # imzolovchi (LEAD, taklif bilan qo'shilgan) F.I.Sh.
    assert "Elektrolab" in html
    # Shaxsiy ma'lumot minimal: obyekt manzili, buyurtmachi, telefon sahifada yo'q.
    for secret in ("Manzil 1", "Buyurtmachi", env.users["LEAD"].phone):
        assert secret not in html
    assert "ishlash xavfsiz" not in html.lower()
    assert "Ilova faqat tavsiya beradi" in html
    csp = r.headers["content-security-policy"]
    assert "default-src 'none'" in csp and "script-src 'self'" in csp
    assert r.headers["cache-control"] == "no-store"

    d = await env.api.c.get(f"/v/{proto['qr_token']}/pdf")
    assert d.status_code == 200
    assert d.headers["content-type"] == "application/pdf"
    assert d.content == pdf
    assert proto["number"] in d.headers["content-disposition"]

    # LEAD bekor qiladi (audit hodisasi sync orqali) — sahifa holati o'zgaradi.
    await env.ok([env.field.event("PROTOCOL_REVOKED", proto["id"], {"reason": "Xato"})])
    html = (await env.api.c.get(f"/v/{proto['qr_token']}?lang=ru")).text
    assert "Отозван" in html and 'lang="ru"' in html


async def test_verify_page_language_and_not_found(env: Env) -> None:  # noqa: F811
    proto, _, _ = await signed(env)
    r = await env.api.c.get(f"/v/{proto['qr_token']}", headers={"accept-language": "ru-RU,ru;q=0.9"})
    assert "Проверка протокола" in r.text
    for token in ("0" * 32, "not-a-token", "A" * 32, proto["qr_token"] + "0"):
        r = await env.api.c.get(f"/v/{token}")
        assert r.status_code == 404
        assert 'id="not-found"' in r.text
        assert (await env.api.c.get(f"/v/{token}/pdf")).status_code == 404


async def test_static_assets(env: Env) -> None:  # noqa: F811
    for path in ("/static/verify.js", "/static/verify.css", "/static/NotoSans-Regular.ttf"):
        assert (await env.api.c.get(path)).status_code == 200


def test_bundled_fonts_match_app() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for name in ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"):
        a = (root / "app" / "assets" / "fonts" / name).read_bytes()
        b = (root / "server" / "zanjir_server" / "web" / "static" / name).read_bytes()
        assert a == b, name


async def test_health_ready_metrics(env: Env) -> None:  # noqa: F811
    c = env.api.c
    assert (await c.get("/healthz")).json() == {"status": "ok"}
    assert (await c.get("/readyz")).json() == {"status": "ready"}
    m = (await c.get("/metrics")).text
    assert "zanjir_http_requests_total" in m
    assert 'route="/v/{qr_token}"' not in m or "0" * 32 not in m
    assert (await c.get("/docs")).status_code == 404
    assert (await c.get("/openapi.json")).status_code == 404


async def test_readyz_without_database(app_url: str) -> None:
    url = app_url.rsplit("@", 1)[0] + "@127.0.0.1:1/none"
    app = create_app(make_settings(url))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/readyz")
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "database_unavailable"


async def test_body_limit(app_url: str) -> None:
    app = create_app(make_settings(app_url, max_body_bytes=1000))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/auth/login", content=b"x" * 2000, headers={"content-type": "application/json"})
        assert r.status_code == 413
        assert r.json()["detail"]["code"] == "body_too_large"

        async def chunks() -> Any:
            for _ in range(5):
                yield b"y" * 500

        r = await c.post("/auth/login", content=chunks(), headers={"content-type": "application/json"})
        assert r.status_code == 413
    await app.state.ctx.db.dispose()


async def test_cors_only_configured_origins(app_url: str) -> None:
    app = create_app(make_settings(app_url, cors_origins=["https://zanjir.example"]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        ok = await c.options(
            "/me", headers={"origin": "https://zanjir.example", "access-control-request-method": "GET"}
        )
        bad = await c.options("/me", headers={"origin": "https://evil.example", "access-control-request-method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "https://zanjir.example"
    assert "access-control-allow-origin" not in bad.headers
    await app.state.ctx.db.dispose()


async def test_access_log_has_no_secrets(env: Env, caplog: pytest.LogCaptureFixture) -> None:  # noqa: F811
    proto, _, _ = await signed(env)
    lead = env.users["LEAD"]
    logger = logging.getLogger("zanjir")
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="zanjir"):
            await env.api.c.get(f"/v/{proto['qr_token']}")
            await env.api.c.post("/auth/login", json={"phone": lead.phone, "password": "Juda-maxfiy-parol-1"})
            await env.api.c.get("/me", headers=lead.headers)
    finally:
        logger.propagate = False
    text = "\n".join(json.dumps(getattr(r, "fields", {})) + r.getMessage() for r in caplog.records)
    assert "/v/{qr_token}" in text and "/auth/login" in text
    for secret in (proto["qr_token"], lead.phone, "Juda-maxfiy-parol-1", lead.access):
        assert secret not in text


async def test_unhandled_error_is_reported_without_details(app_url: str) -> None:
    reported: list[str] = []

    class Reporter:
        def report(self, exc: BaseException, *, route: str) -> None:
            reported.append(route)

    app = create_app(make_settings(app_url), reporter=Reporter())

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("ichki tafsilot")

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as c:
        r = await c.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"detail": {"code": "internal_error"}}
    assert "ichki" not in r.text
    assert reported
    await app.state.ctx.db.dispose()
