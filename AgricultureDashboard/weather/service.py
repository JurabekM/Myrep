"""Weather service with live providers and a guaranteed offline path.

Online: Open-Meteo (default, no API key) or NASA POWER. Every successful
response is cached to disk and mirrored into the ``weather_records`` table,
so the dashboard keeps working from the last known data when offline.
"""
from __future__ import annotations

import json
import logging
import socket
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import requests

from config import settings
from core.cache import cached
from database.engine import get_setting, read_df, session_scope
from database.models import District, WeatherRecord

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
REQUEST_TIMEOUT = 8


@cached(ttl=60)
def is_online() -> bool:
    """Cheap connectivity probe honouring the offline_mode setting."""
    mode = get_setting("offline_mode", "auto")
    if mode == "on":
        return False
    if mode == "off":
        return True
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3).close()
        return True
    except OSError:
        return False


def _cache_file(lat: float, lon: float) -> Any:
    return settings.CACHE_DIR / f"forecast_{lat:.2f}_{lon:.2f}.json"


def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict[str, Any] | None:
    """7-day forecast: live when online, otherwise the last cached response."""
    cache_path = _cache_file(lat, lon)
    if is_online():
        try:
            response = requests.get(OPEN_METEO_URL, params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_sum,relative_humidity_2m_mean",
                "forecast_days": days, "timezone": "Asia/Tashkent",
            }, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            payload["_fetched_at"] = datetime.now().isoformat(timespec="seconds")
            payload["_source"] = "open-meteo (jonli)"
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload
        except (requests.RequestException, ValueError) as exc:
            log.warning("Open-Meteo so'rovi muvaffaqiyatsiz: %s", exc)
    if cache_path.exists():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            payload["_source"] = f"kesh ({payload.get('_fetched_at', 'noma`lum')})"
            return payload
        except (json.JSONDecodeError, OSError):
            pass
    return None


def fetch_nasa_power(lat: float, lon: float, start: date, end: date) -> pd.DataFrame | None:
    """Historical daily data from NASA POWER (used when provider=nasa-power)."""
    if not is_online():
        return None
    try:
        response = requests.get(NASA_POWER_URL, params={
            "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M",
            "community": "AG", "latitude": lat, "longitude": lon,
            "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }, timeout=REQUEST_TIMEOUT * 2)
        response.raise_for_status()
        block = response.json()["properties"]["parameter"]
        rows = []
        for key, t_max in block["T2M_MAX"].items():
            rows.append({
                "date": datetime.strptime(key, "%Y%m%d").date(),
                "t_max": t_max, "t_min": block["T2M_MIN"].get(key),
                "precipitation_mm": block["PRECTOTCORR"].get(key, 0),
                "humidity": block["RH2M"].get(key, 50),
            })
        return pd.DataFrame(rows)
    except (requests.RequestException, KeyError, ValueError) as exc:
        log.warning("NASA POWER so'rovi muvaffaqiyatsiz: %s", exc)
        return None


def refresh_all_districts() -> int:
    """Background job: pull recent live daily data into weather_records."""
    if not is_online():
        return 0
    updated = 0
    with session_scope() as session:
        districts = session.query(District).all()
    for district in districts[:6]:  # polite batch per hourly cycle
        try:
            response = requests.get(OPEN_METEO_URL, params={
                "latitude": district.lat, "longitude": district.lon,
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_sum,relative_humidity_2m_mean",
                "past_days": 7, "forecast_days": 1, "timezone": "Asia/Tashkent",
            }, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            daily = response.json()["daily"]
        except (requests.RequestException, KeyError, ValueError):
            continue
        with session_scope() as session:
            for i, day_str in enumerate(daily["time"]):
                day = datetime.strptime(day_str, "%Y-%m-%d").date()
                if day >= date.today():
                    continue
                exists = session.query(WeatherRecord).filter_by(
                    district_id=district.id, date=day).first()
                values = {
                    "t_max": float(daily["temperature_2m_max"][i] or 0),
                    "t_min": float(daily["temperature_2m_min"][i] or 0),
                    "precipitation_mm": float(daily["precipitation_sum"][i] or 0),
                    "humidity": float(daily["relative_humidity_2m_mean"][i] or 50),
                    "source": "open-meteo",
                }
                if exists is None:
                    session.add(WeatherRecord(district_id=district.id, date=day, **values))
                    updated += 1
                elif exists.source == "demo":
                    for key, value in values.items():
                        setattr(exists, key, value)
                    updated += 1
    if updated:
        log.info("Ob-havo yangilandi: %d yozuv.", updated)
    return updated


def history_frame(district_id: int | None = None,
                  days: int = 365) -> pd.DataFrame:
    """Daily history for charts (optionally filtered by district)."""
    since = (date.today() - timedelta(days=days)).isoformat()
    if district_id:
        return read_df(
            "SELECT date, t_min, t_max, precipitation_mm, humidity"
            " FROM weather_records WHERE district_id = :d AND date >= :s"
            " ORDER BY date", {"d": district_id, "s": since},
        )
    return read_df(
        "SELECT date, AVG(t_min) AS t_min, AVG(t_max) AS t_max,"
        " AVG(precipitation_mm) AS precipitation_mm, AVG(humidity) AS humidity"
        " FROM weather_records WHERE date >= :s GROUP BY date ORDER BY date",
        {"s": since},
    )


def monthly_climate(district_id: int) -> pd.DataFrame:
    """Long-term monthly averages for the climate profile chart."""
    return read_df(
        "SELECT CAST(strftime('%m', date) AS INTEGER) AS month,"
        " ROUND(AVG(t_max),1) AS t_max, ROUND(AVG(t_min),1) AS t_min,"
        " ROUND(SUM(precipitation_mm)/COUNT(DISTINCT strftime('%Y', date)),1) AS precip,"
        " ROUND(AVG(humidity),1) AS humidity"
        " FROM weather_records WHERE district_id = :d"
        " GROUP BY month ORDER BY month", {"d": district_id},
    )


def season_summary(region_name: str, year: int) -> dict[str, float] | None:
    """Season (Apr–Sep) precipitation and temperature for a region-year."""
    df = read_df(
        "SELECT SUM(w.precipitation_mm) AS precip,"
        " AVG((w.t_min+w.t_max)/2) AS t_avg, AVG(w.humidity) AS humidity"
        " FROM weather_records w"
        " JOIN districts d ON d.id = w.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " WHERE r.name = :r AND CAST(strftime('%Y', w.date) AS INTEGER) = :y"
        " AND CAST(strftime('%m', w.date) AS INTEGER) BETWEEN 4 AND 9",
        {"r": region_name, "y": year},
    )
    if df.empty or pd.isna(df.iloc[0]["precip"]):
        return None
    row = df.iloc[0]
    # Region has 2 districts — normalise the precipitation sum per district.
    return {"precip": float(row["precip"]) / 2, "t_avg": float(row["t_avg"]),
            "humidity": float(row["humidity"])}
