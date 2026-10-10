import uuid
from decimal import Decimal

from omborai_desktop.offline.store import LocalStore
from omborai_desktop.offline.sync import SyncService

STORE = str(uuid.uuid4())
PRODUCT = str(uuid.uuid4())
PRODUCT_DICT = {
    "id": PRODUCT,
    "name": "Shakar 1 kg",
    "unit": "kg",
    "sale_price": 14500,
    "barcodes": ["4780012300017"],
}


def _sale_payload(qty: str) -> dict:
    sale_id = str(uuid.uuid4())
    return {
        "id": sale_id,
        "store_id": STORE,
        "items": [{"product_id": PRODUCT, "qty": qty}],
        "discount": 0,
        "payments": [{"method": "cash", "amount": 14500}],
    }


def _movement(qty: str, kind: str = "receipt") -> dict:
    return {"id": str(uuid.uuid4()), "store_id": STORE, "product_id": PRODUCT, "qty": qty, "kind": kind}


def test_balance_is_confirmed_minus_pending_sales():
    local = LocalStore()
    local.apply_pull(
        {"products": [PRODUCT_DICT], "movements": [_movement("10")], "cursors": {}, "has_more": False}
    )
    local.enqueue_sale(STORE, _sale_payload("3"), "2026-10-10T10:00:00")

    assert local.balance(STORE, PRODUCT) == Decimal(7)
    assert local.pending_count() == 1


def test_applied_result_waits_for_server_movement_then_is_dropped():
    local = LocalStore()
    ok, bad = _sale_payload("1"), _sale_payload("99")
    local.enqueue_sale(STORE, ok, "2026-10-10T10:00:00")
    local.enqueue_sale(STORE, bad, "2026-10-10T10:01:00")

    local.apply_push_results(
        [
            {"op_id": ok["id"], "status": "applied"},
            {
                "op_id": bad["id"],
                "status": "rejected",
                "error_title": "Qoldiq yetarli emas",
                "error_detail": "0",
            },
        ]
    )

    assert local.pending_count() == 0
    assert [r["op_id"] for r in local.rejected_ops()] == [bad["id"]]
    assert local.rejected_ops()[0]["error_title"] == "Qoldiq yetarli emas"

    # Server qo'llagan savdo hali pull qilinmagan: qoldiq noto'g'ri oshib ketmasligi kerak
    local.apply_pull(
        {"products": [PRODUCT_DICT], "movements": [_movement("5")], "cursors": {}, "has_more": False}
    )
    assert local.balance(STORE, PRODUCT) == Decimal(4)

    # Harakat kelgach, navbat yozuvi tozalanadi va qoldiq server bilan bir xil
    sale_movement = {**_movement("-1", "sale"), "reference_id": ok["id"]}
    local.apply_pull({"products": [], "movements": [sale_movement], "cursors": {}, "has_more": False})
    assert local.balance(STORE, PRODUCT) == Decimal(4)
    assert [r["op_id"] for r in local.rejected_ops()] == [bad["id"]]

    local.acknowledge_rejected(bad["id"])
    assert local.rejected_ops() == []


def test_rejected_sale_no_longer_reserves_stock():
    local = LocalStore()
    local.apply_pull(
        {"products": [PRODUCT_DICT], "movements": [_movement("5")], "cursors": {}, "has_more": False}
    )
    bad = _sale_payload("4")
    local.enqueue_sale(STORE, bad, "2026-10-10T10:00:00")
    assert local.balance(STORE, PRODUCT) == Decimal(1)

    local.apply_push_results([{"op_id": bad["id"], "status": "rejected", "error_title": "x"}])
    assert local.balance(STORE, PRODUCT) == Decimal(5)


def test_pull_is_idempotent_and_keeps_cursors():
    local = LocalStore()
    movement = _movement("2")
    page = {
        "products": [PRODUCT_DICT],
        "movements": [movement],
        "cursors": {"movements": "m1"},
        "has_more": False,
    }
    local.apply_pull(page)
    local.apply_pull(page)

    assert local.balance(STORE, PRODUCT) == Decimal(2)
    assert local.cursors() == {"movements": "m1"}


def test_product_cache_search_and_barcode_and_deleted():
    local = LocalStore()
    local.upsert_products([PRODUCT_DICT])
    assert local.product_by_barcode("4780012300017", STORE)["name"] == "Shakar 1 kg"
    assert [p["name"] for p in local.search_products("shakar", STORE)] == ["Shakar 1 kg"]

    local.upsert_products([{**PRODUCT_DICT, "deleted": True}])
    assert local.product_by_barcode("4780012300017", STORE) is None
    assert local.search_products("shakar", STORE) == []


class FakeApi:
    def __init__(self, pages: list[dict]) -> None:
        self._pages = pages
        self.pushed: list[dict] = []
        self.pull_calls: list[dict] = []

    def sync_push(self, body: dict) -> dict:
        self.pushed.append(body)
        return {
            "results": [{"op_id": op["op_id"], "status": "applied", "duplicate": False} for op in body["ops"]]
        }

    def sync_pull(self, store_id: str, cursors: dict, limit: int = 200) -> dict:
        self.pull_calls.append(dict(cursors))
        return self._pages.pop(0)


def test_sync_service_pushes_then_pulls_all_pages():
    local = LocalStore()
    sale = _sale_payload("1")
    local.enqueue_sale(STORE, sale, "2026-10-10T10:00:00")
    pages = [
        {
            "products": [PRODUCT_DICT],
            "movements": [_movement("4")],
            "cursors": {"movements": "a"},
            "has_more": True,
        },
        {
            "products": [],
            "movements": [_movement("1"), {**_movement("-1", "sale"), "reference_id": sale["id"]}],
            "cursors": {"movements": "b"},
            "has_more": False,
        },
    ]
    api = FakeApi(pages)

    report = SyncService(api, local).run_once(STORE)

    assert report.pushed == 1 and report.applied == 1 and report.rejected == 0
    assert report.pulled_products == 1 and report.pulled_movements == 3
    assert api.pushed[0]["ops"][0]["op_id"] == sale["id"]
    assert api.pull_calls == [{}, {"movements": "a"}]
    assert local.cursors() == {"movements": "b"}
    assert local.balance(STORE, PRODUCT) == Decimal(
        4
    )  # 4 + 1 - 1 (savdo hali ham navbatda emas, server qo'lladi)
