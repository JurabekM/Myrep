"""Pure-numpy time-series toolkit: trend, seasonality, forecasting, anomalies."""
from __future__ import annotations

import numpy as np


def moving_average(values: list[float], window: int = 3) -> list[float]:
    """Simple trailing moving average (leading values use a growing window)."""
    result: list[float] = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1): i + 1]
        result.append(float(np.mean(chunk)))
    return result


def trend_slope(values: list[float]) -> float:
    """Least-squares slope per step; 0 for degenerate series."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, np.asarray(values, dtype=float), 1)[0])


def linear_forecast(
    values: list[float], periods: int = 1,
) -> tuple[list[float], list[float], list[float]]:
    """Linear-trend forecast with a residual-based ~95% confidence band."""
    data = np.asarray(values, dtype=float)
    if len(data) == 0:
        return [], [], []
    if len(data) == 1:
        flat = [float(data[0])] * periods
        return flat, flat, flat
    x = np.arange(len(data), dtype=float)
    slope, intercept = np.polyfit(x, data, 1)
    residual_std = float(np.std(data - (slope * x + intercept)))
    future_x = np.arange(len(data), len(data) + periods, dtype=float)
    forecast = slope * future_x + intercept
    band = 1.96 * residual_std * np.sqrt(1 + (future_x - x.mean()) ** 2 / max(1e-9, ((x - x.mean()) ** 2).sum()))
    return (
        [round(float(v), 3) for v in forecast],
        [round(float(v), 3) for v in forecast - band],
        [round(float(v), 3) for v in forecast + band],
    )


def seasonal_forecast(
    values: list[float], season_length: int = 12, periods: int = 12,
) -> tuple[list[float], list[float], list[float]]:
    """Trend + multiplicative seasonal-index forecast (classic decomposition)."""
    data = np.asarray(values, dtype=float)
    if len(data) < season_length * 2:
        return linear_forecast(values, periods)
    x = np.arange(len(data), dtype=float)
    slope, intercept = np.polyfit(x, data, 1)
    trend = slope * x + intercept
    safe_trend = np.where(np.abs(trend) < 1e-9, 1e-9, trend)
    ratio = data / safe_trend
    seasonal = np.array([
        float(np.mean(ratio[i::season_length])) for i in range(season_length)
    ])
    residual_std = float(np.std(data - trend * seasonal[np.arange(len(data)) % season_length]))
    future_x = np.arange(len(data), len(data) + periods, dtype=float)
    future_trend = slope * future_x + intercept
    future_seasonal = seasonal[np.arange(len(data), len(data) + periods) % season_length]
    forecast = future_trend * future_seasonal
    return (
        [round(float(v), 3) for v in forecast],
        [round(float(v - 1.96 * residual_std), 3) for v in forecast],
        [round(float(v + 1.96 * residual_std), 3) for v in forecast],
    )


def zscore_anomalies(values: list[float], threshold: float = 2.0) -> list[int]:
    """Indices whose z-score magnitude exceeds the threshold."""
    data = np.asarray(values, dtype=float)
    if len(data) < 3:
        return []
    std = data.std()
    if std < 1e-12:
        return []
    z = (data - data.mean()) / std
    return [int(i) for i in np.where(np.abs(z) > threshold)[0]]


def percent_change(previous: float, current: float) -> float:
    """Safe percentage change from previous to current."""
    if abs(previous) < 1e-12:
        return 0.0
    return round((current - previous) / abs(previous) * 100, 1)
