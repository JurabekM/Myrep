"""Market price analytics and manual/API data entry."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from analytics.timeseries import linear_forecast, percent_change
from core.cache import cached
from database.engine import read_df, session_scope
from database.models import MarketPrice


@cached(ttl=120)
def latest_prices() -> pd.DataFrame:
    """Latest price per crop with 30-day change percentage."""
    df = read_df(
        "SELECT c.name AS crop, m.price_per_kg, m.date, m.market_name"
        " FROM market_prices m JOIN crops c ON c.id = m.crop_id"
        " ORDER BY m.date"
    )
    if df.empty:
        return df
    rows = []
    for crop, group in df.groupby("crop"):
        group = group.sort_values("date")
        latest = group.iloc[-1]
        month_ago = group[group.date <= str(date.today() - timedelta(days=30))]
        base = float(month_ago.iloc[-1]["price_per_kg"]) if not month_ago.empty else float(latest["price_per_kg"])
        rows.append({
            "crop": crop,
            "price": round(float(latest["price_per_kg"]), 0),
            "date": str(latest["date"]),
            "market": latest["market_name"],
            "change_30d": percent_change(base, float(latest["price_per_kg"])),
        })
    return pd.DataFrame(rows).sort_values("crop").reset_index(drop=True)


def price_history(crop_id: int, days: int = 730) -> pd.DataFrame:
    """Price series for one crop."""
    since = (date.today() - timedelta(days=days)).isoformat()
    return read_df(
        "SELECT date, price_per_kg FROM market_prices"
        " WHERE crop_id = :c AND date >= :s ORDER BY date",
        {"c": crop_id, "s": since},
    )


def price_forecast(crop_id: int, periods: int = 12) -> dict[str, list]:
    """Weekly price forecast with confidence band."""
    history = price_history(crop_id, days=365)
    values = history["price_per_kg"].tolist()
    forecast, lower, upper = linear_forecast(values, periods)
    return {"history": values[-26:], "forecast": forecast,
            "lower": lower, "upper": upper}


def add_price(crop_id: int, price: float, market_name: str = "Qo'lda kiritilgan",
              day: date | None = None) -> None:
    """Manual price entry from the UI or API."""
    with session_scope() as session:
        session.add(MarketPrice(
            crop_id=crop_id, date=day or date.today(),
            price_per_kg=price, market_name=market_name, source="manual",
        ))
    latest_prices.cache.clear()  # type: ignore[attr-defined]


def crop_options() -> dict[int, str]:
    """id -> name mapping for select widgets."""
    df = read_df("SELECT id, name FROM crops ORDER BY name")
    return {int(row.id): row.name for row in df.itertuples()}
