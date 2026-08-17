"""Unified Inbox logic: ingesting inbound traffic and sending replies."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_config
from app.database.engine import session_scope
from app.integrations.base import IncomingMessage
from app.integrations.llm import nlu
from app.models.crm import Lead, MarketingCampaign, MarketingSource
from app.models.enums import (
    ConversationStatus,
    LeadStatus,
    MessageDirection,
    MessageSender,
    MessageStatus,
    NotificationLevel,
)
from app.models.enums import (
    Permission as Perm,
)
from app.models.messaging import (
    Attachment,
    Conversation,
    ConversationAssignment,
    Message,
    QuickReply,
)
from app.repositories.conversation_repository import ConversationFilter, ConversationRepository
from app.repositories.lead_repository import LeadRepository
from app.services import audit_service, lead_service, notification_service
from app.services.auth_service import CurrentUser
from app.utils.dates import minutes_between, now
from app.utils.formatting import truncate

logger = logging.getLogger(__name__)


class ConversationError(Exception):
    """Business rule violation in the inbox (``code`` is an i18n key)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #
def list_conversations(
    flt: ConversationFilter, *, actor: CurrentUser | None = None, limit: int = 300
) -> list[Conversation]:
    """Conversation list for the inbox, scoped to what the actor may see."""
    scoped = ConversationFilter(**flt.__dict__)
    if actor is not None:
        scoped.assigned_to_id = actor.id
        if not actor.can(Perm.LEAD_VIEW_ALL):
            scoped.only_mine = True
    with session_scope() as session:
        return ConversationRepository(session).search(scoped, limit=limit)


def get_conversation(conversation_id: int) -> Conversation | None:
    """Load one conversation."""
    with session_scope() as session:
        return session.get(Conversation, conversation_id)


def messages_of(
    conversation_id: int,
    *,
    search: str = "",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Message]:
    """Messages of a conversation with optional search / date filtering."""
    with session_scope() as session:
        return ConversationRepository(session).messages(
            conversation_id, search=search, date_from=date_from, date_to=date_to
        )


def conversations_for_lead(lead_id: int) -> list[Conversation]:
    """All conversations of one lead (used by the merge dialog)."""
    with session_scope() as session:
        return ConversationRepository(session).for_lead(lead_id)


def mark_read(conversation_id: int, *, actor: CurrentUser | None = None) -> None:
    """Reset the unread counter of a conversation."""
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            return
        conversation.unread_count = 0
        for message in session.execute(
            select(Message).where(
                Message.conversation_id == conversation_id, Message.is_read.is_(False)
            )
        ).scalars():
            message.is_read = True


def total_unread(actor: CurrentUser | None = None) -> int:
    """Unread message counter for the sidebar badge."""
    with session_scope() as session:
        repo = ConversationRepository(session)
        if actor is None or actor.can(Perm.LEAD_VIEW_ALL):
            return repo.total_unread()
        return repo.total_unread(actor.id)


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
def _resolve_marketing(session: Session, utm: dict[str, str]) -> tuple[int | None, int | None]:
    """Map UTM parameters onto a marketing source / campaign."""
    source_id: int | None = None
    campaign_id: int | None = None
    utm_source = (utm.get("utm_source") or "").strip().lower()
    if utm_source:
        source = session.execute(
            select(MarketingSource).where(MarketingSource.utm_source == utm_source)
        ).scalar_one_or_none()
        if source is not None:
            source_id = source.id
    utm_campaign = (utm.get("utm_campaign") or "").strip().lower()
    if utm_campaign:
        campaign = session.execute(
            select(MarketingCampaign).where(MarketingCampaign.utm_campaign == utm_campaign)
        ).scalar_one_or_none()
        if campaign is not None:
            campaign_id = campaign.id
            source_id = source_id or campaign.source_id
    return source_id, campaign_id


def _find_or_create_lead(session: Session, incoming: IncomingMessage) -> tuple[Lead, bool]:
    """Match the sender to an existing lead or create a new one."""
    repo = LeadRepository(session)
    existing = repo.find_duplicates(
        phone=incoming.phone,
        telegram_username=incoming.sender_username or None,
        external_id=incoming.external_chat_id or None,
    )
    if existing:
        return existing[0], False
    source_id, campaign_id = _resolve_marketing(session, incoming.utm)
    language = nlu.detect_language(incoming.text)
    lead = lead_service.create_lead(
        session=session,
        full_name=incoming.sender_name,
        phone=incoming.phone or "",
        telegram_username=incoming.sender_username,
        channel=incoming.channel,
        language=language,
        external_id=incoming.external_chat_id,
        source_id=source_id,
        campaign_id=campaign_id,
        utm=incoming.utm,
        status=LeadStatus.NEW,
    )
    return lead, True


def _find_or_create_conversation(
    session: Session, lead: Lead, incoming: IncomingMessage
) -> Conversation:
    """Return the open conversation for this chat, creating one if needed."""
    conversation = (
        session.execute(
            select(Conversation).where(
                Conversation.lead_id == lead.id,
                Conversation.channel == incoming.channel,
                Conversation.external_chat_id == incoming.external_chat_id,
            )
        )
        .scalars()
        .first()
    )
    if conversation is not None:
        return conversation
    conversation = Conversation(
        lead_id=lead.id,
        channel=incoming.channel,
        external_chat_id=incoming.external_chat_id,
        status=ConversationStatus.OPEN,
        assigned_to_id=lead.owner_id,
        ai_enabled=True,
    )
    session.add(conversation)
    session.flush()
    return conversation


def ingest_incoming(incoming: IncomingMessage, *, session: Session | None = None) -> dict[str, int]:
    """Persist an inbound message and update lead score / status.

    Returns ``{"lead_id", "conversation_id", "message_id", "is_new_lead"}``.
    """

    def _ingest(db: Session) -> dict[str, int]:
        lead, is_new = _find_or_create_lead(db, incoming)
        conversation = _find_or_create_conversation(db, lead, incoming)

        silent_minutes = (
            minutes_between(lead.last_inbound_at, incoming.received_at)
            if lead.last_inbound_at
            else 0
        )
        understanding = nlu.understand(incoming.text, lead.language)
        if understanding.language != "unknown":
            lead.language = understanding.language
        if understanding.phone and not lead.phone:
            lead.phone = understanding.phone
        if understanding.name and not lead.full_name:
            lead.full_name = understanding.name

        message = Message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            direction=MessageDirection.INBOUND,
            sender=MessageSender.CUSTOMER,
            channel=incoming.channel,
            body=incoming.text,
            language=understanding.language,
            status=MessageStatus.DELIVERED,
            is_read=False,
            external_id=incoming.external_message_id,
            created_at=incoming.received_at,
        )
        db.add(message)
        db.flush()

        conversation.last_message_at = incoming.received_at
        conversation.last_message_preview = truncate(incoming.text, 120)
        conversation.unread_count = (conversation.unread_count or 0) + 1
        lead.last_inbound_at = incoming.received_at
        lead.last_activity_at = incoming.received_at

        delta, reasons = lead_service.score_message(
            db,
            incoming.text,
            phone_provided=bool(understanding.phone),
            silent_minutes=silent_minutes,
        )
        if delta:
            lead_service.apply_score(db, lead, delta, reasons=reasons)

        if understanding.has("opt_out"):
            lead_service.set_do_not_contact(lead.id, True, session=db)
            conversation.ai_enabled = False

        if lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.AI_CONVERSATION
        lead_service.add_activity(
            db,
            lead,
            kind="message_in",
            title="Mijozdan xabar",
            detail=truncate(incoming.text, 200),
        )
        if is_new:
            notification_service.push(
                db,
                title="Yangi lead",
                body=f"{lead.display_name} — {incoming.channel}",
                level=NotificationLevel.INFO,
                category="lead",
                lead_id=lead.id,
                conversation_id=conversation.id,
            )
        if lead.intent == "hot":
            notification_service.push(
                db,
                title="Issiq lead",
                body=f"{lead.display_name} — skor {lead.score}",
                level=NotificationLevel.WARNING,
                category="hot_lead",
                lead_id=lead.id,
                conversation_id=conversation.id,
                user_id=lead.owner_id,
            )
        db.flush()
        return {
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "message_id": message.id,
            "is_new_lead": int(is_new),
        }

    if session is not None:
        return _ingest(session)
    with session_scope() as db:
        return _ingest(db)


# --------------------------------------------------------------------------- #
# Sending
# --------------------------------------------------------------------------- #
def send_message(
    conversation_id: int,
    text: str,
    *,
    actor: CurrentUser,
    sender: str = MessageSender.OPERATOR,
    attachments: list[str] | None = None,
    ai_interaction_id: int | None = None,
    session: Session | None = None,
) -> Message:
    """Send an outbound message through the channel adapter.

    Enforces opt-out, quiet hours and the operator/AI hand-off rule.
    """
    from app.services import integration_service  # local import breaks the cycle

    def _send(db: Session) -> Message:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationError("conversation_not_found")
        lead = db.get(Lead, conversation.lead_id)
        if lead is None:
            raise ConversationError("lead_not_found")
        allowed, reason = lead_service.may_send_message(lead)
        if not allowed:
            raise ConversationError(reason)
        if not text.strip() and not attachments:
            raise ConversationError("message_empty")

        adapter = integration_service.channel_adapter(conversation.channel)
        result = adapter.send_message(
            conversation.external_chat_id or str(lead.id), text, attachments
        )
        message = Message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            direction=MessageDirection.OUTBOUND,
            sender=sender,
            sender_user_id=actor.id if sender == MessageSender.OPERATOR else None,
            channel=conversation.channel,
            body=text,
            language=lead.language,
            status=MessageStatus.SENT if result.ok else MessageStatus.FAILED,
            error_text="" if result.ok else result.message,
            external_id=str(result.data.get("external_id", "")),
            ai_interaction_id=ai_interaction_id,
            created_at=now(),
        )
        db.add(message)
        db.flush()
        _attach_files(db, message, attachments or [])

        conversation.last_message_at = message.created_at
        conversation.last_message_preview = truncate(text, 120)
        conversation.unread_count = 0
        if sender == MessageSender.OPERATOR:
            conversation.status = ConversationStatus.OPERATOR_HANDLING
            conversation.ai_enabled = False
            conversation.assigned_to_id = conversation.assigned_to_id or actor.id
            if lead.owner_id is None:
                lead.owner_id = actor.id
            if lead.status in (
                LeadStatus.NEW,
                LeadStatus.AI_CONVERSATION,
                LeadStatus.WAITING_OPERATOR,
            ):
                lead.status = LeadStatus.OPERATOR_WORKING
        else:
            conversation.ai_message_count = (conversation.ai_message_count or 0) + 1

        if lead.first_response_seconds is None and lead.last_inbound_at:
            lead.first_response_seconds = max(
                0, int((message.created_at - lead.last_inbound_at).total_seconds())
            )
        lead.last_activity_at = message.created_at
        lead_service.add_activity(
            db,
            lead,
            kind="message_out_ai" if sender == MessageSender.AI else "message_out",
            title="AI javob berdi" if sender == MessageSender.AI else "Operator javob berdi",
            detail=truncate(text, 200),
            user_id=actor.id if sender == MessageSender.OPERATOR else None,
        )
        if not result.ok:
            logger.warning(
                "Outbound message failed on %s: %s", conversation.channel, result.message
            )
        db.flush()
        return message

    if session is not None:
        return _send(session)
    with session_scope() as db:
        return _send(db)


def _attach_files(session: Session, message: Message, paths: list[str]) -> None:
    """Copy attachments into the data directory and link them to the message."""
    target_dir = load_config().attachments_dir
    for raw_path in paths:
        source = Path(raw_path)
        if not source.exists():
            continue
        destination = target_dir / f"msg{message.id}_{source.name}"
        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            logger.warning("Attachment copy failed: %s", exc)
            continue
        session.add(
            Attachment(
                message_id=message.id,
                file_name=source.name,
                file_path=str(destination),
                size_bytes=destination.stat().st_size,
                kind=_attachment_kind(source.suffix.lower()),
            )
        )
    session.flush()


def _attachment_kind(suffix: str) -> str:
    """Classify an attachment by file extension."""
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return "image"
    if suffix in {".mp3", ".ogg", ".wav", ".m4a", ".opus"}:
        return "audio"
    if suffix == ".pdf":
        return "pdf"
    return "file"


def add_internal_note(conversation_id: int, text: str, *, actor: CurrentUser) -> Message:
    """Add an operator-only note that is never delivered to the customer."""
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationError("conversation_not_found")
        if not text.strip():
            raise ConversationError("message_empty")
        note = Message(
            conversation_id=conversation.id,
            lead_id=conversation.lead_id,
            direction=MessageDirection.INTERNAL,
            sender=MessageSender.OPERATOR,
            sender_user_id=actor.id,
            channel=conversation.channel,
            body=text.strip(),
            status=MessageStatus.SENT,
            is_internal=True,
            created_at=now(),
        )
        session.add(note)
        session.flush()
        audit_service.record(
            session,
            action="internal_note",
            entity_type="conversation",
            entity_id=conversation.id,
            entity_label=f"lead#{conversation.lead_id}",
            user_id=actor.id,
            username=actor.username,
        )
        return note


def internal_notes(conversation_id: int) -> list[str]:
    """Internal notes of a conversation, used as AI context."""
    with session_scope() as session:
        rows = session.execute(
            select(Message.body)
            .where(Message.conversation_id == conversation_id, Message.is_internal.is_(True))
            .order_by(Message.created_at.desc())
            .limit(5)
        ).all()
        return [row[0] for row in rows]


# --------------------------------------------------------------------------- #
# Assignment / escalation / status
# --------------------------------------------------------------------------- #
def escalate(
    conversation_id: int,
    reason: str,
    *,
    actor: CurrentUser | None = None,
    to_user_id: int | None = None,
    session: Session | None = None,
) -> Conversation:
    """Hand a conversation over to a human operator and stop the AI."""

    def _escalate(db: Session) -> Conversation:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationError("conversation_not_found")
        lead = db.get(Lead, conversation.lead_id)
        conversation.status = ConversationStatus.WAITING_OPERATOR
        conversation.ai_enabled = False
        conversation.escalated_at = now()
        conversation.escalation_reason = reason[:120]
        if to_user_id:
            conversation.assigned_to_id = to_user_id
        if lead is not None:
            if lead.status in (LeadStatus.NEW, LeadStatus.AI_CONVERSATION):
                lead.status = LeadStatus.WAITING_OPERATOR
            if to_user_id:
                lead.owner_id = to_user_id
            lead_service.add_activity(
                db,
                lead,
                kind="escalated",
                title="Operatorga eskalatsiya",
                detail=reason,
                user_id=actor.id if actor else None,
            )
            notification_service.push(
                db,
                title="Operatorga eskalatsiya",
                body=f"{lead.display_name}: {reason}",
                level=NotificationLevel.WARNING,
                category="escalation",
                lead_id=lead.id,
                conversation_id=conversation.id,
                user_id=conversation.assigned_to_id,
            )
        db.flush()
        return conversation

    if session is not None:
        return _escalate(session)
    with session_scope() as db:
        return _escalate(db)


def assign_conversation(conversation_id: int, user_id: int | None, *, actor: CurrentUser) -> None:
    """Assign a conversation (and its lead) to an operator."""
    actor.require(Perm.LEAD_ASSIGN)
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationError("conversation_not_found")
        old = conversation.assigned_to_id
        conversation.assigned_to_id = user_id
        conversation.status = (
            ConversationStatus.OPERATOR_HANDLING if user_id else ConversationStatus.OPEN
        )
        lead = session.get(Lead, conversation.lead_id)
        if lead is not None:
            lead.owner_id = user_id
        session.add(
            ConversationAssignment(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                from_user_id=old,
                to_user_id=user_id,
                assigned_by_id=actor.id,
                created_at=now(),
            )
        )
        audit_service.record(
            session,
            action="conversation_assigned",
            entity_type="conversation",
            entity_id=conversation.id,
            old_value=str(old or "-"),
            new_value=str(user_id or "-"),
            user_id=actor.id,
            username=actor.username,
        )


def set_ai_enabled(conversation_id: int, enabled: bool, *, actor: CurrentUser) -> None:
    """Turn the AI agent on or off for one conversation."""
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationError("conversation_not_found")
        conversation.ai_enabled = enabled
        if enabled and conversation.status == ConversationStatus.WAITING_OPERATOR:
            conversation.status = ConversationStatus.AI_HANDLING
        audit_service.record(
            session,
            action="conversation_ai_toggled",
            entity_type="conversation",
            entity_id=conversation.id,
            new_value=str(enabled),
            user_id=actor.id,
            username=actor.username,
        )


def close_conversation(conversation_id: int, *, actor: CurrentUser) -> None:
    """Mark a conversation as closed."""
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationError("conversation_not_found")
        conversation.status = ConversationStatus.CLOSED
        conversation.closed_at = now()
        conversation.unread_count = 0
        audit_service.record(
            session,
            action="conversation_closed",
            entity_type="conversation",
            entity_id=conversation.id,
            user_id=actor.id,
            username=actor.username,
        )


# --------------------------------------------------------------------------- #
# Quick replies
# --------------------------------------------------------------------------- #
def list_quick_replies() -> list[QuickReply]:
    """Active canned answers for the composer."""
    with session_scope() as session:
        stmt = (
            select(QuickReply)
            .where(QuickReply.is_archived.is_(False), QuickReply.is_active.is_(True))
            .order_by(QuickReply.title)
        )
        return list(session.execute(stmt).scalars().all())


def save_quick_reply(
    *, title: str, body_uz: str, body_ru: str, reply_id: int | None = None, actor: CurrentUser
) -> QuickReply:
    """Create or update a quick reply template."""
    actor.require(Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        if reply_id:
            reply = session.get(QuickReply, reply_id)
            if reply is None:
                raise ConversationError("quick_reply_not_found")
        else:
            reply = QuickReply(title=title)
            session.add(reply)
        reply.title = title.strip()
        reply.body_uz = body_uz
        reply.body_ru = body_ru
        session.flush()
        return reply
