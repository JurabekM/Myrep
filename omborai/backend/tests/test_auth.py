from tests.helpers import PASSWORD, bearer, register


async def test_register_creates_tokens(client):
    tokens = await register(client, "egasi@example.uz")
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["expires_in"] == 15 * 60


async def test_register_duplicate_email_returns_problem_json(client):
    await register(client, "dup@example.uz")
    resp = await client.post(
        "/v1/auth/register",
        json={
            "email": "DUP@example.uz",
            "password": PASSWORD,
            "full_name": "Boshqa",
            "tenant_name": "Boshqa do'kon",
            "store_name": "Filial",
        },
    )
    assert resp.status_code == 409
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["status"] == 409


async def test_register_validation_error_is_problem_json(client):
    resp = await client.post(
        "/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "short",
            "full_name": "A",
            "tenant_name": "B",
            "store_name": "C",
        },
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_login_success_and_wrong_password(client):
    await register(client, "login@example.uz")

    ok = await client.post("/v1/auth/login", json={"email": "login@example.uz", "password": PASSWORD})
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    bad = await client.post(
        "/v1/auth/login", json={"email": "login@example.uz", "password": "noto'g'ri-parol"}
    )
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Email yoki parol noto'g'ri"


async def test_login_unknown_email_is_same_error(client):
    resp = await client.post("/v1/auth/login", json={"email": "yoq@example.uz", "password": PASSWORD})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Email yoki parol noto'g'ri"


async def test_me_requires_token(client):
    resp = await client.get("/v1/me")
    assert resp.status_code == 401


async def test_invalid_token_rejected(client):
    resp = await client.get("/v1/me", headers={"Authorization": "Bearer yaroqsiz.token.qiymati"})
    assert resp.status_code == 401


async def test_me_returns_owner_role(client):
    tokens = await register(client, "me@example.uz")
    resp = await client.get("/v1/me", headers=bearer(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.uz"
    assert [m["role"] for m in body["memberships"]] == ["owner"]


async def test_refresh_rotates_and_detects_reuse(client):
    first = await register(client, "rotate@example.uz")

    rotated = await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    second = rotated.json()
    assert second["refresh_token"] != first["refresh_token"]

    # Eski token qayta ishlatilsa — rad etiladi
    reused = await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reused.status_code == 401

    # Reuse aniqlangach, shu oiladagi yangi token ham bekor qilingan bo'lishi kerak
    after = await client.post("/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert after.status_code == 401
