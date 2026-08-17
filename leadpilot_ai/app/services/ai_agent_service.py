"""AI sales operator orchestration.

Responsibilities:

* build a safe context from approved data only (knowledge base, services,
  branches, free slots, internal notes);
* call the configured LLM provider and fall back to the deterministic demo agent
  when the provider is unavailable;
* enforce escalation, working-hours and message-limit rules;
* record every generated reply for the quality review module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.integrations.llm.base_llm import AgentContext, AgentReply, ChatTurn
from app.models.crm import Lead
from app.models.enums import (
    AIInteractionStatus,
    AIState,
    ConversationStatus,
    LeadStatus,
    MessageSender,
    ToneOfVoice,
)
from app.models.enums import (
    Permission as Perm,
)
from app.models.intelligence import AIInteraction, AIProfile
from app.models.messaging import Conversation, Message
from app.models.organization import Branch, Company, Service
from app.services import audit_service, booking_service, knowledge_service, lead_service
from app.services.auth_service import CurrentUser
from app.utils.dates import fmt_datetime, now, parse_hhmm
from app.utils.formatting import truncate

logger = logging.getLogger(__name__)


class AIError(Exception):
    """AI agent rule violation (``code`` is an i18n key)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass
class SuggestionResult:
    """What the inbox shows to the operator after asking the AI."""

    interaction_id: int
    text: str
    escalate: bool
    escalation_reason: str
    wants_booking: bool
    next_state: str
    provider: str
    model: str
    auto_sent: bool = False


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #
def get_profile(session: Session | None = None) -> AIProfile:
    """Return the AI profile, creating a default one when missing."""

    def _get(db: Session) -> AIProfile:
        profile = db.execute(select(AIProfile)).scalars().first()
        if profile is None:
            company = db.execute(select(Company)).scalars().first()
            profile = AIProfile(
                company_id=company.id if company else 1,
                agent_name="Aziza",
                tone=ToneOfVoice.FRIENDLY,
            )
            db.add(profile)
            db.flush()
        return profile

    if session is not None:
        return _get(session)
    with session_scope() as db:
        return _get(db)


def save_profile(*, actor: CurrentUser, **values: object) -> AIProfile:
    """Update the AI agent configuration."""
    actor.require(Perm.AI_CONFIGURE)
    with session_scope() as session:
        profile = get_profile(session)
        changes = []
        for field, value in values.items():
            if not hasattr(profile, field):
                continue
            old = getattr(profile, field)
            if old == value:
                continue
            setattr(profile, field, value)
            changes.append(f"{field}: {old} → {value}")
        session.flush()
        if changes:
            audit_service.record(
                session,
                action="ai_profile_updated",
                entity_type="ai_profile",
                entity_id=profile.id,
                detail="; ".join(changes)[:2000],
                user_id=actor.id,
                username=actor.username,
            )
        return profile


def within_working_hours(profile: AIProfile, moment: datetime | None = None) -> bool:
    """Whether ``moment`` falls inside the agent's configured working hours."""
    current = (moment or now()).time()
    return parse_hhmm(profile.work_start) <= current <= parse_hhmm(profile.work_end)


# --------------------------------------------------------------------------- #
# Context building
# --------------------------------------------------------------------------- #
def build_context(
    session: Session, conversation: Conversation, lead: Lead, customer_message: str
) -> AgentContext:
    """Collect every approved fact the AI is allowed to use."""
    profile = get_profile(session)
    company = (
        session.get(Company, lead.company_id) or session.execute(select(Company)).scalars().first()
    )
    language = (
        lead.language
        if lead.language in ("uz", "ru")
        else (company.default_language if company else "uz")
    )

    services = [
        {
            "id": service.id,
            "name": service.name,
            "name_ru": service.name_ru,
            "price_label": service.price_label,
            "duration": service.duration_minutes,
        }
        for service in session.execute(
            select(Service).where(Service.is_archived.is_(False), Service.is_active.is_(True))
        )
        .scalars()
        .all()
    ]
    branches = [
        {
            "id": branch.id,
            "name": branch.name,
            "address": branch.address,
            "hours": f"{branch.work_start}–{branch.work_end}",
        }
        for branch in session.execute(
            select(Branch).where(Branch.is_archived.is_(False), Branch.is_active.is_(True))
        )
        .scalars()
        .all()
    ]

    history_rows = (
        session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(14)
        )
        .scalars()
        .all()
    )
    history = [
        ChatTurn(
            role="customer" if message.sender == MessageSender.CUSTOMER else "agent",
            text=message.body,
        )
        for message in reversed(history_rows)
        if not message.is_internal
    ]
    notes = [
        row[0]
        for row in session.execute(
            select(Message.body)
            .where(Message.conversation_id == conversation.id, Message.is_internal.is_(True))
            .order_by(Message.created_at.desc())
            .limit(5)
        ).all()
    ]

    from app.integrations.llm import nlu

    keywords = nlu.keywords_of(customer_message)
    knowledge = knowledge_service.retrieve(session, keywords, language=language)
    promos = knowledge_service.active_promos(session, language)
    slots = booking_service.free_slots(
        session, branch_id=lead.branch_id, duration_minutes=30, limit=4
    )

    return AgentContext(
        agent_name=profile.agent_name,
        company_name=company.name if company else "",
        tone=profile.tone,
        language=language,
        state=conversation.ai_state or AIState.NEW_LEAD,
        lead_name=lead.full_name,
        lead_phone=lead.phone or "",
        lead_interest=lead.interest,
        lead_score=lead.score,
        history=history,
        knowledge=knowledge,
        services=services,
        branches=branches,
        promos=promos,
        internal_notes=notes,
        free_slots=[fmt_datetime(slot) for slot in slots],
        channel=conversation.channel,
        forbidden_topics=[t.strip() for t in profile.forbidden_topics.split(",") if t.strip()],
        signature=profile.signature,
        within_working_hours=within_working_hours(profile),
    )


# --------------------------------------------------------------------------- #
# Escalation rules
# --------------------------------------------------------------------------- #
def evaluate_escalation(
    profile: AIProfile, conversation: Conversation, lead: Lead, reply: AgentReply
) -> tuple[bool, str]:
    """Apply the configured escalation policy on top of the provider's answer."""
    if reply.escalate:
        return True, reply.escalation_reason or "AI eskalatsiya so'radi"
    if profile.escalate_on_negative and reply.confidence < 0.3:
        return True, "AI ishonchsiz javob"
    if conversation.ai_message_count >= profile.max_auto_messages:
        return True, "Avtomatik xabarlar limiti"
    if (
        profile.escalate_score_threshold
        and lead.score >= profile.escalate_score_threshold
        and reply.wants_booking
    ):
        return True, "Yuqori niyatli lead — operator tasdig'i"
    if conversation.ai_unanswered_count >= profile.escalate_after_unanswered:
        return True, "AI ketma-ket aniq javob bera olmadi"
    return False, ""


# --------------------------------------------------------------------------- #
# Main entry points
# --------------------------------------------------------------------------- #
def suggest_reply(
    conversation_id: int,
    *,
    actor: CurrentUser | None = None,
    customer_message: str | None = None,
    auto_send: bool | None = None,
) -> SuggestionResult:
    """Generate the next AI reply for a conversation.

    When ``auto_send`` is ``True`` (or the profile is autonomous and no
    escalation is required) the message is delivered immediately.
    """
    from app.services import conversation_service, integration_service

    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise AIError("conversation_not_found")
        lead = session.get(Lead, conversation.lead_id)
        if lead is None:
            raise AIError("lead_not_found")
        profile = get_profile(session)
        if not profile.is_enabled:
            raise AIError("ai_disabled")

        allowed, reason = lead_service.may_send_message(lead)
        if not allowed:
            raise AIError(reason)

        text = customer_message
        if text is None:
            last_inbound = (
                session.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation.id,
                        Message.sender == MessageSender.CUSTOMER,
                    )
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            text = last_inbound.body if last_inbound else ""

        context = build_context(session, conversation, lead, text)
        provider = integration_service.llm_provider()
        state_before = conversation.ai_state or AIState.NEW_LEAD
        try:
            reply = provider.generate_reply(context, text)
        except Exception as exc:
            logger.warning(
                "LLM provider %s failed (%s) — falling back to demo agent",
                provider.provider,
                type(exc).__name__,
            )
            integration_service.update_status("openai_compatible", "error", f"{type(exc).__name__}")
            reply = integration_service.demo_llm().generate_reply(context, text)

        escalate, escalation_reason = evaluate_escalation(profile, conversation, lead, reply)

        interaction = AIInteraction(
            lead_id=lead.id,
            conversation_id=conversation.id,
            provider=reply.provider,
            model=reply.model,
            state_before=state_before,
            state_after=reply.next_state,
            customer_message=truncate(text, 2000),
            suggested_reply=reply.text,
            language=reply.extracted.get("language", context.language),
            status=AIInteractionStatus.SUGGESTED,
            escalated=escalate,
            escalation_reason=escalation_reason,
            latency_ms=reply.latency_ms,
            kb_refs=",".join(reply.kb_refs)[:255],
            created_at=now(),
        )
        session.add(interaction)
        session.flush()

        conversation.ai_state = reply.next_state
        lead.ai_state = reply.next_state
        if reply.confidence < 0.3:
            conversation.ai_unanswered_count = (conversation.ai_unanswered_count or 0) + 1
        else:
            conversation.ai_unanswered_count = 0
        _apply_extracted(session, lead, reply)

        should_send = auto_send
        if should_send is None:
            should_send = bool(profile.autonomous and conversation.ai_enabled and not escalate)
        if should_send and not within_working_hours(profile) and not profile.night_send_allowed:
            should_send = False

        auto_sent = False
        if should_send:
            system_actor = actor or _system_actor(lead)
            conversation_service.send_message(
                conversation.id,
                reply.text,
                actor=system_actor,
                sender=MessageSender.AI,
                ai_interaction_id=interaction.id,
                session=session,
            )
            interaction.final_reply = reply.text
            interaction.status = AIInteractionStatus.SENT
            conversation.status = ConversationStatus.AI_HANDLING
            if lead.status == LeadStatus.NEW:
                lead.status = LeadStatus.AI_CONVERSATION
            auto_sent = True

        if escalate:
            interaction.status = AIInteractionStatus.ESCALATED
            conversation_service.escalate(
                conversation.id, escalation_reason, actor=actor, session=session
            )

        if reply.wants_booking and auto_sent:
            _try_auto_booking(session, lead, reply)

        session.flush()
        return SuggestionResult(
            interaction_id=interaction.id,
            text=reply.text,
            escalate=escalate,
            escalation_reason=escalation_reason,
            wants_booking=reply.wants_booking,
            next_state=reply.next_state,
            provider=reply.provider,
            model=reply.model,
            auto_sent=auto_sent,
        )


def _system_actor(lead: Lead) -> CurrentUser:
    """Synthetic actor used when the AI acts without a signed-in operator."""
    return CurrentUser(
        id=lead.owner_id or 0,
        username="ai-agent",
        full_name="AI agent",
        role="operator",
        company_id=lead.company_id,
        permissions={Perm.CONVERSATION_REPLY.value, Perm.LEAD_EDIT.value},
    )


def _apply_extracted(session: Session, lead: Lead, reply: AgentReply) -> None:
    """Persist customer data the agent extracted from the message."""
    from app.utils.formatting import normalize_phone

    changed = False
    phone = reply.extracted.get("phone")
    if phone and not lead.phone:
        lead.phone = normalize_phone(phone)
        changed = True
    name = reply.extracted.get("full_name")
    if name and not lead.full_name:
        lead.full_name = name
        changed = True
    language = reply.extracted.get("language")
    if language in ("uz", "ru") and lead.language != language:
        lead.language = language
        changed = True
    if reply.extracted.get("opt_out"):
        lead_service.set_do_not_contact(lead.id, True, session=session)
    if changed:
        session.flush()


def _try_auto_booking(session: Session, lead: Lead, reply: AgentReply) -> None:
    """Create a booking when the AI collected every required field."""
    profile = get_profile(session)
    required = profile.required_booking_fields()
    raw_datetime = reply.extracted.get("datetime")
    if not raw_datetime:
        return
    try:
        starts_at = datetime.fromisoformat(raw_datetime)
    except ValueError:
        return
    if "phone" in required and not lead.phone:
        return
    if "full_name" in required and not lead.full_name:
        return
    try:
        booking_service.create_booking(
            session=session,
            lead_id=lead.id,
            starts_at=starts_at,
            service_id=lead.service_id,
            branch_id=lead.branch_id,
            created_channel="ai",
            created_by_ai=True,
            send_confirmation=True,
        )
    except booking_service.BookingError as exc:
        logger.info("AI booking refused: %s", exc.code)


# --------------------------------------------------------------------------- #
# Quality review
# --------------------------------------------------------------------------- #
def mark_interaction(
    interaction_id: int,
    status: str,
    *,
    actor: CurrentUser,
    final_reply: str = "",
) -> None:
    """Record what the operator did with a suggested answer."""
    with session_scope() as session:
        interaction = session.get(AIInteraction, interaction_id)
        if interaction is None:
            raise AIError("ai_interaction_not_found")
        interaction.status = status
        if final_reply:
            interaction.final_reply = final_reply
        session.flush()
        audit_service.record(
            session,
            action="ai_interaction_marked",
            entity_type="ai_interaction",
            entity_id=interaction.id,
            new_value=status,
            user_id=actor.id,
            username=actor.username,
        )


def review_interaction(
    interaction_id: int,
    *,
    actor: CurrentUser,
    useful: bool,
    category: str = "",
    comment: str = "",
) -> None:
    """Manager review of one AI answer (feeds the improvement dataset)."""
    actor.require(Perm.AI_REVIEW)
    with session_scope() as session:
        interaction = session.get(AIInteraction, interaction_id)
        if interaction is None:
            raise AIError("ai_interaction_not_found")
        interaction.reviewed_by_id = actor.id
        interaction.review_useful = useful
        interaction.review_category = category
        interaction.review_comment = comment
        session.flush()
        audit_service.record(
            session,
            action="ai_reviewed",
            entity_type="ai_interaction",
            entity_id=interaction.id,
            new_value="useful" if useful else category,
            detail=comment,
            user_id=actor.id,
            username=actor.username,
        )


def list_interactions(
    *,
    search: str = "",
    statuses: list[str] | None = None,
    only_unreviewed: bool = False,
    only_rejected: bool = False,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 400,
) -> list[AIInteraction]:
    """Filtered AI interaction list for the quality review page."""
    with session_scope() as session:
        stmt = select(AIInteraction)
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                AIInteraction.customer_message.ilike(pattern)
                | AIInteraction.suggested_reply.ilike(pattern)
            )
        if statuses:
            stmt = stmt.where(AIInteraction.status.in_(statuses))
        if only_unreviewed:
            stmt = stmt.where(AIInteraction.review_useful.is_(None))
        if only_rejected:
            stmt = stmt.where(AIInteraction.status == AIInteractionStatus.REJECTED)
        if date_from:
            stmt = stmt.where(AIInteraction.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AIInteraction.created_at <= date_to)
        stmt = stmt.order_by(AIInteraction.created_at.desc()).limit(limit)
        return list(session.execute(stmt).scalars().all())


def rejection_examples(limit: int = 100) -> list[AIInteraction]:
    """Rejected or negatively reviewed answers kept as improvement examples."""
    with session_scope() as session:
        stmt = (
            select(AIInteraction)
            .where(
                (AIInteraction.status == AIInteractionStatus.REJECTED)
                | (AIInteraction.review_useful.is_(False))
            )
            .order_by(AIInteraction.created_at.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())


def quality_summary(
    date_from: datetime | None = None, date_to: datetime | None = None
) -> dict[str, float]:
    """Aggregate AI quality metrics for the reports page."""
    with session_scope() as session:
        stmt = select(AIInteraction.status, func.count(AIInteraction.id))
        if date_from:
            stmt = stmt.where(AIInteraction.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AIInteraction.created_at <= date_to)
        rows = session.execute(stmt.group_by(AIInteraction.status)).all()
        counts = {status: count for status, count in rows}
        total = sum(counts.values()) or 1
        useful_rows = session.execute(
            select(
                func.sum(cast(AIInteraction.review_useful, Integer)),
                func.count(AIInteraction.id),
            ).where(AIInteraction.review_useful.isnot(None))
        ).one()
        reviewed_useful = int(useful_rows[0] or 0)
        reviewed_total = int(useful_rows[1] or 0)
        return {
            "total": float(sum(counts.values())),
            "sent": float(counts.get(AIInteractionStatus.SENT, 0)),
            "edited": float(counts.get(AIInteractionStatus.EDITED, 0)),
            "rejected": float(counts.get(AIInteractionStatus.REJECTED, 0)),
            "escalated": float(counts.get(AIInteractionStatus.ESCALATED, 0)),
            "positive": float(counts.get(AIInteractionStatus.POSITIVE_REPLY, 0)),
            "sent_ratio": counts.get(AIInteractionStatus.SENT, 0) / total * 100,
            "reject_ratio": counts.get(AIInteractionStatus.REJECTED, 0) / total * 100,
            "useful_ratio": (reviewed_useful / reviewed_total * 100) if reviewed_total else 0.0,
        }
