"""Moliya servisi — kalkulyatorlarga yupqa fasad (AI'siz, deterministik)."""

from __future__ import annotations

from app.services.calculators import finance_calculator as calc


class FinanceService:
    """Barcha hisob-kitoblar sof Python; AI chaqirilmaydi (aniqlik kafolati)."""

    def npv(self, rate: float, cash_flows: list[float]) -> float:
        return calc.npv(rate, cash_flows)

    def irr(self, cash_flows: list[float]) -> float:
        return calc.irr(cash_flows)

    def roi(self, gain: float, cost: float) -> float:
        return calc.roi(gain, cost)

    def roe(self, net_income: float, equity: float) -> float:
        return calc.roe(net_income, equity)

    def break_even(self, fixed: float, price: float, variable: float) -> calc.BreakEvenResult:
        return calc.break_even(fixed, price, variable)

    def loan(self, principal: float, annual_rate: float, months: int):  # noqa: ANN201
        return calc.annuity_loan(principal, annual_rate, months)

    def cash_flow(self, opening: float, inflows: list[float], outflows: list[float]):  # noqa: ANN201
        return calc.cash_flow(opening, inflows, outflows)
