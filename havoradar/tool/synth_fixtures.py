#!/usr/bin/env python3
"""Namunaviy (sintetik) ob-havo va havo sifati javoblari — aniq Open-Meteo formatida.

Nega sintetik: issiqlik to'lqini ssenariysi (iyul) noyabrda jonli olinmaydi, bulut sessiyasida esa
api.open-meteo.com kunlik limitga tushgan edi. Haqiqiy javoblar: air_*_2026-11-02.json (jonli olingan).
Format jonli manbaga qarshi LiveSmokeTest bilan tekshiriladi.

Ishga tushirish:  python3 tool/synth_fixtures.py engine/src/test/resources/fixtures
"""
import json
import math
import sys
from datetime import datetime, timedelta


def shape(h):
    """Kun ichidagi harorat shakli: 05:00 da 0 (eng past), 15:00 da 1 (eng yuqori)."""
    if 5 <= h <= 15:
        return (1 - math.cos(math.pi * (h - 5) / 10)) / 2
    x = (h - 15) % 24  # 15:00 dan keyingi soatlar, 14 soatda pasayadi
    return (1 + math.cos(math.pi * x / 14)) / 2


def weather(start, tmax, tmin, rh_lo, rh_hi, uv_peak, tz, offset):
    times, temp, rh, uv = [], [], [], []
    t0 = datetime.fromisoformat(start)
    for d in range(len(tmax)):
        for h in range(24):
            s = shape(h)
            # Kechqurun pasayish keyingi kun minimumiga qarab ketadi.
            lo = tmin[d] if h <= 15 else tmin[min(d + 1, len(tmin) - 1)]
            times.append((t0 + timedelta(days=d, hours=h)).strftime("%Y-%m-%dT%H:%M"))
            temp.append(round(lo + (tmax[d] - lo) * s, 1))
            rh.append(round(rh_hi - (rh_hi - rh_lo) * s))
            uv.append(round(max(0.0, uv_peak[d] * math.sin(math.pi * (h - 6) / 14)), 2) if 6 <= h <= 20 else 0.0)
    return {
        "latitude": 41.3, "longitude": 69.25, "generationtime_ms": 0.1, "utc_offset_seconds": offset,
        "timezone": tz, "timezone_abbreviation": "GMT+5", "elevation": 455.0,
        "hourly_units": {"time": "iso8601", "temperature_2m": "°C", "relative_humidity_2m": "%", "uv_index": ""},
        "hourly": {"time": times, "temperature_2m": temp, "relative_humidity_2m": rh, "uv_index": uv},
    }


def air(start, days, pm25_base, pm10_base, dust_base, o3_peak, no2_base, tz, offset):
    times, pm25, pm10, o3, no2, dust = [], [], [], [], [], []
    t0 = datetime.fromisoformat(start)
    for d in range(days):
        for h in range(24):
            rush = 1 + 0.5 * math.exp(-((h - 8) ** 2) / 4) + 0.7 * math.exp(-((h - 20) ** 2) / 6)
            sun = max(0.0, math.sin(math.pi * (h - 7) / 14)) if 7 <= h <= 21 else 0.0
            times.append((t0 + timedelta(days=d, hours=h)).strftime("%Y-%m-%dT%H:%M"))
            du = dust_base[d] * (0.6 + 0.8 * sun)
            pm10.append(round(pm10_base[d] * rush + du, 1))
            pm25.append(round(pm25_base[d] * rush + du * 0.25, 1))
            dust.append(round(du, 1))
            o3.append(round(40 + (o3_peak[d] - 40) * sun, 1))
            no2.append(round(no2_base[d] * rush * (1.2 - 0.6 * sun), 1))
    return {
        "latitude": 41.3, "longitude": 69.2, "generationtime_ms": 0.2, "utc_offset_seconds": offset,
        "timezone": tz, "timezone_abbreviation": "GMT+5", "elevation": 447.0,
        "hourly_units": {"time": "iso8601", "pm2_5": "μg/m³", "pm10": "μg/m³", "ozone": "μg/m³", "nitrogen_dioxide": "μg/m³", "dust": "μg/m³"},
        "hourly": {"time": times, "pm2_5": pm25, "pm10": pm10, "ozone": o3, "nitrogen_dioxide": no2, "dust": dust},
    }


def main(out):
    tz, off = "Asia/Tashkent", 18000
    files = {
        # Toshkent, iyul: 13–14 — o'tgan kunlar (past_days=2), «bugun» — 15-iyul, 7 kunlik prognoz.
        "weather_tashkent_2026-07.json": weather(
            "2026-07-13",
            tmax=[38.5, 40.0, 41.5, 43.0, 44.5, 44.0, 41.0, 38.0, 36.5],
            tmin=[24.0, 25.0, 26.5, 27.5, 28.5, 28.0, 26.0, 24.0, 23.0],
            rh_lo=14, rh_hi=42, uv_peak=[9.6, 9.8, 9.7, 9.9, 10.1, 10.0, 9.5, 9.2, 9.0], tz=tz, offset=off),
        # Toshkent, iyul havosi: 17-iyulda chang ko'tarilishi, tushdan keyin ozon.
        "air_tashkent_2026-07.json": air(
            "2026-07-14", 6,
            pm25_base=[14, 15, 16, 22, 18, 15], pm10_base=[38, 40, 45, 70, 52, 42], dust_base=[8, 10, 14, 110, 40, 12],
            o3_peak=[118, 126, 138, 150, 158, 140], no2_base=[18, 20, 20, 22, 19, 18], tz=tz, offset=off),
        # Toshkent, noyabr: haqiqiy havo sifati fixture'i (air_tashkent_2026-11-02.json) bilan bir xil sanalar.
        "weather_tashkent_2026-11.json": weather(
            "2026-10-31",
            tmax=[17.0, 16.5, 15.0, 14.0, 12.5, 13.0, 15.5, 16.0, 14.5],
            tmin=[6.0, 5.5, 5.0, 4.0, 3.5, 4.5, 6.0, 6.5, 5.0],
            rh_lo=45, rh_hi=85, uv_peak=[2.8, 2.7, 2.6, 2.5, 2.4, 2.4, 2.3, 2.3, 2.2], tz=tz, offset=off),
    }
    for name, data in files.items():
        with open(f"{out}/{name}", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(name)


if __name__ == "__main__":
    main(sys.argv[1])
