"""Conversation, message, attachment and channel connection models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin
from app.models.crm import Lead
from app.models.enums import (
    Channel,
    ConversationStatus,
    IntegrationStatus,
    MessageDirection,
    MessageSender,
    MessageStatus,
)
from app.models.organization import User


class ChannelConnection(Base, IdMixin, TimestampMixin):
    """A configured (or demo) channel endpoint the application listens to."""

    __tablename__ = "channel_connections"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(120), default="")
    account_label: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(24), default=IntegrationStatus.NOT_CONFIGURED)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    demo_fallback: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")


class Conversation(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """A dialogue with one lead on one channel."""

    __tablename__ = "conversations"

    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(24), default=Channel.DEMO, index=True)
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("channel_connections.id"), nullable=True
    )
    external_chat_id: Mapped[str] = mapped_column(String(120), default="")
    subject: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(32), default=ConversationStatus.OPEN, index=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_state: Mapped[str] = mapped_column(String(32), default="new_lead")
    ai_message_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_unanswered_count: Mapped[int] = mapped_column(Integer, default=0)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_message_preview: Mapped[str] = mapped_column(String(255), default="")
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalation_reason: Mapped[str] = mapped_column(String(120), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    lead: Mapped[Lead] = relationship(lazy="joined")
    assigned_to: Mapped[User | None] = relationship(lazy="joined")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base, IdMixin):
    """One message inside a conversation (customer, AI, operator or internal note)."""

    __tablename__ = "messages"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), default=MessageDirection.INBOUND)
    sender: Mapped[str] = mapped_column(String(16), default=MessageSender.CUSTOMER)
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(24), default=Channel.DEMO)
    body: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(8), default="unknown")
    status: Mapped[str] = mapped_column(String(16), default=MessageStatus.SENT)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=True)
    external_id: Mapped[str] = mapped_column(String(120), default="")
    error_text: Mapped[str] = mapped_column(Text, default="")
    ai_interaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_interactions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sender_user: Mapped[User | None] = relationship(lazy="joined")
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="message", cascade="all, delete-orphan", lazy="selectin"
    )


class Attachment(Base, IdMixin, TimestampMixin):
    """File attached to a message, a call recording or a knowledge base item."""

    __tablename__ = "attachments"

    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )
    kb_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("kb_items.id", ondelete="CASCADE"), nullable=True
    )
    call_id: Mapped[int | None] = mapped_column(ForeignKey("calls.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(24), default="file")

    message: Mapped[Message | None] = relationship(back_populates="attachments")


class ConversationAssignment(Base, IdMixin):
    """History of operator assignments for a conversation."""

    __tablename__ = "conversation_assignments"

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    from_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(160), default="")
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class QuickReply(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """Reusable canned answer available in the inbox composer."""

    __tablename__ = "quick_replies"

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body_uz: Mapped[str] = mapped_column(Text, default="")
    body_ru: Mapped[str] = mapped_column(Text, default="")
    shortcut: Mapped[str] = mapped_column(String(32), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
