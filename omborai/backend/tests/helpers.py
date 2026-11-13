from httpx import AsyncClient

PASSWORD = "parol-12345"


async def register(
    client: AsyncClient, email: str, tenant: str = "Test do'kon", store: str = "Asosiy filial"
):
    resp = await client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Test Egasi",
            "tenant_name": tenant,
            "store_name": store,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def bearer(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def add_member(
    owner_url: str, tenant_id: str, email: str, role: str, store_id: str | None = None
) -> None:
    """Xodimni egasi nomidan bevosita bazaga qo'shadi (taklif oqimi keyingi fazada)."""
    import uuid

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.security import hash_password

    engine = create_async_engine(owner_url)
    async with engine.begin() as conn:
        user_id = str(uuid.uuid4())
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, version) "
                "VALUES (:id, :email, :ph, 'Xodim', 1)"
            ),
            {"id": user_id, "email": email, "ph": hash_password(PASSWORD)},
        )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, tenant_id, user_id, store_id, role, version) "
                "VALUES (gen_random_uuid(), :t, :u, :s, :r, 1)"
            ),
            {"t": tenant_id, "u": user_id, "s": store_id, "r": role},
        )
    await engine.dispose()


async def first_store_id(client, tokens: dict) -> str:
    resp = await client.get("/v1/stores", headers=bearer(tokens))
    return resp.json()[0]["id"]
