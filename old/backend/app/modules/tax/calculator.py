"""O'zbekiston soliq kalkulyatori — deterministic hisob-kitob.

Stavkalar 2026 yil holatiga ko'ra konstanta sifatida versiyalangan; o'zgarsa
shu modul yangilanadi va `TAX_RATES_VERSION` oshiriladi. AI tushuntirish
beradi, ammo raqamlar har doim shu kod orqali hisoblanadi (hallucination
bo'lmasligi uchun).
"""

from dataclasses import dataclass
from enum import StrEnum

TAX_RATES_VERSION = "2026-01"

# --- Stavkalar ---
VAT_RATE = 0.12  # QQS
TURNOVER_TAX_RATE = 0.04  # Aylanma soliq (asosiy stavka)
PROFIT_TAX_RATE = 0.15  # Foyda solig'i (asosiy)
PERSONAL_INCOME_TAX_RATE = 0.12  # Jismoniy shaxslar daromad solig'i
SOCIAL_TAX_RATE = 0.12  # Ijtimoiy soliq (asosiy)
DIVIDEND_TAX_RESIDENT = 0.05  # Rezident dividend solig'i

# Aylanma soliq → umumiy rejimga majburiy o'tish chegarasi (yillik aylanma, so'm)
TURNOVER_TAX_THRESHOLD_UZS = 1_000_000_000


class TaxRegime(StrEnum):
    TURNOVER = "turnover"  # Aylanma soliq (kichik biznes)
    GENERAL = "general"  # Umumiy rejim (QQS + foyda solig'i)
    YTT_FIXED = "ytt_fixed"  # YTT qat'iy soliq


@dataclass(frozen=True)
class TaxBreakdownLine:
    name: str
    base: float
    rate: float
    amount: float
    note: str = ""


@dataclass(frozen=True)
class TaxCalculationResult:
    regime: TaxRegime
    annual_revenue: float
    lines: list[TaxBreakdownLine]
    total_tax: float
    effective_rate: float
    rates_version: str = TAX_RATES_VERSION
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", self.warnings or [])


def calculate_turnover_tax(annual_revenue: float) -> TaxCalculationResult:
    """Aylanma soliq rejimi (yillik aylanmasi 1 mlrd so'mgacha)."""
    warnings: list[str] = []
    if annual_revenue > TURNOVER_TAX_THRESHOLD_UZS:
        warnings.append(
            "Yillik aylanma 1 mlrd so'mdan oshgan — umumiy rejimga (QQS + foyda "
            "solig'i) o'tish majburiy."
        )
    tax = annual_revenue * TURNOVER_TAX_RATE
    lines = [
        TaxBreakdownLine(
            name="Aylanma soliq",
            base=annual_revenue,
            rate=TURNOVER_TAX_RATE,
            amount=tax,
            note="Asosiy stavka 4% (faoliyat turiga qarab farq qilishi mumkin)",
        )
    ]
    return TaxCalculationResult(
        regime=TaxRegime.TURNOVER,
        annual_revenue=annual_revenue,
        lines=lines,
        total_tax=tax,
        effective_rate=tax / annual_revenue if annual_revenue else 0.0,
        warnings=warnings,
    )


def calculate_general_regime(
    annual_revenue: float,
    deductible_expenses: float,
    *,
    vat_taxable_share: float = 1.0,
) -> TaxCalculationResult:
    """Umumiy rejim: QQS 12% + foyda solig'i 15%."""
    if deductible_expenses > annual_revenue:
        deductible_expenses = annual_revenue
    vat_base = annual_revenue * max(min(vat_taxable_share, 1.0), 0.0)
    # Revenue treated as VAT-inclusive: QQS = base * 12/112
    vat = vat_base * VAT_RATE / (1 + VAT_RATE)
    profit = max(annual_revenue - vat - deductible_expenses, 0.0)
    profit_tax = profit * PROFIT_TAX_RATE
    lines = [
        TaxBreakdownLine(
            name="QQS",
            base=vat_base,
            rate=VAT_RATE,
            amount=vat,
            note="Aylanma QQS ichida deb hisoblangan (12/112)",
        ),
        TaxBreakdownLine(
            name="Foyda solig'i",
            base=profit,
            rate=PROFIT_TAX_RATE,
            amount=profit_tax,
        ),
    ]
    total = vat + profit_tax
    return TaxCalculationResult(
        regime=TaxRegime.GENERAL,
        annual_revenue=annual_revenue,
        lines=lines,
        total_tax=total,
        effective_rate=total / annual_revenue if annual_revenue else 0.0,
    )


def calculate_payroll_taxes(gross_monthly_salary: float) -> dict[str, float]:
    """Ish haqi solig'i: JShDS 12% (xodimdan) + ijtimoiy soliq 12% (ish beruvchidan)."""
    income_tax = gross_monthly_salary * PERSONAL_INCOME_TAX_RATE
    social_tax = gross_monthly_salary * SOCIAL_TAX_RATE
    return {
        "gross": gross_monthly_salary,
        "income_tax": income_tax,
        "social_tax": social_tax,
        "net_salary": gross_monthly_salary - income_tax,
        "employer_total_cost": gross_monthly_salary + social_tax,
    }


def compare_regimes(annual_revenue: float, deductible_expenses: float) -> dict[str, object]:
    """Aylanma vs umumiy rejim taqqoslash — qaysi biri foydali."""
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
