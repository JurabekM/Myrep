"""Lead status transitions and the rules attached to them."""

from __future__ import annotations

import pytest

from app.models.enums import LeadStatus, LossReason
from app.services import lead_service


def test_new_to_ai_conversation_is_allowed() -> None:
    """The happy path transition is permitted."""
    assert lead_service.can_transition(LeadStatus.NEW, LeadStatus.AI_CONVERSATION)


def test_new_to_won_is_rejected() -> None:
    """A lead cannot jump straight from NEW to WON."""
    assert not lead_service.can_transition(LeadStatus.NEW, LeadStatus.WON)


def test_lost_and_spam_are_reachable_from_anywhere() -> None:
    """Universal statuses bypass the transition table."""
    for source in (LeadStatus.NEW, LeadStatus.BOOKED, LeadStatus.OPERATOR_WORKING):
        assert lead_service.can_transition(source, LeadStatus.LOST)
        assert lead_service.can_transition(source, LeadStatus.SPAM)


def test_won_is_terminal() -> None:
    """Nothing follows a closed sale."""
    assert not lead_service.can_transition(LeadStatus.WON, LeadStatus.OPERATOR_WORKING)


def test_change_status_rejects_invalid_transition(admin) -> None:
    """The service refuses a transition the pipeline does not allow."""
    lead = lead_service.create_lead(actor=admin, full_name="Transition Test")
    with pytest.raises(lead_service.LeadError) as exc:
        lead_service.change_status(lead.id, LeadStatus.WON, actor=admin)
    assert exc.value.code == "invalid_status_transition"


def test_lost_requires_a_reason(admin) -> None:
    """Moving to LOST without a reason is refused."""
    lead = lead_service.create_lead(actor=admin, full_name="Loss Test")
    with pytest.raises(lead_service.LeadError) as exc:
        lead_service.change_status(lead.id, LeadStatus.LOST, actor=admin)
    assert exc.value.code == "loss_reason_required"

    lead_service.change_status(lead.id, LeadStatus.LOST, actor=admin, loss_reason=LossReason.PRICE)
    refreshed = lead_service.get_lead(lead.id)
    assert refreshed.status == LeadStatus.LOST
    assert refreshed.loss_reason == LossReason.PRICE
    assert refreshed.lost_at is not None


def test_won_records_revenue(admin) -> None:
    """Closing a sale stores the amount and the timestamp."""
    lead = lead_service.create_lead(actor=admin, full_name="Revenue Test")
    lead_service.change_status(lead.id, LeadStatus.OPERATOR_WORKING, actor=admin)
    lead_service.change_status(lead.id, LeadStatus.WON, actor=admin, revenue=1_250_000)
    refreshed = lead_service.get_lead(lead.id)
    assert refreshed.status == LeadStatus.WON
    assert refreshed.revenue == 1_250_000
    assert refreshed.won_at is not None


def test_status_change_is_written_to_the_timeline(admin) -> None:
    """Every transition appears in the lead timeline."""
    lead = lead_service.create_lead(actor=admin, full_name="Timeline Test")
    lead_service.change_status(lead.id, LeadStatus.WAITING_OPERATOR, actor=admin)
    kinds = [activity.kind for activity in lead_service.timeline(lead.id)]
    assert "lead_created" in kinds
    assert "status_changed" in kinds
