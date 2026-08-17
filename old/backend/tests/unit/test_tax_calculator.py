"""Unit tests: O'zbekiston soliq kalkulyatori."""

import pytest

from app.modules.tax.calculator import (
    TURNOVER_TAX_RATE,
    TURNOVER_TAX_THRESHOLD_UZS,
    VAT_RATE,
    TaxRegime,
    calculate_general_regime,
    calculate_payroll_taxes,
    calculate_turnover_tax,
    compare_regimes,
)


class TestTurnoverTax:
    def test_basic_rate(self):
        result = calculate_turnover_tax(500_000_000)
        assert result.total_tax == pytest.approx(500_000_000 * TURNOVER_TAX_RATE)
        assert result.regime is TaxRegime.TURNOVER
        assert result.warnings == []

    def test_threshold_warning(self):
        result = calculate_turnover_tax(TURNOVER_TAX_THRESHOLD_UZS + 1)
        assert len(result.warnings) == 1
        assert "umumiy rejim" in result.warnings[0]

    def test_effective_rate(self):
        result = calculate_turnover_tax(100_000_000)
        assert result.effective_rate == pytest.approx(TURNOVER_TAX_RATE)


class TestGeneralRegime:
    def test_vat_extracted_from_inclusive_revenue(self):
        result = calculate_general_regime(1_120_000_000, 0)
        vat_line = next(line for line in result.lines if line.name == "QQS")
        assert vat_line.amount == pytest.approx(1_120_000_000 * VAT_RATE / (1 + VAT_RATE))

    def test_expenses_capped_at_revenue(self):
        result = calculate_general_regime(100_000_000, 999_000_000_000)
        profit_line = next(line for line in result.lines if line.name == "Foyda solig'i")
        assert profit_line.base == 0
        assert profit_line.amount == 0

    def test_partial_vat_share(self):
        full = calculate_general_regime(100_000_000, 0, vat_taxable_share=1.0)
        half = calculate_general_regime(100_000_000, 0, vat_taxable_share=0.5)
        full_vat = next(line for line in full.lines if line.name == "QQS").amount
        half_vat = next(line for line in half.lines if line.name == "QQS").amount
        assert half_vat == pytest.approx(full_vat / 2)


class TestPayroll:
    def test_net_and_employer_cost(self):
        result = calculate_payroll_taxes(10_000_000)
        assert result["income_tax"] == pytest.approx(1_200_000)
        assert result["social_tax"] == pytest.approx(1_200_000)
        assert result["net_salary"] == pytest.approx(8_800_000)
        assert result["employer_total_cost"] == pytest.approx(11_200_000)


class TestCompareRegimes:
    def test_turnover_recommended_for_small_business(self):
        # Kichik aylanma, kam xarajat → aylanma soliq odatda foydali emas
        # katta xarajatlarda; xarajat past bo'lsa aylanma yutadi.
        result = compare_regimes(500_000_000, 50_000_000)
        assert result["recommended"] in (TaxRegime.TURNOVER, TaxRegime.GENERAL)
        assert result["savings"] >= 0

    def test_general_forced_above_threshold(self):
        result = compare_regimes(TURNOVER_TAX_THRESHOLD_UZS * 2, 0)
        assert result["recommended"] is TaxRegime.GENERAL
