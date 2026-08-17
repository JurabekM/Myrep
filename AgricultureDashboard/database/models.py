"""SQLAlchemy ORM models for the AgroVision platform (SQLite backend).

Geometries are stored as GeoJSON text so the schema works on plain SQLite;
when SpatiaLite is available the same column feeds spatial tooling.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(128), nullable=False, default="")
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="viewer")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    username = Column(String(64), nullable=False, default="system")
    action = Column(String(64), nullable=False)
    details = Column(Text, nullable=False, default="")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    fertility = Column(Float, nullable=False, default=1.0)  # relative soil factor

    districts = relationship("District", back_populates="region")


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    region = relationship("Region", back_populates="districts")
    farms = relationship("Farm", back_populates="district")


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    phone = Column(String(32), nullable=False, default="")
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)

    district = relationship("District")
    farms = relationship("Farm", back_populates="farmer")


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False, index=True)
    area_ha = Column(Float, nullable=False, default=0.0)

    farmer = relationship("Farmer", back_populates="farms")
    district = relationship("District", back_populates="farms")
    fields = relationship("Field", back_populates="farm")


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    area_ha = Column(Float, nullable=False)
    soil_type = Column(String(32), nullable=False, default="bo'z tuproq")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    geometry_geojson = Column(Text, nullable=False, default="")  # GeoJSON Polygon

    farm = relationship("Farm", back_populates="fields")
    yields = relationship("YieldRecord", back_populates="field")


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    category = Column(String(32), nullable=False, default="don")
    season = Column(String(32), nullable=False, default="yozgi")
    water_need_mm = Column(Float, nullable=False, default=500.0)
    base_yield_t_ha = Column(Float, nullable=False, default=3.0)
    base_price_per_kg = Column(Float, nullable=False, default=3000.0)
    cost_per_ha = Column(Float, nullable=False, default=6_000_000.0)


class YieldRecord(Base):
    __tablename__ = "yield_records"

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    area_ha = Column(Float, nullable=False)
    yield_t_ha = Column(Float, nullable=False)
    production_t = Column(Float, nullable=False)

    field = relationship("Field", back_populates="yields")
    crop = relationship("Crop")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    t_min = Column(Float, nullable=False)
    t_max = Column(Float, nullable=False)
    precipitation_mm = Column(Float, nullable=False, default=0.0)
    humidity = Column(Float, nullable=False, default=50.0)
    source = Column(String(32), nullable=False, default="demo")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    price_per_kg = Column(Float, nullable=False)
    market_name = Column(String(64), nullable=False, default="Milliy bozor")
    source = Column(String(32), nullable=False, default="demo")

    crop = relationship("Crop")


class IrrigationRecord(Base):
    __tablename__ = "irrigation_records"

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    water_m3 = Column(Float, nullable=False)
    method = Column(String(32), nullable=False, default="egat")


class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    category = Column(String(32), nullable=False)  # income|expense|credit|subsidy
    amount = Column(Float, nullable=False)
    note = Column(String(256), nullable=False, default="")


class SatelliteIndex(Base):
    __tablename__ = "satellite_indices"

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    ndvi = Column(Float, nullable=False)
    evi = Column(Float, nullable=False)
    source = Column(String(32), nullable=False, default="demo")


class ImportedFile(Base):
    __tablename__ = "imported_files"

    id = Column(Integer, primary_key=True)
    filename = Column(String(256), nullable=False)
    file_type = Column(String(32), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by = Column(String(64), nullable=False, default="")
    summary = Column(Text, nullable=False, default="")


def today() -> date:
    """Convenience wrapper so services avoid importing datetime everywhere."""
    return date.today()
