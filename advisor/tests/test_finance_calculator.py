"""Moliya kalkulyatori testlari."""

import pytest

from app.core.exceptions import ValidationError
from app.services.calculators.finance_calculator import (
    annuity_loan,
    break_even,
    cash_flow,
    irr,
    npv,
    roi,
)


def test_npv_zero_rate():
    assert npv(0.0, [-100, 50, 60]) == pytest.approx(10)


def test_irr_matches_npv_zero():
    flows = [-1000, 500, 500, 500]
    rate = irr(flows)
    assert npv(rate, flows) == pytest.approx(0, abs=1e-4)


def test_irr_requires_sign_change():
    with pytest.raises(ValidationError):
        irr([100, 200, 300])


def test_roi():
    assert roi(150, 100) == pytest.approx(0.5)


def test_break_even():
    result = break_even(10_000, 50, 30)
    assert result.units == pytest.approx(500)
    assert result.revenue == pytest.approx(25_000)


def test_break_even_negative_margin():
    with pytest.raises(ValidationError):
        break_even(1000, 10, 20)


def test_annuity_loan_amortizes_to_zero():
    payment, schedule = annuity_loan(100_000_000, 0.24, 12)
    assert len(schedule) == 12
    assert schedule[-1].balance == pytest.approx(0, abs=1)
    assert payment > 0


def test_annuity_zero_rate():
    payment, _ = annuity_loan(12_000, 0.0, 12)
    assert payment == pytest.approx(1000)


def test_cash_flow_negative_months():
    result = cash_flow(100, [50, 50, 300], [200, 100, 50])
    assert result.negative_months == [1, 2]
    assert result.closing_balance == pytest.approx(150)
