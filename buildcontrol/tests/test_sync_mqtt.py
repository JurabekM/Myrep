"""MQTT transport: payload sealing, topic layout and a live broker round-trip."""

from __future__ import annotations

import json
import socket

import pytest

from app.sync.crypto import DecryptionError, decrypt, derive_key, encrypt
from app.sync.transports.base import Change
from app.sync.transports.mqtt import PUBLIC_BROKERS, MqttTransport

LIVE_HOST = "broker.hivemq.com"
LIVE_PORT = 8883


def _broker_reachable(host: str = LIVE_HOST, port: int = LIVE_PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except OSError:
        return False


requires_broker = pytest.mark.skipif(
    not _broker_reachable(), reason="public MQTT broker not reachable"
)


# --------------------------------------------------------------------------- #
# Payload encryption
# --------------------------------------------------------------------------- #


def test_encrypted_payload_round_trips() -> None:
    key = derive_key("maxfiy-parol", "firma-kaliti")
    body = {"entity": "Project", "uid": "u1", "payload": {"name": "Uy", "planned_budget": 1000.0}}
    sealed = encrypt(body, key)
    assert b"planned_budget" not in sealed  # the content is not readable
    assert decrypt(sealed, key) == body


def test_wrong_passphrase_is_rejected() -> None:
    sealed = encrypt({"a": 1}, derive_key("to'g'ri", "firma"))
    with pytest.raises(DecryptionError):
        decrypt(sealed, derive_key("noto'g'ri", "firma"))


def test_same_passphrase_and_workspace_derive_the_same_key() -> None:
    assert derive_key("parol", "firma") == derive_key("parol", "firma")
    assert derive_key("parol", "firma") != derive_key("parol", "boshqa-firma")


def test_plain_payload_passes_through() -> None:
    raw = json.dumps({"entity": "Project"}).encode("utf-8")
    assert decrypt(raw, None) == {"entity": "Project"}


def test_encrypted_payload_without_passphrase_is_reported() -> None:
    sealed = encrypt({"a": 1}, derive_key("parol", "firma"))
    with pytest.raises(DecryptionError):
        decrypt(sealed, None)


# --------------------------------------------------------------------------- #
# Topics and configuration
# --------------------------------------------------------------------------- #


def test_topic_layout_is_one_topic_per_row() -> None:
    transport = MqttTransport(tenant="firma", prefix="buildcontrol")
    assert transport._topic("Project", "abc") == "buildcontrol/firma/Project/abc"
    assert transport._root == "buildcontrol/firma"


def test_describe_mentions_encryption_when_enabled() -> None:
    plain = MqttTransport(tenant="firma")
    sealed = MqttTransport(tenant="firma", passphrase="parol")
    assert "shifrlangan" not in plain.describe()
    assert "shifrlangan" in sealed.describe()


def test_public_broker_list_is_tls() -> None:
    assert PUBLIC_BROKERS, "at least one broker must be offered"
    for host, port, label in PUBLIC_BROKERS:
        assert host and label
        assert port in (8883, 8886), f"{host} should default to a TLS port"


# --------------------------------------------------------------------------- #
# Live broker
# --------------------------------------------------------------------------- #


@requires_broker
def test_retained_snapshot_reaches_a_fresh_subscriber() -> None:
    """A device that was never connected still receives the whole state."""
    import uuid

    tenant = "bc-pytest-" + uuid.uuid4().hex[:10]
    passphrase = "sinov-paroli"

    def make() -> MqttTransport:
        return MqttTransport(
            host=LIVE_HOST, port=LIVE_PORT, tenant=tenant, use_tls=True, passphrase=passphrase
        )

    publisher = make()
    try:
        publisher.push(
            [
                Change("Project", "uid-a", "upsert", {"name": "Birinchi"}, "", "dev-1"),
                Change("Project", "uid-b", "upsert", {"name": "Ikkinchi"}, "", "dev-1"),
            ]
        )
    finally:
        publisher.close()

    subscriber = make()
    try:
        received = subscriber.pull("", limit=100)
    finally:
        subscriber.close()

    by_uid = {change.uid: change for change in received}
    assert {"uid-a", "uid-b"} <= set(by_uid)
    assert by_uid["uid-a"].payload["name"] == "Birinchi"
    assert by_uid["uid-a"].device == "dev-1"
    assert by_uid["uid-a"].entity == "Project"


@requires_broker
def test_a_different_workspace_key_sees_nothing() -> None:
    import uuid

    stamp = uuid.uuid4().hex[:8]
    theirs = MqttTransport(host=LIVE_HOST, port=LIVE_PORT, tenant=f"bc-a-{stamp}")
    mine = MqttTransport(host=LIVE_HOST, port=LIVE_PORT, tenant=f"bc-b-{stamp}")
    try:
        theirs.push([Change("Project", "x", "upsert", {"name": "Yashirin"}, "", "dev")])
        assert mine.pull("") == []
    finally:
        theirs.close()
        mine.close()
