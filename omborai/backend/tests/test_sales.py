import asyncio
import uuid
from decimal import Decimal

from tests.helpers import add_member, bearer, first_store_id, register

PRICE = 14500


async def _setup(client, email: str, *, opening_cash: int = 0, stock: str = "10"):
    tokens = await register(client, email)
    store_id = await first_store_id(client, tokens)
    product = (
        await client.post(
            "/v1/products",
            json={"name": "Shakar 1 kg", "unit": "kg", "sale_price": PRICE, "barcodes": ["4780012300017"]},
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
    shift = await client.post(
        "/v1/shifts", json={"store_id": store_id, "opening_cash": opening_cash}, headers=bearer(tokens)
    )
    assert shift.status_code == 201, shift.text
    return tokens, store_id, product["id"]


def _sale(store_id: str, product_id: str, *, qty: str = "2", payments=None, discount: int = 0, sale_id=None):
    payments = payments if payments is not None else [{"method": "cash", "amount": PRICE * float(qty)}]
    return {
        "id": str(sale_id or uuid.uuid4()),
        "store_id": store_id,
        "items": [{"product_id": product_id, "qty": qty}],
        "discount": discount,
        "payments": payments,
    }


async def _balance(client, tokens, store_id, product_id) -> Decimal:
    rows = (await client.get(f"/v1/stock/balances?store_id={store_id}", headers=bearer(tokens))).json()
    return Decimal(next(r for r in rows if r["product_id"] == product_id)["qty"])


async def test_sale_requires_open_shift(client):
    tokens = await register(client, "smenasiz@example.uz")
    store_id = await first_store_id(client, tokens)
    product = (
        await client.post("/v1/products", json={"name": "Non", "sale_price": 4000}, headers=bearer(tokens))
    ).json()
    resp = await client.post(
        "/v1/sales", json=_sale(store_id, product["id"], qty="1"), headers=bearer(tokens)
    )
    assert resp.status_code == 409
    assert resp.json()["title"] == "Smena ochilmagan"


async def test_server_side_pricing_and_stock_decrease(client):
    tokens, store_id, product_id = await _setup(client, "narx@example.uz")
    body = _sale(store_id, product_id, qty="2")
    body["items"][0]["unit_price"] = 1  # klient narxni yuborsa ham e'tiborga olinmaydi
    resp = await client.post("/v1/sales", json=body, headers=bearer(tokens))

    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert sale["total"] == PRICE * 2
    assert sale["items"][0]["unit_price"] == PRICE
    assert sale["number"] > 0
    assert await _balance(client, tokens, store_id, product_id) == Decimal(8)


async def test_payment_mismatch_is_rejected_without_side_effects(client):
    tokens, store_id, product_id = await _setup(client, "tolov@example.uz")
    bad = _sale(store_id, product_id, qty="2", payments=[{"method": "cash", "amount": 1000}])
    resp = await client.post("/v1/sales", json=bad, headers=bearer(tokens))

    assert resp.status_code == 422
    assert (await client.get(f"/v1/sales?store_id={store_id}", headers=bearer(tokens))).json() == []
    assert await _balance(client, tokens, store_id, product_id) == Decimal(10)


async def test_insufficient_stock_rolls_back_whole_sale(client):
    tokens, store_id, product_id = await _setup(client, "yetmaydi@example.uz", stock="1")
    resp = await client.post("/v1/sales", json=_sale(store_id, product_id, qty="3"), headers=bearer(tokens))

    assert resp.status_code == 409
    assert (await client.get(f"/v1/sales?store_id={store_id}", headers=bearer(tokens))).json() == []
    assert await _balance(client, tokens, store_id, product_id) == Decimal(1)


async def test_resubmitting_same_sale_id_is_idempotent(client):
    tokens, store_id, product_id = await _setup(client, "idempotent@example.uz")
    body = _sale(store_id, product_id, qty="1")

    first = await client.post("/v1/sales", json=body, headers=bearer(tokens))
    second = await client.post("/v1/sales", json=body, headers=bearer(tokens))

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["number"] == first.json()["number"]
    assert await _balance(client, tokens, store_id, product_id) == Decimal(9)


async def test_concurrent_duplicate_sale_id_creates_one_sale(client):
    tokens, store_id, product_id = await _setup(client, "parallel-chek@example.uz")
    body = _sale(store_id, product_id, qty="1")

    a, b = await asyncio.gather(
        client.post("/v1/sales", json=body, headers=bearer(tokens)),
        client.post("/v1/sales", json=body, headers=bearer(tokens)),
    )
    assert sorted([a.status_code, b.status_code]) == [200, 201]
    assert await _balance(client, tokens, store_id, product_id) == Decimal(9)
    assert len((await client.get(f"/v1/sales?store_id={store_id}", headers=bearer(tokens))).json()) == 1


async def test_cashier_cannot_discount_but_manager_can(client, owner_url):
    tokens, store_id, product_id = await _setup(client, "chegirma@example.uz")
    me = (await client.get("/v1/me", headers=bearer(tokens))).json()
    await add_member(owner_url, me["tenant_id"], "kassir@example.uz", "cashier")
    cashier = (
        await client.post("/v1/auth/login", json={"email": "kassir@example.uz", "password": "parol-12345"})
    ).json()

    discounted = _sale(
        store_id,
        product_id,
        qty="2",
        discount=1000,
        payments=[{"method": "cash", "amount": PRICE * 2 - 1000}],
    )
    denied = await client.post("/v1/sales", json=discounted, headers=bearer(cashier))
    assert denied.status_code == 403

    allowed = await client.post("/v1/sales", json=discounted, headers=bearer(tokens))
    assert allowed.status_code == 201
    assert allowed.json()["total"] == PRICE * 2 - 1000


async def test_refund_restores_stock_once(client, owner_url):
    tokens, store_id, product_id = await _setup(client, "qaytarish@example.uz")
    sale = (
        await client.post("/v1/sales", json=_sale(store_id, product_id, qty="3"), headers=bearer(tokens))
    ).json()
    assert await _balance(client, tokens, store_id, product_id) == Decimal(7)

    refunded = await client.post(f"/v1/sales/{sale['id']}/refund", headers=bearer(tokens))
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"
    assert await _balance(client, tokens, store_id, product_id) == Decimal(10)

    again = await client.post(f"/v1/sales/{sale['id']}/refund", headers=bearer(tokens))
    assert again.status_code == 409
    assert await _balance(client, tokens, store_id, product_id) == Decimal(10)


async def test_cashier_cannot_refund(client, owner_url):
    tokens, store_id, product_id = await _setup(client, "qaytarmas@example.uz")
    sale = (
        await client.post("/v1/sales", json=_sale(store_id, product_id, qty="1"), headers=bearer(tokens))
    ).json()
    me = (await client.get("/v1/me", headers=bearer(tokens))).json()
    await add_member(owner_url, me["tenant_id"], "kassir2@example.uz", "cashier")
    cashier = (
        await client.post("/v1/auth/login", json={"email": "kassir2@example.uz", "password": "parol-12345"})
    ).json()

    resp = await client.post(f"/v1/sales/{sale['id']}/refund", headers=bearer(cashier))
    assert resp.status_code == 403


async def test_shift_close_summary_and_cash_difference(client):
    tokens, store_id, product_id = await _setup(client, "smena@example.uz", opening_cash=100000)

    cash_sale = await client.post(
        "/v1/sales", json=_sale(store_id, product_id, qty="2"), headers=bearer(tokens)
    )
    assert cash_sale.status_code == 201
    card_sale = await client.post(
        "/v1/sales",
        json=_sale(store_id, product_id, qty="1", payments=[{"method": "card", "amount": PRICE}]),
        headers=bearer(tokens),
    )
    assert card_sale.status_code == 201

    current = (await client.get(f"/v1/shifts/current?store_id={store_id}", headers=bearer(tokens))).json()
    closed = await client.post(
        f"/v1/shifts/{current['id']}/close", json={"closing_cash": 120000}, headers=bearer(tokens)
    )
    assert closed.status_code == 200, closed.text
    summary = closed.json()
    assert summary["sales_count"] == 2
    assert summary["total_sales"] == PRICE * 3
    assert summary["by_method"] == {"cash": PRICE * 2, "card": PRICE}
    assert summary["expected_cash"] == 100000 + PRICE * 2
    assert summary["difference"] == 120000 - (100000 + PRICE * 2)

    # Ochiq smena qolmagan: joriy smena so'rovi 409 qaytaradi
    no_shift = await client.get(f"/v1/shifts/current?store_id={store_id}", headers=bearer(tokens))
    assert no_shift.status_code == 409


async def test_only_one_open_shift_per_store(client):
    tokens = await register(client, "bitta-smena@example.uz")
    store_id = await first_store_id(client, tokens)
    first = await client.post(
        "/v1/shifts", json={"store_id": store_id, "opening_cash": 0}, headers=bearer(tokens)
    )
    second = await client.post(
        "/v1/shifts", json={"store_id": store_id, "opening_cash": 0}, headers=bearer(tokens)
    )
    assert first.status_code == 201
    assert second.status_code == 409


async def test_sale_numbers_increase(client):
    tokens, store_id, product_id = await _setup(client, "raqam@example.uz")
    a = (
        await client.post("/v1/sales", json=_sale(store_id, product_id, qty="1"), headers=bearer(tokens))
    ).json()
    b = (
        await client.post("/v1/sales", json=_sale(store_id, product_id, qty="1"), headers=bearer(tokens))
    ).json()
    assert b["number"] > a["number"]
