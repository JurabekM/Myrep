"""Conversation and message queries used by the Unified Inbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.crm import Lead
from app.models.enums import ConversationStatus, IntentLevel
from app.models.messaging import Conversation, Message
from app.repositories.base import BaseRepository


@dataclass
class ConversationFilter:
    """Filter for the inbox conversation list."""

    search: str = ""
    channels: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    assigned_to_id: int | None = None
    only_mine: bool = False
    only_waiting_ai: bool = False
    only_hot: bool = False
    only_unanswered: bool = False
    only_closed: bool = False
    include_archived: bool = False
    date_from: datetime | None = None
    date_to: datetime | None = None


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for :class:`~app.models.messaging.Conversation`."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Conversation)

    def _apply(self, stmt: Select, flt: ConversationFilter) -> Select:
        """Apply a :class:`ConversationFilter` to a select statement."""
        stmt = stmt.join(Lead, Lead.id == Conversation.lead_id)
        if not flt.include_archived:
            stmt = stmt.where(Conversation.is_archived.is_(False))
        if flt.search:
            pattern = f"%{flt.search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Lead.full_name).like(pattern),
                    func.lower(Lead.telegram_username).like(pattern),
                    Lead.phone.like(f"%{flt.search.strip()}%"),
                    func.lower(Conversation.last_message_preview).like(pattern),
                )
            )
        if flt.channels:
            stmt = stmt.where(Conversation.channel.in_(flt.channels))
        if flt.statuses:
            stmt = stmt.where(Conversation.status.in_(flt.statuses))
        if flt.only_mine and flt.assigned_to_id:
            stmt = stmt.where(Conversation.assigned_to_id == flt.assigned_to_id)
        if flt.only_waiting_ai:
            stmt = stmt.where(Conversation.status == ConversationStatus.WAITING_OPERATOR)
        if flt.only_hot:
            stmt = stmt.where(or_(Lead.score >= 70, Lead.intent == IntentLevel.HOT))
        if flt.only_unanswered:
            stmt = stmt.where(Conversation.unread_count > 0)
        if flt.only_closed:
            stmt = stmt.where(Conversation.status == ConversationStatus.CLOSED)
        elif not flt.statuses:
            stmt = stmt.where(Conversation.status != ConversationStatus.CLOSED)
        if flt.date_from:
            stmt = stmt.where(Conversation.last_message_at >= flt.date_from)
        if flt.date_to:
            stmt = stmt.where(Conversation.last_message_at <= flt.date_to)
        return stmt

    def search(
        self, flt: ConversationFilter, limit: int = 200, offset: int = 0
    ) -> list[Conversation]:
        """Return conversations for the inbox list, newest activity first."""
        stmt = self._apply(select(Conversation), flt)
        stmt = stmt.order_by(
            Conversation.unread_count.desc(),
            Conversation.last_message_at.desc().nullslast(),
            Conversation.id.desc(),
        )
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().unique().all())

    def count_filtered(self, flt: ConversationFilter) -> int:
        """Number of conversations matching ``flt``."""
        stmt = self._apply(select(func.count(Conversation.id)), flt)
        return int(self.session.execute(stmt).scalar_one())

    def for_lead(self, lead_id: int) -> list[Conversation]:
        """All conversations belonging to a lead."""
        stmt = (
            select(Conversation)
            .where(Conversation.lead_id == lead_id)
            .order_by(Conversation.last_message_at.desc().nullslast())
        )
        return list(self.session.execute(stmt).scalars().unique().all())

    def with_messages(self, conversation_id: int) -> Conversation | None:
        """Load a conversation together with its messages and attachments."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages).selectinload(Message.attachments))
        )
        return self.session.execute(stmt).scalars().unique().one_or_none()

    def messages(
        self,
        conversation_id: int,
        *,
        search: str = "",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        include_internal: bool = True,
        limit: int | None = None,
    ) -> list[Message]:
        """Return messages of a conversation with optional filtering."""
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        if search:
            stmt = stmt.where(func.lower(Message.body).like(f"%{search.strip().lower()}%"))
        if date_from:
            stmt = stmt.where(Message.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Message.created_at <= date_to)
        if not include_internal:
            stmt = stmt.where(Message.is_internal.is_(False))
        stmt = stmt.order_by(Message.created_at.asc(), Message.id.asc())
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().unique().all())

    def total_unread(self, user_id: int | None = None) -> int:
        """Sum of unread counters, optionally limited to one operator."""
        stmt = select(func.coalesce(func.sum(Conversation.unread_count), 0)).where(
            Conversation.is_archived.is_(False)
        )
        if user_id is not None:
            stmt = stmt.where(Conversation.assigned_to_id == user_id)
        return int(self.session.execute(stmt).scalar_one())
