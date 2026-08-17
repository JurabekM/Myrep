"""Satellite services with a provider chain.

``GEEProvider`` activates when the ``earthengine-api`` package and service
credentials are configured; otherwise ``LocalProvider`` serves the NDVI/EVI
series stored in the database (seeded + drone-derived), so every feature is
fully functional offline. Planet API is exposed as a plugin-style provider.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from core.cache import cached
from core.optional import try_import
from database.engine import get_setting, read_df, session_scope
from database.models import ImportedFile, SatelliteIndex

log = logging.getLogger(__name__)


class LocalProvider:
    """Offline provider backed by the satellite_indices table."""

    name = "Lokal demo (Sentinel-2 uslubi)"

    def ndvi_series(self, field_id: int, days: int = 730) -> pd.DataFrame:
        since = (date.today() - timedelta(days=days)).isoformat()
        return read_df(
            "SELECT date, ndvi, evi FROM satellite_indices"
            " WHERE field_id = :f AND date >= :s ORDER BY date",
            {"f": field_id, "s": since},
        )


class GEEProvider(LocalProvider):
    """Google Earth Engine provider (Sentinel-2 SR) when credentials exist."""

    name = "Google Earth Engine (Sentinel-2)"

    def __init__(self) -> None:
        import ee  # noqa: PLC0415 - optional import guarded by get_provider

        account = get_setting("gee_service_account")
        key_file = get_setting("gee_key_file")
        credentials = ee.ServiceAccountCredentials(account, key_file)
        ee.Initialize(credentials)
        self._ee = ee

    def ndvi_series(self, field_id: int, days: int = 730) -> pd.DataFrame:
        field = read_df("SELECT lat, lon FROM fields WHERE id = :f", {"f": field_id})
        if field.empty:
            return super().ndvi_series(field_id, days)
        try:
            ee = self._ee
            point = ee.Geometry.Point([float(field.iloc[0].lon), float(field.iloc[0].lat)])
            start = (date.today() - timedelta(days=days)).isoformat()
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(point).filterDate(start, date.today().isoformat())
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
            )

            def to_feature(image):  # type: ignore[no-untyped-def]
                ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
                stats = ndvi.reduceRegion(ee.Reducer.mean(), point.buffer(300), 20)
                return ee.Feature(None, {
                    "date": image.date().format("YYYY-MM-dd"), "ndvi": stats.get("ndvi"),
                })

            features = collection.map(to_feature).getInfo()["features"]
            rows = [
                {"date": f["properties"]["date"],
                 "ndvi": round(float(f["properties"]["ndvi"]), 3),
                 "evi": round(float(f["properties"]["ndvi"]) * 0.85, 3)}
                for f in features if f["properties"].get("ndvi") is not None
            ]
            if rows:
                return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("GEE so'rovi muvaffaqiyatsiz, lokal rejimga o'tildi: %s", exc)
        return super().ndvi_series(field_id, days)


def get_provider() -> LocalProvider:
    """Provider chain: GEE (if configured) -> local demo."""
    if try_import("ee") is not None and get_setting("gee_service_account"):
        try:
            return GEEProvider()
        except Exception as exc:  # noqa: BLE001
            log.warning("GEE ulanmadi (%s); lokal provayder ishlatiladi.", exc)
    return LocalProvider()


def ndvi_series(field_id: int, days: int = 730) -> pd.DataFrame:
    """NDVI/EVI time series for a field through the active provider."""
    return get_provider().ndvi_series(field_id, days)


@cached(ttl=300)
def field_health() -> pd.DataFrame:
    """Latest NDVI per field with a simple health classification."""
    df = read_df(
        "SELECT f.id AS field_id, f.name AS field, fa.name AS farm,"
        " r.name AS region, s.ndvi, s.evi, MAX(s.date) AS date"
        " FROM satellite_indices s"
        " JOIN fields f ON f.id = s.field_id"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " GROUP BY f.id"
    )
    if df.empty:
        return df

    def classify(ndvi: float) -> str:
        if ndvi >= 0.55:
            return "A'lo"
        if ndvi >= 0.4:
            return "Yaxshi"
        if ndvi >= 0.25:
            return "O'rtacha"
        return "Zaif"

    df["holat"] = df["ndvi"].apply(classify)
    return df.sort_values("ndvi", ascending=False)


def process_drone_image(path: Path, field_id: int | None = None,
                        username: str = "") -> str:
    """Process an uploaded GeoTIFF/TIFF/JPG/PNG orthomosaic or NDVI raster.

    With rasterio: reads bands, computes NDVI when NIR+Red exist, stores the
    result as a satellite index record. Without rasterio: Pillow-based
    brightness statistics as the fallback vegetation proxy.
    """
    summary: str
    ndvi_value: float | None = None
    rasterio = try_import("rasterio")
    if rasterio is not None and path.suffix.lower() in {".tif", ".tiff"}:
        try:
            with rasterio.open(path) as src:
                bands = src.count
                if bands >= 4:  # assume R,G,B,NIR orthomosaic
                    red = src.read(1).astype(float)
                    nir = src.read(4).astype(float)
                    denominator = np.where((nir + red) == 0, 1e-6, nir + red)
                    ndvi_value = float(np.clip(np.mean((nir - red) / denominator), -1, 1))
                    summary = (f"GeoTIFF qabul qilindi: {bands} kanal, "
                               f"{src.width}x{src.height}px, o'rtacha NDVI={ndvi_value:.3f}")
                elif bands == 1:
                    data = src.read(1).astype(float)
                    ndvi_value = float(np.clip(np.nanmean(data), -1, 1))
                    summary = (f"NDVI raster qabul qilindi: {src.width}x{src.height}px, "
                               f"o'rtacha qiymat={ndvi_value:.3f}")
                else:
                    summary = f"GeoTIFF qabul qilindi: {bands} kanal, {src.width}x{src.height}px."
        except Exception as exc:  # noqa: BLE001
            summary = f"Rasterni o'qishda xato: {exc}"
    else:
        pil = try_import("PIL.Image")
        if pil is not None:
            try:
                with pil.open(path) as image:
                    gray = np.asarray(image.convert("L"), dtype=float) / 255.0
                    greenness = float(gray.mean())
                    ndvi_value = round(0.1 + greenness * 0.6, 3)
                    summary = (f"Tasvir qabul qilindi: {image.size[0]}x{image.size[1]}px, "
                               f"vegetatsiya bahosi≈{ndvi_value:.3f} (Pillow rejimi)")
            except Exception as exc:  # noqa: BLE001
                summary = f"Tasvirni o'qishda xato: {exc}"
        else:
            summary = f"Fayl saqlandi: {path.name} (raster kutubxonalari o'rnatilmagan)."

    with session_scope() as session:
        session.add(ImportedFile(filename=path.name, file_type=path.suffix.lstrip("."),
                                 uploaded_by=username, summary=summary))
        if ndvi_value is not None and field_id:
            session.add(SatelliteIndex(
                field_id=field_id, date=date.today(), ndvi=round(ndvi_value, 3),
                evi=round(ndvi_value * 0.85, 3), source="dron",
            ))
    field_health.cache.clear()  # type: ignore[attr-defined]
    return summary


def field_options() -> dict[int, str]:
    """id -> label map for field select widgets."""
    df = read_df(
        "SELECT f.id, f.name || ' — ' || fa.name AS label"
        " FROM fields f JOIN farms fa ON fa.id = f.farm_id ORDER BY f.id"
    )
    return {int(row.id): row.label for row in df.itertuples()}
