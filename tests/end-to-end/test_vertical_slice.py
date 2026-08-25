"""1-bosqich vertical slice: offline buyurtma desktop'da paydo bo'ladi.

Bu test butun zanjirni bosib o'tadi — lokal baza, outbox, AETHER-Q muhri,
transport, inbox, deduplikatsiya, proyektor, application ACK.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.domain.ids import uuid7_str
from distribos.persistence.models import (
    DeliveryState,
    InboxEntry,
    Order,
    OrderLine,
    OutboxEntry,
    Product,
)
from distribos.sync.event_store import NewEvent
from harness import shared_tenant_setup


@pytest.fixture
def cluster():
    bus, _tenant_id, (desktop, phone) = shared_tenant_setup("desktop-1", "android-1")
    return bus, desktop, phone


def _seed_catalog(node) -> tuple[str, str]:
    """Desktop'da mahsulot va mijoz yaratadi."""
    product_id, customer_id = uuid7_str(), uuid7_str()
    with node.database.unit_of_work() as session:
        node.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "COLA-1L", "name": "Cola 1L",
             "unit": "dona", "wholesale_price": 1_500_000, "retail_price": 1_800_000},
        ))
        node.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "M-001", "name": "Dilshod savdo",
             "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 0},
        ))
    return product_id, customer_id


def _create_order(node, customer_id: str, product_id: str, *, quantity: str = "10") -> str:
    order_id = uuid7_str()
    with node.database.unit_of_work() as session:
        node.command.submit(session, NewEvent(
            "ORDER_CREATED", "Order", order_id,
            {
                "order_id": order_id, "number": f"B-{order_id[-12:]}",
                "customer_id": customer_id, "ordered_at": "2026-08-23T10:00:00+00:00",
                "lines": [{"line_id": uuid7_str(), "product_id": product_id,
                           "quantity": quantity, "unit_price": 1_500_000}],
            },
        ))
    return order_id


# --- asosiy ssenariy ------------------------------------------------------


def test_offline_order_reaches_desktop_after_reconnect(cluster) -> None:
    bus, desktop, phone = cluster
    product_id, customer_id = _seed_catalog(desktop)
    desktop.sync()

    # Telefon katalogni oldi.
    with phone.database.session() as session:
        assert session.get(Product, product_id) is not None

    # --- internet o'chdi ---
    bus.set_online(phone.device_id, False)

    order_id = _create_order(phone, customer_id, product_id)

    # Offline bo'lsa ham lokal baza yozildi (topshiriq §7.1, 1-8 bosqich).
    with phone.database.session() as session:
        assert session.get(Order, order_id) is not None
        outbox = session.query(OutboxEntry).count()
        assert outbox >= 1

    # Desktop hali ko'rmaydi.
    with desktop.database.session() as session:
        assert session.get(Order, order_id) is None

    # --- internet qaytdi ---
    bus.set_online(phone.device_id, True)
    phone.sync()

    with desktop.database.session() as session:
        order = session.get(Order, order_id)
        assert order is not None, "Buyurtma desktop'da paydo bo'lmadi"
        assert order.total == 15_000_000
        lines = session.query(OrderLine).filter_by(order_id=order_id).all()
        assert len(lines) == 1


def test_application_ack_marks_peer_applied(cluster) -> None:
    """Broker ACK emas, PEER QO'LLADI degan holat."""
    _bus, desktop, phone = cluster
    product_id, customer_id = _seed_catalog(desktop)
    desktop.sync()

    _create_order(phone, customer_id, product_id)
    phone.sync()

    with phone.database.session() as session:
        entry = session.query(OutboxEntry).filter_by(
            event_id=session.query(OutboxEntry.event_id)
            .order_by(OutboxEntry.id.desc()).first()[0]
        ).one()
        assert entry.state == DeliveryState.PEER_APPLIED, (
            f"ACK kelmadi, holat: {entry.state}"
        )


def test_identical_envelope_stopped_by_replay_window(cluster) -> None:
    """Bir xil envelope 10 marta kelsa — kripto qatlami rad etadi.

    Bu inbox'gacha yetib bormaydi: DES-1 replay oynasi `(epoch, device,
    seq)` bo'yicha allaqachon ko'rilgan xabarni to'xtatadi.
    """
    bus, desktop, phone = cluster
    product_id, customer_id = _seed_catalog(desktop)
    desktop.sync()

    bus.duplicate_factor = 10
    order_id = _create_order(phone, customer_id, product_id)
    phone.sync()

    with desktop.database.session() as session:
        assert session.query(Order).filter_by(id=order_id).count() == 1
        assert session.query(OrderLine).filter_by(order_id=order_id).count() == 1

    assert desktop.engine.stats.rejections.get("REPLAY", 0) >= 9, (
        f"replay oynasi ishlamadi: {desktop.engine.stats.rejections}"
    )


def test_resent_event_deduplicated_by_inbox(cluster) -> None:
    """Hodisa YANGI envelope ichida qayta kelsa — inbox dedup qiladi.

    Anti-entropy tiklashda aynan shunday bo'ladi: hodisa qayta muhrlanadi
    (yangi nonce, ya'ni replay oynasi uni to'xtatmaydi), lekin `event_id`
    o'zgarmaydi. Biznes natijasi baribir BIR marta qo'llanishi kerak.
    """
    _bus, desktop, phone = cluster
    product_id, customer_id = _seed_catalog(desktop)
    desktop.sync()

    order_id = _create_order(phone, customer_id, product_id)
    phone.sync()

    # Aynan shu hodisani qo'lda QAYTA muhrlab yuboramiz.
    import cbor2
    from distribos.aether_q.provider import ContentType
    from distribos.persistence.models import EventLog

    with phone.database.session() as session:
        record = session.query(EventLog).filter_by(
            aggregate_id=order_id, event_type="ORDER_CREATED"
        ).one()
        payload = cbor2.dumps({
            "events": [phone.engine._event_to_dict(record)]
        })

    envelope = phone.provider.seal_message(payload, ContentType.EVENT_BATCH)
    desktop.engine.handle_inbound(envelope.wire)

    with desktop.database.session() as session:
        assert session.query(Order).filter_by(id=order_id).count() == 1
        assert session.query(OrderLine).filter_by(order_id=order_id).count() == 1
        duplicates = session.query(InboxEntry).filter(
            InboxEntry.duplicate_count > 0
        ).all()
        assert duplicates, "inbox dublikatni tanimadi"

    assert desktop.engine.stats.duplicates >= 1


def test_out_of_order_delivery_still_converges(cluster) -> None:
    """Tartib buzilsa ham yakuniy holat to'g'ri."""
    bus, desktop, phone = cluster
    product_id, customer_id = _seed_catalog(desktop)
    desktop.sync()

    bus.set_online(phone.device_id, False)
    order_ids = [_create_order(phone, customer_id, product_id) for _ in range(3)]

    bus.reorder = True
    bus.set_online(phone.device_id, True)
    phone.sync(rounds=5)

    with desktop.database.session() as session:
        for order_id in order_ids:
            assert session.get(Order, order_id) is not None


def test_stock_is_computed_from_movements(cluster) -> None:
    _bus, desktop, phone = cluster
    product_id, _ = _seed_catalog(desktop)
    warehouse_id = uuid7_str()

    from distribos.persistence.models import StockSnapshot, Warehouse

    for node in (desktop, phone):
        with node.database.unit_of_work() as session:
            session.add(Warehouse(id=warehouse_id, name="Asosiy", code="W1"))

    for movement_type, quantity in (("RECEIPT", "100"), ("SALE", "30"), ("RETURN_IN", "5")):
        with desktop.database.unit_of_work() as session:
            desktop.command.submit(session, NewEvent(
                "INVENTORY_MOVED", "Inventory", product_id,
                {"movement_id": uuid7_str(), "warehouse_id": warehouse_id,
                 "product_id": product_id, "movement_type": movement_type,
                 "quantity": quantity, "occurred_at": "2026-08-23T10:00:00+00:00"},
            ))

    desktop.sync(rounds=4)

    with desktop.database.session() as session:
        snapshot = session.get(StockSnapshot, (warehouse_id, product_id))
        assert snapshot is not None
        assert float(snapshot.quantity) == 75.0


def test_no_plaintext_business_data_on_the_wire(cluster) -> None:
    """Simga chiqqan XOM baytlarda ochiq biznes matni bo'lmasligi kerak."""
    bus, desktop, _phone = cluster
    _seed_catalog(desktop)
    desktop.sync()

    assert bus.wire_log, "hech narsa yuborilmadi"
    blob = b"".join(bus.wire_log)
    for secret in (b"Cola 1L", b"Dilshod savdo", b"COLA-1L", b"M-001"):
        assert secret not in blob, f"Ochiq matn simga chiqdi: {secret!r}"
