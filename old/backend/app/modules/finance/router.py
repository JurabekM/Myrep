"""Finance endpoints over the pure calculation functions."""

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.safety.pipeline import FINANCE_DISCLAIMER
from app.core.dependencies import CurrentUser
from app.modules.finance.calculations import (
    annuity_loan_schedule,
    break_even,
    cash_flow_summary,
    irr,
    npv,
    roe,
    roi,
    simple_forecast,
)

router = APIRouter(prefix="/finance", tags=["finance"])


class NPVRequest(BaseModel):
    rate: float = Field(gt=-1, lt=10)
    cash_flows: list[float] = Field(min_length=2, max_length=600)


class IRRRequest(BaseModel):
    cash_flows: list[float] = Field(min_length=2, max_length=600)


class ROIRequest(BaseModel):
    gain: float
    cost: float = Field(gt=0)


class ROERequest(BaseModel):
    net_income: float
    equity: float = Field(gt=0)


class BreakEvenRequest(BaseModel):
    fixed_costs: float = Field(ge=0)
    price_per_unit: float = Field(gt=0)
    variable_cost_per_unit: float = Field(ge=0)


class LoanRequest(BaseModel):
    principal: float = Field(gt=0)
    annual_rate: float = Field(ge=0, le=2)  # 200% dan yuqori stavka — xato
    months: int = Field(gt=0, le=600)


class CashFlowRequest(BaseModel):
    opening_balance: float
    inflows: list[float] = Field(min_length=1, max_length=120)
    outflows: list[float] = Field(min_length=1, max_length=120)


class ForecastRequest(BaseModel):
    history: list[float] = Field(min_length=2, max_length=120)
    periods: int = Field(gt=0, le=60)


@router.post("/npv")
async def npv_endpoint(req: NPVRequest, user: CurrentUser) -> dict:
    return {"npv": npv(req.rate, req.cash_flows), "disclaimer": FINANCE_DISCLAIMER}


@router.post("/irr")
async def irr_endpoint(req: IRRRequest, user: CurrentUser) -> dict:
    return {"irr": irr(req.cash_flows), "disclaimer": FINANCE_DISCLAIMER}


@router.post("/roi")
async def roi_endpoint(req: ROIRequest, user: CurrentUser) -> dict:
    return {"roi": roi(req.gain, req.cost), "disclaimer": FINANCE_DISCLAIMER}


@router.post("/roe")
async def roe_endpoint(req: ROERequest, user: CurrentUser) -> dict:
    return {"roe": roe(req.net_income, req.equity), "disclaimer": FINANCE_DISCLAIMER}


@router.post("/break-even")
async def break_even_endpoint(req: BreakEvenRequest, user: CurrentUser) -> dict:
    result = break_even(req.fixed_costs, req.price_per_unit, req.variable_cost_per_unit)
    return {**asdict(result), "disclaimer": FINANCE_DISCLAIMER}


@router.post("/loan")
async def loan_endpoint(req: LoanRequest, user: CurrentUser) -> dict:
    payment, schedule = annuity_loan_schedule(req.principal, req.annual_rate, req.months)
    total_paid = payment * req.months
    return {
        "monthly_payment": payment,
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_paid - req.principal, 2),
        "schedule": [asdict(row) for row in schedule],
        "disclaimer": FINANCE_DISCLAIMER,
    }


@router.post("/cash-flow")
async def cash_flow_endpoint(req: CashFlowRequest, user: CurrentUser) -> dict:
    result = cash_flow_summary(req.opening_balance, req.inflows, req.outflows)
    return {**asdict(result), "disclaimer": FINANCE_DISCLAIMER}


@router.post("/forecast")
async def forecast_endpoint(req: ForecastRequest, user: CurrentUser) -> dict:
    return {
        "forecast": simple_forecast(req.history, req.periods),
        "method": "linear_trend",
        "disclaimer": FINANCE_DISCLAIMER,
    }
