"""Telephony: placing calls, transcription and AI call analysis."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.crm import Lead
from app.models.enums import (
    CallDirection,
    CallOutcome,
    LeadStatus,
    NotificationLevel,
    Sentiment,
    TaskPriority,
    TaskType,
)
from app.models.enums import (
    Permission as Perm,
)
from app.models.operations import Call, CallAnalysis, CallTranscript
from app.services import audit_service, lead_service, notification_service
from app.services.auth_service import CurrentUser
from app.utils.dates import end_of_day, now, start_of_day

logger = logging.getLogger(__name__)

#: Score delta applied per call outcome.
OUTCOME_SCORES: dict[str, int] = {
    CallOutcome.NO_ANSWER: -5,
    CallOutcome.CALLBACK: 5,
    CallOutcome.INTERESTED: 15,
    CallOutcome.BOOKED: 30,
    CallOutcome.TOO_EXPENSIVE: -10,
    CallOutcome.WRONG_NUMBER: -20,
    CallOutcome.SOLD: 30,
    CallOutcome.REFUSED: -20,
}


class CallError(Exception):
    """Call rule violation (``code`` is an i18n key)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def place_call(lead_id: int, *, actor: CurrentUser) -> Call:
    """Place an outbound call through the telephony adapter and analyse it."""
    actor.require(Perm.CALL_MANAGE)
    from app.services import integration_service

    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise CallError("lead_not_found")
        if not lead.phone:
            raise CallError("lead_has_no_phone")
        if lead.do_not_contact:
            raise CallError("lead_opted_out")

        adapter = integration_service.telephony_adapter()
        result = adapter.place_call(lead.phone)
        if not result.ok:
            raise CallError("call_failed", result.message)

        payload = result.data.get("call")
        started = getattr(payload, "started_at", now())
        duration = int(getattr(payload, "duration_seconds", 0) or 0)
        outcome = getattr(payload, "outcome", CallOutcome.NO_ANSWER)
        transcript_text = getattr(payload, "transcript_text", "")

        call = Call(
            lead_id=lead.id,
            operator_id=actor.id,
            direction=CallDirection.OUTBOUND,
            phone=lead.phone,
            provider=adapter.provider,
            external_id=str(result.data.get("external_id", "")),
            started_at=started,
            ended_at=started + timedelta(seconds=duration),
            duration_seconds=duration,
            outcome=outcome,
        )
        session.add(call)
        session.flush()

        if transcript_text:
            session.add(
                CallTranscript(
                    call_id=call.id,
                    provider=integration_service.transcriber().provider,
                    language=lead.language if lead.language in ("uz", "ru") else "uz",
                    text=transcript_text,
                    confidence=0.95,
                )
            )
            session.flush()
            analyze_call(call.id, session=session)

        _apply_outcome(session, call, lead, outcome, actor)
        audit_service.record(
            session,
            action="call_placed",
            entity_type="call",
            entity_id=call.id,
            entity_label=lead.display_name,
            new_value=outcome,
            user_id=actor.id,
            username=actor.username,
        )
        return call


def log_manual_call(
    *,
    lead_id: int,
    actor: CurrentUser,
    direction: str = CallDirection.OUTBOUND,
    duration_seconds: int = 0,
    outcome: str = CallOutcome.NO_ANSWER,
    note: str = "",
    started_at: datetime | None = None,
    recording_path: str = "",
) -> Call:
    """Register a call that happened outside the system."""
    actor.require(Perm.CALL_MANAGE)
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise CallError("lead_not_found")
        start = started_at or now()
        call = Call(
            lead_id=lead.id,
            operator_id=actor.id,
            direction=direction,
            phone=lead.phone or "",
            provider="manual",
            started_at=start,
            ended_at=start + timedelta(seconds=duration_seconds),
            duration_seconds=duration_seconds,
            outcome=outcome,
            note=note,
            recording_path=recording_path,
        )
        session.add(call)
        session.flush()
        _apply_outcome(session, call, lead, outcome, actor)
        audit_service.record(
            session,
            action="call_logged",
            entity_type="call",
            entity_id=call.id,
            entity_label=lead.display_name,
            new_value=outcome,
            user_id=actor.id,
            username=actor.username,
        )
        return call


def _apply_outcome(
    session: Session, call: Call, lead: Lead, outcome: str, actor: CurrentUser
) -> None:
    """Apply score, status and follow-up rules linked to a call outcome."""
    from app.services import task_service

    delta = OUTCOME_SCORES.get(outcome, 0)
    change = lead_service.apply_score(session, lead, delta, reasons=[f"call:{outcome}"])
    call.score_delta = change.delta
    lead_service.add_activity(
        session,
        lead,
        kind="call",
        title=f"Qo'ng'iroq: {outcome}",
        detail=call.note,
        user_id=actor.id,
    )
    if outcome == CallOutcome.CALLBACK:
        if lead.status not in (LeadStatus.WON, LeadStatus.LOST):
            lead.status = LeadStatus.CALLBACK
        task_service.create_task(
            session=session,
            lead_id=lead.id,
            assignee_id=lead.owner_id or actor.id,
            task_type=TaskType.CALL_BACK,
            title=f"Qayta qo'ng'iroq: {lead.display_name}",
            due_at=now() + timedelta(hours=4),
            auto_rule="call_callback",
        )
    if outcome == CallOutcome.WRONG_NUMBER:
        lead.phone = None
    if outcome == CallOutcome.NO_ANSWER:
        task_service.create_task(
            session=session,
            lead_id=lead.id,
            assignee_id=lead.owner_id or actor.id,
            task_type=TaskType.CALL_BACK,
            title=f"Javob bermadi — qayta urinish: {lead.display_name}",
            due_at=now() + timedelta(hours=2),
            auto_rule="call_no_answer",
        )
    session.flush()


def transcribe_call(call_id: int, *, actor: CurrentUser) -> CallTranscript:
    """Run speech-to-text on the call recording."""
    actor.require(Perm.CALL_MANAGE)
    from app.services import integration_service

    with session_scope() as session:
        call = session.get(Call, call_id)
        if call is None:
            raise CallError("call_not_found")
        if not call.recording_path:
            raise CallError("call_has_no_recording")
        adapter = integration_service.transcriber()
        lead = session.get(Lead, call.lead_id) if call.lead_id else None
        language = lead.language if lead and lead.language in ("uz", "ru") else "uz"
        result = adapter.transcribe(call.recording_path, language)
        if not result.ok:
            raise CallError("transcription_failed", result.message)
        transcript = call.transcript or CallTranscript(call_id=call.id)
        transcript.provider = adapter.provider
        transcript.language = language
        transcript.text = str(result.data.get("text", ""))
        transcript.confidence = float(result.data.get("confidence", 0.0))
        session.add(transcript)
        session.flush()
        return transcript


def analyze_call(call_id: int, *, session: Session | None = None) -> CallAnalysis:
    """Analyse the transcript and store the structured result."""
    from app.services import integration_service, task_service

    def _analyze(db: Session) -> CallAnalysis:
        call = db.get(Call, call_id)
        if call is None:
            raise CallError("call_not_found")
        transcript = db.execute(
            select(CallTranscript).where(CallTranscript.call_id == call_id)
        ).scalar_one_or_none()
        if transcript is None or not transcript.text:
            raise CallError("call_has_no_transcript")

        provider = integration_service.llm_provider()
        try:
            data = provider.analyze_call(transcript.text, transcript.language)
        except Exception as exc:
            logger.warning("Call analysis via %s failed: %s", provider.provider, type(exc).__name__)
            data = integration_service.demo_llm().analyze_call(transcript.text, transcript.language)
        if not data:
            data = integration_service.demo_llm().analyze_call(transcript.text, transcript.language)

        analysis = db.execute(
            select(CallAnalysis).where(CallAnalysis.call_id == call_id)
        ).scalar_one_or_none() or CallAnalysis(call_id=call_id)
        analysis.summary = str(data.get("summary", ""))
        analysis.customer_need = str(data.get("customer_need", ""))
        analysis.objections = str(data.get("objections", ""))
        analysis.operator_mistakes = str(data.get("operator_mistakes", ""))
        analysis.next_best_action = str(data.get("next_best_action", ""))
        analysis.sentiment = str(data.get("sentiment", Sentiment.NEUTRAL))
        analysis.quality_score = int(data.get("quality_score", 0) or 0)
        analysis.got_phone = bool(data.get("got_phone"))
        analysis.got_purpose = bool(data.get("got_purpose"))
        analysis.got_booking = bool(data.get("got_booking"))
        analysis.alert_raised = bool(data.get("alert_raised"))
        db.add(analysis)
        db.flush()

        if analysis.alert_raised:
            lead = db.get(Lead, call.lead_id) if call.lead_id else None
            notification_service.push(
                db,
                title="Salbiy qo'ng'iroq — rahbar e'tibori kerak",
                body=f"{lead.display_name if lead else 'Lead'}: {analysis.summary[:120]}",
                level=NotificationLevel.CRITICAL,
                category="call_alert",
                lead_id=call.lead_id,
            )
            if lead is not None:
                task_service.create_task(
                    session=db,
                    lead_id=lead.id,
                    assignee_id=lead.owner_id,
                    task_type=TaskType.MANAGER_APPROVAL,
                    title=f"Salbiy qo'ng'iroqni ko'rib chiqish: {lead.display_name}",
                    priority=TaskPriority.CRITICAL,
                    due_at=now() + timedelta(hours=1),
                    auto_rule="negative_call_review",
                )
        return analysis

    if session is not None:
        return _analyze(session)
    with session_scope() as db:
        return _analyze(db)


def update_call(
    call_id: int,
    *,
    actor: CurrentUser,
    outcome: str | None = None,
    note: str | None = None,
    recording_path: str | None = None,
) -> Call:
    """Edit a call record."""
    actor.require(Perm.CALL_MANAGE)
    with session_scope() as session:
        call = session.get(Call, call_id)
        if call is None:
            raise CallError("call_not_found")
        old = call.outcome
        if outcome is not None and outcome != call.outcome:
            call.outcome = outcome
            lead = session.get(Lead, call.lead_id) if call.lead_id else None
            if lead is not None:
                _apply_outcome(session, call, lead, outcome, actor)
        if note is not None:
            call.note = note
        if recording_path is not None:
            call.recording_path = recording_path
        session.flush()
        audit_service.record(
            session,
            action="call_updated",
            entity_type="call",
            entity_id=call.id,
            old_value=old,
            new_value=call.outcome,
            user_id=actor.id,
            username=actor.username,
        )
        return call


def list_calls(
    *,
    actor: CurrentUser | None = None,
    search: str = "",
    outcomes: list[str] | None = None,
    operator_id: int | None = None,
    direction: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    sentiment: str = "",
    limit: int = 500,
) -> list[Call]:
    """Filtered call list."""
    with session_scope() as session:
        stmt = select(Call).where(Call.is_archived.is_(False))
        if outcomes:
            stmt = stmt.where(Call.outcome.in_(outcomes))
        if operator_id:
            stmt = stmt.where(Call.operator_id == operator_id)
        elif actor is not None and not actor.can(Perm.LEAD_VIEW_ALL):
            stmt = stmt.where(Call.operator_id == actor.id)
        if direction:
            stmt = stmt.where(Call.direction == direction)
        if date_from:
            stmt = stmt.where(Call.started_at >= start_of_day(date_from))
        if date_to:
            stmt = stmt.where(Call.started_at <= end_of_day(date_to))
        if sentiment:
            stmt = stmt.join(CallAnalysis, CallAnalysis.call_id == Call.id).where(
                CallAnalysis.sentiment == sentiment
            )
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.join(Lead, Lead.id == Call.lead_id).where(
                or_(Lead.full_name.ilike(pattern), Call.phone.ilike(pattern))
            )
        stmt = stmt.order_by(Call.started_at.desc()).limit(limit)
        return list(session.execute(stmt).scalars().unique().all())


def get_call_detail(call_id: int) -> tuple[Call | None, CallTranscript | None, CallAnalysis | None]:
    """Load a call together with its transcript and analysis."""
    with session_scope() as session:
        call = session.get(Call, call_id)
        if call is None:
            return None, None, None
        transcript = session.execute(
            select(CallTranscript).where(CallTranscript.call_id == call_id)
        ).scalar_one_or_none()
        analysis = session.execute(
            select(CallAnalysis).where(CallAnalysis.call_id == call_id)
        ).scalar_one_or_none()
        return call, transcript, analysis


def calls_for_lead(lead_id: int) -> list[Call]:
    """Calls belonging to one lead."""
    with session_scope() as session:
        stmt = (
            select(Call)
            .where(Call.lead_id == lead_id, Call.is_archived.is_(False))
            .order_by(Call.started_at.desc())
        )
        return list(session.execute(stmt).scalars().unique().all())
