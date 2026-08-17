"""RFQ, quotation, contract and revenue models."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin


class RFQ(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A request for quotation received from a buyer."""

    __tablename__ = "rfqs"

    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id"), nullable=False, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"))
    received_at: Mapped[dt.date] = mapped_column(Date, nullable=False)
    deadline: Mapped[dt.date | None] = mapped_column(Date)
    target_incoterm: Mapped[str | None] = mapped_column(String(20))
    destination: Mapped[str | None] = mapped_column(String(160))
    payment_condition: Mapped[str | None] = mapped_column(String(200))
    certificate_requirements: Mapped[str | None] = mapped_column(String(300))
    packaging_requirements: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False, index=True)
    internal_notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[RFQItem]] = relationship(back_populates="rfq", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RFQ {self.number}>"


class RFQItem(IdMixin, Base):
    """A single requested product line inside an RFQ."""

    __tablename__ = "rfq_items"

    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)
    target_price: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    rfq: Mapped[RFQ] = relationship(back_populates="items")


class Quotation(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A commercial offer issued to a buyer."""

    __tablename__ = "quotations"

    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id"), nullable=False, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    rfq_id: Mapped[int | None] = mapped_column(ForeignKey("rfqs.id"))
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    issue_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[dt.date | None] = mapped_column(Date, index=True)
    payment_terms: Mapped[str | None] = mapped_column(String(200))
    delivery_terms: Mapped[str | None] = mapped_column(String(200))
    incoterm: Mapped[str] = mapped_column(String(20), default="FOB", nullable=False)
    loading_port: Mapped[str | None] = mapped_column(String(160))
    destination: Mapped[str | None] = mapped_column(String(160))
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    packaging: Mapped[str | None] = mapped_column(Text)
    certificate_refs: Mapped[str | None] = mapped_column(String(300))
    intro_text: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)

    freight_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    insurance_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    grand_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    viewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    last_pdf_path: Mapped[str | None] = mapped_column(String(500))

    items: Mapped[list[QuotationItem]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan"
    )
    versions: Mapped[list[QuotationVersion]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Quotation {self.number} [{self.status}]>"


class QuotationItem(IdMixin, Base):
    """A priced line item of a quotation."""

    __tablename__ = "quotation_items"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    price_id: Mapped[int | None] = mapped_column(ForeignKey("product_prices.id"))
    description: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    hs_code: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    moq: Mapped[float | None] = mapped_column(Float)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    packaging: Mapped[str | None] = mapped_column(String(240))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    quotation: Mapped[Quotation] = relationship(back_populates="items")


class QuotationVersion(IdMixin, TimestampMixin, Base):
    """Immutable JSON snapshot of a quotation revision."""

    __tablename__ = "quotation_versions"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    grand_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    comment: Mapped[str | None] = mapped_column(String(300))

    quotation: Mapped[Quotation] = relationship(back_populates="versions")


class Contract(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A signed export contract linked to a won deal."""

    __tablename__ = "contracts"

    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id"), nullable=False)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    sign_date: Mapped[dt.date | None] = mapped_column(Date)
    valid_until: Mapped[dt.date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    incoterm: Mapped[str | None] = mapped_column(String(20))
    payment_terms: Mapped[str | None] = mapped_column(String(200))
    delivery_terms: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Contract {self.number}>"


class RevenueRecord(IdMixin, TimestampMixin, Base):
    """Actual money recognised against a contract/shipment."""

    __tablename__ = "revenue_records"

    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipments.id"))
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyers.id"))
    record_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    expected_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), default="shipment", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
