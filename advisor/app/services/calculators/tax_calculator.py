"""O'zbekiston soliq kalkulyatori — deterministik hisob-kitob.

Stavkalar 2026 yil holatiga ko'ra versiyalangan konstantalar. AI faqat
natijani tushuntiradi; raqamlar har doim shu kod orqali hisoblanadi (soliq
raqamlarida hallucination bo'lmasligi uchun).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

TAX_RATES_VERSION = "2026-01"

VAT_RATE = 0.12                      # QQS
TURNOVER_TAX_RATE = 0.04             # Aylanma soliq (asosiy)
PROFIT_TAX_RATE = 0.15              # Foyda solig'i (asosiy)
PERSONAL_INCOME_TAX_RATE = 0.12     # JShDS
SOCIAL_TAX_RATE = 0.12              # Ijtimoiy soliq (asosiy)

# Aylanma soliqdan umumiy rejimga majburiy o'tish chegarasi (yillik, so'm)
TURNOVER_TAX_THRESHOLD_UZS = 1_000_000_000


class TaxRegime(str, Enum):
    TURNOVER = "turnover"   # Aylanma soliq
    GENERAL = "general"     # Umumiy rejim (QQS + foyda solig'i)


@dataclass(frozen=True)
class TaxLine:
    name: str
    base: float
    rate: float
    amount: float
    note: str = ""


@dataclass
class TaxResult:
    regime: TaxRegime
    annual_revenue: float
    lines: list[TaxLine]
    total_tax: float
    effective_rate: float
    warnings: list[str] = field(default_factory=list)
    rates_version: str = TAX_RATES_VERSION


def calculate_turnover_tax(annual_revenue: float) -> TaxResult:
    warnings: list[str] = []
    if annual_revenue > TURNOVER_TAX_THRESHOLD_UZS:
        warnings.append(
            "Yillik aylanma 1 mlrd so'mdan oshgan — umumiy rejimga (QQS + foyda "
            "solig'i) o'tish majburiy."
        )
    tax = annual_revenue * TURNOVER_TAX_RATE
    lines = [
        TaxLine(
            "Aylanma soliq", annual_revenue, TURNOVER_TAX_RATE, tax,
            "Asosiy stavka 4% (faoliyat turiga qarab farq qilishi mumkin)",
        )
    ]
    return TaxResult(
        TaxRegime.TURNOVER, annual_revenue, lines, tax,
        tax / annual_revenue if annual_revenue else 0.0, warnings,
    )


def calculate_general_regime(
    annual_revenue: float, deductible_expenses: float, *, vat_taxable_share: float = 1.0
) -> TaxResult:
    deductible_expenses = min(deductible_expenses, annual_revenue)
    vat_base = annual_revenue * max(min(vat_taxable_share, 1.0), 0.0)
    # Aylanma QQS ichida deb hisoblanadi: QQS = baza * 12/112
    vat = vat_base * VAT_RATE / (1 + VAT_RATE)
    profit = max(annual_revenue - vat - deductible_expenses, 0.0)
    profit_tax = profit * PROFIT_TAX_RATE
    lines = [
        TaxLine("QQS", vat_base, VAT_RATE, vat, "Aylanma QQS ichida (12/112)"),
        TaxLine("Foyda solig'i", profit, PROFIT_TAX_RATE, profit_tax),
    ]
    total = vat + profit_tax
    return TaxResult(
        TaxRegime.GENERAL, annual_revenue, lines, total,
        total / annual_revenue if annual_revenue else 0.0,
    )


def calculate_payroll(gross_monthly_salary: float) -> dict:
    income_tax = gross_monthly_salary * PERSONAL_INCOME_TAX_RATE
    social_tax = gross_monthly_salary * SOCIAL_TAX_RATE
    return {
        "gross": gross_monthly_salary,
        "income_tax": income_tax,
        "social_tax": social_tax,
        "net_salary": gross_monthly_salary - income_tax,
        "employer_total_cost": gross_monthly_salary + social_tax,
        "rates_version": TAX_RATES_VERSION,
    }


def compare_regimes(annual_revenue: float, deductible_expenses: float) -> dict:
    turnover = calculate_turnover_tax(annual_revenue)
    general = calculate_general_regime(annual_revenue, deductible_expenses)
    recommended = (
        TaxRegime.TURNOVER
        if turnover.total_tax <= general.total_tax
        and annual_revenue <= TURNOVER_TAX_THRESHOLD_UZS
        else TaxRegime.GENERAL
    )
    return {
        "turnover": turnover,
        "general": general,
        "recommended": recommended,
        "savings": abs(turnover.total_tax - general.total_tax),
    }
