"""Ulash sinovi uchun desktop tomoni.

Haqiqiy brokerga ulanadi, taklif yaratadi va telefonning JOIN_REQUEST ini
kutadi. Ulash oqimini **haqiqiy tarmoq ustida** tekshirish uchun.

    python tools/join_host.py

Chiqishda telefonga kiritiladigan kod ko'rsatiladi.

DIQQAT: bu sinov vositasi, mahsulot qismi emas. U `PUBLIC_PILOT`
brokeriga ulanadi va faqat namuna ma'lumot bilan ishlaydi.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "apps" / "desktop" / "src"))

from distribos.app_context import build_context  # noqa: E402
from distribos.domain.ids import opaque_tenant_topic_id, uuid7_str  # noqa: E402
from distribos.infrastructure.config import (  # noqa: E402
    AppSettings,
    MqttSettings,
    PathSettings,
)
from distribos.sync.event_store import NewEvent  # noqa: E402


def main() -> int:
    import tempfile

    workdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        tempfile.mkdtemp(prefix="distribos-host-")
    )
    settings = AppSettings(
        environment="pilot",
        mqtt=MqttSettings(),
        paths=PathSettings(
            data_dir=workdir / "data", log_dir=workdir / "logs",
            backup_dir=workdir / "backups",
        ),
        public_pilot_warning_accepted=True,
    )

    context = build_context(settings, allow_insecure_secrets=True)
    print(f"Desktop tayyor. Ma'lumot: {workdir}")
    print(f"Qurilma: {context.device_id.hex()[:8]}…")

    # Telefonga sinxronlanadigan namuna mahsulot.
    product_id = uuid7_str()
    with context.database.unit_of_work() as session:
        context.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "SINOV-1",
             "name": "Sinov mahsuloti", "unit": "dona",
             "wholesale_price": 1_234_500},
        ))
    print(f"Namuna mahsulot yaratildi: {product_id[:8]}…")

    context.transport.connect()   # type: ignore[union-attr]
    for _ in range(40):
        if context.transport.is_connected():   # type: ignore[union-attr]
            break
        time.sleep(0.5)
    if not context.transport.is_connected():   # type: ignore[union-attr]
        print("XATO: brokerga ulanib bo'lmadi")
        context.close()
        return 1
    print(f"Brokerga ulandi: {settings.mqtt.host}:{settings.mqtt.port}")

    invitation = context.invitations.issue(
        tenant_topic_id=opaque_tenant_topic_id(context.tenant_id),
        role="agent",
        display_name="Sinov telefoni",
        host_sign_public_key=context.provider.export_public_identity().sign_public_key,
        broker_host=settings.mqtt.host,
        broker_port=settings.mqtt.port,
        environment=settings.environment,
    )
    context.provisioning.remember(invitation)   # type: ignore[attr-defined]

    code = invitation.to_qr_payload().hex()
    print("\n" + "=" * 70)
    print("TELEFONGA KIRITILADIGAN KOD:")
    print(code)
    print("=" * 70 + "\n")
    (workdir / "join-code.txt").write_text(code, encoding="utf-8")
    print(f"Kod faylga ham yozildi: {workdir / 'join-code.txt'}")

    print("JOIN_REQUEST kutilmoqda (5 daqiqa)…")
    from distribos.persistence.models import PeerDevice

    deadline = time.monotonic() + 300
    joined = None
    while time.monotonic() < deadline:
        context.run_sync_cycle()
        with context.database.session() as session:
            joined = session.query(PeerDevice).filter(
                PeerDevice.device_id != context.device_id
            ).first()
            if joined is not None:
                name, state, role = joined.display_name, joined.state, joined.role
                break
        time.sleep(1)

    if joined is None:
        print("Telefon ulanmadi (vaqt tugadi).")
        context.close()
        return 1

    print(f"\nQURILMA ULANDI: {name}, rol {role}, holat {state}")

    # Egasi tasdiqlaydi — shundan keyin uning hodisalari qabul qilinadi.
    from distribos.sync.provisioning import confirm_pending_device

    with context.database.unit_of_work() as session:
        confirm_pending_device(session, joined.device_id)
    print("Qurilma TASDIQLANDI. Endi ma'lumot almashinadi.")

    print("\nSinxronizatsiya (180 s)…")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        context.run_sync_cycle()
        time.sleep(2)

    with context.database.session() as session:
        from distribos.persistence.models import EventLog, Order

        remote_events = session.query(EventLog).filter(
            EventLog.device_id != context.device_id
        ).count()
        orders = session.query(Order).count()
    print(f"Telefondan kelgan hodisalar: {remote_events}")
    print(f"Buyurtmalar: {orders}")

    context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
