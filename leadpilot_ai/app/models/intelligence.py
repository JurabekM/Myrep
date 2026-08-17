"""AI agent profile, AI interaction audit and knowledge base models."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin
from app.models.enums import AIInteractionStatus, AIState, KBItemType, ToneOfVoice


class AIProfile(Base, IdMixin, TimestampMixin):
    """Configuration of the virtual sales operator."""

    __tablename__ = "ai_profiles"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(96), default="Aziza")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    autonomous: Mapped[bool] = mapped_column(Boolean, default=False)
    tone: Mapped[str] = mapped_column(String(24), default=ToneOfVoice.FRIENDLY)
    languages: Mapped[str] = mapped_column(String(32), default="uz,ru")
    work_start: Mapped[str] = mapped_column(String(5), default="09:00")
    work_end: Mapped[str] = mapped_column(String(5), default="19:00")
    after_hours_mode: Mapped[str] = mapped_column(String(24), default="reply_and_queue")
    max_auto_messages: Mapped[int] = mapped_column(Integer, default=6)
    escalate_on_negative: Mapped[bool] = mapped_column(Boolean, default=True)
    escalate_on_price_negotiation: Mapped[bool] = mapped_column(Boolean, default=True)
    escalate_on_human_request: Mapped[bool] = mapped_column(Boolean, default=True)
    escalate_after_unanswered: Mapped[int] = mapped_column(Integer, default=2)
    escalate_score_threshold: Mapped[int] = mapped_column(Integer, default=70)
    booking_required_fields: Mapped[str] = mapped_column(
        String(255), default="full_name,phone,service,datetime"
    )
    forbidden_topics: Mapped[str] = mapped_column(
        Text, default="tibbiy tashxis,huquqiy maslahat,moliyaviy maslahat"
    )
    greeting_uz: Mapped[str] = mapped_column(Text, default="")
    greeting_ru: Mapped[str] = mapped_column(Text, default="")
    signature: Mapped[str] = mapped_column(String(160), default="")
    night_send_allowed: Mapped[bool] = mapped_column(Boolean, default=False)

    def language_list(self) -> list[str]:
        """Return configured languages as a list."""
        return [x.strip() for x in self.languages.split(",") if x.strip()]

    def required_booking_fields(self) -> list[str]:
        """Return the fields required before the AI may create a booking."""
        return [x.strip() for x in self.booking_required_fields.split(",") if x.strip()]


class ScoringRule(Base, IdMixin, TimestampMixin):
    """Configurable lead-scoring rule (keyword or signal based)."""

    __tablename__ = "scoring_rules"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title_uz: Mapped[str] = mapped_column(String(160), default="")
    title_ru: Mapped[str] = mapped_column(String(160), default="")
    points: Mapped[int] = mapped_column(Integer, default=0)
    keywords_uz: Mapped[str] = mapped_column(Text, default="")
    keywords_ru: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def keywords(self) -> list[str]:
        """Return all keywords (both languages) lowercased."""
        raw = f"{self.keywords_uz},{self.keywords_ru}"
        return [k.strip().lower() for k in raw.split(",") if k.strip()]


class AIInteraction(Base, IdMixin):
    """Audit record of every reply the AI produced (quality review module)."""

    __tablename__ = "ai_interactions"

    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(48), default="demo")
    model: Mapped[str] = mapped_column(String(80), default="rule-based")
    state_before: Mapped[str] = mapped_column(String(32), default=AIState.NEW_LEAD)
    state_after: Mapped[str] = mapped_column(String(32), default=AIState.GREETING)
    customer_message: Mapped[str] = mapped_column(Text, default="")
    suggested_reply: Mapped[str] = mapped_column(Text, default="")
    final_reply: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(8), default="uz")
    status: Mapped[str] = mapped_column(
        String(24), default=AIInteractionStatus.SUGGESTED, index=True
    )
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[str] = mapped_column(String(120), default="")
    score_delta: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    kb_refs: Mapped[str] = mapped_column(String(255), default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_useful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    review_category: Mapped[str] = mapped_column(String(32), default="")
    review_comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class KnowledgeBaseItem(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Approved company knowledge the AI is allowed to quote."""

    __tablename__ = "kb_items"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), default=KBItemType.FAQ, index=True)
    category: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    body_ru: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(String(255), default="")
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    ai_usable: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    attachments: Mapped[list[KnowledgeBaseAttachment]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )

    def keyword_list(self) -> list[str]:
        """Return the search keywords lowercased."""
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]

    def is_valid_on(self, day: date) -> bool:
        """Whether the item is inside its validity window."""
        if self.valid_from and day < self.valid_from:
            return False
        if self.valid_to and day > self.valid_to:
            return False
        return True


class KnowledgeBaseAttachment(Base, IdMixin, TimestampMixin):
    """File (PDF/DOCX/TXT) linked to a knowledge base article."""

    __tablename__ = "kb_attachments"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("kb_items.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    extracted_text: Mapped[str] = mapped_column(Text, default="")

    item: Mapped[KnowledgeBaseItem] = relationship(back_populates="attachments")
