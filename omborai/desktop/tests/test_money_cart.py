import uuid
from decimal import Decimal

import pytest

from omborai_desktop.cart import Cart
from omborai_desktop.money import format_qty, format_som, round_som

SUT = {"id": str(uuid.uuid4()), "name": "Sut 1 L", "unit": "dona", "sale_price": 12000}
SHAKAR = {"id": str(uuid.uuid4()), "name": "Shakar 1 kg", "unit": "kg", "sale_price": 14500}


def test_format_som_uses_space_thousands():
    assert format_som(14500) == "14 500"
    assert format_som(1234567) == "1 234 567"
    assert format_som(-2000) == "-2 000"


def test_round_som_is_half_up():
    assert round_som(Decimal("2.5")) == 3
    assert round_som(Decimal("2.4")) == 2


def test_format_qty_drops_trailing_zeros():
    assert format_qty(Decimal("2.000")) == "2"
    assert format_qty(Decimal("1.500")) == "1.5"


def test_cart_merges_same_product_and_computes_totals():
    cart = Cart()
    cart.add(SUT)
    cart.add(SUT)
    cart.add(SHAKAR, Decimal("1.5"))

    assert len(cart.lines) == 2
    assert cart.lines[0].qty == Decimal(2)
    assert cart.subtotal == 2 * 12000 + round_som(Decimal("1.5") * 14500)
    assert cart.total == cart.subtotal


def test_cart_discount_validation_and_total():
    cart = Cart()
    cart.add(SUT, Decimal(2))
    cart.set_discount(1000)
    assert cart.total == 23000
    with pytest.raises(ValueError):
        cart.set_discount(999999)
    with pytest.raises(ValueError):
        cart.set_discount(-1)


def test_cart_set_qty_zero_removes_line():
    cart = Cart()
    cart.add(SUT, Decimal(3))
    cart.set_qty(SUT["id"], Decimal(0))
    assert cart.is_empty


def test_sale_payload_never_contains_prices():
    cart = Cart()
    cart.add(SUT, Decimal(2))
    payload = cart.to_sale_payload(str(uuid.uuid4()), [("cash", 24000)])

    assert uuid.UUID(payload["id"])
    assert payload["items"] == [{"product_id": SUT["id"], "qty": "2"}]
    assert "sale_price" not in str(payload) and "unit_price" not in str(payload)
    assert payload["payments"] == [{"method": "cash", "amount": 24000}]


def test_sale_payload_reuses_given_id_for_retries():
    cart = Cart()
    cart.add(SUT)
    sale_id = uuid.uuid4()
    first = cart.to_sale_payload(str(uuid.uuid4()), [("cash", 12000)], sale_id=sale_id)
    second = cart.to_sale_payload(str(uuid.uuid4()), [("cash", 12000)], sale_id=sale_id)
    assert first["id"] == second["id"] == str(sale_id)
