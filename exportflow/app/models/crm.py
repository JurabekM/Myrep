"""Buyer and export lead CRM models."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin


class MarketingSource(IdMixin, TimestampMixin, Base):
    """Configurable marketing/lead channel (Alibaba, LinkedIn, trade fair, ...)."""

    __tablename__ = "marketing_sources"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    cost_per_month: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LeadSource(IdMixin, Base):
    """Free-form origin detail for an individual lead (campaign, fair name)."""

    __tablename__ = "lead_sources"

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    detail: Mapped[str | None] = mapped_column(String(200))
    external_ref: Mapped[str | None] = mapped_column(String(200))


class SalesAgent(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """External sales agent working a specific market."""

    __tablename__ = "sales_agents"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    market: Mapped[str | None] = mapped_column(String(160))
    country: Mapped[str | None] = mapped_column(String(80), index=True)
    phone: Mapped[str | None] = mapped_column(String(60))
    email: Mapped[str | None] = mapped_column(String(160))
    commission_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    commission_terms: Mapped[str | None] = mapped_column(Text)
    commission_status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    buyers: Mapped[list[Buyer]] = relationship(back_populates="agent")


class Buyer(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A foreign buying company."""

    __tablename__ = "buyers"

    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(160))
    position: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="", index=True)
    city: Mapped[str | None] = mapped_column(String(80))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(60), index=True)
    email: Mapped[str | None] = mapped_column(String(160), index=True)
    website: Mapped[str | None] = mapped_column(String(200))
    linkedin: Mapped[str | None] = mapped_column(String(200))
    buyer_type: Mapped[str] = mapped_column(String(30), default="importer", nullable=False)
    interested_categories: Mapped[str | None] = mapped_column(String(300))
    annual_potential: Mapped[float | None] = mapped_column(Float)
    target_market: Mapped[str | None] = mapped_column(String(160))
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="manual", nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    tags: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)

    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("sales_agents.id"))

    agent: Mapped[SalesAgent | None] = relationship(back_populates="buyers")
    contacts: Mapped[list[BuyerContact]] = relationship(
        back_populates="buyer", cascade="all, delete-orphan"
    )
    leads: Mapped[list[Lead]] = relationship(back_populates="buyer")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Buyer {self.company_name} ({self.country})>"


class BuyerContact(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """An individual contact person inside a buyer company."""

    __tablename__ = "buyer_contacts"

    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(60))
    messenger: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    buyer: Mapped[Buyer] = relationship(back_populates="contacts")


class Lead(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """An export opportunity moving through the sales pipeline."""

    __tablename__ = "leads"

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyers.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))
    country: Mapped[str | None] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(40), default="manual", nullable=False, index=True)
    source_detail: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(40), default="new", nullable=False, index=True)
    temperature: Mapped[str] = mapped_column(String(10), default="warm", nullable=False)
    expected_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    probability: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    next_step: Mapped[str | None] = mapped_column(String(240))
    next_follow_up: Mapped[dt.date | None] = mapped_column(Date, index=True)
    incoterm: Mapped[str | None] = mapped_column(String(20))
    destination: Mapped[str | None] = mapped_column(String(160))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("sales_agents.id"))
    lost_reason: Mapped[str | None] = mapped_column(String(60))
    lost_comment: Mapped[str | None] = mapped_column(Text)
    won_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(String(300))

    buyer: Mapped[Buyer | None] = relationship(back_populates="leads", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lead {self.title} [{self.status}]>"
