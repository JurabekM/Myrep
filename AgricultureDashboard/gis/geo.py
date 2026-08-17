"""Geometry helpers that work with or without Shapely/GeoPandas."""
from __future__ import annotations

import json
from typing import Any

from core.optional import try_import


def polygon_centroid(geojson_text: str) -> tuple[float, float] | None:
    """Centroid (lat, lon) of a GeoJSON polygon; Shapely if present, else mean."""
    try:
        geometry = json.loads(geojson_text)
        ring = geometry["coordinates"][0]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None
    shapely_geom = try_import("shapely.geometry")
    if shapely_geom is not None:
        try:
            centroid = shapely_geom.shape(geometry).centroid
            return float(centroid.y), float(centroid.x)
        except Exception:  # noqa: BLE001
            pass
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def polygon_area_ha(geojson_text: str) -> float | None:
    """Approximate polygon area in hectares (pyproj-accurate when available)."""
    try:
        geometry = json.loads(geojson_text)
        ring = geometry["coordinates"][0]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None
    shapely_geom = try_import("shapely.geometry")
    pyproj = try_import("pyproj")
    if shapely_geom is not None and pyproj is not None:
        try:
            from shapely.ops import transform

            shape = shapely_geom.shape(geometry)
            transformer = pyproj.Transformer.from_crs(
                "EPSG:4326", "EPSG:6933", always_xy=True).transform
            return round(transform(transformer, shape).area / 10_000, 2)
        except Exception:  # noqa: BLE001
            pass
    # Shoelace formula on a local equirectangular projection (adequate <10 km).
    import math

    lat0 = sum(point[1] for point in ring) / len(ring)
    metre_per_deg_lat = 111_320.0
    metre_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))
    xy = [(point[0] * metre_per_deg_lon, point[1] * metre_per_deg_lat) for point in ring]
    area = 0.0
    for i in range(len(xy) - 1):
        area += xy[i][0] * xy[i + 1][1] - xy[i + 1][0] * xy[i][1]
    return round(abs(area) / 2 / 10_000, 2)


def feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap features into a GeoJSON FeatureCollection."""
    return {"type": "FeatureCollection", "features": features}
