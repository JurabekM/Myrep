from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    daily_expenses: list[float] = Field(min_length=1, description="So'nggi kunlar bo'yicha xarajat summasi")


class ForecastResponse(BaseModel):
    daily_trend_slope: float
    predicted_next_30_days_total: float
    predicted_daily_avg: float


class RunoutRequest(BaseModel):
    current_balance: float
    daily_expenses: list[float]
    daily_income: list[float] = []


class RunoutResponse(BaseModel):
    days_until_depletion: int | None
    will_run_out: bool
