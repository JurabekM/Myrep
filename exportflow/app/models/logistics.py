"""Shipment and freight models."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin


class Shipment(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A physical export shipment."""

    __tablename__ = "shipments"

    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id"), nullable=False, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))

    incoterm: Mapped[str] = mapped_column(String(20), default="FOB", nullable=False)
    origin: Mapped[str | None] = mapped_column(String(160))
    loading_port: Mapped[str | None] = mapped_column(String(160))
    destination: Mapped[str | None] = mapped_column(String(160))
    container_type: Mapped[str | None] = mapped_column(String(20))
    package_count: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    net_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gross_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    forwarder: Mapped[str | None] = mapped_column(String(200))
    carrier: Mapped[str | None] = mapped_column(String(200))
    tracking_reference: Mapped[str | None] = mapped_column(String(120))

    etd: Mapped[dt.date | None] = mapped_column(Date, index=True)
    eta: Mapped[dt.date | None] = mapped_column(Date, index=True)
    actual_departure: Mapped[dt.date | None] = mapped_column(Date)
    actual_arrival: Mapped[dt.date | None] = mapped_column(Date)

    customs_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="planning", nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    planned_freight_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    freight_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    planned_insurance_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    insurance_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    other_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[ShipmentItem]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )
    freight_quotes: Mapped[list[FreightQuote]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )

    @property
    def total_cost(self) -> float:
        """Actual logistics cost of the shipment."""
        return round(self.freight_cost + self.insurance_cost + self.other_cost, 2)

    @property
    def planned_cost(self) -> float:
        """Budgeted logistics cost of the shipment."""
        return round(self.planned_freight_cost + self.planned_insurance_cost, 2)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Shipment {self.number} [{self.status}]>"


class ShipmentItem(IdMixin, Base):
    """A product line inside a shipment (feeds the packing list)."""

    __tablename__ = "shipment_items"

    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    hs_code: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    packages: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    net_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gross_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="items")

    @property
    def amount(self) -> float:
        """Invoice amount for this line."""
        return round(self.quantity * self.unit_price, 2)


class FreightQuote(IdMixin, TimestampMixin, Base):
    """A forwarder offer that can be compared against alternatives."""

    __tablename__ = "freight_quotes"

    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    forwarder: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="sea", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transit_days: Mapped[int | None] = mapped_column(Integer)
    valid_until: Mapped[dt.date | None] = mapped_column(Date)
    is_selected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    shipment: Mapped[Shipment] = relationship(back_populates="freight_quotes")
