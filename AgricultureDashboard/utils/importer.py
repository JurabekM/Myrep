"""Universal import pipeline.

Accepts CSV / Excel / JSON / GeoJSON / Shapefile / KML / TIFF / GeoTIFF / ZIP
uploads, auto-detects the payload type by extension + column signature, and
routes rows into the right tables. Optional geo libraries improve fidelity;
pure-Python fallbacks keep every path working.
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config import settings
from core.cache import clear_all_caches
from core.optional import try_import
from core.security import audit
from database.engine import session_scope
from database.models import (
    Crop, Farm, Field, ImportedFile, MarketPrice, YieldRecord,
)

log = logging.getLogger(__name__)

PRICE_COLUMNS = {"crop", "ekin", "price", "narx"}
YIELD_COLUMNS = {"crop", "ekin", "yield", "hosildorlik", "year", "yil"}


def handle_upload(filename: str, content: bytes, username: str = "") -> str:
    """Entry point for every UI upload; returns a human-readable summary."""
    settings.ensure_directories()
    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    target = settings.UPLOAD_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{safe_name}"
    target.write_bytes(content)
    extension = target.suffix.lower()
    try:
        if extension == ".zip":
            summary = _handle_zip(target, username)
        elif extension in {".csv", ".xlsx", ".xls"}:
            summary = _handle_table(target, username)
        elif extension in {".geojson", ".json"}:
            summary = _handle_geojson(target, username)
        elif extension == ".shp":
            summary = _handle_shapefile(target, username)
        elif extension == ".kml":
            summary = _handle_kml(target, username)
        elif extension in {".tif", ".tiff", ".jpg", ".jpeg", ".png"}:
            from satellite.service import process_drone_image

            summary = process_drone_image(target, username=username)
        elif extension in {".db", ".sqlite"}:
            summary = (f"SQLite fayl saqlandi: {target.name}. Uni tiklash uchun "
                       f"Administrator sahifasidagi Backup bo'limidan foydalaning.")
        else:
            summary = f"Fayl saqlandi: {target.name} (avtomatik import qo'llanmaydi)."
    except Exception as exc:  # noqa: BLE001
        log.exception("Import xatosi: %s", filename)
        summary = f"Import xatosi ({filename}): {exc}"

    _register(target.name, extension.lstrip("."), username, summary)
    clear_all_caches()
    audit("import", username, f"{filename}: {summary[:200]}")
    return summary


def _register(filename: str, file_type: str, username: str, summary: str) -> None:
    with session_scope() as session:
        session.add(ImportedFile(filename=filename, file_type=file_type,
                                 uploaded_by=username, summary=summary[:900]))


# --------------------------------------------------------------------------
# Tabular data (CSV / Excel) — auto-detected as prices or yields
# --------------------------------------------------------------------------
def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    return pd.read_excel(path)


def _handle_table(path: Path, username: str) -> str:
    df = _read_table(path)
    df.columns = [str(column).strip().lower() for column in df.columns]
    columns = set(df.columns)
    if columns & {"price", "narx", "price_per_kg"}:
        return _import_prices(df)
    if columns & {"yield", "hosildorlik", "yield_t_ha"}:
        return _import_yields(df)
    return (f"Jadval saqlandi ({len(df)} qator), lekin ustunlar bo'yicha "
            f"avtomatik moslik topilmadi. Kutilgan ustunlar: "
            f"narx importi uchun [ekin, narx, sana]; hosildorlik uchun "
            f"[ekin, yil, hosildorlik].")


def _column(df: pd.DataFrame, *names: str) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def _parse_date(value: object) -> date:
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    try:
        return pd.to_datetime(str(value)).date()
    except (ValueError, TypeError):
        return date.today()


def _import_prices(df: pd.DataFrame) -> str:
    crop_column = _column(df, "crop", "ekin", "ekin_nomi")
    price_column = _column(df, "price", "narx", "price_per_kg")
    date_column = _column(df, "date", "sana")
    if not crop_column or not price_column:
        return "Narx importi uchun 'ekin' va 'narx' ustunlari topilmadi."
    imported = skipped = 0
    with session_scope() as session:
        crops = {crop.name.lower(): crop.id for crop in session.query(Crop).all()}
        for _, row in df.iterrows():
            crop_id = crops.get(str(row[crop_column]).strip().lower())
            try:
                price = float(row[price_column])
            except (ValueError, TypeError):
                crop_id = None
            if crop_id is None:
                skipped += 1
                continue
            session.add(MarketPrice(
                crop_id=crop_id, price_per_kg=price,
                date=_parse_date(row[date_column]) if date_column else date.today(),
                market_name="Import", source="import",
            ))
            imported += 1
    return f"Bozor narxlari importi: {imported} qator qo'shildi, {skipped} o'tkazildi."


def _import_yields(df: pd.DataFrame) -> str:
    crop_column = _column(df, "crop", "ekin")
    yield_column = _column(df, "yield", "hosildorlik", "yield_t_ha")
    year_column = _column(df, "year", "yil")
    field_column = _column(df, "field", "dala", "field_id")
    if not crop_column or not yield_column or not year_column:
        return "Hosildorlik importi uchun 'ekin', 'yil', 'hosildorlik' ustunlari kerak."
    imported = skipped = 0
    with session_scope() as session:
        crops = {crop.name.lower(): crop.id for crop in session.query(Crop).all()}
        fields = {field.name.lower(): field for field in session.query(Field).all()}
        default_field = next(iter(fields.values()), None)
        for _, row in df.iterrows():
            crop_id = crops.get(str(row[crop_column]).strip().lower())
            field = fields.get(str(row[field_column]).strip().lower()) \
                if field_column else default_field
            field = field or default_field
            try:
                yield_value = float(row[yield_column])
                year = int(row[year_column])
            except (ValueError, TypeError):
                crop_id = None
            if crop_id is None or field is None:
                skipped += 1
                continue
            session.add(YieldRecord(
                field_id=field.id, crop_id=crop_id, year=year,
                area_ha=field.area_ha, yield_t_ha=yield_value,
                production_t=round(yield_value * field.area_ha, 1),
            ))
            imported += 1
    return f"Hosildorlik importi: {imported} qator qo'shildi, {skipped} o'tkazildi."


# --------------------------------------------------------------------------
# Geo formats
# --------------------------------------------------------------------------
def _import_features(features: list[dict], source: str) -> str:
    """Create Field rows from GeoJSON-like features, attached to an import farm."""
    from gis.geo import polygon_area_ha, polygon_centroid

    created = 0
    with session_scope() as session:
        farm = session.query(Farm).filter(Farm.name == "Import xo'jaligi").first()
        if farm is None:
            any_farm = session.query(Farm).first()
            if any_farm is None:
                return "Import uchun kamida bitta xo'jalik mavjud bo'lishi kerak."
            farm = Farm(name="Import xo'jaligi", farmer_id=any_farm.farmer_id,
                        district_id=any_farm.district_id, area_ha=0.0)
            session.add(farm)
            session.flush()
        for i, feature in enumerate(features, start=1):
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Polygon":
                continue
            geometry_text = json.dumps(geometry)
            centroid = polygon_centroid(geometry_text)
            if centroid is None:
                continue
            properties = feature.get("properties") or {}
            area = properties.get("area_ha") or polygon_area_ha(geometry_text) or 1.0
            name = str(properties.get("name") or f"{source}-kontur-{i}")
            session.add(Field(
                farm_id=farm.id, name=name[:120], area_ha=float(area),
                soil_type=str(properties.get("soil", "bo'z tuproq"))[:32],
                lat=centroid[0], lon=centroid[1], geometry_geojson=geometry_text,
            ))
            farm.area_ha = round(farm.area_ha + float(area), 1)
            created += 1
    return f"{source} importi: {created} ta dala poligoni qo'shildi."


def _handle_geojson(path: Path, _username: str) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        return _import_features(payload.get("features", []), "GeoJSON")
    if payload.get("type") == "Feature":
        return _import_features([payload], "GeoJSON")
    return "JSON fayl saqlandi (GeoJSON strukturasi topilmadi)."


def _handle_shapefile(path: Path, _username: str) -> str:
    shapefile = try_import("shapefile")  # pyshp
    if shapefile is None:
        return ("Shapefile saqlandi. To'liq import uchun 'pyshp' paketini "
                "o'rnating: pip install pyshp")
    reader = shapefile.Reader(str(path))
    features = []
    for shape_record in reader.shapeRecords():
        geo = shape_record.shape.__geo_interface__
        if geo["type"] == "Polygon":
            features.append({"geometry": geo,
                             "properties": dict(shape_record.record.as_dict())})
    return _import_features(features, "Shapefile")


def _handle_kml(path: Path, _username: str) -> str:
    """Minimal KML polygon parser (stdlib XML, no external deps)."""
    import xml.etree.ElementTree as ET

    namespace = {"kml": "http://www.opengis.net/kml/2.2"}
    tree = ET.parse(path)
    features = []
    for placemark in tree.iter(f"{{{namespace['kml']}}}Placemark"):
        name_node = placemark.find("kml:name", namespace)
        for coords_node in placemark.iter(f"{{{namespace['kml']}}}coordinates"):
            points = []
            for token in (coords_node.text or "").split():
                parts = token.split(",")
                if len(parts) >= 2:
                    points.append([float(parts[0]), float(parts[1])])
            if len(points) >= 4:
                features.append({
                    "geometry": {"type": "Polygon", "coordinates": [points]},
                    "properties": {"name": name_node.text if name_node is not None else None},
                })
    return _import_features(features, "KML")


def _handle_zip(path: Path, username: str) -> str:
    """Extract a ZIP and recursively import each supported member."""
    summaries = []
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist()[:20]:
            extension = Path(member).suffix.lower()
            if extension in {".csv", ".xlsx", ".geojson", ".json", ".kml",
                             ".shp", ".tif", ".tiff", ".jpg", ".png"}:
                summaries.append(
                    f"{member}: "
                    + handle_upload(Path(member).name, archive.read(member), username)
                )
    if not summaries:
        return "ZIP ichida import qilinadigan fayl topilmadi."
    return " | ".join(summaries[:5])
