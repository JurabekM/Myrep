"""Certificates, documents, checklists, tasks, activities and email models."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin


class Certificate(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """An export certificate with an expiry date and verification state."""

    __tablename__ = "certificates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cert_type: Mapped[str] = mapped_column(String(40), default="other", nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    issuer: Mapped[str | None] = mapped_column(String(200))
    number: Mapped[str | None] = mapped_column(String(80))
    issue_date: Mapped[dt.date | None] = mapped_column(Date)
    expiry_date: Mapped[dt.date | None] = mapped_column(Date, index=True)
    target_market: Mapped[str | None] = mapped_column(String(160))
    file_path: Mapped[str | None] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(
        String(20), default="unverified", nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="valid", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Certificate {self.name}>"


class Document(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A generic export document attached to a buyer, deal or shipment."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(40), default="other", nullable=False, index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyers.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipments.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    file_path: Mapped[str | None] = mapped_column(String(500))
    doc_date: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Attachment(IdMixin, TimestampMixin, Base):
    """A file attached to any entity, addressed by (entity_type, entity_id)."""

    __tablename__ = "attachments"

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(240), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))


class ChecklistTemplate(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A reusable export readiness checklist blueprint."""

    __tablename__ = "checklist_templates"

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="lead", nullable=False)
    trigger_status: Mapped[str | None] = mapped_column(String(40), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[ChecklistTemplateItem]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ChecklistTemplateItem.sort_order",
    )


class ChecklistTemplateItem(IdMixin, Base):
    """A single task defined by a checklist template."""

    __tablename__ = "checklist_template_items"

    template_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_templates.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(40), default="product_readiness", nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)
    due_offset_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    template: Mapped[ChecklistTemplate] = relationship(back_populates="items")


class Checklist(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A checklist instance applied to a product, buyer, lead or shipment."""

    __tablename__ = "checklists"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="lead", nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("checklist_templates.id"))
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[ChecklistItem]] = relationship(
        back_populates="checklist", cascade="all, delete-orphan", order_by="ChecklistItem.id"
    )

    @property
    def completion_percent(self) -> float:
        """Share of completed items, 0-100."""
        if not self.items:
            return 0.0
        done = sum(1 for item in self.items if item.is_done)
        return round(done * 100.0 / len(self.items), 1)


class ChecklistItem(IdMixin, TimestampMixin, Base):
    """A single actionable line of a checklist."""

    __tablename__ = "checklist_items"

    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(40), default="product_readiness", nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    done_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[dt.date | None] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    checklist: Mapped[Checklist] = relationship(back_populates="items")


class Task(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A follow-up task, either manual or generated by a business rule."""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(40), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyers.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    due_date: Mapped[dt.date | None] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    rule_code: Mapped[str | None] = mapped_column(String(60), index=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class Activity(IdMixin, TimestampMixin, Base):
    """A timeline entry describing something that happened to an entity."""

    __tablename__ = "activities"

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), default="note", nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    happened_at: Mapped[dt.datetime | None] = mapped_column(DateTime, index=True)


class EmailTemplate(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A reusable email body with ``{placeholder}`` substitution."""

    __tablename__ = "email_templates"

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    subject: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), default="general", nullable=False)


class EmailMessage(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """An outgoing (or logged incoming) email tied to CRM records."""

    __tablename__ = "email_messages"

    subject: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    to_address: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    cc_address: Mapped[str | None] = mapped_column(String(300))
    from_address: Mapped[str | None] = mapped_column(String(300))
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyers.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    template_id: Mapped[int | None] = mapped_column(ForeignKey("email_templates.id"))
    attachment_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(40))
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime, index=True)
    reply_received_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class AIGeneration(IdMixin, TimestampMixin, Base):
    """History entry for every piece of AI generated content."""

    __tablename__ = "ai_generations"

    content_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    tone: Mapped[str] = mapped_column(String(20), default="professional", nullable=False)
    provider: Mapped[str] = mapped_column(String(40), default="demo", nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("buyers.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"))
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    instruction: Mapped[str | None] = mapped_column(Text)
    fact_sources: Mapped[str | None] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
