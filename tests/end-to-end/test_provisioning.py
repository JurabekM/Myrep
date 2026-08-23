"""Qurilmani ulash (BOOT-1) va undan keyingi jonli sinxronizatsiya.

Bu test topshiriqdagi to'liq ssenariyni bosib o'tadi: yangi qurilma
QR taklif orqali qo'shiladi, epoch kalitini oladi, keyin ODDIY DES-1
sinxronizatsiyasi ishlay boshlaydi.

Aynan shu halqa uzilgan bo'lsa, "protokol ishlaydi" degan da'vo
ma'nosiz bo'ladi — qurilmalar bir-birini topa olmaydi.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.aether_q import boot1
from distribos.aether_q.onboarding import (
    Invitation,
    InvitationRegistry,
    OnboardingError,
)
from distribos.domain.ids import (
    new_tenant_id,
    opaque_tenant_topic_id,
    uuid7_str,
)
from distribos.persistence.models import (
    DeviceState,
    EpochKeyRecord,
    Order,
    PeerDevice,
    Product,
)
from distribos.sync.event_store import NewEvent
from distribos.sync.provisioning import (
    ProvisioningService,
    confirm_pending_device,
)
from harness import LoopbackBus, build_node


@pytest.fixture
def desktop_and_phone():
    """Desktop tayyor, telefon HALI QO'SHILMAGAN (boshqa tenant, kalitsiz)."""
    bus = LoopbackBus()
    tenant_id = new_tenant_id()

    desktop = build_node("desktop-1", tenant_id, bus)
    # Telefon o'zining ALOHIDA tenant va kaliti bilan boshlaydi —
    # ya'ni u hozircha desktopning hech narsasini ocholmaydi.
    phone = build_node("android-1", new_tenant_id(), bus)

    from distribos.infrastructure.secret_store import default_secret_store

    registry = InvitationRegistry()
    service = ProvisioningService(
        registry,
        tenant_id=tenant_id,
        host_device_id=desktop.device_id,
        host_sign_public_key=desktop.keys.sign_public_key,
        secret_store=default_secret_store(allow_insecure=True),
    )
    return bus, desktop, phone, registry, service, tenant_id


def _issue(registry: InvitationRegistry, service: ProvisioningService,
           tenant_id: bytes, desktop, role: str = "agent") -> Invitation:
    invitation = registry.issue(
        tenant_topic_id=opaque_tenant_topic_id(tenant_id),
        role=role,
        display_name="Aziz — savdo agenti",
        host_sign_public_key=desktop.keys.sign_public_key,
        broker_host="broker.hivemq.com",
        broker_port=8883,
    )
    service.remember(invitation)
    return invitation


def _join(phone, invitation: Invitation) -> bytes:
    return boot1.build_join_request(
        invitation_id=bytes.fromhex(invitation.invitation_id),
        invitation_secret=invitation.secret,
        device_id=phone.device_id,
        sign_public_key=phone.keys.sign_public_key,
        kem_public_key=phone.keys.kem_public_key,
        platform="android",
        display_name="Aziz telefoni",
    )


def _install_response(phone, invitation: Invitation, wire: bytes) -> None:
    """Telefon javobni ochib, tenant va epoch kalitini o'rnatadi."""
    from distribos.aether_q.real import _key_context
    from distribos.infrastructure.secret_store import default_secret_store

    response = boot1.parse_join_response(wire, invitation.secret)
    store = default_secret_store(allow_insecure=True)

    with phone.database.unit_of_work() as session:
        session.query(EpochKeyRecord).delete()
        session.add(EpochKeyRecord(
            epoch=response.epoch, key_id=response.key_id,
            tenant_id=response.tenant_id,
            root_secret_wrapped=store.wrap(
                response.epoch_root_secret,
                _key_context(response.epoch, response.key_id),
            ),
            profile_id=response.profile_id, is_current=True,
        ))
        # Desktopni tanilgan peer sifatida yozamiz.
        session.add(PeerDevice(
            device_id=response.host_device_id, tenant_id=response.tenant_id,
            display_name="Desktop", platform="desktop", role="owner",
            sign_public_key=response.host_sign_public_key,
            kem_public_key=b"", state=DeviceState.ACTIVE, is_full_replica=True,
        ))

    # Telefonning provayderi va hodisa do'koni yangi tenant bilan ishlashi kerak.
    phone.provider._tenant_id = response.tenant_id
    phone.provider._key_cache.clear()
    phone.store._tenant_id = response.tenant_id
    phone.tenant_id = response.tenant_id


# --- asosiy oqim ----------------------------------------------------------


def test_full_join_then_live_sync(desktop_and_phone) -> None:
    """QR taklif → ulash → epoch kaliti → oddiy sinxronizatsiya."""
    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone

    # 1. Egasi taklif yaratadi.
    invitation = _issue(registry, service, tenant_id, desktop)
    assert not invitation.is_expired
    assert len(registry.open_invitations) == 1

    # 2-3. Telefon QR ni o'qib JOIN_REQUEST yuboradi.
    payload = invitation.to_qr_payload()
    decoded = Invitation.from_qr_payload(payload)
    assert decoded.invitation_id == invitation.invitation_id
    # QR kodda epoch kaliti YO'Q — faqat bir martalik teg.
    assert invitation.secret in payload
    # Va u qo'lda kiritish uchun yetarlicha KICHIK bo'lishi kerak:
    # to'liq ML-DSA kaliti (1952 bayt) QR ga sig'sa ham, uni qo'lda
    # kiritish 4000 belgi degani — amalda ishlamaydi.
    assert len(payload) < 300, f"QR payload juda katta: {len(payload)} bayt"
    request_wire = _join(phone, decoded)

    # 4-6. Desktop tekshiradi va javob beradi.
    with desktop.database.unit_of_work() as session:
        outcome = service.handle_join_request(session, request_wire)
    assert outcome.role == "agent"

    # 7. Telefon kalitni o'rnatadi.
    _install_response(phone, invitation, outcome.response_wire)

    # Qurilma TASDIQ KUTMOQDA holatida — hali hodisa yubora olmaydi.
    with desktop.database.session() as session:
        peer = session.get(PeerDevice, phone.device_id)
        assert peer is not None
        assert peer.state == DeviceState.INVITED

    # 9. Egasi tasdiqlaydi.
    with desktop.database.unit_of_work() as session:
        confirm_pending_device(session, phone.device_id)

    # --- endi ODDIY sinxronizatsiya ishlashi kerak ---

    product_id = uuid7_str()
    with desktop.database.unit_of_work() as session:
        desktop.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "COLA-1L", "name": "Cola 1L",
             "unit": "dona", "wholesale_price": 1_500_000},
        ))
    desktop.sync(rounds=4)

    with phone.database.session() as session:
        assert session.get(Product, product_id) is not None, (
            "ulangandan keyin ham desktop ma'lumoti telefonga yetmadi"
        )

    # Teskari yo'nalish: telefon buyurtma yozadi.
    customer_id = uuid7_str()
    with desktop.database.unit_of_work() as session:
        desktop.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "M-1", "name": "Mijoz",
             "kind": "COMPANY"},
        ))
    desktop.sync(rounds=4)

    order_id = uuid7_str()
    with phone.database.unit_of_work() as session:
        phone.command.submit(session, NewEvent(
            "ORDER_CREATED", "Order", order_id,
            {"order_id": order_id, "number": f"A-{order_id[-8:]}",
             "customer_id": customer_id, "ordered_at": "2026-08-23T10:00:00+00:00",
             "lines": [{"line_id": uuid7_str(), "product_id": product_id,
                        "quantity": "5", "unit_price": 1_500_000}]},
        ))
    phone.sync(rounds=4)

    with desktop.database.session() as session:
        assert session.get(Order, order_id) is not None, (
            "telefonda yozilgan buyurtma desktopga yetmadi"
        )


# --- xavfsizlik -----------------------------------------------------------


def test_invitation_works_only_once(desktop_and_phone) -> None:
    """Bir QR bilan ikkinchi qurilma qo'shib bo'lmaydi."""
    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = _issue(registry, service, tenant_id, desktop)

    with desktop.database.unit_of_work() as session:
        service.handle_join_request(session, _join(phone, invitation))

    second = build_node("android-2", new_tenant_id(), bus)
    with pytest.raises(OnboardingError):
        with desktop.database.unit_of_work() as session:
            service.handle_join_request(session, _join(second, invitation))


def test_expired_invitation_rejected(desktop_and_phone) -> None:
    import datetime as dt

    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = registry.issue(
        tenant_topic_id=opaque_tenant_topic_id(tenant_id),
        role="agent", display_name="Kech qolgan",
        host_sign_public_key=desktop.keys.sign_public_key,
        broker_host="broker.hivemq.com", broker_port=8883,
        ttl=dt.timedelta(seconds=-1),
    )
    service.remember(invitation)

    assert invitation.is_expired
    with pytest.raises(OnboardingError):
        with desktop.database.unit_of_work() as session:
            service.handle_join_request(session, _join(phone, invitation))


def test_wrong_secret_rejected(desktop_and_phone) -> None:
    """Taklif ID to'g'ri, lekin sir noto'g'ri — rad etiladi."""
    import os

    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = _issue(registry, service, tenant_id, desktop)

    forged = boot1.build_join_request(
        invitation_id=bytes.fromhex(invitation.invitation_id),
        invitation_secret=os.urandom(32),      # taxmin qilingan sir
        device_id=phone.device_id,
        sign_public_key=phone.keys.sign_public_key,
        kem_public_key=phone.keys.kem_public_key,
        platform="android", display_name="Soxta",
    )
    with pytest.raises(OnboardingError):
        with desktop.database.unit_of_work() as session:
            service.handle_join_request(session, forged)


def test_proof_bound_to_device_identity(desktop_and_phone) -> None:
    """Tegni ushlab olgan BOSHQA qurilma uni ishlatolmaydi."""
    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = _issue(registry, service, tenant_id, desktop)

    keys = boot1.derive_keys(invitation.secret)
    attacker = build_node("android-hacker", new_tenant_id(), bus)

    # Hujumchi haqiqiy so'rovni ushlab oldi va o'z kalitini qo'ydi,
    # lekin isbot ESKI qurilmaga bog'langan.
    wire = boot1.seal(
        {
            "device_id": attacker.device_id,
            "sign_public_key": attacker.keys.sign_public_key,
            "kem_public_key": attacker.keys.kem_public_key,
            "platform": "android",
            "display_name": "Hujumchi",
            "proof": boot1.join_proof(keys, phone.device_id, phone.keys.sign_public_key),
        },
        boot1.Boot1Kind.JOIN_REQUEST,
        bytes.fromhex(invitation.invitation_id), keys,
    )
    with pytest.raises(OnboardingError, match="yaroqsiz"):
        with desktop.database.unit_of_work() as session:
            service.handle_join_request(session, wire)


def test_unconfirmed_device_events_are_not_accepted(desktop_and_phone) -> None:
    """Egasi tasdiqlamaguncha qurilma hodisalari QABUL QILINMAYDI."""
    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = _issue(registry, service, tenant_id, desktop)

    with desktop.database.unit_of_work() as session:
        outcome = service.handle_join_request(session, _join(phone, invitation))
    _install_response(phone, invitation, outcome.response_wire)

    # Telefon tasdiqlanmagan (INVITED) holatda hodisa yuboradi.
    customer_id = uuid7_str()
    with phone.database.unit_of_work() as session:
        phone.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "M-X", "name": "Erta",
             "kind": "COMPANY"},
        ))
    phone.sync(rounds=3)

    from distribos.persistence.models import Customer

    with desktop.database.session() as session:
        assert session.get(Customer, customer_id) is None, (
            "tasdiqlanmagan qurilma hodisasi qabul qilindi"
        )


def test_join_request_cannot_be_replayed_as_response(desktop_and_phone) -> None:
    """Yo'nalishli kalitlar: so'rovni javob sifatida ochib bo'lmaydi."""
    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = _issue(registry, service, tenant_id, desktop)

    request_wire = _join(phone, invitation)
    with pytest.raises(boot1.Boot1Error):
        boot1.parse_join_response(request_wire, invitation.secret)


def test_response_carries_no_plaintext_secret(desktop_and_phone) -> None:
    """Epoch kaliti javob ichida OCHIQ ko'rinmaydi."""
    bus, desktop, phone, registry, service, tenant_id = desktop_and_phone
    invitation = _issue(registry, service, tenant_id, desktop)

    with desktop.database.unit_of_work() as session:
        outcome = service.handle_join_request(session, _join(phone, invitation))

    response = boot1.parse_join_response(outcome.response_wire, invitation.secret)
    # Ochilgan sir simdagi baytlarda TOPILMASLIGI kerak.
    assert response.epoch_root_secret not in outcome.response_wire
    assert repr(response).count("secrets hidden") == 1
