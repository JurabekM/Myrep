"""Financial mathematics — pure functions, fully unit-testable."""

from dataclasses import dataclass

from app.core.exceptions import ValidationError


def npv(rate: float, cash_flows: list[float]) -> float:
    """Net Present Value. cash_flows[0] is t=0 (usually negative investment)."""
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))


def irr(cash_flows: list[float], *, tol: float = 1e-7, max_iter: int = 200) -> float:
    """Internal Rate of Return via bisection on [-0.9999, 10].

    Requires at least one sign change in the cash flows.
    """
    if len(cash_flows) < 2:
        raise ValidationError("IRR uchun kamida 2 ta davr kerak")
    has_positive = any(cf > 0 for cf in cash_flows)
    has_negative = any(cf < 0 for cf in cash_flows)
    if not (has_positive and has_negative):
        raise ValidationError("IRR uchun musbat va manfiy oqimlar bo'lishi kerak")

    low, high = -0.9999, 10.0
    f_low, f_high = npv(low, cash_flows), npv(high, cash_flows)
    if f_low * f_high > 0:
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


def break_even(
    fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float
) -> BreakEvenResult:
    margin = price_per_unit - variable_cost_per_unit
    if margin <= 0:
        raise ValidationError(
            "Narx o'zgaruvchan xarajatdan katta bo'lishi kerak (marja manfiy)"
        )
    units = fixed_costs / margin
    return BreakEvenResult(
        units=units, revenue=units * price_per_unit, contribution_margin=margin
    )


@dataclass(frozen=True)
class LoanScheduleRow:
    month: int
    payment: float
    principal: float
    interest: float
    balance: float


def annuity_loan_schedule(
    principal: float, annual_rate: float, months: int
) -> tuple[float, list[LoanScheduleRow]]:
    """Annuitet kredit jadvali. Returns (monthly_payment, rows)."""
    if principal <= 0 or months <= 0:
        raise ValidationError("Kredit summasi va muddati musbat bo'lishi kerak")
    if annual_rate < 0:
        raise ValidationError("Stavka manfiy bo'lishi mumkin emas")
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        payment = principal / months
    else:
        payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)
    rows: list[LoanScheduleRow] = []
    balance = principal
    for month in range(1, months + 1):
        interest = balance * monthly_rate
        principal_part = payment - interest
        balance = max(balance - principal_part, 0.0)
        rows.append(
            LoanScheduleRow(
                month=month,
                payment=round(payment, 2),
                principal=round(principal_part, 2),
                interest=round(interest, 2),
                balance=round(balance, 2),
            )
        )
    return round(payment, 2), rows


@dataclass(frozen=True)
class CashFlowSummary:
    opening_balance: float
    total_inflow: float
    total_outflow: float
    net_flow: float
    closing_balance: float
    negative_months: list[int]


def cash_flow_summary(
    opening_balance: float, inflows: list[float], outflows: list[float]
) -> CashFlowSummary:
    if len(inflows) != len(outflows):
        raise ValidationError("Kirim va chiqim davrlari soni teng bo'lishi kerak")
    balance = opening_balance
    negative_months: list[int] = []
    for month, (inflow, outflow) in enumerate(zip(inflows, outflows), start=1):
        balance += inflow - outflow
        if balance < 0:
            negative_months.append(month)
    return CashFlowSummary(
        opening_balance=opening_balance,
        total_inflow=sum(inflows),
        total_outflow=sum(outflows),
        net_flow=sum(inflows) - sum(outflows),
        closing_balance=balance,
        negative_months=negative_months,
    )


def simple_forecast(history: list[float], periods: int) -> list[float]:
    """Linear-trend forecast (least squares). Good enough for SMB budgeting."""
    n = len(history)
    if n < 2:
        raise ValidationError("Prognoz uchun kamida 2 ta davr kerak")
    x_mean = (n - 1) / 2
    y_mean = sum(history) / n
    denom = sum((i - x_mean) ** 2 for i in range(n))
    slope = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(history)) / denom
    intercept = y_mean - slope * x_mean
    return [intercept + slope * (n + t) for t in range(periods)]
