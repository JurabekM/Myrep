"""ML model lifecycle: training frames from the DB, persistence, prediction.

Base models use scikit-learn (always available). When XGBoost / LightGBM /
CatBoost are installed the trainer also evaluates them and keeps whichever
scores best on a hold-out split — fully automatic, no configuration needed.
"""
from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier, RandomForestClassifier, RandomForestRegressor,
)
from sklearn.metrics import accuracy_score, r2_score
from sklearn.model_selection import train_test_split

from config import settings
from core.optional import try_import
from database.engine import read_df

log = logging.getLogger(__name__)

MODEL_FILES = {
    "yield": settings.MODELS_DIR / "yield_model.pkl",
    "disease": settings.MODELS_DIR / "disease_model.pkl",
    "water": settings.MODELS_DIR / "water_model.pkl",
    "crop": settings.MODELS_DIR / "crop_recommender.pkl",
}
METRICS_FILE = settings.MODELS_DIR / "metrics.json"

YIELD_FEATURES = ["crop_id", "region_id", "area_ha", "precip", "t_avg",
                  "irrigation_mm", "water_need_mm", "fertility"]
DISEASE_FEATURES = ["humidity", "t_avg", "precip", "ndvi"]
WATER_FEATURES = ["water_need_mm", "precip", "t_avg", "area_ha"]
CROP_FEATURES = ["region_id", "precip", "t_avg", "fertility"]

_loaded: dict[str, Any] = {}


# --------------------------------------------------------------------------
# Training frames
# --------------------------------------------------------------------------
def _yield_frame() -> pd.DataFrame:
    df = read_df(
        "SELECT y.yield_t_ha, y.area_ha, y.year, y.crop_id, c.water_need_mm,"
        " r.id AS region_id, r.fertility, d.id AS district_id, y.field_id"
        " FROM yield_records y"
        " JOIN crops c ON c.id = y.crop_id"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
    )
    weather = read_df(
        "SELECT district_id, CAST(strftime('%Y', date) AS INTEGER) AS year,"
        " SUM(precipitation_mm) AS precip, AVG((t_min+t_max)/2) AS t_avg"
        " FROM weather_records"
        " WHERE CAST(strftime('%m', date) AS INTEGER) BETWEEN 4 AND 9"
        " GROUP BY district_id, year"
    )
    irrigation = read_df(
        "SELECT field_id, CAST(strftime('%Y', date) AS INTEGER) AS year,"
        " SUM(water_m3) AS water_m3"
        " FROM irrigation_records GROUP BY field_id, year"
    )
    df = df.merge(weather, on=["district_id", "year"], how="left")
    df = df.merge(irrigation, on=["field_id", "year"], how="left")
    df["irrigation_mm"] = df["water_m3"].fillna(0) / (df["area_ha"] * 10).clip(lower=0.1)
    return df.dropna(subset=["precip", "t_avg"])


def _disease_frame() -> pd.DataFrame:
    """Synthetic agronomy labels: fungal risk grows with humidity in 18–28 °C."""
    df = read_df(
        "SELECT w.district_id, CAST(strftime('%Y', w.date) AS INTEGER) AS year,"
        " CAST(strftime('%m', w.date) AS INTEGER) AS month,"
        " AVG(w.humidity) AS humidity, AVG((w.t_min+w.t_max)/2) AS t_avg,"
        " SUM(w.precipitation_mm) AS precip"
        " FROM weather_records w GROUP BY w.district_id, year, month"
    )
    rng = np.random.default_rng(7)
    df["ndvi"] = np.clip(0.2 + 0.5 * np.sin((df["month"] - 2) / 12 * np.pi)
                         + rng.normal(0, 0.05, len(df)), 0.05, 0.9)
    temp_window = ((df["t_avg"] > 18) & (df["t_avg"] < 28)).astype(float)
    risk_score = 1 / (1 + np.exp(-(0.09 * (df["humidity"] - 62)))) * (0.4 + 0.6 * temp_window)
    df["label"] = (rng.random(len(df)) < risk_score).astype(int)
    return df


def _water_frame() -> pd.DataFrame:
    """Water requirement rows: deficit(m3/ha) = (need − effective precip) × 10."""
    crops = read_df("SELECT id AS crop_id, water_need_mm FROM crops")
    weather = read_df(
        "SELECT district_id, CAST(strftime('%Y', date) AS INTEGER) AS year,"
        " SUM(precipitation_mm) AS precip, AVG((t_min+t_max)/2) AS t_avg"
        " FROM weather_records"
        " WHERE CAST(strftime('%m', date) AS INTEGER) BETWEEN 4 AND 9"
        " GROUP BY district_id, year"
    )
    rng = np.random.default_rng(11)
    rows = []
    for crop in crops.itertuples():
        sample = weather.sample(min(60, len(weather)), random_state=int(crop.crop_id))
        for w in sample.itertuples():
            heat_extra = max(0.0, w.t_avg - 24) * 12
            deficit = max(0.0, crop.water_need_mm + heat_extra - 0.7 * w.precip) * 10
            rows.append({
                "water_need_mm": crop.water_need_mm, "precip": w.precip,
                "t_avg": w.t_avg, "area_ha": float(rng.uniform(5, 120)),
                "target_m3_ha": deficit * float(1 + rng.normal(0, 0.05)),
            })
    return pd.DataFrame(rows)


def _crop_frame() -> pd.DataFrame:
    """Label = historically most profitable crop per district-year."""
    df = read_df(
        "SELECT y.crop_id, y.year, d.id AS district_id, r.id AS region_id,"
        " r.fertility, AVG(y.yield_t_ha) AS avg_yield, c.base_price_per_kg,"
        " c.cost_per_ha"
        " FROM yield_records y"
        " JOIN crops c ON c.id = y.crop_id"
        " JOIN fields f ON f.id = y.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " GROUP BY d.id, y.year, y.crop_id"
    )
    weather = read_df(
        "SELECT district_id, CAST(strftime('%Y', date) AS INTEGER) AS year,"
        " SUM(precipitation_mm) AS precip, AVG((t_min+t_max)/2) AS t_avg"
        " FROM weather_records"
        " WHERE CAST(strftime('%m', date) AS INTEGER) BETWEEN 4 AND 9"
        " GROUP BY district_id, year"
    )
    df["profit_ha"] = df["avg_yield"] * 1000 * df["base_price_per_kg"] - df["cost_per_ha"]
    best = df.loc[df.groupby(["district_id", "year"])["profit_ha"].idxmax()]
    return best.merge(weather, on=["district_id", "year"], how="inner")


# --------------------------------------------------------------------------
# Optional gradient-boosting challengers
# --------------------------------------------------------------------------
def _challenger_regressors() -> list[tuple[str, Any]]:
    challengers: list[tuple[str, Any]] = []
    xgb = try_import("xgboost")
    if xgb is not None:
        challengers.append(("xgboost", xgb.XGBRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.08, verbosity=0)))
    lgb = try_import("lightgbm")
    if lgb is not None:
        challengers.append(("lightgbm", lgb.LGBMRegressor(
            n_estimators=200, verbose=-1)))
    cat = try_import("catboost")
    if cat is not None:
        challengers.append(("catboost", cat.CatBoostRegressor(
            iterations=200, verbose=False)))
    return challengers


# --------------------------------------------------------------------------
# Training
# --------------------------------------------------------------------------
def train_all(force: bool = False) -> dict[str, Any]:
    """Train (or load) every model; persists pickles + metrics.json."""
    settings.ensure_directories()
    if not force and all(path.exists() for path in MODEL_FILES.values()):
        return model_status()

    metrics: dict[str, Any] = {"trained_at": datetime.now().isoformat(timespec="seconds")}

    # 1) Yield regression — champion/challenger selection.
    frame = _yield_frame()
    x_train, x_test, y_train, y_test = train_test_split(
        frame[YIELD_FEATURES], frame["yield_t_ha"], test_size=0.2, random_state=42)
    champion_name = "random_forest"
    champion = RandomForestRegressor(n_estimators=180, random_state=42, n_jobs=-1)
    champion.fit(x_train, y_train)
    best_r2 = r2_score(y_test, champion.predict(x_test))
    for name, challenger in _challenger_regressors():
        try:
            challenger.fit(x_train, y_train)
            score = r2_score(y_test, challenger.predict(x_test))
            if score > best_r2:
                champion, champion_name, best_r2 = challenger, name, score
        except Exception as exc:  # noqa: BLE001
            log.warning("Challenger %s failed: %s", name, exc)
    _save("yield", champion)
    metrics["yield"] = {"algorithm": champion_name, "r2": round(float(best_r2), 3),
                        "rows": len(frame)}

    # 2) Disease risk classification.
    disease = _disease_frame()
    x_train, x_test, y_train, y_test = train_test_split(
        disease[DISEASE_FEATURES], disease["label"], test_size=0.2, random_state=42)
    clf = GradientBoostingClassifier(random_state=42)
    clf.fit(x_train, y_train)
    metrics["disease"] = {
        "algorithm": "gradient_boosting",
        "accuracy": round(float(accuracy_score(y_test, clf.predict(x_test))), 3),
        "rows": len(disease),
    }
    _save("disease", clf)

    # 3) Water need regression.
    water = _water_frame()
    x_train, x_test, y_train, y_test = train_test_split(
        water[WATER_FEATURES], water["target_m3_ha"], test_size=0.2, random_state=42)
    reg = RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1)
    reg.fit(x_train, y_train)
    metrics["water"] = {
        "algorithm": "random_forest",
        "r2": round(float(r2_score(y_test, reg.predict(x_test))), 3),
        "rows": len(water),
    }
    _save("water", reg)

    # 4) Crop recommendation classification.
    crop = _crop_frame()
    recommender = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
    recommender.fit(crop[CROP_FEATURES], crop["crop_id"])
    metrics["crop"] = {
        "algorithm": "random_forest",
        "accuracy": round(float(recommender.score(crop[CROP_FEATURES], crop["crop_id"])), 3),
        "rows": len(crop),
    }
    _save("crop", recommender)

    METRICS_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _loaded.clear()
    log.info("ML modellari o'qitildi: yield R²=%.3f (%s)", best_r2, champion_name)
    return metrics


def _save(name: str, model: Any) -> None:
    with open(MODEL_FILES[name], "wb") as fh:
        pickle.dump(model, fh)


def _load(name: str) -> Any:
    if name not in _loaded:
        if not MODEL_FILES[name].exists():
            train_all()
        with open(MODEL_FILES[name], "rb") as fh:
            _loaded[name] = pickle.load(fh)  # noqa: S301 - own artifacts
    return _loaded[name]


def model_status() -> dict[str, Any]:
    """Metrics of the last training run (trains first if never run)."""
    if not METRICS_FILE.exists():
        return train_all(force=True)
    return json.loads(METRICS_FILE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Prediction API
# --------------------------------------------------------------------------
def predict_yield(crop_id: int, region_id: int, area_ha: float, precip: float,
                  t_avg: float, irrigation_mm: float, water_need_mm: float,
                  fertility: float) -> float:
    """Predicted yield in t/ha for the given agronomic scenario."""
    frame = pd.DataFrame([{
        "crop_id": crop_id, "region_id": region_id, "area_ha": area_ha,
        "precip": precip, "t_avg": t_avg, "irrigation_mm": irrigation_mm,
        "water_need_mm": water_need_mm, "fertility": fertility,
    }])[YIELD_FEATURES]
    return round(float(_load("yield").predict(frame)[0]), 2)


def predict_disease_risk(humidity: float, t_avg: float, precip: float,
                         ndvi: float) -> float:
    """Probability (0..1) of fungal disease pressure."""
    frame = pd.DataFrame([{"humidity": humidity, "t_avg": t_avg,
                           "precip": precip, "ndvi": ndvi}])[DISEASE_FEATURES]
    return round(float(_load("disease").predict_proba(frame)[0][1]), 3)


def predict_water_need(water_need_mm: float, precip: float, t_avg: float,
                       area_ha: float) -> float:
    """Predicted irrigation requirement in m³/ha for the season."""
    frame = pd.DataFrame([{"water_need_mm": water_need_mm, "precip": precip,
                           "t_avg": t_avg, "area_ha": area_ha}])[WATER_FEATURES]
    return round(float(_load("water").predict(frame)[0]), 0)


def recommend_crops(region_id: int, precip: float, t_avg: float,
                    fertility: float, top_n: int = 3) -> list[dict[str, Any]]:
    """Top-N recommended crops with model confidence."""
    model = _load("crop")
    frame = pd.DataFrame([{"region_id": region_id, "precip": precip,
                           "t_avg": t_avg, "fertility": fertility}])[CROP_FEATURES]
    probabilities = model.predict_proba(frame)[0]
    crops = read_df("SELECT id, name FROM crops").set_index("id")["name"].to_dict()
    ranked = sorted(zip(model.classes_, probabilities), key=lambda p: -p[1])[:top_n]
    return [
        {"crop": crops.get(int(crop_id), f"Ekin #{crop_id}"),
         "confidence": round(float(prob) * 100, 1)}
        for crop_id, prob in ranked
    ]
