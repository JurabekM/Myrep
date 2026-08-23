"""Qurilmani ro'yxatdan o'tkazish — QR taklif va provisioning.

Topshiriq §12 oqimi:

```
1. Egasi desktop'da bir martalik taklif yaratadi
2. Taklif QR kod ko'rinishida ko'rsatiladi (qisqa muddatli)
3. Android QR ni skanerlaydi
4. AETHER-Q provisioning bajariladi
5. Qurilma o'z identifikatorini oladi
6. Egasi qurilma, foydalanuvchi va rolni TASDIQLAYDI
7. Qurilma role-scoped snapshot oladi
8. Taklif QAYTA ISHLATILMAYDI
```

## Nega QR ichida uzoq muddatli kalit yo'q

QR kod ekranda ko'rinadi, suratga tushadi, messenjerga yuboriladi. Unda
epoch root secret yoki master key bo'lsa — butun tenant ochiladi. Shuning
uchun QR faqat **bir martalik, qisqa muddatli taklif teg'ini** tashiydi.
Haqiqiy kalit AETHER-Q sessiyasi ichida, taklif teg'i bilan
autentifikatsiyalangandan keyin uzatiladi.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Any

import cbor2
from sqlalchemy import select
from sqlalchemy.orm import Session

from distribos.aether_q.vendor import kdf
from distribos.persistence.models import DeviceState, PeerDevice, utcnow

#: Taklif shu muddat ichida ishlatilishi kerak. Qisqa — QR ekranda turadi.
INVITATION_TTL = dt.timedelta(minutes=10)

INVITATION_LABEL = b"DistribOS/onboarding/invitation/v1"
CONFIRM_LABEL = b"DistribOS/onboarding/confirm/v1"


class OnboardingError(RuntimeError):
    """Provisioning bajarilmadi."""


@dataclass(frozen=True, slots=True)
class Invitation:
    """Bir martalik taklif. QR kodga SHU yoziladi."""

    invitation_id: str
    tenant_topic_id: str
    #: Taklif siri — faqat QR orqali uzatiladi, bazada faqat HASH'i yotadi.
    secret: bytes
    role: str
    display_name: str
    expires_at: str
    #: Desktop kalitining BARMOQ IZI (16 bayt), kalitning o'zi emas.
    #:
    #: ML-DSA-65 ochiq kaliti 1952 bayt — uni QR ga qo'yish payload'ni
    #: ~2 KB ga cho'zadi va qo'lda kiritish uchun 4000 belgi kerak
    #: bo'lardi, ya'ni amalda ishlamaydi. Kalitning O'ZI JOIN_RESPONSE
    #: ichida keladi va u allaqachon taklif siri bilan
    #: autentifikatsiyalangan. Barmoq izi qo'shimcha tekshiruv beradi.
    host_key_fingerprint: bytes
    broker_host: str
    broker_port: int
    environment: str

    def to_qr_payload(self) -> bytes:
        """QR kodga yoziladigan baytlar (CBOR, ixcham)."""
        return cbor2.dumps({
            "v": 1,
            "id": self.invitation_id,
            "t": self.tenant_topic_id,
            "s": self.secret,
            "r": self.role,
            "n": self.display_name,
            "e": self.expires_at,
            "k": self.host_key_fingerprint,
            "bh": self.broker_host,
            "bp": self.broker_port,
            "env": self.environment,
        })

    @classmethod
    def from_qr_payload(cls, raw: bytes) -> Invitation:
        try:
            data: dict[str, Any] = cbor2.loads(raw)
        except Exception as exc:
            raise OnboardingError("QR kod o'qilmadi") from exc

        if int(data.get("v", 0)) != 1:
            raise OnboardingError("QR kod versiyasi qo'llab-quvvatlanmaydi")

        try:
            invitation = cls(
                invitation_id=data["id"],
                tenant_topic_id=data["t"],
                secret=bytes(data["s"]),
                role=data["r"],
                display_name=data["n"],
                expires_at=data["e"],
                host_key_fingerprint=bytes(data["k"]),
                broker_host=data["bh"],
                broker_port=int(data["bp"]),
                environment=data.get("env", "pilot"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OnboardingError("QR kod tarkibi to'liq emas") from exc

        if invitation.is_expired:
            raise OnboardingError(
                "Taklif muddati o'tgan. Desktop dasturida yangi QR yarating."
            )
        return invitation

    @property
    def is_expired(self) -> bool:
        return utcnow() > dt.datetime.fromisoformat(self.expires_at)

    @property
    def secret_hash(self) -> str:
        """Bazada saqlanadigan qiymat. Sirning O'ZI saqlanmaydi."""
        return hashlib.sha3_256(INVITATION_LABEL + self.secret).hexdigest()


@dataclass
class PendingInvitation:
    """Desktop tomonida kutilayotgan taklif (xotirada yoki bazada)."""

    invitation_id: str
    secret_hash: str
    role: str
    display_name: str
    expires_at: dt.datetime
    used_at: dt.datetime | None = None

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return utcnow() > self.expires_at


class InvitationRegistry:
    """Takliflarni kuzatadi. Bir martalik ishlatishni MAJBURLAYDI."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingInvitation] = {}

    def issue(
        self,
        *,
        tenant_topic_id: str,
        role: str,
        display_name: str,
        host_sign_public_key: bytes,
        broker_host: str,
        broker_port: int,
        environment: str = "pilot",
        ttl: dt.timedelta = INVITATION_TTL,
    ) -> Invitation:
        """Yangi bir martalik taklif yaratadi."""
        from distribos.application.permissions import ROLE_PERMISSIONS

        if role not in ROLE_PERMISSIONS:
            raise OnboardingError(f"Noma'lum rol: {role}")

        invitation_id = secrets.token_hex(8)
        secret = secrets.token_bytes(32)
        expires_at = utcnow() + ttl

        invitation = Invitation(
            invitation_id=invitation_id,
            tenant_topic_id=tenant_topic_id,
            secret=secret,
            role=role,
            display_name=display_name,
            expires_at=expires_at.isoformat(),
            host_key_fingerprint=key_fingerprint(host_sign_public_key),
            broker_host=broker_host,
            broker_port=broker_port,
            environment=environment,
        )
        self._pending[invitation_id] = PendingInvitation(
            invitation_id=invitation_id,
            secret_hash=invitation.secret_hash,
            role=role,
            display_name=display_name,
            expires_at=expires_at,
        )
        return invitation

    def redeem(self, invitation_id: str, secret: bytes) -> PendingInvitation:
        """Taklifni ishlatadi. Ikkinchi marta ishlamaydi."""
        pending = self._pending.get(invitation_id)
        if pending is None:
            raise OnboardingError("Taklif topilmadi")
        if pending.is_used:
            raise OnboardingError(
                "Taklif allaqachon ishlatilgan. Har QR faqat bir marta "
                "ishlaydi — yangisini yarating."
            )
        if pending.is_expired:
            raise OnboardingError("Taklif muddati o'tgan")

        candidate = hashlib.sha3_256(INVITATION_LABEL + secret).hexdigest()
        # Constant-time solishtirish: sir bo'yicha timing hujumi bo'lmasin.
        if not hmac.compare_digest(candidate, pending.secret_hash):
            raise OnboardingError("Taklif siri noto'g'ri")

        pending.used_at = utcnow()
        return pending

    def revoke(self, invitation_id: str) -> None:
        self._pending.pop(invitation_id, None)

    def purge_expired(self) -> int:
        stale = [k for k, v in self._pending.items() if v.is_expired]
        for key in stale:
            del self._pending[key]
        return len(stale)

    @property
    def open_invitations(self) -> list[PendingInvitation]:
        return [v for v in self._pending.values() if not v.is_used and not v.is_expired]


def derive_join_proof(secret: bytes, device_id: bytes, sign_public_key: bytes) -> bytes:
    """Telefon o'zining taklifga egaligini isbotlaydi.

    KMAC256 tegi taklif siriga VA qurilma identitetiga bog'lanadi, ya'ni
    tegni ushlab olgan boshqa qurilma uni o'z kaliti bilan ishlatolmaydi.
    """
    prk = kdf.hkdf_extract(CONFIRM_LABEL, secret)
    return kdf.kmac256(prk, device_id + sign_public_key, 32, custom=b"DES1/join")


def verify_join_proof(
    secret: bytes, device_id: bytes, sign_public_key: bytes, proof: bytes
) -> bool:
    expected = derive_join_proof(secret, device_id, sign_public_key)
    return kdf.ct_eq(expected, proof)


def register_device(
    session: Session,
    *,
    device_id: bytes,
    tenant_id: bytes,
    display_name: str,
    role: str,
    platform: str,
    sign_public_key: bytes,
    kem_public_key: bytes,
    is_full_replica: bool = False,
) -> PeerDevice:
    """Qurilmani reyestrga qo'shadi (egasi tasdiqlagandan keyin).

    Qurilma darhol ACTIVE bo'lmaydi — avval INVITED. Egasi desktop'da
    tasdiqlaydi (topshiriq §12, 6-qadam).
    """
    if len(sign_public_key) != 1952:
        raise OnboardingError("ML-DSA-65 ochiq kaliti 1952 bayt bo'lishi kerak")
    if len(kem_public_key) != 1184:
        raise OnboardingError("ML-KEM-768 ochiq kaliti 1184 bayt bo'lishi kerak")

    existing = session.get(PeerDevice, device_id)
    if existing is not None:
        if existing.is_revoked:
            raise OnboardingError(
                "Bu qurilma bekor qilingan. Qayta qo'shish uchun avval "
                "bekor qilishni olib tashlang."
            )
        return existing

    peer = PeerDevice(
        device_id=device_id,
        tenant_id=tenant_id,
        display_name=display_name,
        platform=platform,
        role=role,
        sign_public_key=sign_public_key,
        kem_public_key=kem_public_key,
        state=DeviceState.INVITED,
        is_full_replica=is_full_replica,
    )
    session.add(peer)
    return peer


def confirm_device(session: Session, device_id: bytes) -> PeerDevice:
    """Egasi qurilmani tasdiqlaydi — endi u hodisa yubora oladi."""
    peer = session.get(PeerDevice, device_id)
    if peer is None:
        raise OnboardingError("Qurilma topilmadi")
    if peer.is_revoked:
        raise OnboardingError("Bekor qilingan qurilma tasdiqlanmaydi")
    peer.state = DeviceState.ACTIVE
    return peer


def pending_devices(session: Session) -> list[PeerDevice]:
    """Tasdiq kutayotgan qurilmalar (desktop'dagi ish navbati)."""
    return list(session.execute(
        select(PeerDevice).where(PeerDevice.state == DeviceState.INVITED)
    ).scalars())


def new_invitation_secret() -> bytes:
    return os.urandom(32)


def key_fingerprint(public_key: bytes) -> bytes:
    """Ochiq kalitning 16 baytli barmoq izi.

    Domain-ajratilgan hash: boshqa kontekstdagi hash bilan chalkashmaydi.
    """
    return hashlib.sha3_256(b"DistribOS/key-fingerprint/v1" + public_key).digest()[:16]
