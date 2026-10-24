import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import get_sessionmaker
from app.security import hash_password
from tests.helpers import PASSWORD, bearer, register


async def _store_names(client, tokens) -> list[str]:
    resp = await client.get("/v1/stores", headers=bearer(tokens))
    assert resp.status_code == 200, resp.text
    return [s["name"] for s in resp.json()]


async def test_stores_are_isolated_per_tenant(client):
    a = await register(client, "a@example.uz", tenant="Do'kon A", store="A-filial")
    b = await register(client, "b@example.uz", tenant="Do'kon B", store="B-filial")

    assert await _store_names(client, a) == ["A-filial"]
    assert await _store_names(client, b) == ["B-filial"]


async def test_owner_can_add_store_only_to_own_tenant(client):
    a = await register(client, "owner-a@example.uz", tenant="Do'kon A", store="A1")
    b = await register(client, "owner-b@example.uz", tenant="Do'kon B", store="B1")

    created = await client.post("/v1/stores", json={"name": "A2"}, headers=bearer(a))
    assert created.status_code == 201

    assert await _store_names(client, a) == ["A1", "A2"]
    assert await _store_names(client, b) == ["B1"]


async def test_cashier_cannot_create_store_but_can_read(client, owner_url):
    owner = await register(client, "boss@example.uz", tenant="Do'kon C", store="C1")
    tenant_id = (await client.get("/v1/me", headers=bearer(owner))).json()["tenant_id"]

    # Kassirni egasi nomidan bevosita bazaga qo'shamiz (taklif oqimi keyingi fazada)
    cashier_id = str(uuid.uuid4())
    engine = create_async_engine(owner_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, version) "
                "VALUES (:id, :email, :ph, 'Kassir', 1)"
            ),
            {"id": cashier_id, "email": "kassir@example.uz", "ph": hash_password(PASSWORD)},
        )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, tenant_id, user_id, store_id, role, version) "
                "VALUES (gen_random_uuid(), :t, :u, NULL, 'cashier', 1)"
            ),
            {"t": tenant_id, "u": cashier_id},
        )
    await engine.dispose()

    login = await client.post("/v1/auth/login", json={"email": "kassir@example.uz", "password": PASSWORD})
    assert login.status_code == 200
    cashier = login.json()

    denied = await client.post("/v1/stores", json={"name": "Ruxsatsiz"}, headers=bearer(cashier))
    assert denied.status_code == 403
    assert denied.headers["content-type"].startswith("application/problem+json")

    assert await _store_names(client, cashier) == ["C1"]


async def test_rls_hides_rows_without_tenant_context(client):
    """Ilova roli filtrsiz so'rov yuborsa ham, kontekst bo'lmasa hech narsa ko'rinmaydi."""
    await register(client, "rls@example.uz", tenant="RLS", store="Yashirin")

    async with get_sessionmaker()() as session:
        count = await session.scalar(text("SELECT count(*) FROM stores"))
    assert count == 0
