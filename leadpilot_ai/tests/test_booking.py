"""Booking conflicts, free slots and the linked follow-up rules."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.database.engine import session_scope
from app.models.enums import BookingStatus, LeadStatus
from app.services import booking_service, lead_service
from app.utils.dates import now


def _future(hours: int = 24) -> object:
    """Return a rounded datetime in the future."""
    return (now() + timedelta(hours=hours)).replace(minute=0, second=0, microsecond=0)


def test_booking_in_the_past_is_refused(admin) -> None:
    """A booking cannot be created for a past moment."""
    lead = lead_service.create_lead(actor=admin, full_name="Past Booking")
    with pytest.raises(booking_service.BookingError) as exc:
        booking_service.create_booking(
            lead_id=lead.id, starts_at=now() - timedelta(hours=2), actor=admin
        )
    assert exc.value.code == "booking_in_past"


def test_double_booking_of_the_same_specialist_is_refused(admin, operator) -> None:
    """Two bookings may not overlap for one specialist."""
    lead_a = lead_service.create_lead(actor=admin, full_name="Slot A")
    lead_b = lead_service.create_lead(actor=admin, full_name="Slot B")
    start = _future(300)
    booking_service.create_booking(
        lead_id=lead_a.id,
        starts_at=start,
        duration_minutes=60,
        specialist_id=operator.id,
        actor=admin,
    )
    with pytest.raises(booking_service.BookingError) as exc:
        booking_service.create_booking(
            lead_id=lead_b.id,
            starts_at=start + timedelta(minutes=30),
            duration_minutes=60,
            specialist_id=operator.id,
            actor=admin,
        )
    assert exc.value.code == "booking_conflict"


def test_adjacent_bookings_are_allowed(admin, operator) -> None:
    """A booking starting exactly when the previous one ends is fine."""
    lead_a = lead_service.create_lead(actor=admin, full_name="Adjacent A")
    lead_b = lead_service.create_lead(actor=admin, full_name="Adjacent B")
    start = _future(320)
    booking_service.create_booking(
        lead_id=lead_a.id,
        starts_at=start,
        duration_minutes=30,
        specialist_id=operator.id,
        actor=admin,
    )
    booking = booking_service.create_booking(
        lead_id=lead_b.id,
        starts_at=start + timedelta(minutes=30),
        duration_minutes=30,
        specialist_id=operator.id,
        actor=admin,
    )
    assert booking.id is not None


def test_cancelled_booking_frees_the_slot(admin, second_operator) -> None:
    """A cancelled booking no longer blocks its time range."""
    lead_a = lead_service.create_lead(actor=admin, full_name="Cancel A")
    lead_b = lead_service.create_lead(actor=admin, full_name="Cancel B")
    start = _future(340)
    first = booking_service.create_booking(
        lead_id=lead_a.id,
        starts_at=start,
        duration_minutes=30,
        specialist_id=second_operator.id,
        actor=admin,
    )
    booking_service.cancel_booking(first.id, "Mijoz bekor qildi", actor=admin)
    second = booking_service.create_booking(
        lead_id=lead_b.id,
        starts_at=start,
        duration_minutes=30,
        specialist_id=second_operator.id,
        actor=admin,
    )
    assert second.id != first.id


def test_free_slots_never_collide_with_existing_bookings(admin, operator) -> None:
    """A slot disappears from the offer once it is booked."""
    lead = lead_service.create_lead(actor=admin, full_name="Slots Test")
    with session_scope() as session:
        slots = booking_service.free_slots(
            session, duration_minutes=30, specialist_id=operator.id, days_ahead=5, limit=40
        )
    assert slots, "the demo schedule must offer at least one free slot"
    chosen = slots[0]
    booking_service.create_booking(
        lead_id=lead.id,
        starts_at=chosen,
        duration_minutes=30,
        specialist_id=operator.id,
        actor=admin,
    )
    with session_scope() as session:
        remaining = booking_service.free_slots(
            session, duration_minutes=30, specialist_id=operator.id, days_ahead=5, limit=40
        )
    assert chosen not in remaining


def test_booking_moves_the_lead_to_booked(admin) -> None:
    """Creating a booking advances the pipeline status."""
    lead = lead_service.create_lead(actor=admin, full_name="Status Booking")
    booking_service.create_booking(lead_id=lead.id, starts_at=_future(360), actor=admin)
    assert lead_service.get_lead(lead.id).status == LeadStatus.BOOKED


def test_no_show_creates_a_followup_task(admin) -> None:
    """Marking a no-show schedules the follow-up task."""
    from app.services import task_service

    lead = lead_service.create_lead(actor=admin, full_name="No Show Test")
    booking = booking_service.create_booking(lead_id=lead.id, starts_at=_future(380), actor=admin)
    booking_service.change_status(booking.id, BookingStatus.NO_SHOW, actor=admin)
    tasks = task_service.tasks_for_lead(lead.id)
    assert any(task.auto_rule == "no_show_followup" for task in tasks)
