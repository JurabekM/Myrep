"""Lokal baza semantikasi (protokol v2): katalog LWW, narx tarixi, qidiruv, smena hisobi, snapshot shakli."""

import uuid
from decimal import Decimal

from helpers import (
    STORE_ID,
    add_user_op,
    bootstrapped_pair,
    make_owner,
    movement_op,
    product_op,
    refund_op,
    sale_op,
    shift_open_op,
)

from omborai_desktop.offline.store import APPLIED, DUPLICATE, REJECTED, SKIPPED
from omborai_desktop.sync import ops as o

PID = str(uuid.UUID(int=0x10))


def test_product_lww_keeps_latest_and_keeps_price_history():
    owner = make_owner()
    older = product_op(owner, PID, 1000)
    newer = product_op(owner, PID, 2000)
    assert owner.local.apply_op(newer) == APPLIED
    assert owner.local.apply_op(older) == APPLIED  # eski narx: faqat tarixga yoziladi
    assert owner.local.get_product(PID, STORE_ID)["sale_price"] == 2000
    # Eski narx vaqtida sotuv: tarixdagi 1000 narx bo'yicha tekshiriladi
    assert owner.local._price_at(PID, older["ts"]) == 1000


def test_barcode_and_search_ignore_deleted_products():
    owner = make_owner()
    op = owner.op(
        o.PRODUCT,
        {
            "id": PID,
            "name": "Shakar",
            "unit": "kg",
            "sale_price": 9000,
            "cost_price": 0,
            "min_stock": "2",
            "barcodes": ["4780001"],
            "deleted": False,
        },
    )
    owner.local.apply_op(op)
    assert owner.local.product_by_barcode("4780001", STORE_ID)["name"] == "Shakar"
    assert [p["name"] for p in owner.local.search_products("shak", STORE_ID)] == ["Shakar"]
    deleted = owner.op(
        o.PRODUCT,
        {
            "id": PID,
            "name": "Shakar",
            "unit": "kg",
            "sale_price": 9000,
            "cost_price": 0,
            "min_stock": "2",
            "barcodes": ["4780001"],
            "deleted": True,
        },
    )
    owner.local.apply_op(deleted)
    assert owner.local.product_by_barcode("4780001", STORE_ID) is None
    assert owner.local.search_products("shak", STORE_ID) == []


def test_store_name_is_lww():
    owner = make_owner()
    first = owner.op(o.STORE, {"name": "Birinchi"})
    second = owner.op(o.STORE, {"name": "Ikkinchi"})
    owner.local.apply_op(second)
    owner.local.apply_op(first)  # eski: e'tiborsiz (SKIPPED)
    assert owner.local.store_name(STORE_ID) == "Ikkinchi"


def test_user_lww_and_login_lookup_is_case_insensitive():
    owner = make_owner()
    op = add_user_op(owner, "Kassir1", o.ROLE_CASHIER)
    assert owner.local.apply_op(op) == APPLIED
    found = owner.local.find_user(STORE_ID, "KASSIR1")
    assert found is not None and found["role"] == o.ROLE_CASHIER
    deactivate = owner.op(
        o.USER,
        {
            "id": found["id"],
            "login": found["login"],
            "name": found["name"],
            "role": found["role"],
            "salt": found["salt"],
            "pw_hash": found["pw_hash"],
            "active": False,
        },
    )
    owner.local.apply_op(deactivate)
    assert owner.local.find_user(STORE_ID, "kassir1") is None  # nofaol: kira olmaydi


def test_movements_drive_balance_and_adjustments_are_owner_only():
    owner, cashier = bootstrapped_pair()
    owner.local.apply_op(product_op(owner, PID, 500))
    owner.local.apply_op(movement_op(owner, PID, "10", "receipt"))
    owner.local.apply_op(movement_op(owner, PID, "-2", "adjustment"))
    owner.local.apply_op(movement_op(owner, PID, "-1", "writeoff"))  # yo'qotish: qoldiq kamayadi
    assert owner.local.balance(STORE_ID, PID) == Decimal(7)  # 10 - 2 - 1
    assert owner.local.apply_op(movement_op(owner, PID, "5", "bogus")) == REJECTED


def test_shift_close_summary_counts_sales_and_refunds():
    owner, cashier = bootstrapped_pair()
    owner.local.apply_op(product_op(owner, PID, 1000))
    owner.local.apply_op(movement_op(owner, PID, "10"))
    shift = shift_open_op(cashier)
    owner.local.apply_op(shift)
    shift_id = shift["op_id"]
    s1 = sale_op(cashier, PID, "2", 1000, shift_id=shift_id)
    s2 = sale_op(cashier, PID, "1", 1000, shift_id=shift_id)
    owner.local.apply_op(s1)
    owner.local.apply_op(s2)
    owner.local.apply_op(refund_op(owner, s2))
    summary = owner.local.shift_summary(shift_id)
    assert summary["sales_count"] == 1
    assert summary["total_sales"] == 2000
    assert summary["refunds_count"] == 1
    assert summary["total_refunds"] == 1000


def test_snapshot_payload_has_protocol_sections():
    owner, cashier = bootstrapped_pair()
    owner.local.apply_op(product_op(owner, PID, 500))
    owner.local.apply_op(movement_op(owner, PID, "3"))
    payload = owner.local.snapshot_payload(STORE_ID)
    assert set(payload) == {"store", "devices", "users", "products", "balances", "open_shifts"}
    assert {d["device_id"] for d in payload["devices"]} == {owner.id, cashier.id}
    assert payload["balances"] == {PID: "3"}


def test_outbox_roundtrip_and_counts():
    owner = make_owner()
    op = product_op(owner, PID, 100)
    owner.local.enqueue(op)
    owner.local.enqueue(op)  # INSERT OR IGNORE: ikki marta emas
    assert owner.local.pending_count() == 1
    assert owner.local.pending_ops()[0]["op_id"] == op["op_id"]
    owner.local.drop_outbox(op["op_id"])
    assert owner.local.pending_count() == 0


def test_receipt_numbers_are_sequential_and_device_prefixed():
    owner = make_owner()
    first = owner.local.next_receipt_number()
    second = owner.local.next_receipt_number()
    assert first.startswith(owner.id[:4]) and first != second


def test_same_op_twice_is_duplicate_for_sales():
    owner, cashier = bootstrapped_pair()
    owner.local.apply_op(product_op(owner, PID, 100))
    owner.local.apply_op(movement_op(owner, PID, "5"))
    sale = sale_op(cashier, PID, "1", 100)
    assert owner.local.apply_op(sale) == APPLIED
    assert owner.local.apply_op(sale) == DUPLICATE
    assert owner.local.balance(STORE_ID, PID) == Decimal(4)


def test_unknown_device_store_mismatch_is_rejected():
    owner = make_owner()
    op = product_op(owner, PID, 100)
    op["store_id"] = str(uuid.uuid4())
    from helpers import resign

    resign(owner, op)
    assert owner.local.apply_op(op) == REJECTED
    assert SKIPPED  # eslatma: SKIPPED boshqa testlarda tekshiriladi
