"""Domen qoidalari testlari — narx, chegirma, qoldiq, kredit, holat mashinasi."""

from __future__ import annotations

from decimal import Decimal

import pytest

from distribos.domain.rules import (
    ORDER_TRANSITIONS,
    CreditCheck,
    DomainError,
    IllegalStateTransition,
    allocate_payment,
    assert_transition,
    available_stock,
    can_transition,
    check_credit_limit,
    check_stock_available,
    compute_order_totals,
    compute_stock,
    customer_debt,
    is_terminal,
    line_total,
    resolve_unit_price,
)
from distribos.persistence.models import MovementType, OrderState

# --- holat mashinasi ------------------------------------------------------


def test_normal_order_lifecycle() -> None:
    flow = [
        OrderState.DRAFT, OrderState.CONFIRMED, OrderState.APPROVED,
        OrderState.ALLOCATED, OrderState.PICKED, OrderState.SHIPPED,
        OrderState.DELIVERED,
    ]
    for current, target in zip(flow, flow[1:], strict=False):
        assert_transition(current, target)


def test_cannot_skip_states() -> None:
    with pytest.raises(IllegalStateTransition):
        assert_transition(OrderState.DRAFT, OrderState.SHIPPED)


def test_cannot_cancel_after_shipping() -> None:
    """Tovar ketgandan keyin bekor qilib bo'lmaydi — qaytarish kerak."""
    with pytest.raises(IllegalStateTransition):
        assert_transition(OrderState.SHIPPED, OrderState.CANCELLED)


def test_terminal_states_have_no_exit() -> None:
    for state in (OrderState.RETURNED, OrderState.CANCELLED):
        assert is_terminal(state)
        assert not ORDER_TRANSITIONS[state]
        for target in OrderState:
            assert not can_transition(state, target)


def test_transition_error_lists_allowed_targets() -> None:
    with pytest.raises(IllegalStateTransition, match="CONFIRMED"):
        assert_transition(OrderState.DRAFT, OrderState.DELIVERED)


def test_every_state_is_covered_by_the_table() -> None:
    """Yangi holat qo'shilsa jadvalga kiritish esdan chiqmasin."""
    assert set(ORDER_TRANSITIONS) == set(OrderState)


# --- narx -----------------------------------------------------------------


def test_price_tier_selection() -> None:
    prices = {"retail_price": 20000, "wholesale_price": 17000, "agent_price": 15000}
    assert resolve_unit_price(prices, "retail") == 20000
    assert resolve_unit_price(prices, "wholesale") == 17000
    assert resolve_unit_price(prices, "agent") == 15000


def test_price_falls_back_when_tier_is_unset() -> None:
    prices = {"retail_price": 20000, "wholesale_price": 0, "agent_price": 0}
    assert resolve_unit_price(prices, "agent") == 20000


def test_missing_price_is_an_error_not_zero() -> None:
    """0 so'mga sotishni jimgina ruxsat berish moliyaviy teshik ochadi."""
    with pytest.raises(DomainError):
        resolve_unit_price({"retail_price": 0, "wholesale_price": 0}, "retail")


def test_line_total_applies_discount() -> None:
    assert line_total("10", 15000, "0") == 150000
    assert line_total("10", 15000, "10") == 135000


def test_line_total_rounds_half_up() -> None:
    # 3 * 3333 = 9999; 15% chegirma -> 8499.15 -> 8499
    assert line_total("3", 3333, "15") == 8499


def test_line_total_rejects_bad_input() -> None:
    with pytest.raises(DomainError):
        line_total("-1", 1000)
    with pytest.raises(DomainError):
        line_total("1", 1000, "101")


def test_order_totals() -> None:
    totals = compute_order_totals([
        {"quantity": "10", "unit_price": 15000, "discount_percent": "10"},
        {"quantity": "2", "unit_price": 50000},
    ])
    assert totals.subtotal == 250000
    assert totals.total == 235000
    assert totals.discount_total == 15000


def test_money_stays_integral_across_many_lines() -> None:
    """1000 qatorda ham tiyin yo'qolmaydi (float bo'lganda yo'qolardi)."""
    lines = [{"quantity": "3", "unit_price": 3333, "discount_percent": "15"}] * 1000
    totals = compute_order_totals(lines)
    assert totals.total == 8499 * 1000
    assert isinstance(totals.total, int)


# --- kredit ---------------------------------------------------------------


def test_credit_limit_blocks_when_exceeded() -> None:
    result = check_credit_limit(current_debt=800_000, credit_limit=1_000_000,
                               order_total=300_000)
    assert not result.allowed
    assert result.projected_debt == 1_100_000
    assert "limit" in result.reason.lower()


def test_credit_limit_allows_within_bound() -> None:
    assert check_credit_limit(500_000, 1_000_000, 300_000).allowed


def test_zero_credit_limit_means_unlimited() -> None:
    assert check_credit_limit(9_000_000, 0, 5_000_000).allowed


def test_advance_payment_is_negative_debt() -> None:
    result = check_credit_limit(-200_000, 1_000_000, 300_000)
    assert result.allowed
    assert result.projected_debt == 100_000


# --- ombor ----------------------------------------------------------------


def test_stock_computed_from_movements_not_overwritten() -> None:
    on_hand, reserved = compute_stock([
        (MovementType.RECEIPT, "100"),
        (MovementType.SALE, "30"),
        (MovementType.RETURN_IN, "5"),
        (MovementType.WRITE_OFF, "2"),
    ])
    assert on_hand == Decimal(73)
    assert reserved == Decimal(0)


def test_concurrent_sales_both_count() -> None:
    """Ikki qurilma bir vaqtda sotdi — ikkala harakat ham saqlanadi.

    Bu «yo'qolgan yangilanish» muammosining yechimi: qoldiq overwrite
    qilinmaydi, harakatlar qo'shiladi.
    """
    on_hand, _ = compute_stock([
        (MovementType.RECEIPT, "100"),
        (MovementType.SALE, "30"),   # desktop
        (MovementType.SALE, "40"),   # telefon, offline edi
    ])
    assert on_hand == Decimal(30)


def test_reservation_reduces_available_but_not_on_hand() -> None:
    on_hand, reserved = compute_stock([
        (MovementType.RECEIPT, "100"),
        (MovementType.RESERVATION, "25"),
    ])
    assert on_hand == Decimal(100)
    assert reserved == Decimal(25)
    assert available_stock(on_hand, reserved) == Decimal(75)


def test_release_frees_reservation() -> None:
    _, reserved = compute_stock([
        (MovementType.RECEIPT, "100"),
        (MovementType.RESERVATION, "25"),
        (MovementType.RELEASE, "10"),
    ])
    assert reserved == Decimal(15)


def test_negative_adjustment_is_allowed() -> None:
    on_hand, _ = compute_stock([
        (MovementType.RECEIPT, "50"),
        (MovementType.ADJUSTMENT, "-8"),
    ])
    assert on_hand == Decimal(42)


def test_stock_check_blocks_oversell() -> None:
    assert not check_stock_available(Decimal(10), Decimal(0), "11")
    assert check_stock_available(Decimal(10), Decimal(0), "10")


def test_stock_check_respects_reservation() -> None:
    assert not check_stock_available(Decimal(10), Decimal(5), "6")


def test_oversell_allowed_when_explicitly_enabled() -> None:
    assert check_stock_available(Decimal(0), Decimal(0), "5", allow_negative=True)


def test_unknown_movement_type_rejected() -> None:
    with pytest.raises(DomainError):
        compute_stock([("TELEPORT", "5")])


# --- moliya ---------------------------------------------------------------


def test_customer_debt() -> None:
    assert customer_debt(1_000_000, 400_000, 100_000) == 500_000


def test_payment_allocated_oldest_first() -> None:
    allocations = allocate_payment(500_000, [("o1", 300_000), ("o2", 400_000)])
    assert allocations == [("o1", 300_000), ("o2", 200_000)]


def test_payment_surplus_is_not_allocated() -> None:
    """Ortiqcha summa avans bo'lib qoladi, majburan taqsimlanmaydi."""
    allocations = allocate_payment(1_000_000, [("o1", 300_000)])
    assert allocations == [("o1", 300_000)]
    assert sum(amount for _, amount in allocations) == 300_000


def test_payment_skips_settled_orders() -> None:
    allocations = allocate_payment(100_000, [("o1", 0), ("o2", 250_000)])
    assert allocations == [("o2", 100_000)]


def test_negative_payment_rejected() -> None:
    with pytest.raises(DomainError):
        allocate_payment(-1, [])


def test_credit_check_is_immutable() -> None:
    result = CreditCheck(True, 0, 0, 0)
    with pytest.raises(AttributeError):
        result.allowed = False  # type: ignore[misc]
