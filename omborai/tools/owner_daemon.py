"""Egasi qurilmasi (desktop tomondan, sarlavhasiz) — telefon bilan haqiqiy E2E sinovi uchun.

Nima qiladi: do'kon yaratadi (egasi hisobi, tovar, qoldiq), juftlash kodini chiqaradi, kassa so'rovini
avtomatik tasdiqlaydi (kassir sifatida), snapshot javob beradi, kassadan kelgan savdoni qabul qiladi va
(--auto-refund bo'lsa) qaytaradi. Har bir qadam chop etiladi. Telefon (Dart) imzolari shu yerda tekshiriladi.

Ishga tushirish (desktop venv'dan):
    python tools/owner_daemon.py --seconds 900
"""

import argparse
import sys
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop"))

from omborai_desktop import auth  # noqa: E402
from omborai_desktop.offline.store import APPLIED, LocalStore  # noqa: E402
from omborai_desktop.sync import ops as o  # noqa: E402
from omborai_desktop.sync.crypto import generate_store_key  # noqa: E402
from omborai_desktop.sync.identity import DeviceIdentity  # noqa: E402
from omborai_desktop.sync.mqtt_sync import MqttSync  # noqa: E402

PRODUCT_ID = "00000000-0000-0000-0000-00000000f00d"
OWNER_LOGIN = "egasi"
OWNER_PASSWORD = "parol-12345"


def log(text: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + text, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--host", default="broker.hivemq.com")
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--auto-refund", action="store_true", help="qabul qilingan savdoni qaytaradi")
    args = parser.parse_args()

    key = generate_store_key()
    store_id = str(uuid.uuid4())
    owner = LocalStore(identity=DeviceIdentity.generate())
    owner.init_owner(store_id, "egasi-desktop")
    salt, digest = auth.hash_password(OWNER_PASSWORD)
    owner.apply_op(owner.new_op(o.STORE, {"name": "Telefon sinovi do'koni"}))
    owner.apply_op(
        owner.new_op(
            o.USER,
            {"id": str(uuid.uuid4()), "login": OWNER_LOGIN, "name": "Egasi", "role": o.ROLE_OWNER,
             "salt": salt, "pw_hash": digest, "active": True},
        )
    )
    owner.apply_op(
        owner.new_op(
            o.PRODUCT,
            {"id": PRODUCT_ID, "name": "Un", "unit": "kg", "sale_price": 10000, "cost_price": 0,
             "min_stock": "0", "barcodes": ["4780000001"], "deleted": False},
        )
    )
    owner.apply_op(owner.new_op(o.MOVEMENT, {"product_id": PRODUCT_ID, "qty": "20", "kind": "receipt"}))

    def in_worker(fn):
        return lambda arg: threading.Thread(target=fn, args=(arg,), daemon=True).start()

    def on_join(request: dict) -> None:
        if not owner.verify_join_request(request):
            return
        payload = request["payload"]
        approval = owner.new_op(
            o.DEVICE,
            {"device_id": payload["device_id"], "public_key": payload["public_key"], "role": o.ROLE_CASHIER,
             "label": payload.get("label", ""), "active": True},
        )
        if owner.apply_op(approval) == APPLIED:
            log(f"Kassa tasdiqlandi: {payload.get('label', '')!r} ({payload['device_id'][:8]})")
            sync.send(approval)

    def on_request(request: dict) -> None:
        if not owner.is_owner_device(owner.device_id()) or not owner.is_active_device_op(request):
            return
        log(f"Snapshot so'rovi: {request['device'][:8]} — snapshot yuborilmoqda")
        sync.send(owner.new_op(o.SNAPSHOT, owner.snapshot_payload(store_id)))

    def apply_remote(op: dict) -> str:
        result = owner.apply_op(op)
        if op["type"] == o.SALE and result == APPLIED:
            payload = op["payload"]
            log(f"Telefon savdosi qabul qilindi: {payload['number']} jami={payload['total']} so'm")
            if args.auto_refund:
                refund = owner.new_op(
                    o.REFUND,
                    {"sale_id": payload["id"],
                     "items": [{"product_id": i["product_id"], "qty": i["qty"]} for i in payload["items"]]},
                    op_id=o.refund_op_id(payload["id"]),
                )
                owner.apply_op(refund)
                # paho callback ichida send() PUBACK'ni kutib bloklanardi: alohida thread
                threading.Thread(target=sync.send, args=(refund,), daemon=True).start()
                log(f"Savdo qaytarildi: {payload['number']}; qoldiq={owner.balance(store_id, PRODUCT_ID)}")
        elif op["type"] == o.SALE:
            log(f"Savdo qo'llanmadi: {result}")
        return result

    sync = MqttSync(key, device_id=owner.device_id(), apply_op=apply_remote,
                    on_request=in_worker(on_request), on_join_request=in_worker(on_join),
                    host=args.host, port=args.port, tls=not args.plain)
    sync.start()
    code = f"{store_id}:{owner.device_id()}:{owner.public_key_hex()}:{key.hex()}"
    log("Egasi qurilmasi ishga tushdi. Juftlash kodi (telefonga kiriting):")
    print(code, flush=True)
    log(f"Login: {OWNER_LOGIN} / {OWNER_PASSWORD}; tovar: Un 10000 so'm, qoldiq 20 kg")
    try:
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            time.sleep(1)
    finally:
        sync.stop()
        log("Egasi qurilmasi to'xtatildi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
