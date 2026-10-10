import json

import httpx
import pytest

from omborai_desktop.api import ApiClient, ApiError

ACCESS_1 = "access-1"
ACCESS_2 = "access-2"


def _tokens(access: str, refresh: str) -> dict:
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "expires_in": 900}


def _client(handler) -> ApiClient:
    return ApiClient("http://api.test", transport=httpx.MockTransport(handler))


def test_login_stores_tokens_and_sends_bearer():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/auth/login":
            return httpx.Response(200, json=_tokens(ACCESS_1, "r1"))
        seen.append(request.headers["authorization"])
        return httpx.Response(
            200, json={"id": "u", "email": "a@b.uz", "full_name": "A", "tenant_id": "t", "memberships": []}
        )

    api = _client(handler)
    api.login("a@b.uz", "parol-12345")
    api.me()
    assert seen == [f"Bearer {ACCESS_1}"]


def test_expired_access_token_is_refreshed_once_and_request_retried():
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.headers.get("authorization", "")))
        if request.url.path == "/v1/auth/login":
            return httpx.Response(200, json=_tokens(ACCESS_1, "r1"))
        if request.url.path == "/v1/auth/refresh":
            return httpx.Response(200, json=_tokens(ACCESS_2, "r2"))
        if request.headers.get("authorization") == f"Bearer {ACCESS_1}":
            return httpx.Response(401, json={"title": "Token muddati tugagan"})
        return httpx.Response(200, json=[])

    api = _client(handler)
    api.login("a@b.uz", "parol-12345")
    assert api.stores() == []
    paths = [p for p, _ in calls]
    assert paths == ["/v1/auth/login", "/v1/stores", "/v1/auth/refresh", "/v1/stores"]


def test_problem_json_error_is_mapped_to_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"title": "Qoldiq yetarli emas", "detail": "Joriy qoldiq: 1", "status": 409},
            headers={"content-type": "application/problem+json"},
        )

    api = _client(handler)
    api._access = "x"  # noqa: SLF001 - test uchun token
    with pytest.raises(ApiError) as info:
        api.create_sale({"id": "x"})
    assert info.value.status == 409
    assert info.value.message == "Qoldiq yetarli emas: Joriy qoldiq: 1"


def test_no_open_shift_returns_none():
    api = _client(lambda r: httpx.Response(409, json={"title": "Smena ochilmagan"}))
    api._access = "x"  # noqa: SLF001
    assert api.current_shift("store") is None


def test_unknown_barcode_returns_none():
    api = _client(lambda r: httpx.Response(404, json={"title": "Tovar topilmadi"}))
    api._access = "x"  # noqa: SLF001
    assert api.product_by_barcode("0000", "store") is None


def test_create_sale_sends_only_ids_and_quantities():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": captured["body"]["id"], "number": 1})

    api = _client(handler)
    api._access = "x"  # noqa: SLF001
    api.create_sale(
        {
            "id": "s1",
            "store_id": "st",
            "items": [{"product_id": "p", "qty": "2"}],
            "discount": 0,
            "payments": [{"method": "cash", "amount": 10}],
        }
    )
    assert "unit_price" not in captured["body"]["items"][0]
    assert captured["body"]["items"] == [{"product_id": "p", "qty": "2"}]
