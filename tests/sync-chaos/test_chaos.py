"""Sync chaos testlari — tarmoq yomon bo'lganda ham to'g'ri ishlash.

Topshiriq §22 dagi ro'yxat: uzilish, dublikat, tartib buzilishi, kechikish,
uzoq offline, session yo'qolishi, clock skew, bir vaqtda tahrirlash,
snapshot uzilishi, buzilgan paket, katta paket, noto'g'ri sxema.

Har bir holat ANIQ bajariladi va natija tekshiriladi — «yiqilmadi» degani
«to'g'ri ishladi» degani emas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.aether_q.provider import AetherQError, ContentType
from distribos.domain.ids import uuid7_str
from distribos.persistence.models import (
    ConflictRecord,
    DeadLetter,
    Order,
    Product,
)
from distribos.sync.event_store import NewEvent
from harness import shared_tenant_setup


@pytest.fixture
def pair():
    _bus, _tenant, (desktop, phone) = shared_tenant_setup("desktop-1", "android-1")
    return _bus, desktop, phone


def _product(node, name: str = "Cola 1L") -> str:
    product_id = uuid7_str()
    with node.database.unit_of_work() as session:
        node.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": f"SKU-{product_id[-8:]}",
             "name": name, "unit": "dona", "wholesale_price": 1_000_000},
        ))
    return product_id


def _customer(node) -> str:
    customer_id = uuid7_str()
    with node.database.unit_of_work() as session:
        node.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": f"C-{customer_id[-6:]}",
             "name": "Mijoz", "kind": "COMPANY"},
        ))
    return customer_id


def _order(node, customer_id: str, product_id: str) -> str:
    order_id = uuid7_str()
    with node.database.unit_of_work() as session:
        node.command.submit(session, NewEvent(
            "ORDER_CREATED", "Order", order_id,
            {"order_id": order_id, "number": f"B-{order_id[-12:]}",
             "customer_id": customer_id, "ordered_at": "2026-08-23T10:00:00+00:00",
             "lines": [{"line_id": uuid7_str(), "product_id": product_id,
                        "quantity": "5", "unit_price": 1_000_000}]},
        ))
    return order_id


# --- tarmoq buzilishlari --------------------------------------------------


def test_long_offline_device_catches_up(pair) -> None:
    """Bir necha kun offline qurilma qaytganda hammasini oladi."""
    bus, desktop, phone = pair
    product_id = _product(desktop)
    customer_id = _customer(desktop)
    desktop.sync()

    bus.set_online(phone.device_id, False)

    order_ids = []
    for _ in range(12):
        order_ids.append(_order(desktop, customer_id, product_id))
    desktop.sync()

    with phone.database.session() as session:
        assert session.query(Order).count() == 0

    bus.set_online(phone.device_id, True)
    desktop.sync(rounds=8)

    with phone.database.session() as session:
        for order_id in order_ids:
            assert session.get(Order, order_id) is not None, "hodisa yo'qoldi"


def test_anti_entropy_recovers_lost_messages(pair) -> None:
    """Xabar butunlay yo'qolsa — digest almashuvi tiklaydi.

    Bu broker tarixiga TAYANMAYDI: yo'qolgan hodisani peer o'z lokal
    jurnalidan topib qayta yuboradi.
    """
    bus, desktop, phone = pair
    product_id = _product(desktop)
    customer_id = _customer(desktop)
    desktop.sync()

    # Hodisa yaratamiz, lekin uni yo'lda YO'QOTAMIZ.
    order_id = _order(desktop, customer_id, product_id)
    desktop.engine.publish_pending()
    bus.inflight.clear()          # xabar yo'qoldi
    bus.pump()

    with phone.database.session() as session:
        assert session.get(Order, order_id) is None, "test noto'g'ri: xabar yetib bordi"

    # Anti-entropy: telefon o'z digest'ini e'lon qiladi.
    phone.engine.send_digest()
    for _ in range(6):
        bus.pump()
        desktop.engine.publish_pending()
        phone.engine.publish_pending()

    with phone.database.session() as session:
        assert session.get(Order, order_id) is not None, (
            "anti-entropy yo'qolgan hodisani tiklamadi"
        )


def test_duplicate_and_reorder_together(pair) -> None:
    """Dublikat VA tartib buzilishi bir vaqtda."""
    bus, desktop, phone = pair
    product_id = _product(desktop)
    customer_id = _customer(desktop)
    desktop.sync()

    bus.duplicate_factor = 3
    bus.reorder = True

    order_ids = [_order(desktop, customer_id, product_id) for _ in range(5)]
    desktop.sync(rounds=8)

    with phone.database.session() as session:
        for order_id in order_ids:
            assert session.query(Order).filter_by(id=order_id).count() == 1


def test_concurrent_edit_resolves_deterministically(pair) -> None:
    """Ikki qurilma bir maydonni bir vaqtda o'zgartirdi.

    Natija HLC bo'yicha deterministik: ikkala qurilmada ham BIR XIL
    qiymat qoladi (kim oxirgi yozgani emas, kim kechroq tamg'a olgani).
    """
    bus, desktop, phone = pair
    product_id = _product(desktop)
    desktop.sync()

    bus.set_online(phone.device_id, False)

    with desktop.database.unit_of_work() as session:
        desktop.command.submit(session, NewEvent(
            "PRODUCT_PRICE_CHANGED", "Product", product_id,
            {"product_id": product_id, "field": "wholesale_price",
             "new_price": 2_000_000},
        ))
    with phone.database.unit_of_work() as session:
        phone.command.submit(session, NewEvent(
            "PRODUCT_PRICE_CHANGED", "Product", product_id,
            {"product_id": product_id, "field": "wholesale_price",
             "new_price": 3_000_000},
        ))

    bus.set_online(phone.device_id, True)
    for _ in range(6):
        desktop.sync()
        phone.sync()

    with desktop.database.session() as s1, phone.database.session() as s2:
        desktop_price = s1.get(Product, product_id).wholesale_price
        phone_price = s2.get(Product, product_id).wholesale_price

    assert desktop_price == phone_price, (
        f"qurilmalar bir xil natijaga kelmadi: {desktop_price} != {phone_price}"
    )
    assert desktop_price in (2_000_000, 3_000_000)


def test_illegal_state_transition_becomes_conflict(pair) -> None:
    """Noqonuniy holat o'tishi JIMGINA qabul qilinmaydi."""
    bus, desktop, phone = pair
    product_id = _product(desktop)
    customer_id = _customer(desktop)
    order_id = _order(desktop, customer_id, product_id)
    desktop.sync()

    with desktop.database.unit_of_work() as session:
        desktop.command.submit(session, NewEvent(
            "ORDER_STATE_CHANGED", "Order", order_id,
            {"order_id": order_id, "from_state": "DRAFT", "to_state": "SHIPPED"},
        ))

    with desktop.database.session() as session:
        conflicts = session.query(ConflictRecord).filter_by(
            strategy="STATE_MACHINE"
        ).all()
        assert conflicts, "noqonuniy o'tish konflikt sifatida yozilmadi"
        assert session.get(Order, order_id).state == "DRAFT", "holat o'zgarib ketdi"


# --- buzilgan va zararli paketlar -----------------------------------------


def test_corrupted_packet_is_rejected(pair) -> None:
    bus, desktop, phone = pair
    _product(desktop)
    desktop.engine.publish_pending()

    wire = bytearray(bus.inflight[0][2])
    wire[100] ^= 0xFF
    bus.inflight.clear()

    phone.engine.handle_inbound(bytes(wire))
    assert phone.engine.stats.rejected >= 1
    with phone.database.session() as session:
        assert session.query(DeadLetter).count() >= 1


def test_truncated_packet_is_rejected(pair) -> None:
    bus, desktop, phone = pair
    _product(desktop)
    desktop.engine.publish_pending()
    wire = bus.inflight[0][2][:200]
    bus.inflight.clear()

    phone.engine.handle_inbound(wire)
    assert phone.engine.stats.rejections.get("MALFORMED", 0) >= 1


def test_oversized_packet_is_rejected(pair) -> None:
    """Haddan tashqari katta paket kripto qatlamiga YETIB BORMAYDI."""
    _bus, desktop, phone = pair
    huge = b"\x00" * (2 * 1024 * 1024)
    phone.engine.handle_inbound(huge)
    assert phone.engine.stats.rejections.get("TOO_LARGE", 0) >= 1


def test_foreign_tenant_message_is_rejected() -> None:
    """Boshqa tenantning xabari rad etiladi."""
    from distribos.domain.ids import new_tenant_id
    from harness import LoopbackBus, build_node

    bus = LoopbackBus()
    tenant_a, tenant_b = new_tenant_id(), new_tenant_id()
    node_a = build_node("desktop-a", tenant_a, bus)
    node_b = build_node("desktop-b", tenant_b, bus)

    envelope = node_a.provider.seal_message(b"salom", ContentType.EVENT_BATCH)
    with pytest.raises(AetherQError) as caught:
        node_b.provider.open_message(envelope.wire)
    # Kalit boshqa tenant uchun ajratilgan -> kalit topilmaydi yoki teg mos emas.
    assert caught.value.reason.name in ("FOREIGN_TENANT", "UNKNOWN_KEY", "UNKNOWN_SENDER")


def test_revoked_device_messages_rejected(pair) -> None:
    """Bekor qilingan qurilmaning hodisalari qabul qilinmaydi."""
    bus, desktop, phone = pair
    product_id = _product(desktop)
    desktop.sync()

    desktop.provider.revoke_device(phone.device_id, "telefon yo'qoldi")

    with phone.database.unit_of_work() as session:
        phone.command.submit(session, NewEvent(
            "PRODUCT_PRICE_CHANGED", "Product", product_id,
            {"product_id": product_id, "field": "wholesale_price",
             "new_price": 999_000_000},
        ))
    phone.sync()

    with desktop.database.session() as session:
        assert session.get(Product, product_id).wholesale_price == 1_000_000, (
            "bekor qilingan qurilma narxni o'zgartirib yubordi"
        )
    assert desktop.engine.stats.rejections.get("REVOKED_SENDER", 0) >= 1


def test_unknown_event_type_does_not_crash(pair) -> None:
    """Noma'lum hodisa turi rad etiladi, lekin tizimni yiqitmaydi."""
    bus, desktop, phone = pair
    _product(desktop)
    desktop.sync()

    import cbor2
    from distribos.persistence.models import EventLog

    with desktop.database.session() as session:
        template = session.query(EventLog).first()
        item = desktop.engine._event_to_dict(template)

    item["event_type"] = "SOMETHING_FROM_THE_FUTURE"
    item["event_id"] = uuid7_str()
    item["device_sequence"] = 9999
    payload = cbor2.dumps({"events": [item]})
    envelope = desktop.provider.seal_message(payload, ContentType.EVENT_BATCH)

    phone.engine.handle_inbound(envelope.wire)   # yiqilmasligi kerak

    with phone.database.session() as session:
        # Kontrakt tekshiruvi hodisa turini QO'LLOVCHIDAN OLDIN ushlaydi —
        # shuning uchun strategiya "CONTRACT".
        conflicts = session.query(ConflictRecord).filter(
            ConflictRecord.strategy.in_(("CONTRACT", "UNKNOWN_TYPE"))
        ).count()
        assert conflicts >= 1


# --- clock skew -----------------------------------------------------------


def test_clock_skew_does_not_break_ordering() -> None:
    """Soati oldinga ketgan qurilma butun mesh soatini buzmasligi kerak."""
    from distribos.domain.ids import HybridClock, HybridTimestamp

    clock = HybridClock("device01")
    baseline = clock.now()

    # 10 yil oldinga ketgan tamg'a.
    absurd = HybridTimestamp(baseline.wall_ms + 10 * 365 * 24 * 3600 * 1000, 0, "evil")
    clock.observe(absurd)

    after = clock.now()
    drift = after.wall_ms - baseline.wall_ms
    assert drift < 10 * 60 * 1000, (
        f"soat {drift} ms ga oldinga surildi — chetlangan tamg'a qabul qilindi"
    )


def test_hybrid_timestamp_is_monotonic() -> None:
    from distribos.domain.ids import HybridClock

    clock = HybridClock("device01")
    stamps = [clock.now() for _ in range(1000)]
    assert stamps == sorted(stamps), "HLC monotonik emas"
    assert len(set(s.encode() for s in stamps)) == 1000, "takroriy tamg'a"


# --- snapshot -------------------------------------------------------------


def test_snapshot_resumes_after_interruption(pair) -> None:
    """Snapshot uzilib qolsa — faqat yetishmagan qismlar so'raladi."""
    from distribos.sync.snapshot import SnapshotAssembler, build_snapshot

    bus, desktop, phone = pair
    for index in range(40):
        _product(desktop, f"Mahsulot {index}")
    _customer(desktop)

    with desktop.database.session() as session:
        manifest, chunks = build_snapshot(session, role="agent", snapshot_id="s1")

    assembler = SnapshotAssembler(manifest)
    # Uzilish: birinchi yarmi keldi.
    for chunk in chunks[: max(1, len(chunks) // 2)]:
        assembler.add(chunk)

    if len(chunks) > 1:
        assert not assembler.is_complete
        assert assembler.missing_indexes

    for index in assembler.missing_indexes:
        assembler.add(chunks[index])

    assert assembler.is_complete
    payload = assembler.finish()
    assert payload["tables"]["products"]


def test_snapshot_integrity_is_verified(pair) -> None:
    from distribos.sync.snapshot import SnapshotAssembler, SnapshotError, build_snapshot

    bus, desktop, phone = pair
    _product(desktop)

    with desktop.database.session() as session:
        manifest, chunks = build_snapshot(session, role="owner", snapshot_id="s2")

    assembler = SnapshotAssembler(manifest)
    for chunk in chunks:
        corrupted = bytearray(chunk.data)
        if corrupted:
            corrupted[0] ^= 0xFF
        assembler.add(type(chunk)(chunk.snapshot_id, chunk.index, bytes(corrupted)))

    with pytest.raises(SnapshotError, match="yaxlitligi"):
        assembler.finish()


def test_snapshot_is_role_scoped(pair) -> None:
    """Agentga moliyaviy jadval YUBORILMAYDI."""
    from distribos.sync.snapshot import build_snapshot

    bus, desktop, phone = pair
    _product(desktop)
    customer_id = _customer(desktop)

    with desktop.database.unit_of_work() as session:
        desktop.command.submit(session, NewEvent(
            "PAYMENT_RECORDED", "Payment", uuid7_str(),
            {"payment_id": uuid7_str(), "number": "T-1", "direction": "IN",
             "amount": 5_000_000, "occurred_at": "2026-08-23T10:00:00+00:00",
             "customer_id": customer_id},
        ))

    with desktop.database.session() as session:
        owner_manifest, owner_chunks = build_snapshot(
            session, role="owner", snapshot_id="s3"
        )
        warehouse_manifest, warehouse_chunks = build_snapshot(
            session, role="warehouse", snapshot_id="s4"
        )

    import cbor2

    owner_body = cbor2.loads(b"".join(c.data for c in owner_chunks))
    warehouse_body = cbor2.loads(b"".join(c.data for c in warehouse_chunks))

    assert "payments" in owner_body["tables"]
    assert "payments" not in warehouse_body["tables"], (
        "omborchi roli moliyaviy ma'lumot oldi"
    )
    assert "customers" not in warehouse_body["tables"]
