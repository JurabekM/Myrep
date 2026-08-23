"""Qurilmani ulash xizmati (desktop tomoni).

BOOT-1 oqimining serverdek ishlaydigan tomoni — lekin bu **server emas**:
oddiy desktop ilovaning fon moduli. U faqat egasining kompyuterida
ishlaydi va faqat egasining o'zi yaratgan taklif uchun javob beradi.

Xavfsizlik qoidalari (`specs/distribos-event-seal/BOOT-1.md`):

* taklif **bir marta** ishlaydi;
* muddati o'tgan taklif rad etiladi;
* `proof` qurilma identitetiga bog'langan — tegni ushlab olgan boshqa
  qurilma uni ishlatolmaydi;
* qurilma **INVITED** holatida yoziladi; egasi qo'lda tasdiqlamaguncha
  uning hodisalari qabul qilinmaydi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from distribos.aether_q import boot1
from distribos.aether_q.onboarding import (
    Invitation,
    InvitationRegistry,
    OnboardingError,
    register_device,
)
from distribos.persistence.models import DeviceState, EpochKeyRecord, PeerDevice

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class JoinOutcome:
    """Ulash natijasi. `response_wire` peer'ga qaytariladi."""

    device_id: bytes
    display_name: str
    role: str
    response_wire: bytes


class ProvisioningService:
    """Kelgan JOIN_REQUEST larni qayta ishlaydi."""

    def __init__(
        self,
        registry: InvitationRegistry,
        *,
        tenant_id: bytes,
        host_device_id: bytes,
        host_sign_public_key: bytes,
        secret_store: object,
    ) -> None:
        self._registry = registry
        self._tenant_id = tenant_id
        self._host_device_id = host_device_id
        self._host_sign_public_key = host_sign_public_key
        self._secret_store = secret_store
        #: `invitation_id` -> sir. Faqat XOTIRADA: taklif qisqa umrli va
        #: uni diskka yozish keraksiz xavf.
        self._secrets: dict[str, bytes] = {}

    def remember(self, invitation: Invitation) -> None:
        """Yaratilgan taklif sirini eslab qoladi (javob shifrlash uchun)."""
        self._secrets[invitation.invitation_id] = invitation.secret

    def forget(self, invitation_id: str) -> None:
        self._secrets.pop(invitation_id, None)

    def handle_join_request(self, session: Session, wire: bytes) -> JoinOutcome:
        """JOIN_REQUEST ni tekshiradi, qurilmani yozadi, javob tayyorlaydi.

        Har qanday xatoda `OnboardingError` — chaqiruvchi javob
        YUBORMAYDI. Sabab tarmoqqa chiqmaydi.
        """
        invitation_id = boot1.peek_invitation_id(wire).hex()
        secret = self._secrets.get(invitation_id)
        if secret is None:
            # Bu taklif bizniki emas yoki allaqachon unutilgan.
            raise OnboardingError("Taklif topilmadi")

        try:
            request = boot1.parse_join_request(wire, secret)
        except boot1.Boot1Error as exc:
            raise OnboardingError(f"So'rov yaroqsiz: {exc}") from exc

        # Bir martalik ishlatishni MAJBURLAYDI (muddat ham shu yerda).
        pending = self._registry.redeem(invitation_id, secret)

        peer = register_device(
            session,
            device_id=request.device_id,
            tenant_id=self._tenant_id,
            display_name=pending.display_name or request.display_name,
            role=pending.role,
            platform=request.platform,
            sign_public_key=request.sign_public_key,
            kem_public_key=request.kem_public_key,
            is_full_replica=False,
        )
        session.flush()

        epoch_record = self._current_epoch(session)
        root = self._secret_store.unwrap(   # type: ignore[attr-defined]
            epoch_record.root_secret_wrapped,
            _key_context(epoch_record.epoch, epoch_record.key_id),
        )

        response = boot1.build_join_response(
            invitation_id=bytes.fromhex(invitation_id),
            invitation_secret=secret,
            tenant_id=self._tenant_id,
            epoch=epoch_record.epoch,
            key_id=epoch_record.key_id,
            epoch_root_secret=root,
            profile_id=epoch_record.profile_id,
            role=pending.role,
            host_device_id=self._host_device_id,
            host_sign_public_key=self._host_sign_public_key,
        )

        # Sir endi kerak emas — xotiradan olib tashlaymiz.
        self.forget(invitation_id)

        logger.info(
            "Qurilma qo'shildi (tasdiq kutmoqda): %s, rol %s",
            peer.display_name, peer.role,
        )
        return JoinOutcome(
            device_id=request.device_id,
            display_name=peer.display_name,
            role=peer.role,
            response_wire=response,
        )

    def _current_epoch(self, session: Session) -> EpochKeyRecord:
        from sqlalchemy import select

        record = session.execute(
            select(EpochKeyRecord).where(
                EpochKeyRecord.tenant_id == self._tenant_id,
                EpochKeyRecord.is_current.is_(True),
            )
        ).scalar_one_or_none()
        if record is None:
            raise OnboardingError("Joriy epoch kaliti yo'q")
        return record

    @property
    def open_invitation_ids(self) -> list[str]:
        return list(self._secrets)


def _key_context(epoch: int, key_id: int) -> bytes:
    from distribos.aether_q.real import _key_context as context

    return context(epoch, key_id)


def confirm_pending_device(session: Session, device_id: bytes) -> PeerDevice:
    """Egasi qurilmani tasdiqlaydi — endi u hodisa yubora oladi."""
    peer = session.get(PeerDevice, device_id)
    if peer is None:
        raise OnboardingError("Qurilma topilmadi")
    if peer.is_revoked:
        raise OnboardingError("Bekor qilingan qurilma tasdiqlanmaydi")
    peer.state = DeviceState.ACTIVE
    return peer
