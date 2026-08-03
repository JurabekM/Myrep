"""Provider-agnostic weather source, mirroring the mobile app's `WeatherProvider` interface so
both sides behave consistently. Swap `MockWeatherProvider` for a real client (Open-Meteo,
OpenWeatherMap) via `get_weather_provider()` once `WEATHER_PROVIDER_API_KEY` is configured.
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.config import get_settings


@dataclass
class DailyForecast:
    epoch_day: int
    temp_min_c: float
    temp_max_c: float
    rain_probability_percent: int
    summary: str


@dataclass
class WeatherSnapshot:
    region: str
    current_temp_c: float
    current_condition: str
    forecast: list[DailyForecast]


class WeatherProvider(ABC):
    @abstractmethod
    def fetch_weather(self, region: str) -> WeatherSnapshot: ...


class MockWeatherProvider(WeatherProvider):
    def fetch_weather(self, region: str) -> WeatherSnapshot:
        today = datetime.now(timezone.utc).date()
        seed = hash((region, today.toordinal())) & 0xFFFFFFFF
        rng = random.Random(seed)

        base_temp = 22 + rng.randint(-4, 12)
        conditions = ["Ochiq", "Bulutli", "Yengil yomg'ir", "Issiq va quruq", "Shamolli"]
        current_condition = rng.choice(conditions)

        forecast: list[DailyForecast] = []
        for offset in range(5):
            day = today + timedelta(days=offset)
            day_rng = random.Random(seed + offset)
            temp_min = base_temp - day_rng.randint(2, 6)
            temp_max = base_temp + day_rng.randint(2, 8)
            rain = day_rng.randint(0, 100)
            summary = (
                "Yomg'ir ehtimoli yuqori" if rain > 60
                else "Yomg'ir ehtimoli bor" if rain > 30
                else "Issiq kun" if temp_max > 34
                else "Quyoshli"
            )
            forecast.append(
                DailyForecast(
                    epoch_day=day.toordinal() - date(1970, 1, 1).toordinal(),
                    temp_min_c=float(temp_min),
                    temp_max_c=float(temp_max),
                    rain_probability_percent=rain,
                    summary=summary,
                ),
            )

        return WeatherSnapshot(
            region=region,
            current_temp_c=round(base_temp + rng.uniform(-2, 2), 1),
            current_condition=current_condition,
            forecast=forecast,
        )


def get_weather_provider() -> WeatherProvider:
    settings = get_settings()
    if settings.weather_provider_api_key:
        # A real implementation would be selected here, e.g.:
        # return OpenMeteoWeatherProvider(api_key=settings.weather_provider_api_key)
        pass
    return MockWeatherProvider()
