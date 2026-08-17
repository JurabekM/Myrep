from fastapi import APIRouter

from app.inference.forecast_service import get_forecast_service
from app.schemas.forecast import ForecastRequest, ForecastResponse, RunoutRequest, RunoutResponse

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("/spending", response_model=ForecastResponse)
async def forecast_spending(payload: ForecastRequest) -> ForecastResponse:
    result = get_forecast_service().forecast_next_month(payload.daily_expenses)
    return ForecastResponse(**result)


@router.post("/runout", response_model=RunoutResponse)
async def forecast_runout(payload: RunoutRequest) -> RunoutResponse:
    result = get_forecast_service().estimate_money_runout(
        payload.current_balance, payload.daily_expenses, payload.daily_income
    )
    return RunoutResponse(**result)
