"""Ochiq matn brokerga CHIQMASLIGINI qulflaydi.

Bu topshiriqning eng qat'iy talablaridan biri: MQTT'ga chiqadigan har
bayt yo DES-1 bilan muhrlangan, yo BOOT-1 bilan shifrlangan bo'lishi
kerak. Bitta e'tiborsizlik butun korxona ma'lumotini ochiq brokerga
chiqarib yuborishi mumkin.

Shuning uchun bu qoida **tip darajasida** va **test bilan** ikki marta
qulflanadi.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.aether_q.provider import SealedEnvelope  # noqa: E402
from distribos.mqtt.client import MqttTransport, MqttTransportError  # noqa: E402
from distribos.mqtt.topics import Channel  # noqa: E402


def test_publish_accepts_only_sealed_envelopes() -> None:
    """`publish()` imzosi xom `bytes` ni QABUL QILMAYDI.

    Bu tip darajasidagi himoya: ochiq matnni tasodifan yuborish uchun
    avval uni `SealedEnvelope` ga o'rash kerak bo'ladi, ya'ni dasturchi
    buni ATAYLAB qilishi kerak.
    """
    # `from __future__ import annotations` tufayli izohlar MATN bo'ladi,
    # shuning uchun ularni ataylab hal qilamiz.
    hints = inspect.get_annotations(MqttTransport.publish, eval_str=True)
    assert hints["envelope"] is SealedEnvelope, (
        f"publish() faqat SealedEnvelope qabul qilishi kerak, hozir: {hints['envelope']}"
    )


def test_publish_raw_is_restricted_to_bootstrap_channel() -> None:
    """`publish_raw()` faqat `protocol-control` da ishlaydi.

    U qurilmani ulash uchun kerak (yangi qurilmada epoch kaliti yo'q),
    lekin boshqa kanalda ishlatilsa bu ochiq matn yuborish bo'lardi.
    """
    transport = MqttTransport.__new__(MqttTransport)   # __init__ siz

    for channel in Channel:
        if channel is Channel.PROTOCOL_CONTROL:
            continue
        with pytest.raises(MqttTransportError, match="protocol-control"):
            MqttTransport.publish_raw(transport, b"ochiq matn", channel)


def test_engine_only_publishes_through_provider() -> None:
    """Dvigatel transportga FAQAT provayder muhrlagan narsani beradi.

    `SyncEngine` manbasida `_transport.publish(` chaqiruvlari bor; ularning
    har birida argument `provider.seal_message(...)` natijasi yoki shundan
    kelib chiqqan o'zgaruvchi bo'lishi kerak.
    """
    import ast

    from distribos.sync import engine as engine_module

    source = Path(engine_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    #: `publish()` ning birinchi argumenti sifatida ruxsat etilgan shakllar.
    #: Ko'p qatorli chaqiruvlar uchun matn bo'yicha qidirish ishonchsiz,
    #: shuning uchun AST ishlatiladi.
    allowed_names = {"envelope", "sealed"}
    problems: list[str] = []
    raw_calls = 0

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr == "publish_raw":
            raw_calls += 1
            continue

        if node.func.attr != "publish" or not node.args:
            continue

        first = node.args[0]
        if isinstance(first, ast.Name) and first.id in allowed_names:
            continue
        # `self._provider.seal_message(...)` to'g'ridan-to'g'ri berilgan
        if (
            isinstance(first, ast.Call)
            and isinstance(first.func, ast.Attribute)
            and first.func.attr == "seal_message"
        ):
            continue
        problems.append(f"{node.lineno}-qator: {ast.dump(first)[:80]}")

    assert not problems, (
        "publish() ga muhrlanmagan argument berilgan:\n" + "\n".join(problems)
    )
    assert raw_calls == 1, f"publish_raw {raw_calls} marta chaqirilgan, 1 kutilgan"
    assert "_handle_bootstrap" in source


def test_boot1_response_does_not_contain_plaintext_secret() -> None:
    """BOOT-1 javobidagi epoch kaliti simda OCHIQ ko'rinmaydi."""
    import os

    from distribos.aether_q import boot1

    secret = os.urandom(32)
    epoch_root = os.urandom(32)
    wire = boot1.build_join_response(
        invitation_id=os.urandom(8),
        invitation_secret=secret,
        tenant_id=os.urandom(16),
        epoch=1, key_id=1,
        epoch_root_secret=epoch_root,
        profile_id=0x01, role="agent",
        host_device_id=os.urandom(16),
        host_sign_public_key=bytes(1952),
    )
    assert epoch_root not in wire, "epoch kaliti simga ochiq chiqdi"


def test_boot1_request_does_not_leak_invitation_secret() -> None:
    """Taklif siri so'rov ichida ochiq ketmaydi."""
    import os

    from distribos.aether_q import boot1

    secret = os.urandom(32)
    wire = boot1.build_join_request(
        invitation_id=os.urandom(8),
        invitation_secret=secret,
        device_id=os.urandom(16),
        sign_public_key=bytes(1952),
        kem_public_key=bytes(1184),
        platform="android",
        display_name="Test",
    )
    assert secret not in wire, "taklif siri simga ochiq chiqdi"


def test_business_data_never_reaches_the_wire() -> None:
    """To'liq oqim: hodisa yaratiladi va simdagi baytlar tekshiriladi."""
    from harness import shared_tenant_setup

    from distribos.domain.ids import uuid7_str
    from distribos.sync.event_store import NewEvent

    bus, _tenant, (desktop, _phone) = shared_tenant_setup("desktop-1", "android-1")

    secrets = ["Maxfiy Korxona MChJ", "+998901234567", "Juda Nodir Mahsulot"]
    product_id = uuid7_str()
    with desktop.database.unit_of_work() as session:
        desktop.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "NODIR-1",
             "name": secrets[2], "unit": "dona", "wholesale_price": 1_000_000},
        ))
    desktop.sync()

    assert bus.wire_log, "hech narsa yuborilmadi"
    blob = b"".join(bus.wire_log)
    for value in secrets:
        assert value.encode("utf-8") not in blob, f"ochiq matn simga chiqdi: {value}"

    # Topiklarda ham maxfiy ma'lumot yo'q.
    from distribos.mqtt.topics import assert_no_plaintext_identifiers

    for topic, _qos in desktop.topics.all_subscriptions(desktop.device_id):
        assert_no_plaintext_identifiers(topic, secrets)
