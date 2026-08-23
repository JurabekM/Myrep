"""O'z aks-sadosini qabul qilmaslik.

MQTT brokeri yuborilgan xabarni BARCHA obunachilarga qaytaradi —
yuboruvchining o'ziga ham. Bu holat jonli sinovda aniqlandi: telefon o'z
hodisalarini qaytib oldi, o'ziga ACK yubordi va outbox'ni «peer qo'lladi»
deb belgiladi. Kompyuterda esa nol hodisa edi.

Ya'ni dastur YETKAZILMAGAN ma'lumotni yetkazilgan deb ko'rsatardi. Bu
sinov shuni qaytarmaslikni qulflaydi.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.sync.event_store import NewEvent
from harness import shared_tenant_setup


@pytest.fixture
def juftlik():
    bus, _tenant_id, (alfa, beta) = shared_tenant_setup("desktop-1", "android-1")
    return bus, alfa, beta


def _new_event(name: str = "Aks-sado mijozi") -> NewEvent:
    from distribos.domain.ids import uuid7_str

    customer_id = uuid7_str()
    return NewEvent(
        "CUSTOMER_CREATED", "Customer", customer_id,
        {"customer_id": customer_id, "code": "M-900", "name": name,
         "kind": "COMPANY", "price_tier": "wholesale", "credit_limit": 0},
    )


def test_oz_hodisasi_inbox_ga_tushmaydi(juftlik):
    """Yuborilgan hodisa yuboruvchining O'Z inbox'iga yozilmasin."""
    bus, alfa, beta = juftlik

    with alfa.database.unit_of_work() as session:
        alfa.command.submit(session, _new_event())

    alfa.engine.publish_pending()
    bus.pump()          # aks-sado ham, haqiqiy yetkazish ham shu yerda

    from distribos.persistence.models import InboxEntry

    with alfa.database.session() as session:
        own = session.query(InboxEntry).count()
    assert own == 0, "o'z hodisasi o'z inbox'iga tushdi"

    with beta.database.session() as session:
        theirs = session.query(InboxEntry).count()
    assert theirs == 1, "peer hodisani olmadi"


def test_oz_ack_i_yetkazildi_deb_belgilamaydi(juftlik):
    """Aks-sado peer tasdig'i o'rniga o'tmasin."""
    bus, alfa, beta = juftlik

    with alfa.database.unit_of_work() as session:
        alfa.command.submit(session, _new_event())

    alfa.engine.publish_pending()

    # Peer'ni o'chirib qo'yamiz: u xabarni umuman ko'rmaydi, faqat
    # bizning aks-sadomiz qaytadi.
    bus.set_online(beta.device_id, False)
    bus.pump()

    from distribos.persistence.models import OutboxEntry

    with alfa.database.session() as session:
        states = {e.state for e in session.query(OutboxEntry).all()}
    assert "PEER_APPLIED" not in {str(s) for s in states}, (
        "hech kim olmagan hodisa 'peer qo'lladi' deb belgilandi"
    )


def test_aks_sado_soxta_hujum_yozuvi_yaratmaydi(juftlik):
    """Aks-sado replay oynasiga TUSHMASIN.

    Aks holda har yuborilgan xabar bitta soxta «replay hujumi» yozuvini
    qoldiradi. Jonli sinovda 3 daqiqada 83 ta shunday yozuv to'plandi —
    va HAQIQIY hujum ular orasida ko'rinmay qolardi.
    """
    bus, alfa, beta = juftlik

    for _ in range(5):
        with alfa.database.unit_of_work() as session:
            alfa.command.submit(session, _new_event())
        alfa.engine.publish_pending()
        bus.pump()

    from distribos.persistence.models import DeadLetter

    with alfa.database.session() as session:
        soxta = session.query(DeadLetter).filter(
            DeadLetter.reason == "REPLAY"
        ).count()

    assert soxta == 0, f"o'z aks-sadosidan {soxta} ta soxta hujum yozuvi paydo bo'ldi"


def test_aks_sado_rad_etish_hisoblagichini_shishirmaydi(juftlik):
    """Foydalanuvchiga ko'rsatiladigan xato soni to'g'ri bo'lsin."""
    bus, alfa, _beta = juftlik

    with alfa.database.unit_of_work() as session:
        alfa.command.submit(session, _new_event())
    alfa.engine.publish_pending()
    bus.pump()

    assert alfa.engine.stats.rejected == 0, (
        "o'z xabarimiz rad etilgan deb sanaldi"
    )
