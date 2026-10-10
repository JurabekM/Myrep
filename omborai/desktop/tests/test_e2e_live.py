"""Haqiqiy, ishga tushgan backend bilan offline-sinxronizatsiya scenariysi.

Ishga tushirish: OMBORAI_E2E_URL=http://127.0.0.1:8000 pytest tests/test_e2e_live.py
URL berilmasa, test o'tkazib yuboriladi.
"""

import os
import time
import uuid
from decimal import Decimal

import httpx
import pytest

from omborai_desktop.api import ApiClient
from omborai_desktop.cart import Cart
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.offline.sync import SyncService

BASE = os.environ.get("OMBORAI_E2E_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="OMBORAI_E2E_URL berilmagan")


def test_offline_sales_reconcile_with_server():
    raw = httpx.Client(base_url=BASE, timeout=10)
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.uz"
    reg = raw.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "parol-12345",
            "full_name": "E2E",
            "tenant_name": "E2E do'kon",
            "store_name": "Markaz",
        },
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    api = ApiClient(BASE)
    api.login(email, "parol-12345")
    store_id = api.stores()[0]["id"]
    product = raw.post(
        "/v1/products",
        headers=headers,
        json={"name": "Shakar 1 kg", "unit": "kg", "sale_price": 14500, "barcodes": ["4780012300017"]},
    ).json()
    raw.post(
        "/v1/purchases",
        headers=headers,
        json={"store_id": store_id, "items": [{"product_id": product["id"], "qty": "10", "unit_cost": 9000}]},
    )
    api.open_shift(store_id, 0)

    local = LocalStore()
    sync = SyncService(api, local)
    time.sleep(4)  # sinxronizatsiya horizon'i (3 soniya)
    sync.run_once(store_id)
    assert local.balance(store_id, product["id"]) == Decimal(10)

    cart = Cart()
    cart.add({"id": product["id"], "name": "Shakar 1 kg", "unit": "kg", "sale_price": 14500}, Decimal(3))
    good = cart.to_sale_payload(store_id, [("cash", cart.total)])
    local.enqueue_sale(store_id, good, "2026-10-10T10:00:00")

    cart2 = Cart()
    cart2.add({"id": product["id"], "name": "Shakar 1 kg", "unit": "kg", "sale_price": 14500}, Decimal(50))
    local.enqueue_sale(
        store_id, cart2.to_sale_payload(store_id, [("cash", cart2.total)]), "2026-10-10T10:01:00"
    )

    time.sleep(4)
    report = sync.run_once(store_id)
    assert report.applied == 1 and report.rejected == 1
    assert local.pending_count() == 0
    assert "Qoldiq yetarli emas" in [r["error_title"] for r in local.rejected_ops()]

    time.sleep(4)
    sync.run_once(store_id)
    server_qty = Decimal(
        next(
            b
            for b in raw.get(f"/v1/stock/balances?store_id={store_id}", headers=headers).json()
            if b["product_id"] == product["id"]
        )["qty"]
    )
    assert server_qty == Decimal(7)
    assert local.balance(store_id, product["id"]) == server_qty

    sales = raw.get(f"/v1/sales?store_id={store_id}", headers=headers).json()
    assert [s["id"] for s in sales] == [good["id"]]
    api.close()
