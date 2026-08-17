"""Soliq servisi — deterministik kalkulyator + ixtiyoriy AI tushuntirish."""

from __future__ import annotations

from app.ai.base import ChatMessage, CompletionRequest, Role
from app.ai.prompts import build_system_prompt
from app.ai.router import ModelRouter
from app.core.config import BusinessProfile
from app.services.calculators import tax_calculator as calc


class TaxService:
    def __init__(self, router: ModelRouter, profile: BusinessProfile):
        self._router = router
        self._profile = profile

    # Kalkulyatorlar (sof, AI'siz) ---------------------------------------

    def compare_regimes(self, annual_revenue: float, deductible_expenses: float) -> dict:
        return calc.compare_regimes(annual_revenue, deductible_expenses)

    def payroll(self, gross_monthly_salary: float) -> dict:
        return calc.calculate_payroll(gross_monthly_salary)

    # AI tushuntirish -----------------------------------------------------

    def explain_comparison(self, annual_revenue: float, deductible_expenses: float) -> str:
        comparison = calc.compare_regimes(annual_revenue, deductible_expenses)
        system = build_system_prompt("tax", self._profile)
        user_prompt = (
            f"Yillik aylanma: {annual_revenue:,.0f} so'm, xarajatlar: "
            f"{deductible_expenses:,.0f} so'm.\nHisob-kitob: aylanma soliq="
            f"{comparison['turnover'].total_tax:,.0f}, umumiy rejim="
            f"{comparison['general'].total_tax:,.0f}, tavsiya="
            f"{comparison['recommended'].value}.\nUshbu natijani tadbirkorga oddiy "
            "tilda tushuntir (raqamlarni o'zgartirma)."
        )
        result = self._router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(Role.SYSTEM, system),
                    ChatMessage(Role.USER, user_prompt),
                ),
                temperature=0.3,
                max_tokens=800,
            ),
            module="tax",
        )
        return result.content
