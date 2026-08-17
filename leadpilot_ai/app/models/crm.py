"""Lead CRM models: leads, tags, activity timeline, marketing attribution."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin
from app.models.enums import Channel, IntentLevel, LeadStatus
from app.models.organization import Branch, Service, User

lead_tags = Table(
    "lead_tags",
    Base.metadata,
    Column("lead_id", ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base, IdMixin, TimestampMixin):
    """Colored label attachable to leads."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#3B82F6")
    description: Mapped[str] = mapped_column(String(255), default="")

    leads: Mapped[list[Lead]] = relationship(secondary=lead_tags, back_populates="tags")


class MarketingSource(Base, IdMixin, TimestampMixin):
    """Advertising source (Instagram Ads, Google Ads, Telegram channel, ...)."""

    __tablename__ = "marketing_sources"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(48), default="other")
    utm_source: Mapped[str] = mapped_column(String(80), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    campaigns: Mapped[list[MarketingCampaign]] = relationship(back_populates="source")


class MarketingCampaign(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """A concrete advertising campaign with a budget used for ROI math."""

    __tablename__ = "marketing_campaigns"

    source_id: Mapped[int] = mapped_column(ForeignKey("marketing_sources.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    utm_campaign: Mapped[str] = mapped_column(String(120), default="")
    utm_medium: Mapped[str] = mapped_column(String(80), default="")
    utm_content: Mapped[str] = mapped_column(String(120), default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    source: Mapped[MarketingSource] = relationship(back_populates="campaigns", lazy="joined")


class Lead(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Central CRM entity: a potential customer."""

    __tablename__ = "leads"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    phone_raw: Mapped[str] = mapped_column(String(48), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    telegram_username: Mapped[str] = mapped_column(String(96), default="")
    external_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    language: Mapped[str] = mapped_column(String(8), default="unknown")

    channel: Mapped[str] = mapped_column(String(24), default=Channel.MANUAL, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("marketing_sources.id"), nullable=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("marketing_campaigns.id"), nullable=True
    )
    utm_source: Mapped[str] = mapped_column(String(80), default="")
    utm_medium: Mapped[str] = mapped_column(String(80), default="")
    utm_campaign: Mapped[str] = mapped_column(String(120), default="")
    utm_content: Mapped[str] = mapped_column(String(120), default="")

    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    interest: Mapped[str] = mapped_column(String(200), default="")
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    intent: Mapped[str] = mapped_column(String(16), default=IntentLevel.COLD)
    status: Mapped[str] = mapped_column(String(32), default=LeadStatus.NEW, index=True)
    ai_state: Mapped[str] = mapped_column(String(32), default="new_lead")

    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    opt_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_contact_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_response_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    won_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    loss_reason: Mapped[str] = mapped_column(String(48), default="")
    loss_comment: Mapped[str] = mapped_column(Text, default="")

    notes: Mapped[str] = mapped_column(Text, default="")
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)

    owner: Mapped[User | None] = relationship("User", lazy="joined", foreign_keys=[owner_id])
    service: Mapped[Service | None] = relationship("Service", lazy="joined")
    branch: Mapped[Branch | None] = relationship("Branch", lazy="joined")
    source: Mapped[MarketingSource | None] = relationship(lazy="joined")
    campaign: Mapped[MarketingCampaign | None] = relationship(lazy="joined")
    tags: Mapped[list[Tag]] = relationship(
        secondary=lead_tags, back_populates="leads", lazy="selectin"
    )
    activities: Mapped[list[LeadActivity]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadActivity.created_at"
    )

    @property
    def display_name(self) -> str:
        """Best available human label for the lead."""
        if self.full_name:
            return self.full_name
        if self.telegram_username:
            return f"@{self.telegram_username}"
        if self.phone:
            return self.phone
        return f"Lead #{self.id}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lead {self.id} {self.display_name} {self.status}>"


class LeadActivity(Base, IdMixin):
    """One entry of the lead timeline."""

    __tablename__ = "lead_activities"

    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    old_value: Mapped[str] = mapped_column(String(200), default="")
    new_value: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    lead: Mapped[Lead] = relationship(back_populates="activities")


class RevenueRecord(Base, IdMixin, TimestampMixin):
    """Money actually earned from a lead, used by ROI/ROAS reports."""

    __tablename__ = "revenue_records"

    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("marketing_campaigns.id"), nullable=True
    )
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
