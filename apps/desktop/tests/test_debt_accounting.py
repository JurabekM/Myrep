"""Qarzdorlik hisobi testlari.

Bu testlar haqiqiy xatodan keyin yozildi: taqsimlanmagan to'lov mijoz
qarzini kamaytirmayotgan edi. Real savdoda mijoz ko'pincha «hisobga»
umumiy summa to'laydi va uni hech qaysi buyurtmaga biriktirmaydi —
o'shanda ham qarzi kamayishi SHART.
"""

from __future__ import annotations

import pytest

from distribos.application import queries
from distribos.application.command_service import CommandService
from distribos.application.projector import Projector
from distribos.domain.ids import HybridClock, new_device_id, new_tenant_id, uuid7_str
from distribos.persistence.base import Database
from distribos.persistence.triggers import install_triggers
from distribos.reports import builders
from distribos.sync.event_store import EventStore, NewEvent


@pytest.fixture
def shop():
    database = Database.in_memory()
    database.create_all()
    install_triggers(database.engine)

    device_id, tenant_id = new_device_id(), new_tenant_id()
    store = EventStore(device_id, tenant_id, HybridClock(device_id.hex()[:8]))
    command = CommandService(store, Projector(), actor_role="owner")

    product_id, customer_id = uuid7_str(), uuid7_str()
    with database.unit_of_work() as session:
        command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "P-1", "name": "Mahsulot",
             "unit": "dona", "wholesale_price": 1_000_000},
        ))
        command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "C-1", "name": "Mijoz",
             "kind": "COMPANY", "credit_limit": 10_000_000},
        ))
    return database, command, product_id, customer_id


def _order(database, command, customer_id, product_id, quantity="10") -> str:
    order_id = uuid7_str()
    with database.unit_of_work() as session:
        command.submit(session, NewEvent(
            "ORDER_CREATED", "Order", order_id,
            {"order_id": order_id, "number": f"B-{order_id[-10:]}",
             "customer_id": customer_id, "ordered_at": "2026-08-23T10:00:00+00:00",
             "lines": [{"line_id": uuid7_str(), "product_id": product_id,
                        "quantity": quantity, "unit_price": 1_000_000}]},
        ))
    return order_id


def _payment(database, command, customer_id, amount, direction="IN") -> str:
    payment_id = uuid7_str()
    with database.unit_of_work() as session:
        command.submit(session, NewEvent(
            "PAYMENT_RECORDED", "Payment", payment_id,
            {"payment_id": payment_id, "number": f"T-{payment_id[-10:]}",
             "direction": direction, "amount": amount,
             "occurred_at": "2026-08-23T11:00:00+00:00",
             "customer_id": customer_id},
        ))
    return payment_id


def test_order_creates_debt(shop) -> None:
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 10_000_000


def test_unallocated_payment_reduces_debt(shop) -> None:
    """Buyurtmaga biriktirilmagan to'lov ham qarzni kamaytiradi."""
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    _payment(database, command, customer_id, 4_000_000)

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 6_000_000
        row = next(c for c in queries.list_customers(session) if c.id == customer_id)
        assert row.debt == 6_000_000


def test_full_payment_clears_debt(shop) -> None:
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    _payment(database, command, customer_id, 10_000_000)

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 0


def test_overpayment_becomes_advance(shop) -> None:
    """Ortiqcha to'lov manfiy qarz — ya'ni avans."""
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    _payment(database, command, customer_id, 12_000_000)

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == -2_000_000


def test_reversal_restores_debt(shop) -> None:
    """To'lov bekor qilinsa qarz QAYTADI.

    Bekor qilish teskari yozuv yaratadi, ya'ni yig'indi o'z-o'zidan
    to'g'rilanadi — alohida `is_reversed` filtri kerak emas.
    """
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    payment_id = _payment(database, command, customer_id, 4_000_000)

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 6_000_000

    reversal_id = uuid7_str()
    with database.unit_of_work() as session:
        command.submit(session, NewEvent(
            "PAYMENT_REVERSED", "Payment", reversal_id,
            {"payment_id": reversal_id, "reverses_payment_id": payment_id,
             "number": f"R-{reversal_id[-10:]}", "amount": 4_000_000,
             "occurred_at": "2026-08-23T12:00:00+00:00", "reason": "xato"},
        ))

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 10_000_000


def test_cash_out_increases_debt(shop) -> None:
    """Mijozga pul qaytarilsa (OUT) qarzi oshadi."""
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    _payment(database, command, customer_id, 10_000_000)
    _payment(database, command, customer_id, 3_000_000, direction="OUT")

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 3_000_000


def test_cancelled_order_excluded_from_debt(shop) -> None:
    database, command, product_id, customer_id = shop
    order_id = _order(database, command, customer_id, product_id)

    with database.unit_of_work() as session:
        command.submit(session, NewEvent(
            "ORDER_STATE_CHANGED", "Order", order_id,
            {"order_id": order_id, "from_state": "DRAFT", "to_state": "CANCELLED"},
        ))

    with database.session() as session:
        assert queries.customer_debt(session, customer_id) == 0


def test_debt_report_matches_query(shop) -> None:
    """Hisobot va ekrandagi raqam BIR XIL bo'lishi kerak."""
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    _payment(database, command, customer_id, 4_000_000)

    with database.session() as session:
        expected = queries.customer_debt(session, customer_id)
        report = builders.debt_report(session)

    assert report.rows, "qarzdorlik hisoboti bo'sh"
    from distribos.presentation.status import money

    assert report.rows[0][4] == money(expected)


def test_sales_by_customer_report_uses_real_payments(shop) -> None:
    database, command, product_id, customer_id = shop
    _order(database, command, customer_id, product_id)
    _payment(database, command, customer_id, 4_000_000)

    with database.session() as session:
        report = builders.sales_by_customer(session)

    from distribos.presentation.status import money

    assert report.rows[0][4] == money(4_000_000), "to'langan summa ko'rinmadi"
    assert report.rows[0][5] == money(6_000_000), "qarz noto'g'ri"


def test_credit_limit_uses_real_debt(shop) -> None:
    """Kredit limiti tekshiruvi to'lovni hisobga olishi kerak."""
    database, command, product_id, customer_id = shop
    for _ in range(2):
        _order(database, command, customer_id, product_id)   # jami 20 mln, limit 10 mln
    _payment(database, command, customer_id, 15_000_000)

    with database.session() as session:
        row = next(c for c in queries.list_customers(session) if c.id == customer_id)

    assert row.debt == 5_000_000
    assert not row.over_limit, "to'lovdan keyin limit oshgan deb ko'rsatildi"
