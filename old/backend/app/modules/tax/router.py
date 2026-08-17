"""Tax endpoints: deterministic calculators + AI explanation."""

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.base import ChatMessage, ChatRole, CompletionRequest
from app.ai.safety.pipeline import LEGAL_TAX_DISCLAIMER
from app.core.dependencies import Container, CurrentUser
from app.modules.tax.calculator import (
    TAX_RATES_VERSION,
    calculate_general_regime,
    calculate_payroll_taxes,
    calculate_turnover_tax,
    compare_regimes,
)

router = APIRouter(prefix="/tax", tags=["tax"])


class TurnoverTaxRequest(BaseModel):
    annual_revenue: float = Field(gt=0, le=1e15)


class GeneralRegimeRequest(BaseModel):
    annual_revenue: float = Field(gt=0, le=1e15)
    deductible_expenses: float = Field(ge=0, le=1e15)
    vat_taxable_share: float = Field(default=1.0, ge=0, le=1)


class PayrollRequest(BaseModel):
    gross_monthly_salary: float = Field(gt=0, le=1e12)


class CompareRequest(BaseModel):
    annual_revenue: float = Field(gt=0, le=1e15)
    deductible_expenses: float = Field(ge=0, le=1e15)
    explain: bool = False  # True → AI tushuntirish qo'shiladi


@router.get("/rates")
async def rates(user: CurrentUser) -> dict:
    from app.modules.tax import calculator as c

    return {
        "version": TAX_RATES_VERSION,
        "vat": c.VAT_RATE,
        "turnover": c.TURNOVER_TAX_RATE,
        "profit": c.PROFIT_TAX_RATE,
        "personal_income": c.PERSONAL_INCOME_TAX_RATE,
        "social": c.SOCIAL_TAX_RATE,
        "turnover_threshold_uzs": c.TURNOVER_TAX_THRESHOLD_UZS,
        "disclaimer": LEGAL_TAX_DISCLAIMER,
    }


@router.post("/turnover")
async def turnover_tax(req: TurnoverTaxRequest, user: CurrentUser) -> dict:
    result = calculate_turnover_tax(req.annual_revenue)
    return {**asdict(result), "disclaimer": LEGAL_TAX_DISCLAIMER}


@router.post("/general")
async def general_regime(req: GeneralRegimeRequest, user: CurrentUser) -> dict:
    result = calculate_general_regime(
        req.annual_revenue, req.deductible_expenses, vat_taxable_share=req.vat_taxable_share
    )
    return {**asdict(result), "disclaimer": LEGAL_TAX_DISCLAIMER}


@router.post("/payroll")
async def payroll(req: PayrollRequest, user: CurrentUser) -> dict:
    return {
        **calculate_payroll_taxes(req.gross_monthly_salary),
        "rates_version": TAX_RATES_VERSION,
        "disclaimer": LEGAL_TAX_DISCLAIMER,
    }


@router.post("/compare")
async def compare(req: CompareRequest, user: CurrentUser, container: Container) -> dict:
    comparison = compare_regimes(req.annual_revenue, req.deductible_expenses)
    result = {
        "turnover": asdict(comparison["turnover"]),
        "general": asdict(comparison["general"]),
        "recommended": comparison["recommended"],
        "savings": comparison["savings"],
        "disclaimer": LEGAL_TAX_DISCLAIMER,
    }
    if req.explain:
        prompt = await container.prompts.get("module.tax")
        response = await container.ai_router.complete(
            CompletionRequest(
                messages=(
                    ChatMessage(role=ChatRole.SYSTEM, content=prompt),
                    ChatMessage(
                        role=ChatRole.USER,
                        content=(
                            f"Yillik aylanma: {req.annual_revenue:,.0f} so'm, xarajatlar: "
                            f"{req.deductible_expenses:,.0f} so'm.\nHisob-kitob natijasi: "
                            f"aylanma soliq={comparison['turnover'].total_tax:,.0f}, "
                            f"umumiy rejim={comparison['general'].total_tax:,.0f}, tavsiya="
                            f"{comparison['recommended']}.\nUshbu natijani tadbirkorga oddiy "
                            "tilda tushuntir (raqamlarni o'zgartirma)."
                        ),
                    ),
                ),
                model="tax",
                temperature=0.3,
                max_tokens=800,
            ),
            user_id=user.id,
            module="tax",
        )
        result["explanation"] = response.content
    return result
