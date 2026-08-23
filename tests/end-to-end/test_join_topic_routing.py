"""Taklifdagi manzil kompyuter eshitadigan manzil bilan bir xil bo'lsin.

Bu sinov jonli sinovda topilgan nosozlikdan keyin yozildi: telefon
JOIN_REQUEST ni O'ZINING vaqtinchalik manziliga yuborardi, kompyuter esa
uni hech qachon eshitmasdi. Telefon «javob kutilmoqda» da abadiy qolardi,
ikkala tomonda ham xato ko'rinmasdi — shuning uchun buni faqat haqiqiy
tarmoqdagi sinov ochib berdi.

Kotlin tomonida shu invariant `Topics.Space.fromTopicId()` bilan
ta'minlanadi; bu yerda uning Python juftini qulflaymiz.
"""

from __future__ import annotations

import os

from distribos.aether_q.onboarding import Invitation, InvitationRegistry
from distribos.domain.ids import opaque_tenant_topic_id
from distribos.mqtt.topics import Channel, TopicSpace


def _invitation(tenant_id: bytes, environment: str = "pilot") -> Invitation:
    registry = InvitationRegistry()
    return registry.issue(
        tenant_topic_id=opaque_tenant_topic_id(tenant_id),
        role="agent",
        display_name="Telefon",
        host_sign_public_key=b"\x01" * 1952,
        broker_host="broker.hivemq.com",
        broker_port=8883,
        environment=environment,
    )


def test_taklifdagi_manzil_kompyuternikiga_teng():
    tenant_id = os.urandom(16)
    invitation = _invitation(tenant_id)

    desktop = TopicSpace.create(tenant_id, "pilot")
    telefon = TopicSpace(invitation.tenant_topic_id, invitation.environment)

    assert telefon.publish_topic(Channel.PROTOCOL_CONTROL, "boot") == \
        desktop.publish_topic(Channel.PROTOCOL_CONTROL, "boot")


def test_boshqa_kompaniya_manzili_boshqacha():
    """Ehtiyot sinov: yuqoridagi tenglik tasodifiy bo'lmasin."""
    a = TopicSpace.create(os.urandom(16), "pilot")
    b = TopicSpace.create(os.urandom(16), "pilot")
    assert a.publish_topic(Channel.PROTOCOL_CONTROL, "boot") != \
        b.publish_topic(Channel.PROTOCOL_CONTROL, "boot")


def test_qr_dan_otgan_manzil_saqlanadi():
    """QR orqali o'tib-kelgan qiymat o'zgarmasligi kerak."""
    tenant_id = os.urandom(16)
    invitation = _invitation(tenant_id)
    qayta = Invitation.from_qr_payload(invitation.to_qr_payload())

    assert qayta.tenant_topic_id == opaque_tenant_topic_id(tenant_id)
    assert qayta.environment == invitation.environment


def test_manzilda_ochiq_kompaniya_identifikatori_yoq():
    """Topikda kompaniyaning HAQIQIY identifikatori ko'rinmasin."""
    tenant_id = os.urandom(16)
    topic = TopicSpace.create(tenant_id, "pilot").publish_topic(
        Channel.PROTOCOL_CONTROL, "boot"
    )
    assert tenant_id.hex() not in topic
