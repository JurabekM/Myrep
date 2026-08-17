"""Soliq kalkulyatori testlari."""

import pytest

from app.services.calculators.tax_calculator import (
    TURNOVER_TAX_RATE,
    TURNOVER_TAX_THRESHOLD_UZS,
    VAT_RATE,
    TaxRegime,
    calculate_general_regime,
    calculate_payroll,
    calculate_turnover_tax,
    compare_regimes,
)


def test_turnover_basic_rate():
    result = calculate_turnover_tax(500_000_000)
    assert result.total_tax == pytest.approx(500_000_000 * TURNOVER_TAX_RATE)
    assert result.regime is TaxRegime.TURNOVER
    assert result.warnings == []


def test_turnover_threshold_warning():
    result = calculate_turnover_tax(TURNOVER_TAX_THRESHOLD_UZS + 1)
    assert len(result.warnings) == 1


def test_general_vat_from_inclusive():
    result = calculate_general_regime(1_120_000_000, 0)
    vat_line = next(ln for ln in result.lines if ln.name == "QQS")
    assert vat_line.amount == pytest.approx(1_120_000_000 * VAT_RATE / (1 + VAT_RATE))


def test_general_expenses_capped():
    result = calculate_general_regime(100_000_000, 999_000_000_000)
    profit_line = next(ln for ln in result.lines if ln.name == "Foyda solig'i")
    assert profit_line.amount == 0


def test_payroll():
    result = calculate_payroll(10_000_000)
    assert result["income_tax"] == pytest.approx(1_200_000)
    assert result["net_salary"] == pytest.approx(8_800_000)
    assert result["employer_total_cost"] == pytest.approx(11_200_000)


def test_compare_forces_general_above_threshold():
    result = compare_regimes(TURNOVER_TAX_THRESHOLD_UZS * 2, 0)
    assert result["recommended"] is TaxRegime.GENERAL
    assert result["savings"] >= 0
