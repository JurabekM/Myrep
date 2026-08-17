"""Unit tests: moliyaviy formulalar."""

import pytest

from app.core.exceptions import ValidationError
from app.modules.finance.calculations import (
    annuity_loan_schedule,
    break_even,
    cash_flow_summary,
    irr,
    npv,
    roe,
    roi,
    simple_forecast,
)


class TestNPV:
    def test_zero_rate_is_sum(self):
        assert npv(0.0, [-100, 50, 60]) == pytest.approx(10)

    def test_known_value(self):
        # -1000 + 500/1.1 + 500/1.21 + 500/1.331
        assert npv(0.1, [-1000, 500, 500, 500]) == pytest.approx(243.426, abs=0.01)


class TestIRR:
    def test_known_irr(self):
        # NPV=0 at ~23.375% for this flow
        rate = irr([-1000, 500, 500, 500])
        assert npv(rate, [-1000, 500, 500, 500]) == pytest.approx(0, abs=1e-4)

    def test_requires_sign_change(self):
        with pytest.raises(ValidationError):
            irr([100, 200, 300])

    def test_requires_two_periods(self):
        with pytest.raises(ValidationError):
            irr([-100])


class TestROIandROE:
    def test_roi(self):
        assert roi(150, 100) == pytest.approx(0.5)

    def test_roi_requires_positive_cost(self):
        with pytest.raises(ValidationError):
            roi(100, 0)

    def test_roe(self):
        assert roe(20, 100) == pytest.approx(0.2)


class TestBreakEven:
    def test_units_and_revenue(self):
        result = break_even(10_000, 50, 30)
        assert result.units == pytest.approx(500)
        assert result.revenue == pytest.approx(25_000)

    def test_negative_margin_rejected(self):
        with pytest.raises(ValidationError):
            break_even(1000, 10, 20)


class TestLoan:
    def test_annuity_payment(self):
        payment, schedule = annuity_loan_schedule(100_000_000, 0.24, 12)
        # Standard annuity formula check
        monthly = 0.02
        expected = 100_000_000 * monthly / (1 - (1 + monthly) ** -12)
        assert payment == pytest.approx(expected, abs=1)
        assert len(schedule) == 12
        assert schedule[-1].balance == pytest.approx(0, abs=1)

    def test_zero_rate(self):
        payment, schedule = annuity_loan_schedule(12_000, 0.0, 12)
        assert payment == pytest.approx(1000)

    def test_invalid_inputs(self):
        with pytest.raises(ValidationError):
            annuity_loan_schedule(0, 0.2, 12)
        with pytest.raises(ValidationError):
            annuity_loan_schedule(1000, -0.1, 12)


class TestCashFlow:
    def test_summary_and_negative_months(self):
        result = cash_flow_summary(100, [50, 50, 300], [200, 100, 50])
        assert result.closing_balance == pytest.approx(150)
        assert result.negative_months == [1, 2]

    def test_length_mismatch(self):
        with pytest.raises(ValidationError):
            cash_flow_summary(0, [1, 2], [1])


class TestForecast:
    def test_linear_trend(self):
        forecast = simple_forecast([10, 20, 30, 40], 2)
        assert forecast == pytest.approx([50, 60])

    def test_requires_history(self):
        with pytest.raises(ValidationError):
            simple_forecast([5], 3)
