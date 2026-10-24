import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from tests.helpers import add_member, bearer, first_store_id, register

PRICE = 14500


@pytest.fixture(autouse=True)
def no_horizon(monkeypatch):
    """Testlarda yangi yozuvlar darhol ko'rinsin (ishlab chiqarishda HORIZON = 3 soniya)."""
    monkeypatch.setattr("app.api.sync.HORIZON", timedelta(0))


async def _setup(client, email: str, stock: str = "10"):
    tokens = await register(client, email)
    store_id = await first_store_id(client, tokens)
    product = (
        await client.post(
            "/v1/products",
            json={"name": "Shakar", "unit": "kg", "sale_price": PRICE, "barcodes": ["4780012300017"]},
            headers=bearer(tokens),
        )
    ).json()
    await client.post(
        "/v1/purchases",
        json={
            "store_id": store_id,
            "items": [{"product_id": product["id"], "qty": stock, "unit_cost": 9000}],
        },
        headers=bearer(tokens),
    )
    await client.post("/v1/shifts", json={"store_id": store_id, "opening_cash": 0}, headers=bearer(tokens))
    return tokens, store_id, product["id"]


def _sale_op(store_id: str, product_id: str, qty: str = "2", sale_id: str | None = None) -> dict:
    sid = sale_id or str(uuid.uuid4())
    return {
        "type": "sale",
        "op_id": sid,
        "payload": {
            "id": sid,
            "store_id": store_id,
            "items": [{"product_id": product_id, "qty": qty}],
            "payments": [{"method": "cash", "amount": PRICE * int(float(qty))}],
        },
    }


async def _balance(client, tokens, store_id, product_id) -> Decimal:
    rows = (await client.get(f"/v1/stock/balances?store_id={store_id}", headers=bearer(tokens))).json()
    return Decimal(next(r for r in rows if r["product_id"] == product_id)["qty"])


async def test_sale_op_applies_once_and_repush_is_duplicate(client):
    tokens, store_id, product_id = await _setup(client, "push1@example.uz")
    op = _sale_op(store_id, product_id, qty="2")

    first = (await client.post("/v1/sync/push", json={"ops": [op]}, headers=bearer(tokens))).json()
    again = (await client.post("/v1/sync/push", json={"ops": [op]}, headers=bearer(tokens))).json()

    assert first["results"][0]["status"] == "applied"
    assert first["results"][0]["duplicate"] is False
    assert again["results"][0]["status"] == "applied"
    assert again["results"][0]["duplicate"] is True
    assert await _balance(client, tokens, store_id, product_id) == Decimal(8)


async def test_rejected_op_is_recorded_and_not_reapplied(client):
    tokens, store_id, product_id = await _setup(client, "push2@example.uz", stock="1")
    op = _sale_op(store_id, product_id, qty="3")

    first = (await client.post("/v1/sync/push", json={"ops": [op]}, headers=bearer(tokens))).json()
    again = (await client.post("/v1/sync/push", json={"ops": [op]}, headers=bearer(tokens))).json()

    result = first["results"][0]
    assert result["status"] == "rejected"
    assert result["error_title"] == "Qoldiq yetarli emas"
    assert again["results"][0]["duplicate"] is True
    assert again["results"][0]["status"] == "rejected"
    assert await _balance(client, tokens, store_id, product_id) == Decimal(1)
    assert (await client.get(f"/v1/sales?store_id={store_id}", headers=bearer(tokens))).json() == []


async def test_mixed_batch_isolates_failures(client):
    tokens, store_id, product_id = await _setup(client, "batch@example.uz", stock="5")
    ok_sale = _sale_op(store_id, product_id, qty="1")
    bad_sale = _sale_op(store_id, product_id, qty="100")
    writeoff = {
        "type": "movement",
        "op_id": str(uuid.uuid4()),
        "payload": {"store_id": store_id, "product_id": product_id, "kind": "writeoff", "qty": "1"},
    }

    body = (
        await client.post(
            "/v1/sync/push", json={"ops": [ok_sale, bad_sale, writeoff]}, headers=bearer(tokens)
        )
    ).json()
    assert [r["status"] for r in body["results"]] == ["applied", "rejected", "applied"]
    assert await _balance(client, tokens, store_id, product_id) == Decimal(3)


async def test_viewer_cannot_push_movement(client, owner_url):
    tokens, store_id, product_id = await _setup(client, "role@example.uz")
    me = (await client.get("/v1/me", headers=bearer(tokens))).json()
    await add_member(owner_url, me["tenant_id"], "view@example.uz", "viewer")
    viewer = (
        await client.post("/v1/auth/login", json={"email": "view@example.uz", "password": "parol-12345"})
    ).json()

    op = {
        "type": "movement",
        "op_id": str(uuid.uuid4()),
        "payload": {"store_id": store_id, "product_id": product_id, "kind": "writeoff", "qty": "1"},
    }
    body = (await client.post("/v1/sync/push", json={"ops": [op]}, headers=bearer(viewer))).json()
    assert body["results"][0]["status"] == "rejected"
    assert body["results"][0]["error_title"] == "Ruxsat yo'q"


async def test_sale_op_id_must_match_payload_id(client):
    tokens, store_id, product_id = await _setup(client, "mismatch@example.uz")
    op = _sale_op(store_id, product_id)
    op["op_id"] = str(uuid.uuid4())
    resp = await client.post("/v1/sync/push", json={"ops": [op]}, headers=bearer(tokens))
    assert resp.status_code == 422


async def test_pull_returns_everything_then_only_changes(client):
    tokens, store_id, product_id = await _setup(client, "pull@example.uz")
    await client.post(
        "/v1/sync/push", json={"ops": [_sale_op(store_id, product_id, qty="1")]}, headers=bearer(tokens)
    )

    first = (await client.get(f"/v1/sync/pull?store_id={store_id}", headers=bearer(tokens))).json()
    assert [p["id"] for p in first["products"]] == [product_id]
    assert len(first["movements"]) == 2  # kirim (xarid) + savdo
    assert len(first["sales"]) == 1
    assert first["has_more"] is False

    cursors = first["cursors"]
    query = (
        f"/v1/sync/pull?store_id={store_id}&products_cursor={cursors['products']}"
        f"&movements_cursor={cursors['movements']}&sales_cursor={cursors['sales']}"
    )
    quiet = (await client.get(query, headers=bearer(tokens))).json()
    assert quiet["products"] == [] and quiet["movements"] == [] and quiet["sales"] == []

    new = await client.post(
        "/v1/products", json={"name": "Yangi tovar", "sale_price": 100}, headers=bearer(tokens)
    )
    changed = (await client.get(query, headers=bearer(tokens))).json()
    assert [p["id"] for p in changed["products"]] == [new.json()["id"]]


async def test_pull_pagination_covers_all_rows_once(client):
    tokens = await register(client, "pagin@example.uz")
    store_id = await first_store_id(client, tokens)
    created = set()
    for i in range(5):
        resp = await client.post(
            "/v1/products", json={"name": f"Tovar {i}", "sale_price": 1}, headers=bearer(tokens)
        )
        created.add(resp.json()["id"])

    seen: list[str] = []
    cursor = ""
    for _ in range(10):
        page = (
            await client.get(
                f"/v1/sync/pull?store_id={store_id}&products_cursor={cursor}&limit=2", headers=bearer(tokens)
            )
        ).json()
        seen += [p["id"] for p in page["products"]]
        cursor = page["cursors"]["products"]
        if not page["has_more"]:
            break
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == created


async def test_pull_is_tenant_isolated(client):
    a_tokens, a_store, a_product = await _setup(client, "iso-a@example.uz")
    b_tokens = await register(client, "iso-b@example.uz", tenant="B do'kon", store="B1")
    b_store = await first_store_id(client, b_tokens)

    pulled = (await client.get(f"/v1/sync/pull?store_id={b_store}", headers=bearer(b_tokens))).json()
    assert all(p["id"] != a_product for p in pulled["products"])
    assert pulled["movements"] == [] and pulled["sales"] == []

    # A'ning filialini B so'rovida ko'rib bo'lmaydi
    foreign = await client.get(f"/v1/sync/pull?store_id={a_store}", headers=bearer(b_tokens))
    assert foreign.status_code == 404


async def test_pull_shows_deleted_products_and_refunds(client):
    tokens, store_id, product_id = await _setup(client, "deleted@example.uz")
    sale_id = str(uuid.uuid4())
    await client.post(
        "/v1/sync/push",
        json={"ops": [_sale_op(store_id, product_id, qty="1", sale_id=sale_id)]},
        headers=bearer(tokens),
    )
    base = (await client.get(f"/v1/sync/pull?store_id={store_id}", headers=bearer(tokens))).json()

    await client.post(f"/v1/sales/{sale_id}/refund", headers=bearer(tokens))
    await client.delete(f"/v1/products/{product_id}", headers=bearer(tokens))

    cur = base["cursors"]
    query = f"/v1/sync/pull?store_id={store_id}&products_cursor={cur['products']}&sales_cursor={cur['sales']}"
    delta = (await client.get(query, headers=bearer(tokens))).json()
    assert [p["deleted"] for p in delta["products"]] == [True]
    assert [s["status"] for s in delta["sales"]] == ["refunded"]


async def test_invalid_cursor_is_rejected(client):
    tokens, store_id, _ = await _setup(client, "cursor@example.uz")
    resp = await client.get(f"/v1/sync/pull?store_id={store_id}&products_cursor=%%%", headers=bearer(tokens))
    assert resp.status_code == 422
