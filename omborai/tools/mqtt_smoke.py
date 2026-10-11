"""Haqiqiy MQTT broker bilan to'liq sikl (protokol v2) — mock yo'q.

Egasi qurilmasi va kassa qurilmasi broker orqali juftlanadi: kod -> join_request -> egasi tasdig'i -> snapshot
-> kassada savdo -> egasida qabul -> egasi qaytarishi -> kassada qabul. Har bir qadam chop etiladi.

Ishga tushirish (desktop venv'dan):
    python tools/mqtt_smoke.py
    python tools/mqtt_smoke.py --host broker.hivemq.com --port 8883
Muvaffaqiyatsiz bo'lsa exit code 1.
"""

import argparse
import os
import sys
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop"))

from omborai_desktop.money import round_som  # noqa: E402
from omborai_desktop.offline.store import APPLIED, LocalStore  # noqa: E402
from omborai_desktop.sync import ops as o  # noqa: E402
from omborai_desktop.sync.crypto import generate_store_key  # noqa: E402
from omborai_desktop.sync.identity import DeviceIdentity  # noqa: E402
from omborai_desktop.sync.mqtt_sync import MqttSync  # noqa: E402

TIMEOUT_S = 90
PRODUCT_ID = str(uuid.uuid4())
results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'OK ' if ok else 'XATO'}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def wait_until(predicate, timeout: float = TIMEOUT_S, interval: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="broker.hivemq.com")
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--plain", action="store_true", help="TLS'siz (lokal broker uchun)")
    args = parser.parse_args()
    tls = not args.plain

    key = generate_store_key()  # sinov uchun tasodifiy kalit: mavzu ham tasodifiy, boshqalar ko'rmaydi
    store_id = str(uuid.uuid4())

    owner = LocalStore(identity=DeviceIdentity.generate())
    owner.init_owner(store_id, "egasi")
    owner.apply_op(owner.new_op(o.STORE, {"name": "Smoke do'kon"}))
    owner.apply_op(owner.new_op(o.PRODUCT, {"id": PRODUCT_ID, "name": "Un", "unit": "kg", "sale_price": 10000,
                                            "cost_price": 0, "min_stock": "0", "barcodes": [],
                                            "deleted": False}))
    owner.apply_op(owner.new_op(o.MOVEMENT, {"product_id": PRODUCT_ID, "qty": "10", "kind": "receipt"}))

    def in_worker(fn):
        """Handler'ni alohida thread'da bajaradi: paho loop thread'ida send() PUBACK'ni kutib bloklanardi."""
        return lambda arg: threading.Thread(target=fn, args=(arg,), daemon=True).start()

    def owner_on_request(request: dict) -> None:
        if owner.is_owner_device(owner.device_id()) and owner.is_active_device_op(request):
            owner_sync.send(owner.new_op(o.SNAPSHOT, owner.snapshot_payload(store_id)))

    def owner_on_join(request: dict) -> None:
        if not owner.verify_join_request(request):
            return
        approval = owner.new_op(
            o.DEVICE,
            {"device_id": request["payload"]["device_id"], "public_key": request["payload"]["public_key"],
             "role": o.ROLE_CASHIER, "label": request["payload"].get("label", ""), "active": True},
        )
        if owner.apply_op(approval) == APPLIED:
            owner_sync.send(approval)

    owner_sync = MqttSync(key, device_id=owner.device_id(), apply_op=owner.apply_op,
                          on_request=in_worker(owner_on_request), on_join_request=in_worker(owner_on_join),
                          host=args.host, port=args.port, tls=tls)
    cashier = LocalStore(identity=DeviceIdentity.generate())
    cashier_sync = MqttSync(key, device_id=cashier.device_id(), apply_op=cashier.apply_op,
                            host=args.host, port=args.port, tls=tls)
    try:
        owner_sync.start()
        step("egasi qurilmasi brokerga ulandi", True, args.host)
        cashier.set_pairing(store_id, owner.device_id(), owner.public_key_hex())
        cashier_sync.start()
        step("kassa qurilmasi brokerga ulandi", True)

        # 1) qo'shilish: kassa so'raydi, egasi tasdiqlaydi
        def joined() -> bool:
            row = cashier.device_row(cashier.device_id())
            if row is None or not row["active"]:
                cashier_sync.send(cashier.join_request("smoke-kassa"))
                return False
            return True

        ok = wait_until(joined, interval=2.0)
        step("kassa egasi tomonidan tasdiqlandi (join_request -> device)", ok)
        if not ok:
            return 1

        # 2) bootstrap: snapshot kelguncha so'rab turamiz
        def bootstrapped() -> bool:
            if not cashier.is_bootstrapped():
                cashier_sync.send(cashier.new_op(o.SNAPSHOT_REQUEST, {}))
                return False
            return True

        ok = wait_until(bootstrapped, interval=3.0)
        step("kassa snapshot oldi (bootstrap)", ok)
        if not ok:
            return 1
        balance_ok = cashier.balance(store_id, PRODUCT_ID) == Decimal(10)
        step("katalog va qoldiq keldi", balance_ok and cashier.get_product(PRODUCT_ID, store_id) is not None,
             f"qoldiq={cashier.balance(store_id, PRODUCT_ID)}")

        # 3) savdo kassada: imzolangan, egasida qabul qilinadi
        shift_id = str(uuid.uuid4())
        shift = cashier.new_op(o.SHIFT_OPEN, {"shift_id": shift_id, "opening_cash": 0}, op_id=shift_id)
        cashier.apply_op(shift)
        cashier_sync.send(shift)
        line = round_som(Decimal("2") * 10000)
        sale_id = str(uuid.uuid4())
        sale_payload = {
            "id": sale_id, "store_id": store_id,
            "items": [{"product_id": PRODUCT_ID, "qty": "2", "product_name": "Un", "unit": "kg",
                       "unit_price": 10000, "line_total": line}],
            "discount": 0, "subtotal": line, "total": line,
            "payments": [{"method": "cash", "amount": line}], "shift_id": shift_id,
            "number": "SMOKE-1", "created_at": o.now_ts(),
        }
        sale = cashier.new_op(o.SALE, sale_payload, op_id=sale_id)
        cashier.apply_op(sale)
        cashier_sync.send(sale)
        ok = wait_until(lambda: owner.get_sale(sale_id) is not None, timeout=TIMEOUT_S)
        step("egasi kassadagi savdoni qabul qildi", ok,
             f"egasi qoldig'i={owner.balance(store_id, PRODUCT_ID)}")
        if not ok:
            return 1
        step("qoldiq ikkala qurilmada bir xil", owner.balance(store_id, PRODUCT_ID)
             == cashier.balance(store_id, PRODUCT_ID) == Decimal(8))

        # 4) qaytarish egasida, kassada qabul qilinadi
        refund = owner.new_op(o.REFUND, {"sale_id": sale_id,
                                         "items": [{"product_id": PRODUCT_ID, "qty": "2"}]},
                              op_id=o.refund_op_id(sale_id))
        owner.apply_op(refund)
        owner_sync.send(refund)
        ok = wait_until(lambda: cashier.get_sale(sale_id) is not None
                        and cashier.get_sale(sale_id)["status"] == "refunded", timeout=TIMEOUT_S)
        step("kassa qaytarishni qabul qildi (chek 'refunded')", ok)
        step("qaytarishdan keyin qoldiq ikkala qurilmada 10", ok
             and owner.balance(store_id, PRODUCT_ID) == cashier.balance(store_id, PRODUCT_ID) == Decimal(10))
    finally:
        cashier_sync.stop()
        owner_sync.stop()

    failed = [name for name, ok_, _ in results if not ok_]
    print(f"\nNatija: {len(results) - len(failed)}/{len(results)} qadam o'tdi", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
