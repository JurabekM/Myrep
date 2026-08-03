from fastapi import APIRouter, Query, Request

from app.providers.weather import get_weather_provider
from app.rate_limit import limiter
from app.schemas import WeatherDayOut, WeatherOut

router = APIRouter(prefix="/v1/weather", tags=["weather"])


@router.get("", response_model=WeatherOut)
@limiter.limit("30/minute")
def get_weather(request: Request, region: str = Query(..., min_length=1, max_length=100)):
    snapshot = get_weather_provider().fetch_weather(region)
    return WeatherOut(
        region=snapshot.region,
        current_temp_c=snapshot.current_temp_c,
        current_condition=snapshot.current_condition,
        forecast=[
            WeatherDayOut(
                epoch_day=d.epoch_day,
                temp_min_c=d.temp_min_c,
                temp_max_c=d.temp_max_c,
                rain_probability_percent=d.rain_probability_percent,
                summary=d.summary,
            )
            for d in snapshot.forecast
        ],
    )
