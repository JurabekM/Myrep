import uuid
from decimal import Decimal

import pytest

from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import ops as o

STORE = str(uuid.uuid4())
DEVICE = "dev-a"
PRODUCT = str(uuid.uuid4())


def op(op_type, payload, *, ts="2026-10-10T10:00:00+00:00", op_id=None, store=STORE):
    return o.new_op(op_type, store, payload, device_id=DEVICE, op_id=op_id) | {"ts": ts}


def product(name="Shakar", price=14500, ts="2026-10-10T09:00:00+00:00", deleted=False, pid=PRODUCT):
    return op(
        o.PRODUCT,
        {
            "id": pid,
            "name": name,
            "unit": "kg",
            "sale_price": price,
            "cost_price": 9000,
            "min_stock": "5",
            "barcodes": ["4780012300017"],
            "deleted": deleted,
        },
        ts=ts,
    )


def receipt(qty, ts="2026-10-10T09:30:00+00:00"):
    return op(o.MOVEMENT, {"product_id": PRODUCT, "kind": "receipt", "qty": str(qty)}, ts=ts)


def sale(qty, *, shift_id, number="a-1", sale_id=None, price=14500):
    sid = sale_id or str(uuid.uuid4())
    total = int(Decimal(qty) * price)
    payload = {
        "id": sid,
        "shift_id": shift_id,
        "number": number,
        "created_at": "2026-10-10T10:00:00+00:00",
        "items": [
            {
                "product_id": PRODUCT,
                "qty": str(qty),
                "unit_price": price,
                "line_total": total,
                "product_name": "Shakar",
                "unit": "kg",
            }
        ],
        "subtotal": total,
        "discount": 0,
        "total": total,
        "payments": [{"method": "cash", "amount": total}],
    }
    return op(o.SALE, payload, op_id=sid)


@pytest.fixture
def store():
    s = LocalStore()
    yield s
    s.close()


def _stocked(store, qty="10"):
    store.apply_op(product())
    store.apply_op(receipt(qty))


def test_sale_reduces_stock_and_is_applied_once(store):
    _stocked(store)
    shift = op(o.SHIFT_OPEN, {"shift_id": "sh1", "opening_cash": 0}, op_id="sh1")
    store.apply_op(shift)
    s = sale(3, shift_id="sh1")
    assert store.apply_op(s) is True
    assert store.apply_op(s) is False
    assert store.balance(STORE, PRODUCT) == Decimal(7)
    assert store.get_sale(s["op_id"])["status"] == "completed"


def test_refund_restores_stock_once_across_duplicate_ops(store):
    _stocked(store)
    store.apply_op(op(o.SHIFT_OPEN, {"shift_id": "sh1", "opening_cash": 0}, op_id="sh1"))
    s = sale(4, shift_id="sh1")
    store.apply_op(s)
    refund = op(o.REFUND, {"sale_id": s["op_id"]}, op_id=o.refund_op_id(s["op_id"]))
    assert store.apply_op(refund) is True
    assert store.apply_op(refund) is False  # deterministik op_id: ikkinchi qaytarish qo'llanmaydi
    assert store.apply_op(op(o.REFUND, {"sale_id": s["op_id"]}, op_id=o.refund_op_id(s["op_id"]))) is False
    assert store.balance(STORE, PRODUCT) == Decimal(10)
    assert store.get_sale(s["op_id"])["status"] == "refunded"


def test_second_open_shift_is_ignored_and_close_stores_summary(store):
    store.apply_op(op(o.SHIFT_OPEN, {"shift_id": "sh1", "opening_cash": 500}, op_id="sh1"))
    store.apply_op(op(o.SHIFT_OPEN, {"shift_id": "sh2", "opening_cash": 0}, op_id="sh2"))
    assert store.open_shift(STORE)["id"] == "sh1"
    _stocked(store)
    store.apply_op(sale(2, shift_id="sh1"))
    summary = store.shift_summary("sh1")
    assert summary["sales_count"] == 1 and summary["total_sales"] == 29000
    assert summary["by_method"] == {"cash": 29000}
    store.apply_op(op(o.SHIFT_CLOSE, {"shift_id": "sh1", "closing_cash": 29500, "summary": summary}))
    assert store.open_shift(STORE) is None


def test_product_last_writer_wins_by_timestamp(store):
    store.apply_op(product(name="Yangi", price=20000, ts="2026-10-10T12:00:00+00:00"))
    assert store.apply_op(product(name="Eski", price=1, ts="2026-10-10T08:00:00+00:00")) is True
    found = store.get_product(PRODUCT, STORE)
    assert found["name"] == "Yangi" and found["sale_price"] == 20000


def test_deleted_product_is_hidden_from_search_and_barcode(store):
    store.apply_op(product())
    store.apply_op(product(deleted=True, ts="2026-10-10T11:00:00+00:00"))
    assert store.product_by_barcode("4780012300017", STORE) is None
    assert store.search_products("shakar", STORE) == []


def test_snapshot_only_bootstraps_an_empty_device(store):
    source = LocalStore()
    _stocked(source, qty="7")
    source.apply_op(op(o.SHIFT_OPEN, {"shift_id": "sh1", "opening_cash": 100}, op_id="sh1"))
    snap = op(o.SNAPSHOT, source.snapshot_payload(STORE))
    assert store.apply_op(snap) is True
    assert store.balance(STORE, PRODUCT) == Decimal(7)
    assert store.get_product(PRODUCT, STORE)["name"] == "Shakar"
    assert store.open_shift(STORE)["id"] == "sh1"
    # Ikkinchi snapshot (boshqa qurilmadan) ma'lumotni ikki marta hisoblamaydi
    assert store.apply_op(op(o.SNAPSHOT, source.snapshot_payload(STORE))) is False
    assert store.balance(STORE, PRODUCT) == Decimal(7)
    source.close()


def test_snapshot_request_is_not_data(store):
    assert store.apply_op(op(o.SNAPSHOT_REQUEST, {})) is False
    assert store.applied_count() == 0


def test_unknown_op_type_is_rejected_and_rolled_back(store):
    with pytest.raises(ValueError):
        store.apply_op(op("hack", {}))
    assert store.applied_count() == 0


def test_outbox_roundtrip_and_receipt_numbers(store):
    first = op(o.PRODUCT, {"id": str(uuid.uuid4()), "name": "A", "unit": "dona", "sale_price": 1})
    store.enqueue(first)
    store.enqueue(first)  # takror navbatga qo'yilmaydi
    assert store.pending_count() == 1
    assert store.pending_ops()[0]["op_id"] == first["op_id"]
    store.drop_outbox(first["op_id"])
    assert store.pending_count() == 0
    numbers = {store.next_receipt_number() for _ in range(3)}
    assert len(numbers) == 3
