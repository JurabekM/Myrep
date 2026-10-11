"""Ikkinchi qurilma (desktop tomondan, sarlavhasiz) — telefon egasi bilan sinxron va kirim sinovi uchun.

Nima qiladi: juftlash kodi bilan do'konga qo'shiladi (join_request), egasi tasdig'ini kutadi, snapshot oladi.
--receipt bo'lsa, tasdiqlangan egasi sifatida tovarga kirim yozadi (qoldiqni to'ldirish uchun).
Kelgan har bir savdo va qoldiq chop etiladi. Har bir operatsiya bir marta qo'llanganini ko'rsatadi.

Ishga tushirish (desktop venv'dan):
    python tools/joiner_daemon.py "<juftlash kodi>" --receipt 20 --seconds 900
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop"))

from omborai_desktop import auth  # noqa: E402
from omborai_desktop.offline.store import APPLIED, LocalStore  # noqa: E402
from omborai_desktop.sync import ops as o  # noqa: E402
from omborai_desktop.sync.identity import DeviceIdentity  # noqa: E402
from omborai_desktop.sync.mqtt_sync import MqttSync  # noqa: E402

PRODUCT_NAME = "Un"
JOIN_RETRY_S = 5
SNAPSHOT_RETRY_S = 5
STATUS_EVERY_S = 10


def log(text: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + text, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("code")
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--host", default="broker.hivemq.com")
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--receipt", type=str, default="", help="egasi sifatida kirim miqdori (masalan 20)")
    parser.add_argument("--seed-file", default=str(Path(__file__).resolve().parent / "joiner_seed.bin"))
    args = parser.parse_args()

    store_id, owner_device_id, owner_pk, key_hex = auth.parse_pairing_code(args.code)
    key = bytes.fromhex(key_hex)
    # Qurilma kaliti saqlanadi: qayta ishga tushganda ham bir xil qurilma (tasdiq saqlanadi)
    seed_path = Path(args.seed_file)
    if seed_path.exists():
        seed = seed_path.read_bytes()
    else:
        seed = os.urandom(32)
        seed_path.write_bytes(seed)
    local = LocalStore(identity=DeviceIdentity(seed))
    local.set_pairing(store_id, owner_device_id, owner_pk)
    log(f"Juftlandi: do'kon {store_id[:8]}, egasi {owner_device_id[:8]}, qurilma {local.device_id()[:8]}")

    counters = {"sales": 0, "receipt_sent": False}

    def apply_remote(op: dict) -> str:
        result = local.apply_op(op)
        if op["type"] == o.SALE:
            payload = op["payload"]
            if result == APPLIED:
                counters["sales"] += 1
                log(f"Savdo keldi: {payload['number']} jami={payload['total']} so'm (qo'llandi)")
            else:
                log(f"Savdo keldi: {payload['number']} — natija: {result}")
        elif op["type"] == o.REFUND:
            log(f"Qaytarish keldi: sale={op['payload']['sale_id'][:8]} — natija: {result}")
        return result

    sync = MqttSync(key, device_id=local.device_id(), apply_op=apply_remote,
                    host=args.host, port=args.port, tls=not args.plain)
    sync.start()
    log("MQTT ulandi. Egasi qurilmasi tasdiqlashini kutilmoqda (Foydalanuvchilar va qurilmalar > Yangi so'rov).")

    product_id = None
    last_join = last_snap = last_status = 0.0
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            row = local.device_row(local.device_id())
            approved = row is not None and bool(row["active"])
            if not approved:
                if now - last_join >= JOIN_RETRY_S:
                    sync.send(local.join_request("Joiner sinovi"))
                    last_join = now
            elif not local.is_bootstrapped():
                if now - last_snap >= SNAPSHOT_RETRY_S:
                    sync.send(local.new_op(o.SNAPSHOT_REQUEST, {}))
                    last_snap = now
                    log("Snapshot so'raldi")
            else:
                if product_id is None:
                    rows = local._db.execute(
                        "SELECT id FROM products WHERE name = ? AND deleted = 0", (PRODUCT_NAME,)
                    ).fetchall()
                    if rows:
                        first = rows[0]
                        product_id = first["id"] if isinstance(first, dict) else first[0]
                        log(f"Tovar topildi: {PRODUCT_NAME} id={product_id[:8]}")
                        log(f"Qoldiq (boshlang'ich): {local.balance(local.get_state('store_id'), product_id)}")
                if product_id and args.receipt and not counters["receipt_sent"]:
                    if local.is_owner_device(local.device_id()):
                        receipt = local.new_op(
                            o.MOVEMENT, {"product_id": product_id, "qty": args.receipt, "kind": "receipt"}
                        )
                        local.apply_op(receipt)
                        sync.send(receipt)
                        counters["receipt_sent"] = True
                        log(f"Kirim yuborildi: +{args.receipt}")
                    else:
                        log("Kirim uchun qurilma egasi sifatida tasdiqlanishi kerak (hozir kassir)")
                        counters["receipt_sent"] = True
                if product_id and now - last_status >= STATUS_EVERY_S:
                    store = local.get_state("store_id")
                    role = "egasi" if local.is_owner_device(local.device_id()) else "kassir"
                    log(f"Holat: rol={role} savdolar={counters['sales']} "
                        f"qoldiq={local.balance(store, product_id)}")
                    last_status = now
            time.sleep(1)
    finally:
        sync.stop()
        log("Joiner to'xtatildi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
