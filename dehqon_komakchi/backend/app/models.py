import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utc_now_naive() -> datetime:
    """UTC 'now' as a naive datetime, matching how SQLite stores DateTime columns
    (it drops tzinfo on round-trip). Always construct/compare against this helper
    rather than the deprecated datetime.utcnow() so values stay consistent."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    phone_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, default="Foydalanuvchi")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    listings: Mapped[list["Listing"]] = relationship(back_populates="owner")


class OtpRequest(Base):
    """Short-lived OTP challenge. In demo mode the code is always DEMO_CODE (see auth router)."""

    __tablename__ = "otp_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    phone_number: Mapped[str] = mapped_column(String, index=True)
    code: Mapped[str] = mapped_column(String)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class SellGroup(Base):
    __tablename__ = "sell_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    region: Mapped[str] = mapped_column(String)
    admin_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    listings: Mapped[list["Listing"]] = relationship(back_populates="group")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    variety: Mapped[str] = mapped_column(String)
    quantity_kg: Mapped[float] = mapped_column(Float)
    price_som: Mapped[float | None] = mapped_column(Float, nullable=True)
    negotiable: Mapped[bool] = mapped_column(Boolean, default=False)
    region: Mapped[str] = mapped_column(String, index=True)
    availability_date: Mapped[datetime] = mapped_column(DateTime)
    photo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_method: Mapped[str] = mapped_column(String)  # "phone" | "telegram"
    contact_value: Mapped[str] = mapped_column(String)
    contact_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    group_id: Mapped[str | None] = mapped_column(String, ForeignKey("sell_groups.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)  # auto-hidden after N reports

    owner: Mapped["User"] = relationship(back_populates="listings")
    group: Mapped["SellGroup | None"] = relationship(back_populates="listings")
    reports: Mapped[list["ListingReport"]] = relationship(back_populates="listing")


class ListingReport(Base):
    __tablename__ = "listing_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(String, ForeignKey("listings.id"))
    reporter_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String)  # spam | fraud | inappropriate | other
    note: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    listing: Mapped["Listing"] = relationship(back_populates="reports")


class DiagnosisLog(Base):
    """Optional server-side record of a diagnosis request, used only for aggregate quality
    metrics (e.g. useful/not-useful rate) -- never required for the on-device flow to work."""

    __tablename__ = "diagnosis_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    useful_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class AuditLog(Base):
    """Append-only, audit-friendly trail of sensitive actions (auth, moderation)."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String)  # phone number or "system"
    action: Mapped[str] = mapped_column(String)
    detail: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
