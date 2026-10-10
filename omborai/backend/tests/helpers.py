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
