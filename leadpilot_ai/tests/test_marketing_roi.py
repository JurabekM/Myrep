"""Marketing ROI formulas and the attribution worksheet."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.services import analytics_service
from app.services.analytics_service import PeriodFilter
from app.utils.dates import today


# --------------------------------------------------------------------------- #
# Pure formulas
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "sales,leads,expected",
    [(10, 100, 10.0), (0, 100, 0.0), (5, 5, 100.0), (1, 0, 0.0)],
)
def test_conversion_rate(sales: int, leads: int, expected: float) -> None:
    """``Sotuvlar / Leadlar × 100`` with a safe division by zero."""
    assert analytics_service.conversion_rate(sales, leads) == pytest.approx(expected)


@pytest.mark.parametrize(
    "cost,leads,expected",
    [(1_000_000, 50, 20_000.0), (0, 10, 0.0), (500_000, 0, 0.0)],
)
def test_cost_per_lead(cost: float, leads: int, expected: float) -> None:
    """``Reklama xarajati / Leadlar``."""
    assert analytics_service.cost_per_lead(cost, leads) == pytest.approx(expected)


def test_cost_per_booking() -> None:
    """``Reklama xarajati / Bronlar``."""
    assert analytics_service.cost_per_booking(900_000, 9) == pytest.approx(100_000)
    assert analytics_service.cost_per_booking(900_000, 0) == 0.0


def test_cost_per_sale() -> None:
    """``Reklama xarajati / Sotuvlar``."""
    assert analytics_service.cost_per_sale(1_200_000, 4) == pytest.approx(300_000)
    assert analytics_service.cost_per_sale(1_200_000, 0) == 0.0


@pytest.mark.parametrize(
    "revenue,cost,expected",
    [(4_000_000, 1_000_000, 4.0), (1_000_000, 4_000_000, 0.25), (1_000_000, 0, 0.0)],
)
def test_roas(revenue: float, cost: float, expected: float) -> None:
    """``Daromad / Reklama xarajati``."""
    assert analytics_service.roas(revenue, cost) == pytest.approx(expected)


# --------------------------------------------------------------------------- #
# Row aggregation
# --------------------------------------------------------------------------- #
def _row(**kwargs) -> analytics_service.MarketingRow:
    """Build a marketing row for arithmetic checks."""
    base = {
        "key": "1:1",
        "source_id": 1,
        "campaign_id": 1,
        "source_name": "Instagram Ads",
        "campaign_name": "Avgust",
    }
    base.update(kwargs)
    return analytics_service.MarketingRow(**base)


def test_marketing_row_derived_metrics() -> None:
    """Derived properties use the documented formulas."""
    row = _row(leads=100, bookings=25, sales=10, revenue=10_000_000, cost=2_000_000)
    assert row.conversion == pytest.approx(10.0)
    assert row.cpl == pytest.approx(20_000)
    assert row.cpb == pytest.approx(80_000)
    assert row.cps == pytest.approx(200_000)
    assert row.roas == pytest.approx(5.0)


def test_marketing_row_handles_zero_division() -> None:
    """An empty campaign never raises."""
    row = _row()
    assert row.conversion == 0.0
    assert row.cpl == 0.0
    assert row.roas == 0.0


def test_demo_dataset_produces_attribution_rows() -> None:
    """The seeded demo data yields a populated worksheet."""
    flt = PeriodFilter(date_from=today() - timedelta(days=120), date_to=today())
    rows = analytics_service.marketing_rows(flt)
    assert rows
    assert sum(row.leads for row in rows) > 0
    assert any(row.cost > 0 for row in rows)


def test_drill_down_returns_the_source_leads() -> None:
    """Opening a row lists the leads it is built from."""
    flt = PeriodFilter(date_from=today() - timedelta(days=120), date_to=today())
    rows = analytics_service.marketing_rows(flt)
    target = next(row for row in rows if row.leads > 0 and row.source_id)
    leads = analytics_service.leads_of_source(
        flt, source_id=target.source_id, campaign_id=target.campaign_id
    )
    assert len(leads) == target.leads


def test_workspace_summary_matches_the_lead_table() -> None:
    """Headline KPIs are consistent with the underlying leads."""
    flt = PeriodFilter(date_from=today() - timedelta(days=120), date_to=today())
    summary = analytics_service.workspace_summary(flt)
    rows = analytics_service.marketing_rows(flt)
    assert summary["leads"] >= sum(row.leads for row in rows) - 1
    assert summary["conversion"] >= 0
