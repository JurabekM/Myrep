"""`AetherQ51Provider` ning haqiqiy implementatsiyasi.

Bu yerda kripto **o'ylab topilmaydi** — hamma narsa `vendor` modullaridan
(ML-DSA-65, ML-KEM-768, HKDF-SHA3-256, ChaCha20-Poly1305) va DES-1
kodekidan keladi. Bu sinf ularni baza bilan bog'laydi: kalit qayerda
yotadi, kim bekor qilingan, qaysi `seq` allaqachon ko'rilgan.

Ochish tartibi DES-1 spetsifikatsiyasidagi 11 qadamga QAT'IY amal qiladi
va fail-closed: har qanday shubhada `AetherQError`.
"""

from __future__ import annotations

import os
import struct
import threading
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from distribos.aether_q import des1
from distribos.aether_q.provider import (
    AetherQError,
    ContentType,
    DeviceIdentity,
    OpenedEnvelope,
    ProtocolHealth,
    RejectReason,
    SealedEnvelope,
)
from distribos.aether_q.vendor import sig
from distribos.domain.ids import mask_identifier
from distribos.persistence.models import (
    DeviceState,
    EpochKeyRecord,
    PeerDevice,
    ReplayWindow,
    utcnow,
)

#: Replay oynasining kengligi (bit). AETHER-Q N5 kamida 2^20 talab qiladi.
REPLAY_WINDOW_BITS = 1 << 20
_BITMAP_BYTES = 1024   # oxirgi 8192 ta `seq` ni aniq kuzatadi

#: Hodisa qanchalik eski bo'lsa ham qabul qilinadi (offline qurilma
#: bir necha kun ishlashi mumkin), lekin KELAJAK qat'iy cheklanadi.
MAX_FUTURE_SKEW_MS = 5 * 60 * 1000


@dataclass(slots=True)
class DeviceKeyMaterial:
    """Qurilmaning O'Z maxfiy kalitlari. Bazada o'ralgan holda yotadi."""

    device_id: bytes
    sign_public_key: bytes
    sign_private_key: object
    kem_public_key: bytes
    kem_private_key: bytes

    def __repr__(self) -> str:
        return f"DeviceKeyMaterial(device_id={mask_identifier(self.device_id)}, <secrets hidden>)"


class RealAetherQProvider:
    """Baza bilan bog'langan AETHER-Q v5.1 + DES-1 provayderi."""

    def __init__(
        self,
        *,
        tenant_id: bytes,
        keys: DeviceKeyMaterial,
        session_factory: object,
        profile_id: int = 0x01,
        max_payload_bytes: int = 256 * 1024,
    ) -> None:
        if profile_id not in (0x01, 0x03):
            raise ValueError("Faqat 0x01 va 0x03 profillari qo'llab-quvvatlanadi")
        self._tenant_id = tenant_id
        self._keys = keys
        self._session_factory = session_factory
        self._profile_id = profile_id
        self._max_payload = max_payload_bytes
        self._lock = threading.Lock()
        #: `(epoch, key_id)` -> EpochKeys keshi. Sirlar faqat xotirada.
        self._key_cache: dict[tuple[int, int], des1.EpochKeys] = {}
        self._sequence = 0

    # --- yordamchilar ---------------------------------------------------

    def _session(self) -> Session:
        return self._session_factory()  # type: ignore[operator]

    def _epoch_keys(self, session: Session, epoch: int, key_id: int) -> des1.EpochKeys:
        cached = self._key_cache.get((epoch, key_id))
        if cached is not None:
            return cached

        record = session.execute(
            select(EpochKeyRecord).where(
                EpochKeyRecord.epoch == epoch,
                EpochKeyRecord.key_id == key_id,
                EpochKeyRecord.tenant_id == self._tenant_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise AetherQError(RejectReason.UNKNOWN_KEY, f"epoch={epoch} key_id={key_id}")

        from distribos.infrastructure.secret_store import default_secret_store

        store = default_secret_store(allow_insecure=True)
        root = store.unwrap(record.root_secret_wrapped, _key_context(epoch, key_id))
        keys = des1.derive_epoch_keys(
            root, self._tenant_id, epoch, key_id, record.profile_id
        )
        self._key_cache[(epoch, key_id)] = keys
        return keys

    def _current_epoch(self, session: Session) -> EpochKeyRecord:
        record = session.execute(
            select(EpochKeyRecord).where(
                EpochKeyRecord.tenant_id == self._tenant_id,
                EpochKeyRecord.is_current.is_(True),
            )
        ).scalar_one_or_none()
        if record is None:
            raise AetherQError(RejectReason.UNKNOWN_EPOCH, "joriy epoch kaliti yo'q")
        return record

    # --- qurilma hayot sikli ---------------------------------------------

    def export_public_identity(self) -> DeviceIdentity:
        return DeviceIdentity(
            device_id=self._keys.device_id,
            sign_public_key=self._keys.sign_public_key,
            kem_public_key=self._keys.kem_public_key,
            protocol_version="5.1.0",
        )

    def revoke_device(self, device_id: bytes, reason: str) -> None:
        """Qurilmani bekor qiladi. Undan keyingi hodisalar rad etiladi."""
        with self._session() as session, session.begin():
            peer = session.get(PeerDevice, device_id)
            if peer is None:
                raise AetherQError(RejectReason.UNKNOWN_SENDER, "qurilma topilmadi")
            peer.state = DeviceState.REVOKED
            peer.revoked_at = utcnow()
            peer.revoked_reason = reason

    def verify_sender(self, device_id: bytes) -> bool:
        with self._session() as session:
            peer = session.get(PeerDevice, device_id)
            return peer is not None and not peer.is_revoked

    # --- kalit boshqaruvi -------------------------------------------------

    def rotate_keys(self) -> int:
        """Yangi epoch ochadi.

        Eski epoch kaliti O'CHIRILMAYDI — offline qurilma qaytganda uning
        eski hodisalari hali ham ochilishi kerak. Eski kalit `retired_at`
        bilan belgilanadi va yangi xabar u bilan MUHRLANMAYDI.
        """
        from distribos.infrastructure.secret_store import default_secret_store

        store = default_secret_store(allow_insecure=True)
        with self._lock, self._session() as session, session.begin():
            current = session.execute(
                select(EpochKeyRecord).where(
                    EpochKeyRecord.tenant_id == self._tenant_id,
                    EpochKeyRecord.is_current.is_(True),
                )
            ).scalar_one_or_none()

            next_epoch = (current.epoch + 1) if current else 1
            if current is not None:
                current.is_current = False
                current.retired_at = utcnow()

            root = os.urandom(32)
            session.add(
                EpochKeyRecord(
                    epoch=next_epoch,
                    key_id=1,
                    tenant_id=self._tenant_id,
                    root_secret_wrapped=store.wrap(root, _key_context(next_epoch, 1)),
                    profile_id=self._profile_id,
                    is_current=True,
                )
            )
            self._key_cache.clear()
            return next_epoch

    # --- muhrlash ---------------------------------------------------------

    def seal_message(self, payload: bytes, content_type: ContentType) -> SealedEnvelope:
        if len(payload) + des1.MIN_ENVELOPE_SIZE > self._max_payload:
            raise AetherQError(
                RejectReason.TOO_LARGE,
                f"{len(payload)} bayt — chegara {self._max_payload}",
            )

        with self._lock, self._session() as session:
            record = self._current_epoch(session)
            keys = self._epoch_keys(session, record.epoch, record.key_id)
            self._sequence += 1
            sequence = self._sequence

            header = des1.Des1Header(
                version=des1.DES1_VERSION,
                profile_id=self._profile_id,
                content_type=int(content_type),
                epoch=record.epoch,
                key_id=record.key_id,
                tenant_tag=keys.tenant_tag,
                sender_device_id=self._keys.device_id,
                sequence=sequence,
                rand=os.urandom(des1.RAND_SIZE),
            )
            wire = des1.seal(payload, header, keys, self._keys.sign_private_key)

        return SealedEnvelope(
            wire=wire,
            content_type=content_type,
            epoch=record.epoch,
            sender_device_id=self._keys.device_id,
        )

    def seal_with_sequence(
        self, payload: bytes, content_type: ContentType, sequence: int
    ) -> SealedEnvelope:
        """Hodisaning O'Z `device_sequence` i bilan muhrlaydi.

        Hodisa oqimida nonce hodisa jurnalidagi hisoblagichga bog'lanadi —
        shunda qayta yuborish (retry) bir xil baytlarni beradi va peer
        uni takror sifatida tanaydi, yangi xabar deb emas.
        """
        with self._lock, self._session() as session:
            record = self._current_epoch(session)
            keys = self._epoch_keys(session, record.epoch, record.key_id)
            header = des1.Des1Header(
                version=des1.DES1_VERSION,
                profile_id=self._profile_id,
                content_type=int(content_type),
                epoch=record.epoch,
                key_id=record.key_id,
                tenant_tag=keys.tenant_tag,
                sender_device_id=self._keys.device_id,
                sequence=sequence,
                rand=b"\x00" * des1.RAND_SIZE,   # deterministik retry uchun
            )
            wire = des1.seal(payload, header, keys, self._keys.sign_private_key)

        return SealedEnvelope(wire, content_type, record.epoch, self._keys.device_id)

    # --- ochish -----------------------------------------------------------

    def open_message(self, wire: bytes) -> OpenedEnvelope:
        """DES-1 envelope'ni ochadi. Tartib spetsifikatsiyadagidek (11 qadam)."""
        # 1. Hajm
        if len(wire) > self._max_payload:
            raise AetherQError(RejectReason.TOO_LARGE, str(len(wire)))
        try:
            header, packed, ciphertext, signature = des1.split(wire)
        except des1.Des1FormatError as exc:
            raise AetherQError(RejectReason.MALFORMED, str(exc)) from exc

        # 2-3. Versiya va profil
        if header.version != des1.DES1_VERSION:
            raise AetherQError(RejectReason.UNKNOWN_VERSION, str(header.version))
        if header.profile_id not in (0x01, 0x03):
            raise AetherQError(RejectReason.UNSUPPORTED_PROFILE, str(header.profile_id))

        with self._session() as session:
            # 4-5. Epoch va kalit
            keys = self._epoch_keys(session, header.epoch, header.key_id)

            # 6. Tenant izolyatsiyasi (constant-time)
            if not des1.tenant_tag_matches(header, keys):
                raise AetherQError(RejectReason.FOREIGN_TENANT)

            # 7. Jo'natuvchi ma'lum va bekor qilinmagan.
            #    DIQQAT: bu imzo tekshiruvidan OLDIN turadi — bekor qilingan
            #    qurilmaning imzosi hali ham matematik jihatdan to'g'ri.
            peer = session.get(PeerDevice, header.sender_device_id)
            if peer is None:
                raise AetherQError(RejectReason.UNKNOWN_SENDER)
            if peer.is_revoked:
                raise AetherQError(RejectReason.REVOKED_SENDER)

            # 8. Imzo
            if not des1.verify_signature(packed, ciphertext, signature, peer.sign_public_key):
                raise AetherQError(RejectReason.BAD_SIGNATURE)

            # 9. Replay
            if self._check_and_record_replay(
                session, header.epoch, header.sender_device_id, header.sequence
            ):
                raise AetherQError(RejectReason.REPLAY, f"seq={header.sequence}")

            session.commit()

            # 10. AEAD
            try:
                payload = des1.open_aead(header, ciphertext, keys)
            except des1.Des1FormatError as exc:
                raise AetherQError(RejectReason.AEAD_FAILURE) from exc

        # 11. Schema validatsiyasi chaqiruvchi tomonda (contracts/)
        return OpenedEnvelope(
            payload=payload,
            content_type=ContentType(header.content_type),
            epoch=header.epoch,
            sender_device_id=header.sender_device_id,
            sequence=header.sequence,
        )

    # --- replay oynasi ----------------------------------------------------

    def _check_and_record_replay(
        self, session: Session, epoch: int, device_id: bytes, sequence: int
    ) -> bool:
        """`True` — bu takror. Aks holda oynaga yoziladi.

        Sliding-window bitmap: `highest` dan pastdagi 8192 ta `seq` aniq
        kuzatiladi. Undan ham eski xabar — juda kech, rad etiladi.
        """
        window = session.get(ReplayWindow, (epoch, device_id))
        if window is None:
            window = ReplayWindow(
                epoch=epoch,
                device_id=device_id,
                highest_sequence=sequence,
                bitmap=b"\x00" * _BITMAP_BYTES,
            )
            _set_bit(window, 0)
            session.add(window)
            return False

        capacity = _BITMAP_BYTES * 8

        if sequence > window.highest_sequence:
            shift = sequence - window.highest_sequence
            bitmap = int.from_bytes(window.bitmap, "little")
            bitmap = (bitmap << shift) & ((1 << capacity) - 1) if shift < capacity else 0
            bitmap |= 1
            window.bitmap = bitmap.to_bytes(_BITMAP_BYTES, "little")
            window.highest_sequence = sequence
            window.updated_at = utcnow()
            return False

        offset = window.highest_sequence - sequence
        if offset >= capacity:
            return True  # oynadan chetda — juda eski, rad

        bitmap = int.from_bytes(window.bitmap, "little")
        if bitmap >> offset & 1:
            return True  # allaqachon ko'rilgan

        window.bitmap = (bitmap | (1 << offset)).to_bytes(_BITMAP_BYTES, "little")
        window.updated_at = utcnow()
        return False

    def detect_replay(self, epoch: int, device_id: bytes, sequence: int) -> bool:
        with self._session() as session, session.begin():
            return self._check_and_record_replay(session, epoch, device_id, sequence)

    def validate_freshness(self, epoch: int, occurred_at_ms: int) -> bool:
        """Kelajakdagi tamg'a rad etiladi; eski qabul qilinadi (offline ish)."""
        import time

        now_ms = time.time_ns() // 1_000_000
        return occurred_at_ms <= now_ms + MAX_FUTURE_SKEW_MS

    # --- diagnostika ------------------------------------------------------

    def protocol_health_check(self) -> ProtocolHealth:
        from distribos.infrastructure.secret_store import default_secret_store

        blocking: list[str] = []
        with self._session() as session:
            try:
                record = self._current_epoch(session)
                epoch, key_id = record.epoch, record.key_id
            except AetherQError:
                epoch, key_id = 0, 0
                blocking.append("Joriy epoch kaliti yo'q — qurilma sozlanmagan")

            peers = session.execute(select(PeerDevice)).scalars().all()
            known = len(peers)
            revoked = sum(1 for p in peers if p.is_revoked)

        try:
            store = default_secret_store()
            if not store.is_os_protected:
                blocking.append("Kalitlar OS darajasida himoyalanmagan")
        except Exception:
            blocking.append("OS kalit himoyasi mavjud emas")

        return ProtocolHealth(
            protocol_version="5.1.0",
            profile_id=self._profile_id,
            epoch=epoch,
            key_id=key_id,
            device_id_masked=mask_identifier(self._keys.device_id),
            peers_known=known,
            peers_revoked=revoked,
            replay_window_size=_BITMAP_BYTES * 8,
            production_ready=not blocking,
            blocking_reasons=tuple(blocking),
        )


def _set_bit(window: ReplayWindow, offset: int) -> None:
    bitmap = int.from_bytes(window.bitmap, "little") | (1 << offset)
    window.bitmap = bitmap.to_bytes(_BITMAP_BYTES, "little")


def _key_context(epoch: int, key_id: int) -> bytes:
    """Sir o'rashda ishlatiladigan kontekst — kalitni epoch'ga bog'laydi."""
    return b"DistribOS/epoch-root/v1" + struct.pack(">IQ", epoch, key_id)


def generate_device_keys(device_id: bytes) -> DeviceKeyMaterial:
    """Yangi qurilma uchun ML-DSA-65 va ML-KEM-768 juftlari."""
    from distribos.aether_q.vendor import kem

    sign_public, sign_private = sig.MLDSA65.keygen()
    kem_public, kem_private = kem.MLKEM768.keygen()
    return DeviceKeyMaterial(
        device_id=device_id,
        sign_public_key=sign_public,
        sign_private_key=sign_private,
        kem_public_key=kem_public,
        kem_private_key=kem_private,
    )
