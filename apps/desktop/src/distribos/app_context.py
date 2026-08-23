"""Ilova konteksti — barcha qismlarni bog'laydi (composition root).

Bog'lash BITTA joyda bo'lishi kerak. Aks holda «bu obyekt qayerdan
keladi» degan savol kod bo'ylab tarqaladi va testda almashtirish
qiyinlashadi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from distribos.aether_q.onboarding import InvitationRegistry
from distribos.aether_q.real import (
    DeviceKeyMaterial,
    RealAetherQProvider,
    generate_device_keys,
)
from distribos.application.command_service import CommandService
from distribos.application.projector import Projector
from distribos.domain.ids import HybridClock, new_device_id, new_tenant_id
from distribos.infrastructure.config import AppSettings, load_settings
from distribos.infrastructure.secret_store import SecretStore, default_secret_store
from distribos.persistence.base import Database
from distribos.persistence.models import EpochKeyRecord
from distribos.persistence.triggers import install_triggers
from distribos.sync.engine import SyncEngine
from distribos.sync.event_store import EventStore

logger = logging.getLogger(__name__)

#: Qurilma identiteti shu faylda saqlanadi (kalitlar o'ralgan holda).
IDENTITY_FILE = "device_identity.bin"


class SetupRequired(RuntimeError):
    """Korxona hali yaratilmagan — sozlash ustasi ochilishi kerak."""


@dataclass
class AppContext:
    """Ishlayotgan ilovaning barcha bog'liqliklari."""

    settings: AppSettings
    database: Database
    provider: RealAetherQProvider
    store: EventStore
    command: CommandService
    engine: SyncEngine
    invitations: InvitationRegistry
    secret_store: SecretStore
    device_id: bytes
    tenant_id: bytes
    transport: object | None = None

    def close(self) -> None:
        if self.transport is not None and hasattr(self.transport, "disconnect"):
            try:
                self.transport.disconnect()
            except Exception:
                logger.debug("Transportni yopishda xato", exc_info=True)
        self.database.dispose()

    def run_sync_cycle(self) -> tuple[int, int, int, int]:
        """Bitta sinxronizatsiya aylanishi. Fon oqimidan chaqiriladi."""
        published = self.engine.publish_pending()
        with self.database.unit_of_work() as session:
            self.command.replay_pending(session)
        queued, dead = self.engine.queue_depth()
        return published, self.engine.stats.received_events, queued, dead


def _identity_path(settings: AppSettings) -> Path:
    return settings.paths.data_dir / IDENTITY_FILE


def load_or_create_identity(
    settings: AppSettings, secret_store: SecretStore
) -> tuple[bytes, bytes, DeviceKeyMaterial]:
    """Qurilma identitetini yuklaydi yoki yangisini yaratadi.

    Maxfiy kalitlar OS himoyasi ostida (Windows DPAPI) yoziladi — diskda
    ochiq holda HECH QACHON yotmaydi.
    """
    import cbor2

    path = _identity_path(settings)
    context = b"DistribOS/device-identity/v1"

    if path.exists():
        raw = secret_store.unwrap(path.read_bytes(), context)
        data = cbor2.loads(raw)
        keys = DeviceKeyMaterial(
            device_id=bytes(data["device_id"]),
            sign_public_key=bytes(data["sign_pk"]),
            sign_private_key=_load_private(bytes(data["sign_sk"])),
            kem_public_key=bytes(data["kem_pk"]),
            kem_private_key=bytes(data["kem_sk"]),
        )
        return bytes(data["device_id"]), bytes(data["tenant_id"]), keys

    device_id = new_device_id()
    tenant_id = settings.tenant_id or new_tenant_id()
    keys = generate_device_keys(device_id)

    payload = cbor2.dumps({
        "device_id": device_id,
        "tenant_id": tenant_id,
        "sign_pk": keys.sign_public_key,
        "sign_sk": _private_bytes(keys.sign_private_key),
        "kem_pk": keys.kem_public_key,
        "kem_sk": keys.kem_private_key,
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(secret_store.wrap(payload, context))
    logger.info("Yangi qurilma identiteti yaratildi")
    return device_id, tenant_id, keys


def _private_bytes(private_key: object) -> bytes:
    """ML-DSA maxfiy kalitini saqlash uchun baytga aylantiradi.

    `private_bytes_raw()` faqat 32 baytlik urug'ni beradi va uni qayta
    yuklaydigan API `cryptography` da yo'q. Shuning uchun PKCS#8 DER
    ishlatamiz — u `load_der_private_key` bilan qaytariladi.
    """
    if isinstance(private_key, bytes):
        return private_key
    from cryptography.hazmat.primitives import serialization

    return private_key.private_bytes(  # type: ignore[union-attr]
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _load_private(raw: bytes) -> object:
    """Saqlangan ML-DSA maxfiy kalitini tiklaydi."""
    from cryptography.hazmat.primitives.serialization import load_der_private_key

    return load_der_private_key(raw, password=None)


def build_context(
    settings: AppSettings | None = None, *, allow_insecure_secrets: bool = False
) -> AppContext:
    """Ilovani yig'adi."""
    resolved = settings or load_settings()
    resolved.paths.ensure()

    secret_store = default_secret_store(allow_insecure=allow_insecure_secrets)
    device_id, tenant_id, keys = load_or_create_identity(resolved, secret_store)

    database = Database.open(resolved.paths.database_path)
    database.create_all()
    install_triggers(database.engine)

    provider = RealAetherQProvider(
        tenant_id=tenant_id,
        keys=keys,
        session_factory=database.session,
        profile_id=resolved.aether_profile_id,
        max_payload_bytes=resolved.mqtt.max_payload_bytes,
    )

    # Birinchi ishga tushirishda epoch kaliti yaratiladi.
    with database.session() as session:
        has_epoch = session.execute(
            select(EpochKeyRecord).where(
                EpochKeyRecord.tenant_id == tenant_id,
                EpochKeyRecord.is_current.is_(True),
            )
        ).scalar_one_or_none()
    if has_epoch is None:
        provider.rotate_keys()

    store = EventStore(device_id, tenant_id, HybridClock(device_id.hex()[:8]))
    projector = Projector()
    command = CommandService(store, projector, actor_role="owner")

    transport = _build_transport(resolved, tenant_id, device_id)
    engine = SyncEngine(
        device_id=device_id, store=store, provider=provider,
        transport=transport, session_factory=database.session, projector=projector,
    )
    if hasattr(transport, "attach_engine"):
        transport.attach_engine(engine)   # type: ignore[attr-defined]

    return AppContext(
        settings=resolved, database=database, provider=provider, store=store,
        command=command, engine=engine, invitations=InvitationRegistry(),
        secret_store=secret_store, device_id=device_id, tenant_id=tenant_id,
        transport=transport,
    )


def _build_transport(settings: AppSettings, tenant_id: bytes, device_id: bytes):
    """MQTT transportini yaratadi. Ulanish keyinroq, alohida bajariladi."""
    from distribos.mqtt.client import MqttTransport
    from distribos.mqtt.topics import TopicSpace

    topics = TopicSpace.create(tenant_id, settings.environment)
    transport = MqttTransport(settings.mqtt, topics, device_id)

    def attach_engine(engine: SyncEngine) -> None:
        transport._on_message = _make_message_handler(engine)  # noqa: SLF001

    transport.attach_engine = attach_engine   # type: ignore[attr-defined]
    return transport


def _make_message_handler(engine: SyncEngine):
    def handle(message) -> None:
        engine.handle_inbound(message.payload, message.channel)

    return handle
