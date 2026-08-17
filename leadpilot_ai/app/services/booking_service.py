"""Bookings: conflict-free scheduling, confirmations and reminders."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.crm import Lead
from app.models.enums import (
    BookingPurpose,
    BookingStatus,
    LeadStatus,
    NotificationLevel,
    TaskType,
)
from app.models.enums import (
    Permission as Perm,
)
from app.models.operations import Booking, ScheduleSlot
from app.models.organization import Branch, Company, Service
from app.services import audit_service, lead_service, notification_service
from app.services.auth_service import CurrentUser
from app.utils.dates import end_of_day, fmt_datetime, now, parse_hhmm, start_of_day

logger = logging.getLogger(__name__)

#: Booking statuses that still occupy a time slot.
BLOCKING_STATUSES = {
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.ARRIVED,
}


class BookingError(Exception):
    """Booking rule violation (``code`` is an i18n key)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- #
# Conflict detection
# --------------------------------------------------------------------------- #
def find_conflicts(
    session: Session,
    *,
    starts_at: datetime,
    ends_at: datetime,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    exclude_id: int | None = None,
) -> list[Booking]:
    """Return bookings overlapping the requested interval for the same resource."""
    stmt = select(Booking).where(
        Booking.is_archived.is_(False),
        Booking.status.in_(list(BLOCKING_STATUSES)),
        Booking.starts_at < ends_at,
        Booking.ends_at > starts_at,
    )
    resource_clauses = []
    if specialist_id:
        resource_clauses.append(Booking.specialist_id == specialist_id)
    if branch_id and not specialist_id:
        resource_clauses.append(Booking.branch_id == branch_id)
    if resource_clauses:
        stmt = stmt.where(or_(*resource_clauses))
    if exclude_id:
        stmt = stmt.where(Booking.id != exclude_id)
    return list(session.execute(stmt).scalars().unique().all())


def has_conflict(
    session: Session,
    *,
    starts_at: datetime,
    ends_at: datetime,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    exclude_id: int | None = None,
) -> bool:
    """Whether the requested interval is already taken."""
    return bool(
        find_conflicts(
            session,
            starts_at=starts_at,
            ends_at=ends_at,
            branch_id=branch_id,
            specialist_id=specialist_id,
            exclude_id=exclude_id,
        )
    )


def free_slots(
    session: Session,
    *,
    day: date | None = None,
    days_ahead: int = 3,
    duration_minutes: int = 30,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    limit: int = 8,
) -> list[datetime]:
    """Return the next free appointment slots the AI is allowed to offer."""
    start_day = day or now().date()
    company = session.execute(select(Company)).scalars().first()
    default_start = parse_hhmm(company.work_start if company else "09:00")
    default_end = parse_hhmm(company.work_end if company else "19:00")
    work_days = (
        {int(x) for x in (company.work_days or "1,2,3,4,5,6").split(",") if x.strip().isdigit()}
        if company
        else {1, 2, 3, 4, 5, 6}
    )

    branch = session.get(Branch, branch_id) if branch_id else None
    if branch is not None:
        default_start = parse_hhmm(branch.work_start)
        default_end = parse_hhmm(branch.work_end)

    templates = list(
        session.execute(select(ScheduleSlot).where(ScheduleSlot.is_active.is_(True)))
        .scalars()
        .all()
    )

    result: list[datetime] = []
    current = now()
    for offset in range(days_ahead + 1):
        current_day = start_day + timedelta(days=offset)
        weekday = current_day.isoweekday()
        if weekday not in work_days:
            continue
        day_start, day_end = default_start, default_end
        for template in templates:
            matches_branch = template.branch_id in (None, branch_id)
            matches_specialist = template.specialist_id in (None, specialist_id)
            if template.weekday == weekday and matches_branch and matches_specialist:
                day_start = parse_hhmm(template.start_time)
                day_end = parse_hhmm(template.end_time)
                break
        cursor = datetime.combine(current_day, day_start)
        limit_dt = datetime.combine(current_day, day_end)
        while cursor + timedelta(minutes=duration_minutes) <= limit_dt:
            slot_end = cursor + timedelta(minutes=duration_minutes)
            if cursor > current and not has_conflict(
                session,
                starts_at=cursor,
                ends_at=slot_end,
                branch_id=branch_id,
                specialist_id=specialist_id,
            ):
                result.append(cursor)
                if len(result) >= limit:
                    return result
            cursor = slot_end
    return result


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def create_booking(
    *,
    lead_id: int,
    starts_at: datetime,
    duration_minutes: int = 30,
    service_id: int | None = None,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    purpose: str = BookingPurpose.GENERAL_MEETING,
    note: str = "",
    created_channel: str = "manual",
    created_by_ai: bool = False,
    actor: CurrentUser | None = None,
    send_confirmation: bool = True,
    session: Session | None = None,
) -> Booking:
    """Create a booking, refusing overlapping slots."""

    def _create(db: Session) -> Booking:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise BookingError("lead_not_found")
        if starts_at < now() - timedelta(minutes=1):
            raise BookingError("booking_in_past")
        service = db.get(Service, service_id) if service_id else None
        minutes = duration_minutes or (service.duration_minutes if service else 30)
        ends_at = starts_at + timedelta(minutes=minutes)
        if has_conflict(
            db,
            starts_at=starts_at,
            ends_at=ends_at,
            branch_id=branch_id or lead.branch_id,
            specialist_id=specialist_id,
        ):
            raise BookingError("booking_conflict", fmt_datetime(starts_at))

        booking = Booking(
            lead_id=lead_id,
            service_id=service_id or lead.service_id,
            branch_id=branch_id or lead.branch_id,
            specialist_id=specialist_id,
            purpose=purpose,
            starts_at=starts_at,
            ends_at=ends_at,
            duration_minutes=minutes,
            status=BookingStatus.PENDING,
            created_channel=created_channel,
            created_by_ai=created_by_ai,
            note=note,
            created_by_id=actor.id if actor else None,
        )
        db.add(booking)
        db.flush()

        if lead.status in (
            LeadStatus.NEW,
            LeadStatus.AI_CONVERSATION,
            LeadStatus.WAITING_OPERATOR,
            LeadStatus.OPERATOR_WORKING,
            LeadStatus.CALLBACK,
        ):
            lead.status = LeadStatus.BOOKED
        lead_service.apply_score(db, lead, 30, reasons=["booking_created"])
        lead_service.add_activity(
            db,
            lead,
            kind="booking_created",
            title=f"Bron yaratildi: {fmt_datetime(starts_at)}",
            detail=note,
            user_id=actor.id if actor else None,
        )
        audit_service.record(
            db,
            action="booking_created",
            entity_type="booking",
            entity_id=booking.id,
            entity_label=f"{lead.display_name} {fmt_datetime(starts_at)}",
            new_value=str(starts_at),
            user_id=actor.id if actor else None,
            username=actor.username if actor else "ai",
        )
        notification_service.push(
            db,
            title="Yangi bron",
            body=f"{lead.display_name} — {fmt_datetime(starts_at)}",
            level=NotificationLevel.SUCCESS,
            category="booking",
            lead_id=lead.id,
            user_id=lead.owner_id,
        )
        if send_confirmation:
            _queue_confirmation(db, booking, lead)
        return booking

    if session is not None:
        return _create(session)
    with session_scope() as db:
        return _create(db)


def _queue_confirmation(session: Session, booking: Booking, lead: Lead) -> None:
    """Send the customer a confirmation message and schedule a reminder task."""
    from app.services import task_service

    text_uz = (
        f"Bronigiz qabul qilindi: {fmt_datetime(booking.starts_at)}. "
        "Tasdiqlash uchun javob yozing yoki operatorimiz bog'lanadi."
    )
    text_ru = (
        f"Ваша запись принята: {fmt_datetime(booking.starts_at)}. "
        "Напишите для подтверждения или оператор свяжется с вами."
    )
    body = text_ru if lead.language == "ru" else text_uz
    sent = _send_customer_message(session, lead, body)
    if sent:
        booking.confirmation_sent_at = now()
    task_service.create_task(
        session=session,
        lead_id=lead.id,
        booking_id=booking.id,
        assignee_id=lead.owner_id,
        task_type=TaskType.CONFIRM_BOOKING,
        title=f"Bronni tasdiqlash: {fmt_datetime(booking.starts_at)}",
        due_at=min(booking.starts_at - timedelta(hours=24), now() + timedelta(hours=2)),
        auto_rule="booking_confirmation",
    )


def _send_customer_message(session: Session, lead: Lead, text: str) -> bool:
    """Deliver a system message to the lead's most recent conversation."""
    from app.models.enums import MessageDirection, MessageSender, MessageStatus
    from app.models.messaging import Conversation, Message
    from app.services import integration_service

    allowed, _ = lead_service.may_send_message(lead)
    if not allowed:
        return False
    conversation = (
        session.execute(
            select(Conversation)
            .where(Conversation.lead_id == lead.id)
            .order_by(Conversation.last_message_at.desc().nullslast())
        )
        .scalars()
        .first()
    )
    if conversation is None:
        return False
    adapter = integration_service.channel_adapter(conversation.channel)
    result = adapter.send_message(conversation.external_chat_id or str(lead.id), text)
    session.add(
        Message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            direction=MessageDirection.OUTBOUND,
            sender=MessageSender.SYSTEM,
            channel=conversation.channel,
            body=text,
            status=MessageStatus.SENT if result.ok else MessageStatus.FAILED,
            error_text="" if result.ok else result.message,
            created_at=now(),
        )
    )
    conversation.last_message_at = now()
    conversation.last_message_preview = text[:120]
    session.flush()
    return result.ok


def update_booking(
    booking_id: int,
    *,
    actor: CurrentUser,
    starts_at: datetime | None = None,
    duration_minutes: int | None = None,
    service_id: int | None = None,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    purpose: str | None = None,
    note: str | None = None,
) -> Booking:
    """Reschedule or edit a booking (conflict checked again)."""
    actor.require(Perm.BOOKING_MANAGE)
    with session_scope() as session:
        booking = session.get(Booking, booking_id)
        if booking is None:
            raise BookingError("booking_not_found")
        old = fmt_datetime(booking.starts_at)
        new_start = starts_at or booking.starts_at
        minutes = duration_minutes or booking.duration_minutes
        new_end = new_start + timedelta(minutes=minutes)
        if has_conflict(
            session,
            starts_at=new_start,
            ends_at=new_end,
            branch_id=branch_id if branch_id is not None else booking.branch_id,
            specialist_id=specialist_id if specialist_id is not None else booking.specialist_id,
            exclude_id=booking.id,
        ):
            raise BookingError("booking_conflict", fmt_datetime(new_start))
        booking.starts_at = new_start
        booking.ends_at = new_end
        booking.duration_minutes = minutes
        if service_id is not None:
            booking.service_id = service_id
        if branch_id is not None:
            booking.branch_id = branch_id
        if specialist_id is not None:
            booking.specialist_id = specialist_id
        if purpose is not None:
            booking.purpose = purpose
        if note is not None:
            booking.note = note
        session.flush()
        audit_service.record(
            session,
            action="booking_updated",
            entity_type="booking",
            entity_id=booking.id,
            entity_label=str(booking.lead_id),
            old_value=old,
            new_value=fmt_datetime(new_start),
            user_id=actor.id,
            username=actor.username,
        )
        return booking


def change_status(booking_id: int, status: str, *, actor: CurrentUser, reason: str = "") -> Booking:
    """Change the booking status and trigger the linked business rules."""
    actor.require(Perm.BOOKING_MANAGE)
    from app.services import task_service

    with session_scope() as session:
        booking = session.get(Booking, booking_id)
        if booking is None:
            raise BookingError("booking_not_found")
        old = booking.status
        booking.status = status
        lead = session.get(Lead, booking.lead_id)
        if status == BookingStatus.CONFIRMED:
            booking.confirmed_at = now()
        if status == BookingStatus.CANCELLED:
            booking.cancelled_reason = reason
        if lead is not None:
            if status == BookingStatus.ARRIVED and lead.status == LeadStatus.BOOKED:
                lead.status = LeadStatus.ARRIVED
            if status == BookingStatus.NO_SHOW:
                task_service.create_task(
                    session=session,
                    lead_id=lead.id,
                    booking_id=booking.id,
                    assignee_id=lead.owner_id,
                    task_type=TaskType.NO_SHOW_FOLLOWUP,
                    title=f"Kelmagan mijoz bilan bog'lanish: {lead.display_name}",
                    due_at=now() + timedelta(hours=2),
                    auto_rule="no_show_followup",
                )
                lead_service.apply_score(session, lead, -10, reasons=["no_show"])
            lead_service.add_activity(
                session,
                lead,
                kind="booking_status",
                title=f"Bron statusi: {old} → {status}",
                detail=reason,
                user_id=actor.id,
            )
        audit_service.record(
            session,
            action="booking_status_changed",
            entity_type="booking",
            entity_id=booking.id,
            old_value=old,
            new_value=status,
            user_id=actor.id,
            username=actor.username,
        )
        return booking


def cancel_booking(booking_id: int, reason: str, *, actor: CurrentUser) -> Booking:
    """Cancel a booking with a mandatory reason."""
    if not reason.strip():
        raise BookingError("cancel_reason_required")
    return change_status(booking_id, BookingStatus.CANCELLED, actor=actor, reason=reason)


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #
def list_bookings(
    *,
    day_from: date | None = None,
    day_to: date | None = None,
    statuses: list[str] | None = None,
    branch_id: int | None = None,
    specialist_id: int | None = None,
    service_id: int | None = None,
    search: str = "",
    limit: int = 500,
) -> list[Booking]:
    """Filtered booking list used by the calendar and the reports."""
    with session_scope() as session:
        stmt = select(Booking).where(Booking.is_archived.is_(False))
        if day_from:
            stmt = stmt.where(Booking.starts_at >= start_of_day(day_from))
        if day_to:
            stmt = stmt.where(Booking.starts_at <= end_of_day(day_to))
        if statuses:
            stmt = stmt.where(Booking.status.in_(statuses))
        if branch_id:
            stmt = stmt.where(Booking.branch_id == branch_id)
        if specialist_id:
            stmt = stmt.where(Booking.specialist_id == specialist_id)
        if service_id:
            stmt = stmt.where(Booking.service_id == service_id)
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.join(Lead, Lead.id == Booking.lead_id).where(
                or_(Lead.full_name.ilike(pattern), Lead.phone.ilike(pattern))
            )
        stmt = stmt.order_by(Booking.starts_at.asc()).limit(limit)
        return list(session.execute(stmt).scalars().unique().all())


def bookings_for_day(day: date) -> list[Booking]:
    """All bookings of one calendar day."""
    return list_bookings(day_from=day, day_to=day)


def bookings_for_lead(lead_id: int) -> list[Booking]:
    """Bookings belonging to one lead, newest first."""
    with session_scope() as session:
        stmt = (
            select(Booking)
            .where(Booking.lead_id == lead_id, Booking.is_archived.is_(False))
            .order_by(Booking.starts_at.desc())
        )
        return list(session.execute(stmt).scalars().unique().all())


def upcoming_reminders(hours: int = 24) -> list[Booking]:
    """Confirmed bookings that need a reminder within ``hours``."""
    with session_scope() as session:
        horizon = now() + timedelta(hours=hours)
        stmt = select(Booking).where(
            Booking.is_archived.is_(False),
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            Booking.starts_at <= horizon,
            Booking.starts_at > now(),
            Booking.reminder_sent_at.is_(None),
        )
        return list(session.execute(stmt).scalars().unique().all())


def send_reminders(hours: int = 24) -> int:
    """Send reminder messages for upcoming bookings; returns how many were sent."""
    sent = 0
    with session_scope() as session:
        horizon = now() + timedelta(hours=hours)
        stmt = select(Booking).where(
            Booking.is_archived.is_(False),
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            and_(Booking.starts_at <= horizon, Booking.starts_at > now()),
            Booking.reminder_sent_at.is_(None),
        )
        for booking in session.execute(stmt).scalars().unique().all():
            lead = session.get(Lead, booking.lead_id)
            if lead is None:
                continue
            text = (
                f"Напоминание: ваша запись {fmt_datetime(booking.starts_at)}."
                if lead.language == "ru"
                else f"Eslatma: bronigiz {fmt_datetime(booking.starts_at)}."
            )
            if _send_customer_message(session, lead, text):
                booking.reminder_sent_at = now()
                sent += 1
    return sent


def mark_missed_bookings() -> int:
    """Mark past unconfirmed bookings as no-show; returns the number updated."""
    from app.services import task_service

    updated = 0
    with session_scope() as session:
        stmt = select(Booking).where(
            Booking.is_archived.is_(False),
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            Booking.ends_at < now() - timedelta(hours=1),
        )
        for booking in session.execute(stmt).scalars().unique().all():
            booking.status = BookingStatus.NO_SHOW
            lead = session.get(Lead, booking.lead_id)
            if lead is not None:
                task_service.create_task(
                    session=session,
                    lead_id=lead.id,
                    booking_id=booking.id,
                    assignee_id=lead.owner_id,
                    task_type=TaskType.NO_SHOW_FOLLOWUP,
                    title=f"Kelmagan mijoz: {lead.display_name}",
                    due_at=now() + timedelta(hours=2),
                    auto_rule="no_show_auto",
                )
            updated += 1
    return updated
