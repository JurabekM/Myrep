"""Interactive folium map builder: layers, clusters, heatmaps, choropleth."""
from __future__ import annotations

import json
import logging

import folium
from folium.plugins import Fullscreen, HeatMap, MarkerCluster

from database.engine import get_setting, read_df

log = logging.getLogger(__name__)

TILE_LAYERS = [
    ("OpenStreetMap", "OpenStreetMap", "Ko'cha xaritasi"),
    ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
     "Esri", "Sun'iy yo'ldosh"),
    ("https://tile.opentopomap.org/{z}/{x}/{y}.png", "OpenTopoMap", "Relyef"),
]


def _color_for(value: float, low: float, high: float) -> str:
    """Green-yellow-red scale for the metric legend."""
    if high - low < 1e-9:
        return "#4caf50"
    ratio = max(0.0, min(1.0, (value - low) / (high - low)))
    if ratio > 0.66:
        return "#2e7d32"
    if ratio > 0.33:
        return "#f9a825"
    return "#c62828"


def _fields_frame(year: int, region_id: int | None) -> "object":
    sql = (
        "SELECT f.id, f.name, f.area_ha, f.soil_type, f.lat, f.lon,"
        " f.geometry_geojson, fa.name AS farm, fm.name AS farmer,"
        " r.name AS region, r.id AS region_id, d.name AS district,"
        " COALESCE(y.yield_t_ha, 0) AS yield_t_ha,"
        " COALESCE(c.name, '-') AS crop,"
        " COALESCE(s.ndvi, 0) AS ndvi"
        " FROM fields f"
        " JOIN farms fa ON fa.id = f.farm_id"
        " JOIN farmers fm ON fm.id = fa.farmer_id"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id"
        " LEFT JOIN yield_records y ON y.field_id = f.id AND y.year = :year"
        " LEFT JOIN crops c ON c.id = y.crop_id"
        " LEFT JOIN (SELECT field_id, ndvi, MAX(date) FROM satellite_indices"
        "            GROUP BY field_id) s ON s.field_id = f.id"
    )
    params: dict = {"year": year}
    if region_id:
        sql += " WHERE r.id = :region_id"
        params["region_id"] = region_id
    return read_df(sql, params)


def build_map(metric: str = "yield", year: int | None = None,
              region_id: int | None = None, height: int = 640) -> str:
    """Render the interactive map to embeddable HTML.

    metric: 'yield' colors polygons by t/ha, 'ndvi' by vegetation index.
    Layers: 3 tile sets, field polygons, farm marker cluster, heatmap.
    """
    from analytics.kpi import latest_year

    year = year or latest_year()
    df = _fields_frame(year, region_id)

    center = [float(get_setting("map_default_lat", "41.3")),
              float(get_setting("map_default_lon", "64.5"))]
    zoom = int(get_setting("map_default_zoom", "6"))
    if region_id and not df.empty:
        center = [float(df.lat.mean()), float(df.lon.mean())]
        zoom = 9

    fmap = folium.Map(location=center, zoom_start=zoom, tiles=None,
                      control_scale=True)
    for tiles, attr, label in TILE_LAYERS:
        folium.TileLayer(tiles=tiles, attr=attr, name=label,
                         show=(label == "Ko'cha xaritasi")).add_to(fmap)

    metric_column = "ndvi" if metric == "ndvi" else "yield_t_ha"
    metric_label = "NDVI" if metric == "ndvi" else "Hosildorlik (t/ga)"
    values = df[metric_column].astype(float)
    low, high = (float(values.min()), float(values.max())) if len(values) else (0, 1)

    polygons = folium.FeatureGroup(name=f"Dalalar — {metric_label}", show=True)
    heat_points: list[list[float]] = []
    for row in df.itertuples():
        try:
            geometry = json.loads(row.geometry_geojson)
        except (json.JSONDecodeError, TypeError):
            continue
        value = float(getattr(row, metric_column))
        color = _color_for(value, low, high)
        popup = folium.Popup(
            f"<b>{row.name}</b><br>"
            f"Fermer xo'jaligi: {row.farm}<br>"
            f"Fermer: {row.farmer}<br>"
            f"Hudud: {row.region}, {row.district}<br>"
            f"Maydon: {row.area_ha} ga | Tuproq: {row.soil_type}<br>"
            f"Ekin ({year}): {row.crop}<br>"
            f"Hosildorlik: {row.yield_t_ha} t/ga | NDVI: {row.ndvi:.2f}",
            max_width=320,
        )
        folium.GeoJson(
            {"type": "Feature", "geometry": geometry},
            style_function=lambda _f, c=color: {
                "fillColor": c, "color": c, "weight": 2, "fillOpacity": 0.45,
            },
            tooltip=f"{row.name}: {value:.2f}",
        ).add_child(popup).add_to(polygons)
        heat_points.append([row.lat, row.lon, max(0.05, value)])
    polygons.add_to(fmap)

    cluster = MarkerCluster(name="Fermer xo'jaliklari").add_to(fmap)
    farms = df.groupby("farm").agg(
        lat=("lat", "mean"), lon=("lon", "mean"),
        area=("area_ha", "sum"), region=("region", "first"),
    ).reset_index()
    for row in farms.itertuples():
        folium.Marker(
            [row.lat, row.lon],
            icon=folium.Icon(color="green", icon="leaf"),
            popup=f"<b>{row.farm}</b><br>{row.region}<br>Jami: {row.area:.0f} ga",
        ).add_to(cluster)

    if heat_points:
        HeatMap(heat_points, name=f"Issiqlik xaritasi — {metric_label}",
                radius=22, show=False).add_to(fmap)

    Fullscreen(title="To'liq ekran", title_cancel="Chiqish").add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    figure = folium.Figure(height=height)
    fmap.add_to(figure)
    return figure._repr_html_()


def region_options() -> dict[int, str]:
    """id -> name map for region filters (0 = all)."""
    df = read_df("SELECT id, name FROM regions ORDER BY name")
    options = {0: "Barcha viloyatlar"}
    options.update({int(row.id): row.name for row in df.itertuples()})
    return options
