"""Ikki tugun HAQIQIY MQTT broker orqali sinxronlanadi — lekin lokal.

Bu sinov ataylab `tests/harness.py` dagi `LoopbackBus`ni ISHLATMAYDI.
O'sha soxta avtobus xabarni yuboruvchiga qaytarmasdi — haqiqiy broker
esa qaytaradi — va aynan shu farq bir nechta jiddiy xatoni (o'z
aks-sadosi, ikki marta obuna) uzoq vaqt yashirdi. Ular faqat
`broker.hivemq.com` ustidagi qo'lda sinovda ochildi (`docs/HOLAT.md`
§6.1).

CI esa ochiq brokerga bog'liq bo'lishi mumkin emas (ADR-0002). Shuning
uchun bu yerda **lokal, konteynerlashtirilgan** Mosquitto ishlatiladi
(`tests/integration/broker.py`) — TLS bilan, xuddi `PRIVATE_PRODUCTION`
profilidagidek. Docker yo'q bo'lsa sinov o'tkazib yuboriladi.
"""

from __future__ import annotations

import os
import time

import pytest
from broker import LocalMosquittoBroker, docker_available
from distribos.aether_q.real import (
    RealAetherQProvider,
    _key_context,
    generate_device_keys,
)
from distribos.application.command_service import CommandService
from distribos.application.projector import Projector
from distribos.domain.ids import HybridClock, new_device_id, new_tenant_id, uuid7_str
from distribos.infrastructure.config import MqttProfile, MqttSettings
from distribos.infrastructure.secret_store import default_secret_store
from distribos.mqtt.client import MqttTransport
from distribos.mqtt.topics import TopicSpace
from distribos.persistence.base import Database
from distribos.persistence.models import DeviceState, EpochKeyRecord, PeerDevice
from distribos.persistence.triggers import install_triggers
from distribos.sync.engine import SyncEngine
from distribos.sync.event_store import EventStore, NewEvent

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def broker(tmp_path_factory):
    if not docker_available():
        pytest.skip("Docker mavjud emas — lokal broker sinovi o'tkazib yuborildi")
    handle = LocalMosquittoBroker(tmp_path_factory.mktemp("mosquitto"))
    with handle as info:
        yield info


class _LiveNode:
    """`tests/harness.Node` bilan bir xil rol, lekin HAQIQIY transport."""

    def __init__(
        self, name: str, tenant_id: bytes, broker_info, epoch_root: bytes, db_path,
    ):
        self.name = name
        self.tenant_id = tenant_id
        self.device_id = new_device_id()
        self.keys = generate_device_keys(self.device_id)

        # FAYL asosidagi baza — `in_memory()` EMAS. `in_memory()`
        # `StaticPool` ishlatadi: BITTA ulanish barcha sessiyalar
        # orasida bo'lishiladi. Bu yerda esa haqiqiy ko'p oqimli holat
        # bor — MQTT xabari paho'ning FON OQIMIDA keladi
        # (`transport.connect()` -> `loop_start()`), shu payt asosiy
        # oqim `publish_pending()` chaqirishi mumkin. Fayl bazasi
        # (production'dagidek WAL + alohida ulanishlar) buni xavfsiz
        # qo'llab-quvvatlaydi, `StaticPool` esa ikki oqimni bitta
        # ulanishga urib, `StaleDataError` beradi — bu PRODUCTION xatosi
        # emas, faqat `in_memory()` ni noto'g'ri (ko'p oqimli) sharoitda
        # ishlatish xatosi.
        self.database = Database.open(db_path)
        self.database.create_all()
        install_triggers(self.database.engine)

        store_secret = default_secret_store(allow_insecure=True)
        with self.database.unit_of_work() as session:
            session.add(EpochKeyRecord(
                epoch=1, key_id=1, tenant_id=tenant_id,
                root_secret_wrapped=store_secret.wrap(
                    epoch_root, _key_context(1, 1)
                ),
                profile_id=0x01, is_current=True,
            ))

        self.provider = RealAetherQProvider(
            tenant_id=tenant_id, keys=self.keys,
            session_factory=self.database.session, profile_id=0x01,
        )
        self.store = EventStore(
            self.device_id, tenant_id, HybridClock(self.device_id.hex()[:8])
        )
        self.command = CommandService(self.store, Projector(), actor_role="owner")

        mqtt_settings = MqttSettings(
            profile=MqttProfile.PRIVATE_PRODUCTION,
            host=broker_info.host, port=broker_info.port,
            tls_required=True, ca_cert_path=broker_info.ca_cert_path,
            session_expiry_seconds=30, keepalive_seconds=10,
        )
        topics = TopicSpace.create(tenant_id, "integration-test")
        self.transport = MqttTransport(mqtt_settings, topics, self.device_id)
        self.engine = SyncEngine(
            device_id=self.device_id, store=self.store, provider=self.provider,
            transport=self.transport, session_factory=self.database.session,
            projector=Projector(),
        )
        self.transport._on_message = (
            lambda message: self.engine.handle_inbound(message.payload, message.channel)
        )

    def connect(self, *, timeout: float = 10.0) -> None:
        self.transport.connect(timeout=timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.transport.is_connected():
                return
            time.sleep(0.1)
        raise TimeoutError(f"{self.name} brokerga ulanmadi")

    def close(self) -> None:
        self.transport.disconnect()
        self.database.dispose()


def _introduce(*nodes: _LiveNode) -> None:
    """BOOT-1'ni chetlab, bir-birini ACTIVE peer deb yozadi.

    BOOT-1'ning o'zi `broker.hivemq.com` ustida allaqachon uchidan-uchiga
    sinaldi (`docs/HOLAT.md` §5.1). Bu yerdagi maqsad — DES-1 ustidagi
    sinxronizatsiya (o'z aks-sadosi, anti-entropiya, idempotent obuna)
    HAQIQIY soket ustida ishlashini tekshirish, ulash oqimini emas.
    """
    for node in nodes:
        with node.database.unit_of_work() as session:
            for peer in nodes:
                if peer.device_id == node.device_id:
                    continue
                session.add(PeerDevice(
                    device_id=peer.device_id, tenant_id=peer.tenant_id,
                    display_name=peer.name, platform="desktop", role="owner",
                    sign_public_key=peer.keys.sign_public_key,
                    kem_public_key=peer.keys.kem_public_key,
                    state=DeviceState.ACTIVE, is_full_replica=True,
                ))


def _wait_until(condition, *, timeout: float = 15.0, interval: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return condition()


@pytest.fixture
def live_pair(broker, tmp_path):
    tenant_id = new_tenant_id()
    epoch_root = os.urandom(32)
    alfa = _LiveNode("alfa", tenant_id, broker, epoch_root, tmp_path / "alfa.sqlite3")
    beta = _LiveNode("beta", tenant_id, broker, epoch_root, tmp_path / "beta.sqlite3")
    _introduce(alfa, beta)
    alfa.connect()
    beta.connect()
    try:
        yield alfa, beta
    finally:
        alfa.close()
        beta.close()


def test_hodisa_haqiqiy_broker_orqali_yetadi(live_pair):
    alfa, beta = live_pair
    customer_id = uuid7_str()

    with alfa.database.unit_of_work() as session:
        alfa.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "M-100", "name": "Lokal broker mijozi",
             "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 0},
        ))
    alfa.engine.publish_pending()

    from distribos.persistence.models import Customer

    def yetdimi() -> bool:
        with beta.database.session() as session:
            return session.get(Customer, customer_id) is not None

    assert _wait_until(yetdimi), "hodisa haqiqiy brokerdan beta'ga yetmadi"


def test_oz_aks_sadosi_qabul_qilinmaydi(live_pair):
    """Sessiyaning eng katta saboqi — HAQIQIY soketda qulflanadi.

    `LoopbackBus` bu xatoni ko'rsatmasdi (yuboruvchini chetlab o'tardi).
    Haqiqiy broker xabarni yuboruvchiga ham qaytaradi.

    DIQQAT: agar `sync/engine.py` dagi ikki aniq to'siq (§6.1,
    "o'z aks-sadosi peer tasdig'i o'rniga o'tardi") olib tashlansa,
    o'z inbox'i baribir bo'sh qoladi — chunki `peer.state != ACTIVE`
    tekshiruvi (yuboruvchi o'zini o'z peer reyestrida yo'q) buni allaqachon
    to'sadi. LEKIN o'sha holatda har self-echo bitta BEHUDA
    `dead_letter` yozuvini (`UNKNOWN_SENDER`) qoldiradi — bu esa
    foydalanuvchiga «qabul qilinmagan» sonini soxta oshiradi. Aniq
    to'siq buni OLDINDAN, ochishga urinmasdan tashlab yuboradi — shu
    farq shu yerda sinaladi.
    """
    alfa, _beta = live_pair
    customer_id = uuid7_str()

    with alfa.database.unit_of_work() as session:
        alfa.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", customer_id,
            {"customer_id": customer_id, "code": "M-101", "name": "Ikkinchi mijoz",
             "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 0},
        ))
    alfa.engine.publish_pending()

    from distribos.persistence.models import DeadLetter, InboxEntry

    time.sleep(3)   # aks-sado kelishi uchun yetarli vaqt

    with alfa.database.session() as session:
        oz_inboxi = session.query(InboxEntry).count()
        barcha_rad_etilgan = session.query(DeadLetter).count()

    assert oz_inboxi == 0, "o'z hodisasi o'z inbox'iga tushdi"
    assert barcha_rad_etilgan == 0, (
        "aks-sado behuda dead-letter yozuvi qoldirdi — 'qabul qilinmagan' "
        "sonini soxta oshiradi"
    )


def test_ikkala_yonalish_ishlaydi(live_pair):
    """Har ikki tomon ham bir-biriga hodisa yubora oladi."""
    alfa, beta = live_pair
    from distribos.persistence.models import Customer

    alfa_id, beta_id = uuid7_str(), uuid7_str()
    with alfa.database.unit_of_work() as session:
        alfa.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", alfa_id,
            {"customer_id": alfa_id, "code": "M-200", "name": "Alfadan",
             "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 0},
        ))
    with beta.database.unit_of_work() as session:
        beta.command.submit(session, NewEvent(
            "CUSTOMER_CREATED", "Customer", beta_id,
            {"customer_id": beta_id, "code": "M-201", "name": "Betadan",
             "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 0},
        ))
    alfa.engine.publish_pending()
    beta.engine.publish_pending()

    def yakunlandimi() -> bool:
        with alfa.database.session() as session:
            alfa_ok = session.get(Customer, beta_id) is not None
        with beta.database.session() as session:
            beta_ok = session.get(Customer, alfa_id) is not None
        return alfa_ok and beta_ok

    assert _wait_until(yakunlandimi), "ikki yo'nalishli sinxronizatsiya yakunlanmadi"
