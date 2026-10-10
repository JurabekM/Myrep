import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import get_sessionmaker
from tests.helpers import add_member, bearer, first_store_id, register


async def _setup(client, email: str, *, min_stock: float = 0):
    tokens = await register(client, email)
    store_id = await first_store_id(client, tokens)
    resp = await client.post(
        "/v1/products",
        json={
            "name": "Shakar 1 kg",
            "unit": "kg",
            "sale_price": 14500,
            "min_stock": min_stock,
            "barcodes": ["4780012300017"],
        },
        headers=bearer(tokens),
    )
    assert resp.status_code == 201, resp.text
    return tokens, store_id, resp.json()["id"]


async def _balance(client, tokens, store_id, product_id) -> Decimal:
    rows = await client.get(f"/v1/stock/balances?store_id={store_id}", headers=bearer(tokens))
    assert rows.status_code == 200, rows.text
    match = next(r for r in rows.json() if r["product_id"] == product_id)
    return Decimal(match["qty"])


async def _purchase(client, tokens, store_id, product_id, qty: str, cost: int = 8000):
    return await client.post(
        "/v1/purchases",
        json={
            "store_id": store_id,
            "items": [{"product_id": product_id, "qty": qty, "unit_cost": cost}],
        },
        headers=bearer(tokens),
    )


async def test_product_barcode_lookup_and_duplicate_conflict(client):
    tokens, _, product_id = await _setup(client, "katalog@example.uz")

    found = await client.get("/v1/products/by-barcode/4780012300017", headers=bearer(tokens))
    assert found.status_code == 200
    assert found.json()["id"] == product_id
    assert found.json()["barcodes"] == ["4780012300017"]

    missing = await client.get("/v1/products/by-barcode/0000000000000", headers=bearer(tokens))
    assert missing.status_code == 404

    dup = await client.post(
        "/v1/products",
        json={"name": "Boshqa tovar", "sale_price": 1000, "barcodes": ["4780012300017"]},
        headers=bearer(tokens),
    )
    assert dup.status_code == 409


async def test_purchase_increases_balance_and_writeoff_respects_stock(client):
    tokens, store_id, product_id = await _setup(client, "qoldiq@example.uz", min_stock=5)

    bought = await _purchase(client, tokens, store_id, product_id, "10", cost=8000)
    assert bought.status_code == 201, bought.text
    assert bought.json()["total_cost"] == 80000
    assert await _balance(client, tokens, store_id, product_id) == Decimal(10)

    writeoff = await client.post(
        "/v1/stock/movements",
        json={
            "store_id": store_id,
            "product_id": product_id,
            "kind": "writeoff",
            "qty": "3",
            "note": "buzildi",
        },
        headers=bearer(tokens),
    )
    assert writeoff.status_code == 201
    assert await _balance(client, tokens, store_id, product_id) == Decimal(7)

    too_much = await client.post(
        "/v1/stock/movements",
        json={"store_id": store_id, "product_id": product_id, "kind": "writeoff", "qty": "20"},
        headers=bearer(tokens),
    )
    assert too_much.status_code == 409
    assert too_much.json()["title"] == "Qoldiq yetarli emas"
    assert await _balance(client, tokens, store_id, product_id) == Decimal(7)


async def test_low_stock_filter_uses_min_stock(client):
    tokens, store_id, product_id = await _setup(client, "minimal@example.uz", min_stock=5)
    await _purchase(client, tokens, store_id, product_id, "6")

    assert (
        await client.get(f"/v1/stock/balances?store_id={store_id}&low_only=true", headers=bearer(tokens))
    ).json() == []

    await client.post(
        "/v1/stock/movements",
        json={"store_id": store_id, "product_id": product_id, "kind": "writeoff", "qty": "2"},
        headers=bearer(tokens),
    )
    low = (
        await client.get(f"/v1/stock/balances?store_id={store_id}&low_only=true", headers=bearer(tokens))
    ).json()
    assert [r["product_id"] for r in low] == [product_id]
    assert low[0]["low"] is True


async def test_adjustment_accepts_sign_and_ledger_matches_balance(client):
    tokens, store_id, product_id = await _setup(client, "tuzatish@example.uz")
    await _purchase(client, tokens, store_id, product_id, "4.5")

    adj = await client.post(
        "/v1/stock/movements",
        json={
            "store_id": store_id,
            "product_id": product_id,
            "kind": "adjustment",
            "qty": "-1.5",
            "note": "sanash",
        },
        headers=bearer(tokens),
    )
    assert adj.status_code == 201
    assert await _balance(client, tokens, store_id, product_id) == Decimal(3)

    ledger = (
        await client.get(
            f"/v1/stock/movements?store_id={store_id}&product_id={product_id}", headers=bearer(tokens)
        )
    ).json()
    assert sum(Decimal(m["qty"]) for m in ledger) == Decimal(3)
    assert {m["kind"] for m in ledger} == {"receipt", "adjustment"}


async def test_concurrent_writeoffs_cannot_oversell(client):
    """Oxirgi donani ikki so'rov bir vaqtda olmoqchi bo'lsa, faqat bittasi muvaffaqiyatli bo'lishi kerak."""
    tokens, store_id, product_id = await _setup(client, "parallel@example.uz")
    await _purchase(client, tokens, store_id, product_id, "1")

    body = {"store_id": store_id, "product_id": product_id, "kind": "writeoff", "qty": "1"}
    first, second = await asyncio.gather(
        client.post("/v1/stock/movements", json=body, headers=bearer(tokens)),
        client.post("/v1/stock/movements", json=body, headers=bearer(tokens)),
    )
    assert sorted([first.status_code, second.status_code]) == [201, 409]
    assert await _balance(client, tokens, store_id, product_id) == Decimal(0)


async def test_ledger_is_append_only_at_database_level(client):
    tokens, store_id, product_id = await _setup(client, "ledger@example.uz")
    await _purchase(client, tokens, store_id, product_id, "2")

    async with get_sessionmaker()() as session:
        with pytest.raises(DBAPIError, match="permission denied"):
            await session.execute(text("UPDATE stock_movements SET note = 'o''zgartirildi'"))
            await session.commit()


async def test_other_tenant_cannot_see_or_use_product(client):
    a_tokens, a_store, product_id = await _setup(client, "tenant-a@example.uz")
    b_tokens = await register(client, "tenant-b@example.uz", tenant="Do'kon B", store="B-filial")

    assert (await client.get(f"/v1/products/{product_id}", headers=bearer(b_tokens))).status_code == 404
    assert (await client.get("/v1/products", headers=bearer(b_tokens))).json()["items"] == []

    # B, A'ning filialiga kirim qila olmasligi kerak (store lookup RLS orqali 404 beradi)
    attack = await _purchase(client, b_tokens, a_store, product_id, "5")
    assert attack.status_code == 404


async def test_viewer_can_read_but_not_write_catalog(client, owner_url):
    owner = await register(client, "rahbar@example.uz", tenant="Do'kon V", store="V1")
    me = (await client.get("/v1/me", headers=bearer(owner))).json()
    await add_member(owner_url, me["tenant_id"], "kuzatuvchi@example.uz", "viewer")

    login = await client.post(
        "/v1/auth/login", json={"email": "kuzatuvchi@example.uz", "password": "parol-12345"}
    )
    viewer = login.json()

    assert (await client.get("/v1/products", headers=bearer(viewer))).status_code == 200
    denied = await client.post(
        "/v1/products", json={"name": "Ruxsatsiz", "sale_price": 1}, headers=bearer(viewer)
    )
    assert denied.status_code == 403


async def test_product_list_pagination_with_cursor(client):
    tokens = await register(client, "sahifa@example.uz")
    for i in range(5):
        resp = await client.post(
            "/v1/products", json={"name": f"Tovar {i}", "sale_price": 100}, headers=bearer(tokens)
        )
        assert resp.status_code == 201

    seen: list[str] = []
    cursor = None
    while True:
        url = "/v1/products?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = (await client.get(url, headers=bearer(tokens))).json()
        seen += [p["id"] for p in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 5 and len(set(seen)) == 5
