"""Do-Not-Contact enforcement and the AI escalation rules."""

from __future__ import annotations

import pytest

from app.database.engine import session_scope
from app.integrations.base import IncomingMessage
from app.integrations.llm.base_llm import AgentContext
from app.integrations.llm.demo_provider import DemoRuleBasedProvider
from app.models.enums import AIState, Channel, LeadStatus
from app.services import ai_agent_service, conversation_service, lead_service

PROVIDER = DemoRuleBasedProvider()


def _context(**kwargs) -> AgentContext:
    """Build a minimal agent context for the demo provider."""
    base = {
        "agent_name": "Aziza",
        "company_name": "MedLine Clinic",
        "language": "uz",
        "state": AIState.NEED_DISCOVERY,
        "services": [
            {
                "id": 1,
                "name": "Dermatolog qabuli",
                "name_ru": "Приём дерматолога",
                "price_label": "150 000",
            }
        ],
        "branches": [{"name": "Markaziy", "address": "Amir Temur 12", "hours": "09:00–19:00"}],
        "forbidden_topics": ["tashxis", "dori"],
        "free_slots": ["03.08.2026 15:00"],
    }
    base.update(kwargs)
    return AgentContext(**base)


# --------------------------------------------------------------------------- #
# Opt-out
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text",
    ["Menga boshqa yozmang", "Bezovta qilmang iltimos", "Не пишите мне больше", "Стоп"],
)
def test_opt_out_phrases_are_detected(text: str) -> None:
    """The opt-out detector recognises both languages."""
    assert lead_service.detect_opt_out(text)


def test_opt_out_message_sets_do_not_contact(admin) -> None:
    """An inbound opt-out message flips the Do-Not-Contact flag."""
    incoming = IncomingMessage(
        channel=Channel.DEMO,
        external_chat_id="optout-chat-1",
        text="Salom, dermatolog kerak edi",
        sender_name="Opt Out Test",
    )
    result = conversation_service.ingest_incoming(incoming)
    lead_id = result["lead_id"]
    conversation_service.ingest_incoming(
        IncomingMessage(
            channel=Channel.DEMO,
            external_chat_id="optout-chat-1",
            text="Menga boshqa yozmang!",
        )
    )
    assert lead_service.get_lead(lead_id).do_not_contact is True


def test_sending_to_an_opted_out_lead_is_blocked(admin) -> None:
    """Outbound messages to opted-out leads raise a business error."""
    incoming = IncomingMessage(
        channel=Channel.DEMO, external_chat_id="optout-chat-2", text="Narxi qancha?"
    )
    result = conversation_service.ingest_incoming(incoming)
    lead_service.set_do_not_contact(result["lead_id"], True, actor=admin)
    with pytest.raises(conversation_service.ConversationError) as exc:
        conversation_service.send_message(result["conversation_id"], "Salom", actor=admin)
    assert exc.value.code == "lead_opted_out"


def test_may_send_message_blocks_spam_leads(admin) -> None:
    """Leads marked as spam are excluded from outbound traffic."""
    lead = lead_service.create_lead(actor=admin, full_name="Spam Test")
    lead_service.change_status(lead.id, LeadStatus.SPAM, actor=admin)
    allowed, reason = lead_service.may_send_message(lead_service.get_lead(lead.id))
    assert not allowed
    assert reason == "lead_is_spam"


# --------------------------------------------------------------------------- #
# AI escalation
# --------------------------------------------------------------------------- #
def test_ai_escalates_when_the_customer_asks_for_a_human() -> None:
    """'I want to talk to a person' always escalates."""
    reply = PROVIDER.generate_reply(_context(), "Menga operator bilan gaplashish kerak")
    assert reply.escalate
    assert reply.next_state == AIState.HUMAN_HANDOFF


def test_ai_escalates_on_negative_sentiment() -> None:
    """Complaints go straight to a human."""
    reply = PROVIDER.generate_reply(_context(), "Xizmatingiz juda yomon, shikoyat qilaman")
    assert reply.escalate


def test_ai_escalates_on_price_negotiation() -> None:
    """Price haggling is a human decision."""
    reply = PROVIDER.generate_reply(_context(), "Bu juda qimmat, chegirma bormi?")
    assert reply.escalate
    assert reply.next_state == AIState.OBJECTION_HANDLING


def test_ai_escalates_on_forbidden_topics() -> None:
    """Medical advice is never given by the AI."""
    reply = PROVIDER.generate_reply(_context(), "Menga qanday dori ichish kerak?")
    assert reply.escalate


def test_ai_does_not_invent_an_answer() -> None:
    """Unknown questions escalate instead of hallucinating."""
    reply = PROVIDER.generate_reply(_context(), "Sizda kvant nazariyasi kursi bormi?")
    assert reply.escalate
    assert reply.confidence < 0.5


def test_ai_answers_price_from_approved_data() -> None:
    """The published price is quoted verbatim from the context."""
    reply = PROVIDER.generate_reply(_context(), "Dermatolog qabuli narxi qancha?")
    assert "150 000" in reply.text
    assert not reply.escalate


def test_ai_replies_in_the_customer_language() -> None:
    """A Russian question receives a Russian answer."""
    reply = PROVIDER.generate_reply(_context(), "Здравствуйте, сколько стоит приём дерматолога?")
    assert "сум" in reply.text or "Приём" in reply.text
    assert reply.extracted["language"] == "ru"


def test_ai_asks_for_contacts_before_booking() -> None:
    """The agent collects the required fields before creating a booking."""
    reply = PROVIDER.generate_reply(_context(), "Meni ertaga soat 15:00 ga yozing")
    assert reply.next_state == AIState.BOOKING_ATTEMPT
    assert not reply.wants_booking  # name and phone are still missing


def test_ai_confirms_booking_when_all_data_is_present() -> None:
    """With name, phone and time the agent proposes the booking."""
    context = _context(lead_name="Aziz", lead_phone="+998901112233")
    reply = PROVIDER.generate_reply(context, "Meni ertaga soat 15:00 ga yozing")
    assert reply.wants_booking


def test_escalation_policy_respects_the_message_limit() -> None:
    """Exceeding the configured auto-message limit forces a hand-off."""
    with session_scope() as session:
        profile = ai_agent_service.get_profile(session)
        profile.max_auto_messages = 2

        class _Conversation:
            ai_message_count = 5
            ai_unanswered_count = 0

        class _Lead:
            score = 10

        class _Reply:
            escalate = False
            escalation_reason = ""
            confidence = 1.0
            wants_booking = False

        escalate, reason = ai_agent_service.evaluate_escalation(
            profile, _Conversation(), _Lead(), _Reply()
        )
        assert escalate
        assert "limit" in reason.lower() or "Limit" in reason
