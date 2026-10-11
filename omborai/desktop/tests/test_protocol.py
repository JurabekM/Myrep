"""Protokol v2 qoidalari (docs/sync-mqtt.md): imzo, ruxsat, narx, qaytarish, smena, bootstrap (K5)."""

import uuid
from decimal import Decimal

from helpers import (
    STORE_ID,
    Device,
    add_user_op,
    bootstrapped_pair,
    device_op,
    join,
    make_owner,
    movement_op,
    product_op,
    refund_op,
    resign,
    sale_op,
    shift_open_op,
)

from omborai_desktop.offline.store import APPLIED, DUPLICATE, PENDING, REJECTED, SKIPPED
from omborai_desktop.sync import crypto
from omborai_desktop.sync import ops as o

PRODUCT_ID = str(uuid.UUID(int=0x77))


def _deliver(op, *devices):
    return [d.local.apply_op(op) for d in devices]


# --- imzo va kanonik shakl -----------------------------------------------------------


def test_signature_roundtrip_and_tamper_detection():
    owner = make_owner()
    op = product_op(owner, PRODUCT_ID, 1000)
    assert crypto.verify_op(op, owner.identity.public_key_hex)
    op["payload"]["sale_price"] = 1
    assert not crypto.verify_op(op, owner.identity.public_key_hex)


def test_canonical_bytes_do_not_depend_on_key_order():
    a = {"b": 1, "a": {"y": 2, "x": 1}, "sig": "z"}
    b = {"a": {"x": 1, "y": 2}, "b": 1}
    assert crypto.canonical_bytes(a) == crypto.canonical_bytes(b)
    assert b'"a":{"x":1,"y":2}' in crypto.canonical_bytes(a)


def test_signature_from_wrong_device_is_rejected():
    owner, cashier = bootstrapped_pair()
    op = product_op(owner, PRODUCT_ID, 1000)
    op["device"] = cashier.id  # muallif o'zgartirildi, imzo eski
    assert cashier.local.apply_op(op) == REJECTED


# --- ruxsatlar -------------------------------------------------------------------------


def test_cashier_cannot_change_catalog_users_roster_or_stock():
    owner, cashier = bootstrapped_pair()
    assert cashier.local.apply_op(product_op(cashier, PRODUCT_ID, 1)) == REJECTED
    assert cashier.local.apply_op(add_user_op(cashier, "hujum", o.ROLE_OWNER)) == REJECTED
    assert cashier.local.apply_op(movement_op(cashier, PRODUCT_ID, "100")) == REJECTED
    assert cashier.local.apply_op(device_op(cashier, cashier, role=o.ROLE_OWNER)) == REJECTED
    assert owner.local.apply_op(device_op(cashier, cashier, role=o.ROLE_OWNER)) == REJECTED


def test_cashier_cannot_refund_someone_elses_sale():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    sale = sale_op(cashier, PRODUCT_ID, "2", 1000)
    _deliver(sale, owner, cashier)
    fake_refund = cashier.op(
        o.REFUND,
        {"sale_id": sale["op_id"], "items": [{"product_id": PRODUCT_ID, "qty": "2"}]},
        op_id=o.refund_op_id(sale["op_id"]),
    )
    assert owner.local.apply_op(fake_refund) == REJECTED


def test_revoked_device_is_rejected_after_block():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    assert owner.local.apply_op(device_op(owner, cashier, active=False)) == APPLIED
    assert owner.local.apply_op(sale_op(cashier, PRODUCT_ID, "1", 1000)) == REJECTED


def test_owner_device_cannot_be_blocked_or_demoted():
    owner = make_owner()
    assert owner.local.apply_op(device_op(owner, owner, active=False)) == REJECTED
    assert owner.local.apply_op(device_op(owner, owner, role=o.ROLE_CASHIER)) == REJECTED


def test_device_role_promotion_by_owner_applies():
    owner, cashier = bootstrapped_pair()
    promote = device_op(owner, cashier, role=o.ROLE_OWNER)
    assert owner.local.apply_op(promote) == APPLIED
    assert owner.local.is_owner_device(cashier.id)


# --- narx tekshiruvi (Y1) ----------------------------------------------------------------


def test_sale_price_must_match_catalog_and_totals():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 10000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    assert owner.local.apply_op(sale_op(cashier, PRODUCT_ID, "2", 10000)) == APPLIED
    assert owner.local.apply_op(sale_op(cashier, PRODUCT_ID, "2", 1)) == REJECTED
    assert owner.local.balance(STORE_ID, PRODUCT_ID) == Decimal(8)


def test_sale_with_wrong_line_total_is_rejected():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    sale = sale_op(cashier, PRODUCT_ID, "2", 1000)
    sale["payload"]["items"][0]["line_total"] = 1
    resign(cashier, sale)
    assert owner.local.apply_op(sale) == REJECTED


def test_sale_waits_for_catalog_then_applies():
    owner, cashier = bootstrapped_pair()
    catalog = product_op(owner, PRODUCT_ID, 500)  # avval yaratilgan, lekin hali kelmagan
    sale = sale_op(cashier, PRODUCT_ID, "1", 500)
    assert owner.local.apply_op(sale) == PENDING
    assert owner.local.get_sale(sale["op_id"]) is None
    assert owner.local.apply_op(catalog) == APPLIED  # katalog keldi: kutilayotgan savdo qo'llanadi
    assert owner.local.get_sale(sale["op_id"]) is not None


def test_discount_above_subtotal_is_rejected():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    sale = sale_op(cashier, PRODUCT_ID, "1", 1000)
    sale["payload"]["discount"] = 5000
    resign(cashier, sale)
    assert owner.local.apply_op(sale) == REJECTED


# --- smena: har bir qurilmada alohida (K8) -----------------------------------------------


def test_each_device_has_its_own_shift_no_split_brain():
    owner, cashier = bootstrapped_pair()
    own = shift_open_op(owner)
    theirs = shift_open_op(cashier)
    assert owner.local.apply_op(own) == APPLIED
    assert owner.local.apply_op(theirs) == APPLIED
    assert owner.local.open_shift_for_device(owner.id)["id"] == own["op_id"]
    assert owner.local.open_shift_for_device(cashier.id)["id"] == theirs["op_id"]


def test_second_open_shift_on_same_device_is_rejected():
    owner, cashier = bootstrapped_pair()
    assert owner.local.apply_op(shift_open_op(cashier)) == APPLIED
    assert owner.local.apply_op(shift_open_op(cashier)) == REJECTED


def test_only_owner_or_same_device_closes_a_shift():
    owner, cashier = bootstrapped_pair()
    other = Device(9)
    join(owner, other)
    opened = shift_open_op(cashier)
    _deliver(opened, owner, other)
    close_by_other = other.op(o.SHIFT_CLOSE, {"shift_id": opened["op_id"], "closing_cash": 0, "summary": {}})
    assert owner.local.apply_op(close_by_other) == REJECTED
    close_by_owner = owner.op(o.SHIFT_CLOSE, {"shift_id": opened["op_id"], "closing_cash": 0, "summary": {}})
    assert owner.local.apply_op(close_by_owner) == APPLIED
    assert owner.local.open_shift_for_device(cashier.id) is None


# --- qaytarish: o'z-o'zidan to'liq (K6, K7) ---------------------------------------------


def test_refund_restores_stock_on_device_that_never_saw_the_sale():
    """K6: snapshot sotuvdan keyin olingan; qaytarish baribir qoldiqni to'g'ri tiklaydi."""
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    sale = sale_op(cashier, PRODUCT_ID, "3", 1000)
    _deliver(sale, owner, cashier)
    late = Device(5)
    join(owner, late)  # snapshot: qoldiq 7, sotuv tarixisiz
    assert late.local.balance(STORE_ID, PRODUCT_ID) == Decimal(7)
    refund = refund_op(owner, sale)
    _deliver(refund, owner, late)
    assert (
        late.local.balance(STORE_ID, PRODUCT_ID) == owner.local.balance(STORE_ID, PRODUCT_ID) == Decimal(10)
    )


def test_refund_before_sale_marks_sale_refunded_when_it_arrives():
    """K7: qaytarish sotuvdan oldin kelsa ham qoldiq va chek holati to'g'ri bo'ladi."""
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    late = Device(6)
    join(owner, late)  # qoldiq 10, sotuv hali yo'q
    sale = sale_op(cashier, PRODUCT_ID, "3", 1000)
    _deliver(sale, owner)
    refund = refund_op(owner, sale)
    assert late.local.apply_op(refund) == APPLIED
    assert late.local.apply_op(sale) == APPLIED
    assert late.local.balance(STORE_ID, PRODUCT_ID) == Decimal(10)
    assert late.local.get_sale(sale["op_id"])["status"] == "refunded"


def test_refund_twice_is_rejected():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    sale = sale_op(cashier, PRODUCT_ID, "1", 1000)
    _deliver(sale, owner, cashier)
    refund = refund_op(owner, sale)
    assert owner.local.apply_op(refund) == APPLIED
    again = owner.op(o.REFUND, refund["payload"], op_id=refund["op_id"] + "-2")
    assert owner.local.apply_op(again) == REJECTED


# --- bootstrap va snapshot poygasi (K5) ----------------------------------------------------


def test_live_sale_before_snapshot_does_not_block_bootstrap():
    """K5: snapshot kelishidan oldin jonli sotuv keladi — snapshot rad etilmaydi, sotuv ikki marta sanalmaydi."""
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    newcomer = Device(7)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    live = sale_op(cashier, PRODUCT_ID, "2", 1000)
    _deliver(live, owner)
    assert newcomer.local.apply_op(live) == PENDING  # bootstrapgacha holat o'zgarmaydi
    approval = device_op(owner, newcomer)
    _deliver(approval, owner, newcomer)
    snapshot = owner.op(o.SNAPSHOT, owner.local.snapshot_payload(STORE_ID))
    assert newcomer.local.apply_op(snapshot) == APPLIED
    assert newcomer.local.is_bootstrapped()
    assert newcomer.local.balance(STORE_ID, PRODUCT_ID) == Decimal(8)  # 10 - 2, ikki marta emas


def test_live_sale_after_snapshot_time_is_replayed_after_bootstrap():
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    _deliver(movement_op(owner, PRODUCT_ID, "10"), owner, cashier)
    newcomer = Device(8)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    approval = device_op(owner, newcomer)
    _deliver(approval, owner, newcomer)
    snapshot = owner.op(o.SNAPSHOT, owner.local.snapshot_payload(STORE_ID))
    late = sale_op(cashier, PRODUCT_ID, "4", 1000)  # snapshot'dan KEYIN yaratilgan
    _deliver(late, owner)
    assert newcomer.local.apply_op(late) == PENDING
    assert newcomer.local.apply_op(snapshot) == APPLIED
    _deliver(late, newcomer)  # sweep allaqachon bajargan bo'lishi mumkin: dedupe
    assert (
        newcomer.local.balance(STORE_ID, PRODUCT_ID)
        == owner.local.balance(STORE_ID, PRODUCT_ID)
        == Decimal(6)
    )


def test_snapshot_from_cashier_is_not_accepted():
    owner, cashier = bootstrapped_pair()
    newcomer = Device(9)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    fake = cashier.op(
        o.SNAPSHOT,
        {"store": None, "devices": [], "users": [], "products": [], "balances": {}, "open_shifts": []},
    )
    assert newcomer.local.apply_op(fake) != APPLIED
    assert not newcomer.local.is_bootstrapped()


def test_second_snapshot_after_bootstrap_is_rejected():
    owner, cashier = bootstrapped_pair()
    again = owner.op(o.SNAPSHOT, owner.local.snapshot_payload(STORE_ID))
    assert cashier.local.apply_op(again) == REJECTED


def test_join_request_must_be_self_signed_for_this_store():
    owner = make_owner()
    newcomer = Device(10)
    newcomer.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    request = newcomer.local.join_request("kassa")
    assert owner.local.verify_join_request(request)
    forged = dict(request)
    forged["payload"] = {**request["payload"], "public_key": Device(11).identity.public_key_hex}
    assert not owner.local.verify_join_request(forged)
    assert not owner.local.verify_join_request(dict(request, store_id=str(uuid.uuid4())))
    approval = device_op(owner, newcomer)
    _deliver(approval, owner, newcomer)
    assert not owner.local.verify_join_request(request)  # allaqachon qo'shilgan


# --- dedupe, buzilgan va noma'lum operatsiyalar ----------------------------------------


def test_duplicate_delivery_is_idempotent():
    owner = make_owner()
    op = product_op(owner, PRODUCT_ID, 1000)
    assert owner.local.apply_op(op) == APPLIED
    assert owner.local.apply_op(op) == DUPLICATE


def test_malformed_operations_are_rejected_without_crashing():
    owner = make_owner()
    assert owner.local.apply_op({"nope": 1}) == REJECTED
    bad_price = product_op(owner, PRODUCT_ID, 1000)
    bad_price["payload"]["sale_price"] = "x"
    resign(owner, bad_price)
    assert owner.local.apply_op(bad_price) == REJECTED
    unknown = owner.op("nomalum-tur", {})
    assert owner.local.apply_op(unknown) == REJECTED


def test_requests_are_skipped_not_applied():
    owner, cashier = bootstrapped_pair()
    request = cashier.local.new_op("snapshot_request", {})
    assert owner.local.apply_op(request) == SKIPPED


def test_operations_from_before_bootstrap_cutoff_are_skipped():
    """Snapshot T dan oldingi (ts <= T) jonli operatsiyalar snapshot ichida — qo'llanmaydi."""
    owner, cashier = bootstrapped_pair()
    _deliver(product_op(owner, PRODUCT_ID, 1000), owner, cashier)
    old = movement_op(owner, PRODUCT_ID, "5")
    _deliver(old, owner)
    newcomer = Device(12)
    join(owner, newcomer)  # snapshot old'dan keyin: qoldiq 5
    assert newcomer.local.apply_op(old) == SKIPPED
    assert newcomer.local.balance(STORE_ID, PRODUCT_ID) == Decimal(5)
