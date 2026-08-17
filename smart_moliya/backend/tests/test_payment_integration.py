import asyncio
from decimal import Decimal

import pytest

from app.integrations.payments.registry import get_payment_provider


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_payment_provider("unknown-provider")


def test_create_checkout_returns_session():
    provider = get_payment_provider("click")
    session = asyncio.run(
        provider.create_checkout("payment-1", Decimal("50000"), "smartmoliya://result")
    )
    assert session.external_id == "click-payment-1"
    assert "mock-click" in session.checkout_url
    assert "50000" in session.checkout_url


def test_webhook_signature_roundtrip():
    provider = get_payment_provider("payme")
    payload = {"payment_id": "abc-123", "amount": "75000"}
    signature = provider.sign(payload)

    assert provider.verify_webhook_signature(payload, signature) is True


def test_webhook_signature_rejects_tampered_amount():
    provider = get_payment_provider("uzum")
    payload = {"payment_id": "abc-123", "amount": "75000"}
    signature = provider.sign(payload)

    tampered_payload = {"payment_id": "abc-123", "amount": "999999"}
    assert provider.verify_webhook_signature(tampered_payload, signature) is False


def test_different_providers_produce_different_signatures():
    payload = {"payment_id": "abc-123", "amount": "75000"}
    click_signature = get_payment_provider("click").sign(payload)
    payme_signature = get_payment_provider("payme").sign(payload)
    assert click_signature != payme_signature
