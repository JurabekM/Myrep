"""Moliyaviy matematika — sof funksiyalar, to'liq testlanadigan."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import ValidationError


def npv(rate: float, cash_flows: list[float]) -> float:
    """Sof joriy qiymat. cash_flows[0] — t=0 (odatda manfiy investitsiya)."""
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))


def irr(cash_flows: list[float], *, tol: float = 1e-7, max_iter: int = 200) -> float:
    """Ichki daromadlilik normasi — [-0.9999, 10] oraliqda bisektsiya."""
    if len(cash_flows) < 2:
        raise ValidationError("IRR uchun kamida 2 ta davr kerak")
    if not (any(cf > 0 for cf in cash_flows) and any(cf < 0 for cf in cash_flows)):
        raise ValidationError("IRR uchun musbat va manfiy oqimlar bo'lishi kerak")

    low, high = -0.9999, 10.0
    f_low = npv(low, cash_flows)
    if f_low * npv(high, cash_flows) > 0:
        raise ValidationError("IRR bu oraliqda topilmadi — oqimlarni tekshiring")
    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv(mid, cash_flows)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2


def roi(gain: float, cost: float) -> float:
    if cost <= 0:
        raise ValidationError("Xarajat musbat bo'lishi kerak")
    return (gain - cost) / cost


def roe(net_income: float, equity: float) -> float:
    if equity <= 0:
        raise ValidationError("Kapital musbat bo'lishi kerak")
    return net_income / equity


@dataclass(frozen=True)
class BreakEvenResult:
    units: float
    revenue: float
    contribution_margin: float


def break_even(fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float) -> BreakEvenResult:
    margin = price_per_unit - variable_cost_per_unit
    if margin <= 0:
        raise ValidationError("Narx o'zgaruvchan xarajatdan katta bo'lishi kerak")
    units = fixed_costs / margin
    return BreakEvenResult(units, units * price_per_unit, margin)


@dataclass(frozen=True)
class LoanRow:
    month: int
    payment: float
    principal: float
    interest: float
    balance: float


def annuity_loan(principal: float, annual_rate: float, months: int) -> tuple[float, list[LoanRow]]:
    if principal <= 0 or months <= 0:
        raise ValidationError("Kredit summasi va muddati musbat bo'lishi kerak")
    if annual_rate < 0:
        raise ValidationError("Stavka manfiy bo'lishi mumkin emas")
    monthly = annual_rate / 12
    payment = principal / months if monthly == 0 else (
        principal * monthly / (1 - (1 + monthly) ** -months)
    )
    rows: list[LoanRow] = []
    balance = principal
    for month in range(1, months + 1):
        interest = balance * monthly
        principal_part = payment - interest
        balance = max(balance - principal_part, 0.0)
        rows.append(
            LoanRow(month, round(payment, 2), round(principal_part, 2),
                    round(interest, 2), round(balance, 2))
        )
    return round(payment, 2), rows


@dataclass(frozen=True)
class CashFlowResult:
    opening_balance: float
    total_inflow: float
    total_outflow: float
    net_flow: float
    closing_balance: float
    negative_months: list[int]


def cash_flow(opening_balance: float, inflows: list[float], outflows: list[float]) -> CashFlowResult:
    if len(inflows) != len(outflows):
        raise ValidationError("Kirim va chiqim davrlari soni teng bo'lishi kerak")
    balance = opening_balance
    negative_months: list[int] = []
    for month, (inflow, outflow) in enumerate(zip(inflows, outflows), start=1):
        balance += inflow - outflow
        if balance < 0:
            negative_months.append(month)
    return CashFlowResult(
        opening_balance, sum(inflows), sum(outflows),
        sum(inflows) - sum(outflows), balance, negative_months,
    )
