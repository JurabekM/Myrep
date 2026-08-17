"""First-launch installer: deterministic, realistic demo dataset for Uzbekistan.

Seeds users, 13 regions, 26 districts, 60+ farmers, 75+ farms, 140+ fields,
23 crops, 5 years of yields driven by generated weather (including a 2024
Jizzax drought scenario), weekly market prices, irrigation events, finance
records and NDVI/EVI time series. All randomness uses a fixed seed so every
installation produces the same coherent dataset.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import numpy as np

from config import settings
from core.security import hash_password
from database.engine import get_engine, session_scope
from database.models import (
    Crop, District, Farm, Farmer, Field, FinanceRecord, IrrigationRecord,
    MarketPrice, Region, SatelliteIndex, User, WeatherRecord, YieldRecord,
)

log = logging.getLogger(__name__)
rng = np.random.default_rng(42)

HISTORY_YEARS = list(range(settings.HISTORY_START_YEAR, settings.HISTORY_START_YEAR + 5))

# region name -> (lat, lon, fertility, south_factor, [districts])
REGIONS: dict[str, tuple[float, float, float, float, list[str]]] = {
    "Toshkent": (41.31, 69.28, 1.05, 0.0, ["Zangiota", "Chinoz"]),
    "Andijon": (40.78, 72.34, 1.12, 0.2, ["Asaka", "Marhamat"]),
    "Farg'ona": (40.39, 71.78, 1.10, 0.2, ["Quva", "Rishton"]),
    "Namangan": (41.00, 71.67, 1.08, 0.1, ["Chust", "Pop"]),
    "Samarqand": (39.65, 66.96, 1.06, 0.3, ["Urgut", "Ishtixon"]),
    "Buxoro": (39.77, 64.42, 0.95, 0.5, ["G'ijduvon", "Kogon"]),
    "Jizzax": (40.12, 67.83, 0.98, 0.3, ["Zomin", "G'allaorol"]),
    "Qashqadaryo": (38.86, 65.79, 0.97, 0.6, ["Shahrisabz", "Koson"]),
    "Surxondaryo": (37.94, 67.57, 1.02, 0.9, ["Denov", "Sherobod"]),
    "Sirdaryo": (40.84, 68.66, 1.00, 0.1, ["Guliston", "Boyovut"]),
    "Navoiy": (40.09, 65.38, 0.90, 0.4, ["Karmana", "Qiziltepa"]),
    "Xorazm": (41.55, 60.63, 0.96, 0.2, ["Urganch", "Xiva"]),
    "Qoraqalpog'iston": (42.46, 59.61, 0.85, 0.0, ["Nukus", "Chimboy"]),
}

# name, category, season, water_mm, base_yield t/ha, price so'm/kg, cost so'm/ha
CROPS: list[tuple[str, str, str, float, float, float, float]] = [
    ("Bug'doy", "don", "kuzgi", 450, 4.5, 3000, 6_000_000),
    ("Paxta", "texnik", "yozgi", 700, 3.2, 8000, 12_000_000),
    ("Sholi", "don", "yozgi", 1200, 5.0, 7000, 10_000_000),
    ("Makkajo'xori", "don", "yozgi", 550, 7.0, 2800, 7_000_000),
    ("Arpa", "don", "kuzgi", 400, 3.8, 2500, 5_000_000),
    ("Kartoshka", "sabzavot", "bahorgi", 500, 22.0, 4000, 25_000_000),
    ("Sabzi", "sabzavot", "bahorgi", 450, 30.0, 3000, 18_000_000),
    ("Piyoz", "sabzavot", "bahorgi", 480, 28.0, 2500, 16_000_000),
    ("Pomidor", "sabzavot", "yozgi", 600, 40.0, 5000, 30_000_000),
    ("Bodring", "sabzavot", "yozgi", 550, 35.0, 4500, 26_000_000),
    ("Qovun", "poliz", "yozgi", 400, 20.0, 4000, 12_000_000),
    ("Tarvuz", "poliz", "yozgi", 380, 25.0, 2000, 10_000_000),
    ("Uzum", "meva", "ko'p yillik", 500, 12.0, 8000, 20_000_000),
    ("Olma", "meva", "ko'p yillik", 600, 18.0, 6000, 22_000_000),
    ("O'rik", "meva", "ko'p yillik", 500, 10.0, 9000, 15_000_000),
    ("Shaftoli", "meva", "ko'p yillik", 550, 12.0, 8500, 18_000_000),
    ("Anor", "meva", "ko'p yillik", 520, 14.0, 12000, 20_000_000),
    ("Yong'oq", "meva", "ko'p yillik", 480, 3.0, 35000, 14_000_000),
    ("Soya", "dukkakli", "yozgi", 450, 2.5, 6000, 6_000_000),
    ("Kungaboqar", "moyli", "yozgi", 420, 2.2, 5500, 5_000_000),
    ("Beda", "ozuqa", "ko'p yillik", 800, 9.0, 1500, 4_000_000),
    ("Qand lavlagi", "texnik", "yozgi", 600, 35.0, 1200, 15_000_000),
    ("Sarimsoq", "sabzavot", "kuzgi", 400, 8.0, 15000, 20_000_000),
]

FIRST_NAMES = [
    "Akmal", "Bobur", "Davron", "Eldor", "Farrux", "G'ayrat", "Hasan", "Islom",
    "Jasur", "Kamol", "Laziz", "Muzaffar", "Nodir", "Otabek", "Po'lat", "Qudrat",
    "Rustam", "Sardor", "Temur", "Ulug'bek", "Vali", "Xurshid", "Yusuf", "Zafar",
    "Dilnoza", "Gulnora", "Malika", "Nilufar", "Sevara", "Zulfiya",
]
LAST_NAMES = [
    "Karimov", "Rahimov", "Toshmatov", "Yusupov", "Aliyev", "Islomov", "Saidov",
    "Nazarov", "Ergashev", "Qodirov", "Mirzayev", "Abdullayev", "Sultonov",
    "Xolmatov", "Bekmurodov", "Jo'rayev", "Olimov", "Sharipov", "Umarov", "Vohidov",
]
SOIL_TYPES = ["bo'z tuproq", "o'tloq tuproq", "sho'rlangan tuproq", "qumloq tuproq", "gilli tuproq"]
IRRIGATION_METHODS = ["egat", "tomchilatib", "yomg'irlatib", "bostirib"]

# Financial calibration: farmers realise ~45% of the retail market price
# (wholesale), and full production cost (labour, fuel, rent, inputs) runs
# 1.5–1.9x of the base agronomic cost — keeps demo ROI in a realistic range.
WHOLESALE_FACTOR = 0.45
EXPENSE_FACTOR_RANGE = (1.5, 1.9)


def is_seeded() -> bool:
    """The database counts as installed when at least one user exists."""
    try:
        with session_scope() as session:
            return session.query(User).count() > 0
    except Exception:  # noqa: BLE001
        return False


def seed_if_empty() -> bool:
    """Populate the demo dataset on first launch. Returns True when seeded."""
    if is_seeded():
        return False
    log.info("Demo ma'lumotlar yaratilmoqda (birinchi ishga tushirish)...")
    _seed_users()
    region_rows, district_rows = _seed_geography()
    crop_rows = _seed_crops()
    farms, fields = _seed_farms(district_rows)
    weather = _seed_weather(district_rows)
    ratios = _seed_yields_and_irrigation(fields, crop_rows, district_rows, weather)
    price_index = _seed_market_prices(crop_rows)
    _seed_finance(farms, fields, crop_rows, price_index)
    _seed_satellite(fields, ratios)
    log.info("Demo ma'lumotlar tayyor: %d viloyat, %d tuman, %d dala.",
             len(region_rows), len(district_rows), len(fields))
    return True


def _seed_users() -> None:
    with session_scope() as session:
        session.add_all([
            User(username="admin", full_name="Bosh administrator",
                 password_hash=hash_password("admin123"), role="admin"),
            User(username="menejer", full_name="Hudud menejeri",
                 password_hash=hash_password("manager123"), role="manager"),
            User(username="kuzatuvchi", full_name="Tahlilchi-kuzatuvchi",
                 password_hash=hash_password("viewer123"), role="viewer"),
        ])


def _seed_geography() -> tuple[list[Region], list[District]]:
    regions: list[Region] = []
    districts: list[District] = []
    with session_scope() as session:
        for name, (lat, lon, fertility, _south, district_names) in REGIONS.items():
            region = Region(name=name, lat=lat, lon=lon, fertility=fertility)
            session.add(region)
            session.flush()
            regions.append(region)
            for i, dname in enumerate(district_names):
                district = District(
                    region_id=region.id, name=f"{dname} tumani",
                    lat=lat + (0.25 if i == 0 else -0.25) + float(rng.normal(0, 0.05)),
                    lon=lon + (0.30 if i == 0 else -0.30) + float(rng.normal(0, 0.05)),
                )
                session.add(district)
                districts.append(district)
        session.flush()
    return regions, districts


def _seed_crops() -> list[Crop]:
    crops: list[Crop] = []
    with session_scope() as session:
        for name, category, season, water, yield_t, price, cost in CROPS:
            crop = Crop(name=name, category=category, season=season,
                        water_need_mm=water, base_yield_t_ha=yield_t,
                        base_price_per_kg=price, cost_per_ha=cost)
            session.add(crop)
            crops.append(crop)
        session.flush()
    return crops


def _field_polygon(lat: float, lon: float, area_ha: float) -> str:
    """Build an irregular quadrilateral GeoJSON polygon roughly sized to area."""
    half = max(0.0012, float(np.sqrt(area_ha)) * 0.00045)
    jitter = lambda: float(rng.normal(0, half * 0.15))  # noqa: E731
    ring = [
        [lon - half + jitter(), lat - half + jitter()],
        [lon + half + jitter(), lat - half + jitter()],
        [lon + half + jitter(), lat + half + jitter()],
        [lon - half + jitter(), lat + half + jitter()],
    ]
    ring.append(ring[0])
    return json.dumps({"type": "Polygon", "coordinates": [ring]})


def _seed_farms(districts: list[District]) -> tuple[list[Farm], list[Field]]:
    farmers: list[Farmer] = []
    farms: list[Farm] = []
    fields: list[Field] = []
    with session_scope() as session:
        for i in range(60):
            district = districts[int(rng.integers(0, len(districts)))]
            name = (f"{FIRST_NAMES[int(rng.integers(0, len(FIRST_NAMES)))]} "
                    f"{LAST_NAMES[int(rng.integers(0, len(LAST_NAMES)))]}")
            farmer = Farmer(
                name=name, district_id=district.id,
                phone=f"+9989{rng.integers(0, 10)}{rng.integers(1_000_000, 9_999_999)}",
            )
            session.add(farmer)
            farmers.append(farmer)
        session.flush()

        farm_no = 0
        for farmer in farmers:
            for _ in range(1 + int(rng.random() < 0.25)):  # ~75 farms
                farm_no += 1
                farm = Farm(
                    name=f"{farmer.name.split()[-1]} fermer xo'jaligi №{farm_no}",
                    farmer_id=farmer.id, district_id=farmer.district_id, area_ha=0.0,
                )
                session.add(farm)
                farms.append(farm)
        session.flush()

        district_by_id = {d.id: d for d in districts}
        field_no = 0
        while len(fields) < 140:
            farm = farms[int(rng.integers(0, len(farms)))]
            district = district_by_id[farm.district_id]
            field_no += 1
            area = float(np.round(rng.uniform(5, 120), 1))
            lat = district.lat + float(rng.uniform(-0.12, 0.12))
            lon = district.lon + float(rng.uniform(-0.12, 0.12))
            field = Field(
                farm_id=farm.id, name=f"Kontur-{field_no}", area_ha=area,
                soil_type=SOIL_TYPES[int(rng.integers(0, len(SOIL_TYPES)))],
                lat=lat, lon=lon, geometry_geojson=_field_polygon(lat, lon, area),
            )
            farm.area_ha = float(np.round(farm.area_ha + area, 1))
            session.add(field)
            fields.append(field)
        session.flush()
    return farms, fields


def _seed_weather(districts: list[District]) -> dict[tuple[int, int], dict[str, float]]:
    """Generate daily weather per district; return per (district, year) season stats."""
    start = date(settings.HISTORY_START_YEAR, 1, 1)
    end = date.today()
    n_days = (end - start).days + 1
    dates = [start + timedelta(days=i) for i in range(n_days)]
    doy = np.array([d.timetuple().tm_yday for d in dates], dtype=float)
    years = np.array([d.year for d in dates])
    months = np.array([d.month for d in dates])

    region_by_district: dict[int, tuple[str, float]] = {}
    with session_scope() as session:
        for district in districts:
            region = session.get(Region, district.region_id)
            south = REGIONS[region.name][3]
            region_by_district[district.id] = (region.name, south)

    season_mask = np.isin(months, settings.WEATHER_SEASON_MONTHS)
    stats: dict[tuple[int, int], dict[str, float]] = {}
    table = WeatherRecord.__table__
    engine = get_engine()

    for district in districts:
        region_name, south = region_by_district[district.id]
        seasonal = 14.0 + 14.5 * np.sin((doy - 105) / 365.0 * 2 * np.pi)
        t_max = seasonal + 6 + south * 3 + rng.normal(0, 2.5, n_days)
        t_min = seasonal - 5 + south * 2 + rng.normal(0, 2.0, n_days)
        rain_prob = 0.22 + 0.16 * np.cos((doy - 60) / 365.0 * 2 * np.pi)
        rain = (rng.random(n_days) < rain_prob) * rng.exponential(4.5, n_days)
        rain = np.where(np.isin(months, (6, 7, 8)), rain * 0.25, rain)
        # 2024 drought scenario in Jizzax region — feeds analytics & the AI module.
        if region_name == "Jizzax":
            rain = np.where(years == 2024, rain * 0.45, rain)
        humidity = np.clip(78 - (t_max - 10) * 1.3 + rng.normal(0, 6, n_days), 15, 98)

        rows = [
            {
                "district_id": district.id, "date": dates[i],
                "t_min": round(float(t_min[i]), 1), "t_max": round(float(t_max[i]), 1),
                "precipitation_mm": round(float(rain[i]), 1),
                "humidity": round(float(humidity[i]), 1), "source": "demo",
            }
            for i in range(n_days)
        ]
        with engine.begin() as connection:
            connection.execute(table.insert(), rows)

        for year in set(years.tolist()):
            mask = (years == year) & season_mask
            if mask.any():
                stats[(district.id, int(year))] = {
                    "precip": float(rain[mask].sum()),
                    "t_avg": float(((t_max + t_min) / 2)[mask].mean()),
                    "humidity": float(humidity[mask].mean()),
                }
    return stats


def _seed_yields_and_irrigation(
    fields: list[Field], crops: list[Crop], districts: list[District],
    weather: dict[tuple[int, int], dict[str, float]],
) -> dict[tuple[int, int], float]:
    """Yields derive from water supply vs crop need — ML models learn real signal."""
    fertility_by_district: dict[int, float] = {}
    region_name_by_district: dict[int, str] = {}
    with session_scope() as session:
        for district in districts:
            region = session.get(Region, district.region_id)
            fertility_by_district[district.id] = region.fertility
            region_name_by_district[district.id] = region.name
        farms = {farm.id: farm.district_id
                 for farm in session.query(Farm).all()}  # farm -> district

    ratios: dict[tuple[int, int], float] = {}
    yield_rows: list[dict] = []
    irrigation_rows: list[dict] = []

    for field in fields:
        district_id = farms[field.farm_id]
        # Real crop mix: every field's 3-crop rotation contains one strategic
        # crop (wheat or cotton) so region×crop analytics are well-populated.
        pool_idx = [int(rng.integers(0, 2))]
        pool_idx += [int(i) for i in rng.choice(
            np.arange(2, len(crops)), size=2, replace=False)]
        rotation_offset = int(rng.integers(0, 3))
        for year in HISTORY_YEARS:
            crop = crops[pool_idx[(year + rotation_offset) % 3]]
            season = weather.get((district_id, year), {"precip": 120.0, "t_avg": 24.0})
            coverage = float(rng.uniform(0.45, 0.85))
            if year == 2024 and region_name_by_district[district_id] == "Jizzax":
                coverage *= 0.65  # drought year canal restrictions
            irrigation_mm = crop.water_need_mm * coverage
            supply = season["precip"] + irrigation_mm
            ratio = float(np.clip(supply / crop.water_need_mm, 0.35, 1.15))
            heat_penalty = 1.0 - max(0.0, season["t_avg"] - 27.0) * 0.03
            yield_t = max(
                0.2,
                crop.base_yield_t_ha * ratio * fertility_by_district[district_id]
                * heat_penalty * float(1 + rng.normal(0, 0.08)),
            )
            ratios[(field.id, year)] = ratio
            yield_rows.append({
                "field_id": field.id, "crop_id": crop.id, "year": year,
                "area_ha": field.area_ha, "yield_t_ha": round(yield_t, 2),
                "production_t": round(yield_t * field.area_ha, 1),
            })
            total_m3 = irrigation_mm * 10 * field.area_ha  # 1 mm/ha = 10 m3
            method = IRRIGATION_METHODS[int(rng.integers(0, len(IRRIGATION_METHODS)))]
            for month in (4, 5, 6, 7, 8):
                irrigation_rows.append({
                    "field_id": field.id,
                    "date": date(year, month, int(rng.integers(1, 28))),
                    "water_m3": round(total_m3 / 5, 0), "method": method,
                })

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(YieldRecord.__table__.insert(), yield_rows)
        connection.execute(IrrigationRecord.__table__.insert(), irrigation_rows)
    return ratios


def _seed_market_prices(crops: list[Crop]) -> dict[tuple[int, int], float]:
    """Weekly national market prices with inflation + seasonality. Returns yearly avg."""
    start = date(settings.HISTORY_START_YEAR, 1, 4)
    end = date.today()
    price_rows: list[dict] = []
    yearly: dict[tuple[int, int], list[float]] = {}
    for crop in crops:
        phase = float(rng.uniform(0, 2 * np.pi))
        day = start
        while day <= end:
            years_passed = day.year - settings.HISTORY_START_YEAR
            seasonal = 1 + 0.13 * np.sin(2 * np.pi * day.timetuple().tm_yday / 365 + phase)
            price = crop.base_price_per_kg * (1 + 0.09 * years_passed) * seasonal
            price *= float(1 + rng.normal(0, 0.04))
            price_rows.append({
                "crop_id": crop.id, "date": day, "price_per_kg": round(price, 0),
                "market_name": "Milliy bozor", "source": "demo",
            })
            yearly.setdefault((crop.id, day.year), []).append(price)
            day += timedelta(days=7)
    with get_engine().begin() as connection:
        connection.execute(MarketPrice.__table__.insert(), price_rows)
    return {key: float(np.mean(values)) for key, values in yearly.items()}


def _seed_finance(
    farms: list[Farm], fields: list[Field], crops: list[Crop],
    price_index: dict[tuple[int, int], float],
) -> None:
    crop_by_id = {crop.id: crop for crop in crops}
    fields_by_farm: dict[int, list[Field]] = {}
    for field in fields:
        fields_by_farm.setdefault(field.farm_id, []).append(field)

    from database.engine import read_df
    yields_df = read_df(
        "SELECT f.farm_id, y.field_id, y.crop_id, y.year, y.production_t, y.area_ha "
        "FROM yield_records y JOIN fields f ON f.id = y.field_id"
    )

    rows: list[dict] = []
    for farm in farms:
        farm_yields = yields_df[yields_df.farm_id == farm.id]
        for year in HISTORY_YEARS:
            year_slice = farm_yields[farm_yields.year == year]
            if year_slice.empty:
                continue
            expense = float(sum(
                row.area_ha * crop_by_id[row.crop_id].cost_per_ha
                for row in year_slice.itertuples()
            )) * float(rng.uniform(*EXPENSE_FACTOR_RANGE))
            income = float(sum(
                row.production_t * 1000
                * price_index.get((row.crop_id, year),
                                  crop_by_id[row.crop_id].base_price_per_kg)
                for row in year_slice.itertuples()
            )) * WHOLESALE_FACTOR * float(rng.uniform(0.93, 1.05))
            rows.append({"farm_id": farm.id, "year": year, "category": "expense",
                         "amount": round(expense, 0), "note": "Yillik ishlab chiqarish xarajatlari"})
            rows.append({"farm_id": farm.id, "year": year, "category": "income",
                         "amount": round(income, 0), "note": "Mahsulot sotuvidan tushum"})
            if rng.random() < 0.35:
                rows.append({"farm_id": farm.id, "year": year, "category": "credit",
                             "amount": round(expense * 0.3, 0), "note": "Agrobank imtiyozli krediti"})
            if rng.random() < 0.4:
                rows.append({"farm_id": farm.id, "year": year, "category": "subsidy",
                             "amount": round(expense * 0.1, 0), "note": "Davlat subsidiyasi"})
    with get_engine().begin() as connection:
        connection.execute(FinanceRecord.__table__.insert(), rows)


def _seed_satellite(fields: list[Field], ratios: dict[tuple[int, int], float]) -> None:
    """Bi-weekly NDVI/EVI series for the last ~30 months per field."""
    end = date.today()
    start = end - timedelta(days=900)
    rows: list[dict] = []
    for field in fields:
        day = start
        while day <= end:
            doy = day.timetuple().tm_yday
            year_ratio = ratios.get((field.id, min(day.year, HISTORY_YEARS[-1])), 0.8)
            peak = 0.30 + 0.42 * year_ratio
            ndvi = 0.14 + peak * float(np.exp(-((doy - 165) / 72.0) ** 2))
            ndvi = float(np.clip(ndvi + rng.normal(0, 0.03), 0.05, 0.95))
            evi = float(np.clip(ndvi * 0.85 + rng.normal(0, 0.02), 0.03, 0.9))
            rows.append({"field_id": field.id, "date": day, "ndvi": round(ndvi, 3),
                         "evi": round(evi, 3), "source": "demo"})
            day += timedelta(days=14)
    with get_engine().begin() as connection:
        connection.execute(SatelliteIndex.__table__.insert(), rows)
