"""Lead scoring rules."""

from __future__ import annotations

import pytest

from app.database.engine import session_scope
from app.models.enums import IntentLevel
from app.services import lead_service


def _score(text: str, **kwargs) -> tuple[int, list[str]]:
    """Helper running the scoring engine on one message."""
    with session_scope() as session:
        return lead_service.score_message(session, text, **kwargs)


def test_service_interest_adds_points() -> None:
    """A concrete service mention is worth +20."""
    delta, reasons = _score("Dermatolog qabuliga yozilmoqchiman")
    assert "service_interest" in reasons
    assert delta >= 20


def test_price_question_adds_points() -> None:
    """Asking for the price is worth +15."""
    delta, reasons = _score("Narxi qancha?")
    assert "price_or_time" in reasons
    assert delta >= 15


def test_phone_provided_adds_points() -> None:
    """Leaving a phone number is worth +15."""
    delta, reasons = _score("Mana raqamim", phone_provided=True)
    assert "phone_provided" in reasons
    assert delta == 15


def test_booking_request_is_the_strongest_signal() -> None:
    """Asking to be booked is worth +30."""
    delta, reasons = _score("Iltimos meni yozing")
    assert "booking_request" in reasons
    assert delta >= 30


def test_negative_reply_subtracts_points() -> None:
    """A negative answer costs -20."""
    delta, reasons = _score("Kerak emas, qiziqmayman")
    assert "negative_reply" in reasons
    assert delta < 0


def test_urgency_words_add_points() -> None:
    """Urgency words are worth +15."""
    delta, reasons = _score("Bugun kelsam bo'ladimi?")
    assert "urgency" in reasons


def test_silence_penalty_applies_after_an_hour() -> None:
    """Long silence costs -10."""
    delta, reasons = _score("ok", silent_minutes=120)
    assert "silence_penalty" in reasons


def test_russian_keywords_are_recognised() -> None:
    """Russian messages are scored with the same rules."""
    delta, reasons = _score("Сколько стоит приём дерматолога?")
    assert "price_or_time" in reasons
    assert delta >= 15


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, IntentLevel.COLD),
        (39, IntentLevel.COLD),
        (40, IntentLevel.WARM),
        (69, IntentLevel.WARM),
        (70, IntentLevel.HOT),
        (100, IntentLevel.HOT),
    ],
)
def test_intent_thresholds(score: int, expected: str) -> None:
    """Score → intent mapping follows the configured thresholds."""
    assert lead_service.intent_for_score(score) == expected


def test_apply_score_clamps_between_zero_and_hundred(admin) -> None:
    """The stored score never leaves the 0..100 range."""
    lead = lead_service.create_lead(actor=admin, full_name="Score Test", phone="+998901010101")
    with session_scope() as session:
        fresh = session.get(type(lead), lead.id)
        change = lead_service.apply_score(session, fresh, 500)
        assert change.total == 100
        change = lead_service.apply_score(session, fresh, -500)
        assert change.total == 0
        assert change.intent == IntentLevel.COLD
