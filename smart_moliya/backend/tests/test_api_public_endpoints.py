from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_banks_returns_8_banks_without_auth():
    response = client.get("/api/v1/banks")
    assert response.status_code == 200
    banks = response.json()
    assert len(banks) == 8
    assert {"code", "name"} <= banks[0].keys()


def test_badge_catalog_is_public_and_matches_service_catalog():
    from app.services.badges import BADGE_CATALOG

    response = client.get("/api/v1/gamification/badges")
    assert response.status_code == 200
    badges = response.json()
    assert len(badges) == len(BADGE_CATALOG)
    codes = {b["code"] for b in badges}
    assert codes == set(BADGE_CATALOG.keys())


def test_protected_endpoint_without_token_returns_401():
    response = client.get("/api/v1/wallets")
    assert response.status_code == 401


def test_protected_endpoint_with_garbage_token_returns_401():
    response = client.get("/api/v1/wallets", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_register_rejects_short_password():
    response = client.post(
        "/api/v1/auth/register",
        json={"phone": "+998901234567", "password": "123", "full_name": "Test User"},
    )
    assert response.status_code == 422


def test_openapi_schema_is_served():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Smart Moliya API"
    # 10-bosqichda qo'shilgan barcha router'lar OpenAPI sxemasida ko'rinishi kerak
    paths = schema["paths"].keys()
    assert any(p.startswith("/api/v1/gamification") for p in paths)
    assert any(p.startswith("/api/v1/challenges") for p in paths)
    assert any(p.startswith("/api/v1/family") for p in paths)
    assert any(p.startswith("/api/v1/payments") for p in paths)
    assert any(p.startswith("/api/v1/reports") for p in paths)
