from app.models.forecast import fit_linear_trend


class ForecastService:
    def forecast_next_month(self, daily_expenses: list[float]) -> dict:
        """So'nggi N kunlik xarajat qatoridan kelasi 30 kunlik bashoratni hisoblaydi."""
        slope, intercept = fit_linear_trend(daily_expenses)
        history_len = len(daily_expenses)

        predicted_days = [
            max(0.0, slope * (history_len + i) + intercept) for i in range(30)
        ]
        return {
            "daily_trend_slope": round(slope, 2),
            "predicted_next_30_days_total": round(sum(predicted_days), 2),
            "predicted_daily_avg": round(sum(predicted_days) / 30, 2) if predicted_days else 0.0,
        }

    def estimate_money_runout(self, current_balance: float, daily_expenses: list[float], daily_income: list[float]) -> dict:
        """Joriy balans va xarajat/daromad trendidan pul tugash sanasini bashorat qiladi."""
        expense_slope, expense_intercept = fit_linear_trend(daily_expenses)
        income_avg = sum(daily_income) / len(daily_income) if daily_income else 0.0
        history_len = len(daily_expenses)

        balance = current_balance
        for day_offset in range(1, 366):
            projected_expense = max(0.0, expense_slope * (history_len + day_offset) + expense_intercept)
            balance += income_avg - projected_expense
            if balance <= 0:
                return {"days_until_depletion": day_offset, "will_run_out": True}

        return {"days_until_depletion": None, "will_run_out": False}


_forecast_service: ForecastService | None = None


def get_forecast_service() -> ForecastService:
    global _forecast_service
    if _forecast_service is None:
        _forecast_service = ForecastService()
    return _forecast_service
