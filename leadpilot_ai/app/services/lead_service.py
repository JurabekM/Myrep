"""Lead business logic: scoring, status transitions, deduplication and merging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.integrations.llm import nlu
from app.models.crm import Lead, LeadActivity, RevenueRecord, Tag
from app.models.enums import (
    CLOSED_STATUSES,
    LEAD_STATUS_TRANSITIONS,
    UNIVERSAL_STATUSES,
    Channel,
    IntentLevel,
    LeadStatus,
)
from app.models.enums import (
    Permission as Perm,
)
from app.models.intelligence import ScoringRule
from app.models.messaging import Conversation, Message
from app.models.operations import Booking, Call, Task
from app.repositories.lead_repository import LeadFilter, LeadRepository
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.dates import now
from app.utils.formatting import normalize_phone

logger = logging.getLogger(__name__)

#: Default scoring rules created on first run. Codes are stable identifiers.
DEFAULT_SCORING_RULES: list[dict[str, Any]] = [
    {
        "code": "service_interest",
        "title_uz": "Aniq xizmatga qiziqish",
        "title_ru": "Интерес к конкретной услуге",
        "points": 20,
        "keywords_uz": "xizmat,qabul,dermatolog,stomatolog,epilyatsiya,uzi,tekshiruv",
        "keywords_ru": "услуга,приём,дерматолог,стоматолог,эпиляция,узи,обследование",
    },
    {
        "code": "price_or_time",
        "title_uz": "Narx yoki bo'sh vaqt so'rashi",
        "title_ru": "Спрашивает цену или свободное время",
        "points": 15,
        "keywords_uz": "narx,qancha,bo'sh vaqt,soat,qachon",
        "keywords_ru": "цена,сколько,свободно,когда,во сколько",
    },
    {
        "code": "phone_provided",
        "title_uz": "Telefon raqam qoldirdi",
        "title_ru": "Оставил номер телефона",
        "points": 15,
        "keywords_uz": "",
        "keywords_ru": "",
    },
    {
        "code": "booking_request",
        "title_uz": "Bron so'radi",
        "title_ru": "Просит записать",
        "points": 30,
        "keywords_uz": "yozing,bron,band qil,navbat,yozilmoqchi",
        "keywords_ru": "запишите,запись,бронь,забронировать",
    },
    {
        "code": "negative_reply",
        "title_uz": "Salbiy javob",
        "title_ru": "Негативный ответ",
        "points": -20,
        "keywords_uz": "kerak emas,qiziqmayman,yomon,shikoyat",
        "keywords_ru": "не надо,не интересует,плохо,жалоба",
    },
    {
        "code": "urgency",
        "title_uz": "Shoshilinch so'zlar",
        "title_ru": "Слова срочности",
        "points": 15,
        "keywords_uz": "bugun,hozir,tez,shoshilinch",
        "keywords_ru": "сегодня,сейчас,срочно,быстрее",
    },
    {
        "code": "silence_penalty",
        "title_uz": "Uzoq javob bermaslik",
        "title_ru": "Долгое молчание",
        "points": -10,
        "keywords_uz": "",
        "keywords_ru": "",
    },
]

HOT_THRESHOLD = 70
WARM_THRESHOLD = 40


class LeadError(Exception):
    """Business rule violation on a lead operation (``code`` is an i18n key)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass
class ScoreChange:
    """Result of a scoring pass."""

    delta: int
    total: int
    intent: str
    reasons: list[str]


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def ensure_scoring_rules(session: Session) -> None:
    """Create the default scoring rules when the table is empty."""
    existing = {code for (code,) in session.execute(select(ScoringRule.code)).all()}
    for spec in DEFAULT_SCORING_RULES:
        if spec["code"] in existing:
            continue
        session.add(ScoringRule(**spec))
    session.flush()


def load_scoring_rules(session: Session) -> list[ScoringRule]:
    """Return the active scoring rules."""
    ensure_scoring_rules(session)
    return list(
        session.execute(
            select(ScoringRule).where(ScoringRule.is_active.is_(True)).order_by(ScoringRule.id)
        )
        .scalars()
        .all()
    )


def intent_for_score(score: int) -> str:
    """Map a numeric score onto a qualitative intent level."""
    if score >= HOT_THRESHOLD:
        return IntentLevel.HOT
    if score >= WARM_THRESHOLD:
        return IntentLevel.WARM
    return IntentLevel.COLD


def score_message(
    session: Session,
    text: str,
    *,
    phone_provided: bool = False,
    silent_minutes: int = 0,
) -> tuple[int, list[str]]:
    """Score one customer message. Returns ``(delta, reason_codes)``."""
    rules = load_scoring_rules(session)
    lowered = (text or "").lower()
    delta = 0
    reasons: list[str] = []
    for rule in rules:
        if rule.code == "phone_provided":
            if phone_provided:
                delta += rule.points
                reasons.append(rule.code)
            continue
        if rule.code == "silence_penalty":
            if silent_minutes >= 60:
                delta += rule.points
                reasons.append(rule.code)
            continue
        keywords = rule.keywords()
        if keywords and any(kw in lowered for kw in keywords):
            delta += rule.points
            reasons.append(rule.code)
    return delta, reasons


def apply_score(
    session: Session,
    lead: Lead,
    delta: int,
    *,
    reasons: list[str] | None = None,
    actor: CurrentUser | None = None,
) -> ScoreChange:
    """Apply a score delta, clamp to 0..100 and update the intent level."""
    old_score = lead.score
    old_intent = lead.intent
    lead.score = max(0, min(100, lead.score + delta))
    lead.intent = intent_for_score(lead.score)
    session.flush()
    if lead.score != old_score:
        add_activity(
            session,
            lead,
            kind="score_changed",
            title=f"Skor: {old_score} → {lead.score}",
            detail=", ".join(reasons or []),
            old_value=str(old_score),
            new_value=str(lead.score),
            user_id=actor.id if actor else None,
        )
    if lead.intent != old_intent and lead.intent == IntentLevel.HOT:
        add_activity(session, lead, kind="became_hot", title="Lead issiq deb belgilandi")
    return ScoreChange(
        delta=lead.score - old_score,
        total=lead.score,
        intent=lead.intent,
        reasons=reasons or [],
    )


# --------------------------------------------------------------------------- #
# Timeline
# --------------------------------------------------------------------------- #
def add_activity(
    session: Session,
    lead: Lead,
    *,
    kind: str,
    title: str,
    detail: str = "",
    old_value: str = "",
    new_value: str = "",
    user_id: int | None = None,
) -> LeadActivity:
    """Append an entry to the lead timeline."""
    activity = LeadActivity(
        lead_id=lead.id,
        user_id=user_id,
        kind=kind,
        title=title[:200],
        detail=detail[:2000],
        old_value=str(old_value)[:200],
        new_value=str(new_value)[:200],
        created_at=now(),
    )
    session.add(activity)
    lead.last_activity_at = activity.created_at
    session.flush()
    return activity


def timeline(lead_id: int) -> list[LeadActivity]:
    """Full timeline of a lead, oldest first."""
    with session_scope() as session:
        stmt = (
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead_id)
            .order_by(LeadActivity.created_at.asc(), LeadActivity.id.asc())
        )
        return list(session.execute(stmt).scalars().all())


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def create_lead(
    *,
    actor: CurrentUser | None = None,
    company_id: int = 1,
    full_name: str = "",
    phone: str = "",
    email: str = "",
    telegram_username: str = "",
    channel: str = Channel.MANUAL,
    language: str = "unknown",
    service_id: int | None = None,
    branch_id: int | None = None,
    owner_id: int | None = None,
    interest: str = "",
    source_id: int | None = None,
    campaign_id: int | None = None,
    utm: dict[str, str] | None = None,
    external_id: str = "",
    notes: str = "",
    status: str = LeadStatus.NEW,
    session: Session | None = None,
) -> Lead:
    """Create a lead. When ``session`` is given the caller owns the transaction."""

    def _create(db: Session) -> Lead:
        normalized = normalize_phone(phone)
        lead = Lead(
            company_id=company_id,
            full_name=full_name.strip(),
            phone=normalized,
            phone_raw=phone or "",
            email=email.strip(),
            telegram_username=telegram_username.lstrip("@").strip(),
            channel=channel,
            language=language,
            service_id=service_id,
            branch_id=branch_id,
            owner_id=owner_id,
            interest=interest.strip(),
            source_id=source_id,
            campaign_id=campaign_id,
            external_id=external_id,
            notes=notes,
            status=status,
            utm_source=(utm or {}).get("utm_source", ""),
            utm_medium=(utm or {}).get("utm_medium", ""),
            utm_campaign=(utm or {}).get("utm_campaign", ""),
            utm_content=(utm or {}).get("utm_content", ""),
            last_activity_at=now(),
        )
        db.add(lead)
        db.flush()
        add_activity(
            db,
            lead,
            kind="lead_created",
            title="Lead yaratildi",
            detail=f"channel={channel}",
            user_id=actor.id if actor else None,
        )
        audit_service.record(
            db,
            action="lead_created",
            entity_type="lead",
            entity_id=lead.id,
            entity_label=lead.display_name,
            new_value=f"channel={channel}",
            user_id=actor.id if actor else None,
            username=actor.username if actor else "system",
        )
        return lead

    if session is not None:
        return _create(session)
    with session_scope() as db:
        return _create(db)


def get_lead(lead_id: int) -> Lead | None:
    """Fetch a lead by id."""
    with session_scope() as session:
        return LeadRepository(session).get(lead_id)


def search_leads(
    flt: LeadFilter,
    *,
    actor: CurrentUser | None = None,
    sort_field: str = "created_at",
    descending: bool = True,
    limit: int | None = 100,
    offset: int = 0,
) -> tuple[list[Lead], int]:
    """Return ``(page, total)`` honouring the actor's visibility scope."""
    scoped = _scope_filter(flt, actor)
    with session_scope() as session:
        repo = LeadRepository(session)
        total = repo.count_filtered(scoped)
        rows = repo.search(
            scoped, sort_field=sort_field, descending=descending, limit=limit, offset=offset
        )
        return rows, total


def _scope_filter(flt: LeadFilter, actor: CurrentUser | None) -> LeadFilter:
    """Restrict a filter to the leads the actor is allowed to see."""
    if actor is None or actor.sees_all_leads:
        return flt
    scoped = LeadFilter(**{**flt.__dict__})
    scoped.owner_ids = [actor.id]
    return scoped


def can_edit(lead: Lead, actor: CurrentUser) -> bool:
    """Whether ``actor`` may modify ``lead``."""
    if actor.can(Perm.LEAD_VIEW_ALL) and actor.can(Perm.LEAD_EDIT):
        return True
    if not actor.can(Perm.LEAD_EDIT):
        return False
    return lead.owner_id in (None, actor.id)


def update_lead(lead_id: int, *, actor: CurrentUser, **values: Any) -> Lead:
    """Update lead fields with permission and normalisation rules applied."""
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise LeadError("lead_not_found")
        if not can_edit(lead, actor):
            raise LeadError("no_permission_other_lead")
        changes: list[str] = []
        for field_name, value in values.items():
            if not hasattr(lead, field_name):
                continue
            old = getattr(lead, field_name)
            if field_name == "phone":
                value = normalize_phone(value)
            if old == value:
                continue
            setattr(lead, field_name, value)
            changes.append(f"{field_name}: {old} → {value}")
        if changes:
            session.flush()
            add_activity(
                session,
                lead,
                kind="lead_updated",
                title="Lead ma'lumotlari yangilandi",
                detail="; ".join(changes)[:2000],
                user_id=actor.id,
            )
            audit_service.record(
                session,
                action="lead_updated",
                entity_type="lead",
                entity_id=lead.id,
                entity_label=lead.display_name,
                detail="; ".join(changes),
                user_id=actor.id,
                username=actor.username,
            )
        return lead


def can_transition(current: str, target: str) -> bool:
    """Whether the pipeline allows ``current`` → ``target``."""
    if current == target:
        return True
    if target in UNIVERSAL_STATUSES:
        return True
    return target in LEAD_STATUS_TRANSITIONS.get(current, set())


def change_status(
    lead_id: int,
    new_status: str,
    *,
    actor: CurrentUser,
    loss_reason: str = "",
    loss_comment: str = "",
    revenue: float | None = None,
    sale_date: datetime | None = None,
    session: Session | None = None,
) -> Lead:
    """Move a lead through the pipeline enforcing every business rule."""

    def _change(db: Session) -> Lead:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise LeadError("lead_not_found")
        if not can_edit(lead, actor):
            raise LeadError("no_permission_other_lead")
        old = lead.status
        if old == new_status:
            return lead
        if not can_transition(old, new_status):
            raise LeadError("invalid_status_transition", f"{old} → {new_status}")
        if new_status == LeadStatus.LOST and not loss_reason:
            raise LeadError("loss_reason_required")

        lead.status = new_status
        if new_status == LeadStatus.LOST:
            lead.loss_reason = loss_reason
            lead.loss_comment = loss_comment
            lead.lost_at = now()
        if new_status == LeadStatus.WON:
            lead.won_at = now()
            if revenue is not None:
                lead.revenue = float(revenue)
                db.add(
                    RevenueRecord(
                        lead_id=lead.id,
                        service_id=lead.service_id,
                        branch_id=lead.branch_id,
                        campaign_id=lead.campaign_id,
                        amount=float(revenue),
                        sale_date=(sale_date or now()).date(),
                        created_by_id=actor.id,
                    )
                )
        db.flush()
        add_activity(
            db,
            lead,
            kind="status_changed",
            title=f"Status: {old} → {new_status}",
            detail=loss_comment,
            old_value=old,
            new_value=new_status,
            user_id=actor.id,
        )
        audit_service.record(
            db,
            action="lead_status_changed",
            entity_type="lead",
            entity_id=lead.id,
            entity_label=lead.display_name,
            old_value=old,
            new_value=new_status,
            detail=loss_reason or "",
            user_id=actor.id,
            username=actor.username,
        )
        return lead

    if session is not None:
        return _change(session)
    with session_scope() as db:
        return _change(db)


def assign_lead(lead_id: int, owner_id: int | None, *, actor: CurrentUser) -> Lead:
    """Assign or unassign the responsible operator."""
    actor.require(Perm.LEAD_ASSIGN)
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise LeadError("lead_not_found")
        old = lead.owner_id
        lead.owner_id = owner_id
        session.flush()
        conversations = (
            session.execute(select(Conversation).where(Conversation.lead_id == lead_id))
            .scalars()
            .all()
        )
        for conversation in conversations:
            conversation.assigned_to_id = owner_id
        add_activity(
            session,
            lead,
            kind="assigned",
            title="Operator biriktirildi",
            old_value=str(old or "-"),
            new_value=str(owner_id or "-"),
            user_id=actor.id,
        )
        audit_service.record(
            session,
            action="lead_assigned",
            entity_type="lead",
            entity_id=lead.id,
            entity_label=lead.display_name,
            old_value=str(old or "-"),
            new_value=str(owner_id or "-"),
            user_id=actor.id,
            username=actor.username,
        )
        return lead


def set_do_not_contact(
    lead_id: int, value: bool, *, actor: CurrentUser | None = None, session: Session | None = None
) -> None:
    """Mark or clear the ``Do Not Contact`` flag."""

    def _apply(db: Session) -> None:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise LeadError("lead_not_found")
        lead.do_not_contact = value
        lead.opt_out_at = now() if value else None
        db.flush()
        add_activity(
            db,
            lead,
            kind="do_not_contact",
            title="Do Not Contact yoqildi" if value else "Do Not Contact o'chirildi",
            user_id=actor.id if actor else None,
        )
        audit_service.record(
            db,
            action="lead_opt_out" if value else "lead_opt_in",
            entity_type="lead",
            entity_id=lead_id,
            entity_label=lead.display_name,
            new_value=str(value),
            user_id=actor.id if actor else None,
            username=actor.username if actor else "system",
        )

    if session is not None:
        _apply(session)
    else:
        with session_scope() as db:
            _apply(db)


def may_send_message(lead: Lead) -> tuple[bool, str]:
    """Whether an outbound message is allowed. Returns ``(allowed, reason_key)``."""
    if lead.do_not_contact:
        return False, "lead_opted_out"
    if lead.status == LeadStatus.SPAM:
        return False, "lead_is_spam"
    return True, ""


def detect_opt_out(text: str, language: str = "uz") -> bool:
    """Whether the customer asked to stop being contacted."""
    understanding = nlu.understand(text, language)
    return understanding.has("opt_out")


# --------------------------------------------------------------------------- #
# Tags
# --------------------------------------------------------------------------- #
def set_tags(lead_id: int, tag_ids: list[int], *, actor: CurrentUser) -> None:
    """Replace the tag set of a lead."""
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise LeadError("lead_not_found")
        if not can_edit(lead, actor):
            raise LeadError("no_permission_other_lead")
        old = ", ".join(sorted(t.name for t in lead.tags))
        tags = list(session.execute(select(Tag).where(Tag.id.in_(tag_ids))).scalars().all())
        lead.tags = tags
        session.flush()
        new = ", ".join(sorted(t.name for t in tags))
        add_activity(
            session,
            lead,
            kind="tags_changed",
            title="Taglar yangilandi",
            old_value=old,
            new_value=new,
            user_id=actor.id,
        )


def add_tag_to_leads(lead_ids: list[int], tag_id: int, *, actor: CurrentUser) -> int:
    """Bulk-add one tag to many leads; returns the number of leads updated."""
    with session_scope() as session:
        tag = session.get(Tag, tag_id)
        if tag is None:
            raise LeadError("tag_not_found")
        updated = 0
        for lead_id in lead_ids:
            lead = session.get(Lead, lead_id)
            if lead is None or not can_edit(lead, actor):
                continue
            if tag not in lead.tags:
                lead.tags.append(tag)
                updated += 1
        session.flush()
        audit_service.record(
            session,
            action="leads_tagged",
            entity_type="lead",
            entity_label=tag.name,
            detail=f"{updated} ta lead",
            user_id=actor.id,
            username=actor.username,
        )
        return updated


def create_tag(name: str, color: str = "#3B82F6", *, actor: CurrentUser) -> Tag:
    """Create a new tag."""
    with session_scope() as session:
        existing = session.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if existing:
            raise LeadError("tag_exists")
        tag = Tag(name=name.strip(), color=color)
        session.add(tag)
        session.flush()
        audit_service.record(
            session,
            action="tag_created",
            entity_type="tag",
            entity_id=tag.id,
            entity_label=tag.name,
            user_id=actor.id,
            username=actor.username,
        )
        return tag


def list_tags() -> list[Tag]:
    """All tags ordered by name."""
    with session_scope() as session:
        return list(session.execute(select(Tag).order_by(Tag.name)).scalars().all())


# --------------------------------------------------------------------------- #
# Bulk actions / archive
# --------------------------------------------------------------------------- #
def bulk_assign(lead_ids: list[int], owner_id: int | None, *, actor: CurrentUser) -> int:
    """Assign many leads at once."""
    actor.require(Perm.LEAD_ASSIGN)
    count = 0
    for lead_id in lead_ids:
        try:
            assign_lead(lead_id, owner_id, actor=actor)
            count += 1
        except LeadError:
            continue
    return count


def bulk_status(
    lead_ids: list[int], status: str, *, actor: CurrentUser, loss_reason: str = ""
) -> tuple[int, list[str]]:
    """Change status for many leads; returns ``(ok_count, error_codes)``."""
    ok = 0
    errors: list[str] = []
    for lead_id in lead_ids:
        try:
            change_status(lead_id, status, actor=actor, loss_reason=loss_reason)
            ok += 1
        except LeadError as exc:
            errors.append(exc.code)
    return ok, errors


def archive_leads(lead_ids: list[int], *, actor: CurrentUser) -> int:
    """Soft delete (archive) leads."""
    actor.require(Perm.LEAD_DELETE)
    with session_scope() as session:
        count = 0
        for lead_id in lead_ids:
            lead = session.get(Lead, lead_id)
            if lead is None or lead.is_archived:
                continue
            lead.is_archived = True
            lead.archived_at = now()
            count += 1
            audit_service.record(
                session,
                action="lead_archived",
                entity_type="lead",
                entity_id=lead.id,
                entity_label=lead.display_name,
                user_id=actor.id,
                username=actor.username,
            )
        return count


def restore_leads(lead_ids: list[int], *, actor: CurrentUser) -> int:
    """Undo archiving."""
    actor.require(Perm.LEAD_DELETE)
    with session_scope() as session:
        count = 0
        for lead_id in lead_ids:
            lead = session.get(Lead, lead_id)
            if lead is None or not lead.is_archived:
                continue
            lead.is_archived = False
            lead.archived_at = None
            count += 1
        return count


# --------------------------------------------------------------------------- #
# Duplicates and merging
# --------------------------------------------------------------------------- #
def find_duplicates(lead_id: int) -> list[Lead]:
    """Leads that look like the same person as ``lead_id``."""
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if lead is None:
            return []
        return LeadRepository(session).find_duplicates(
            phone=lead.phone,
            telegram_username=lead.telegram_username,
            email=lead.email,
            external_id=lead.external_id or None,
            exclude_id=lead.id,
        )


def find_duplicate_groups(limit: int = 200) -> list[list[Lead]]:
    """Group open leads that share a phone / username / email."""
    with session_scope() as session:
        leads = list(
            session.execute(select(Lead).where(Lead.is_archived.is_(False)).order_by(Lead.id))
            .scalars()
            .unique()
            .all()
        )
        buckets: dict[str, list[Lead]] = {}
        for lead in leads:
            keys = []
            if lead.phone:
                keys.append(f"p:{lead.phone}")
            if lead.telegram_username:
                keys.append(f"t:{lead.telegram_username.lower()}")
            if lead.email:
                keys.append(f"e:{lead.email.lower()}")
            for key in keys:
                buckets.setdefault(key, []).append(lead)
        groups = [g for g in buckets.values() if len(g) > 1]
        unique: list[list[Lead]] = []
        seen: set[tuple[int, ...]] = set()
        for group in groups:
            signature = tuple(sorted(item.id for item in group))
            if signature in seen:
                continue
            seen.add(signature)
            unique.append(group)
        return unique[:limit]


def merge_leads(primary_id: int, duplicate_id: int, *, actor: CurrentUser) -> Lead:
    """Merge ``duplicate_id`` into ``primary_id``.

    All conversations, messages, bookings, calls, tasks, activities and revenue
    records are re-pointed at the primary lead.  The duplicate is archived (not
    deleted) and both leads keep an audit trail, so the merge is reversible by
    an administrator.
    """
    actor.require(Perm.LEAD_MERGE)
    if primary_id == duplicate_id:
        raise LeadError("merge_same_lead")
    with session_scope() as session:
        primary = session.get(Lead, primary_id)
        duplicate = session.get(Lead, duplicate_id)
        if primary is None or duplicate is None:
            raise LeadError("lead_not_found")
        if duplicate.is_archived:
            raise LeadError("lead_already_merged")

        for model in (Conversation, Message, Booking, Call, Task, LeadActivity, RevenueRecord):
            rows = (
                session.execute(select(model).where(model.lead_id == duplicate_id)).scalars().all()
            )
            for row in rows:
                row.lead_id = primary_id

        primary.full_name = primary.full_name or duplicate.full_name
        primary.phone = primary.phone or duplicate.phone
        primary.email = primary.email or duplicate.email
        primary.telegram_username = primary.telegram_username or duplicate.telegram_username
        primary.interest = primary.interest or duplicate.interest
        primary.service_id = primary.service_id or duplicate.service_id
        primary.branch_id = primary.branch_id or duplicate.branch_id
        primary.source_id = primary.source_id or duplicate.source_id
        primary.campaign_id = primary.campaign_id or duplicate.campaign_id
        primary.utm_source = primary.utm_source or duplicate.utm_source
        primary.utm_campaign = primary.utm_campaign or duplicate.utm_campaign
        primary.score = max(primary.score, duplicate.score)
        primary.intent = intent_for_score(primary.score)
        primary.revenue = (primary.revenue or 0) + (duplicate.revenue or 0)
        primary.do_not_contact = primary.do_not_contact or duplicate.do_not_contact
        if duplicate.notes:
            primary.notes = f"{primary.notes}\n[merge #{duplicate_id}] {duplicate.notes}".strip()
        for tag in duplicate.tags:
            if tag not in primary.tags:
                primary.tags.append(tag)

        duplicate.is_archived = True
        duplicate.archived_at = now()
        duplicate.merged_into_id = primary_id
        session.flush()

        add_activity(
            session,
            primary,
            kind="merged",
            title=f"Lead #{duplicate_id} birlashtirildi",
            old_value=str(duplicate_id),
            new_value=str(primary_id),
            user_id=actor.id,
        )
        audit_service.record(
            session,
            action="lead_merged",
            entity_type="lead",
            entity_id=primary_id,
            entity_label=primary.display_name,
            old_value=f"duplicate={duplicate_id}",
            new_value=f"primary={primary_id}",
            detail="Reversible: duplicate archived with merged_into_id",
            user_id=actor.id,
            username=actor.username,
        )
        return primary


def unmerge_lead(duplicate_id: int, *, actor: CurrentUser) -> Lead:
    """Restore a previously merged lead (audit trail keeps the operation traceable)."""
    actor.require(Perm.LEAD_MERGE)
    with session_scope() as session:
        duplicate = session.get(Lead, duplicate_id)
        if duplicate is None or duplicate.merged_into_id is None:
            raise LeadError("lead_not_merged")
        primary_id = duplicate.merged_into_id
        duplicate.is_archived = False
        duplicate.archived_at = None
        duplicate.merged_into_id = None
        session.flush()
        audit_service.record(
            session,
            action="lead_unmerged",
            entity_type="lead",
            entity_id=duplicate_id,
            entity_label=duplicate.display_name,
            old_value=f"primary={primary_id}",
            user_id=actor.id,
            username=actor.username,
        )
        return duplicate


# --------------------------------------------------------------------------- #
# Aggregates for the workspace header
# --------------------------------------------------------------------------- #
def status_counts(actor: CurrentUser | None = None) -> dict[str, int]:
    """Lead counts per status within the actor's scope."""
    with session_scope() as session:
        return LeadRepository(session).status_counts(_scope_filter(LeadFilter(), actor))


def hot_leads(limit: int = 20) -> list[Lead]:
    """Currently hot leads."""
    with session_scope() as session:
        return LeadRepository(session).hot_leads(HOT_THRESHOLD, limit)


def open_lead_count(actor: CurrentUser | None = None) -> int:
    """Number of leads still in the pipeline."""
    counts = status_counts(actor)
    return sum(v for k, v in counts.items() if k not in CLOSED_STATUSES)
