"""Testlar uchun yordamchilar: imzolangan qurilmalar, egasi, juftlash, sotuv va smena operatsiyalari."""

import base64
import uuid
from decimal import Decimal
from typing import Any

from omborai_desktop import auth
from omborai_desktop.money import round_som
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import crypto
from omborai_desktop.sync import ops as o
from omborai_desktop.sync.identity import DeviceIdentity

STORE_ID = str(uuid.UUID(int=0x5151))
OWNER_LOGIN = "egasi"
OWNER_PASSWORD = "parol-12345"


class Device:
    """Imzolovchi qurilma: o'z kaliti va lokal bazasi bor."""

    def __init__(self, seed: int | None = None) -> None:
        identity = DeviceIdentity(bytes([seed]) * 32) if seed is not None else DeviceIdentity.generate()
        self.identity = identity
        self.local = LocalStore(identity=identity)
        self.id = self.local.device_id()

    def op(self, op_type: str, payload: dict[str, Any], op_id: str | None = None) -> dict[str, Any]:
        return self.local.new_op(op_type, payload, op_id=op_id)


def resign(device: Device, op: dict[str, Any]) -> dict[str, Any]:
    """Operatsiya maydonini (masalan `ts`) o'zgartirgach, uni qayta imzolash."""
    op["sig"] = base64.b64encode(device.identity.sign(crypto.canonical_bytes(op))).decode("ascii")
    return op


def make_owner(seed: int = 1) -> Device:
    owner = Device(seed)
    owner.local.init_owner(STORE_ID, "egasi")
    return owner


def add_user_op(owner: Device, login: str = OWNER_LOGIN, role: str = o.ROLE_OWNER) -> dict[str, Any]:
    salt, digest = auth.hash_password(OWNER_PASSWORD)
    return owner.op(
        o.USER,
        {
            "id": str(uuid.uuid4()),
            "login": login,
            "name": login.title(),
            "role": role,
            "salt": salt,
            "pw_hash": digest,
            "active": True,
        },
    )


def product_op(owner: Device, product_id: str, price: int, name: str = "Un", unit: str = "kg") -> dict:
    return owner.op(
        o.PRODUCT,
        {
            "id": product_id,
            "name": name,
            "unit": unit,
            "sale_price": price,
            "cost_price": 0,
            "min_stock": "0",
            "barcodes": [],
            "deleted": False,
        },
    )


def movement_op(owner: Device, product_id: str, qty: str, kind: str = "receipt") -> dict:
    return owner.op(o.MOVEMENT, {"product_id": product_id, "qty": qty, "kind": kind})


def device_op(owner: Device, device: Device, role: str = o.ROLE_CASHIER, active: bool = True) -> dict:
    return owner.op(
        o.DEVICE,
        {
            "device_id": device.id,
            "public_key": device.identity.public_key_hex,
            "role": role,
            "label": f"qurilma-{device.id[:4]}",
            "active": active,
        },
    )


def shift_open_op(device: Device, opening_cash: int = 0) -> dict:
    shift_id = str(uuid.uuid4())
    return device.op(o.SHIFT_OPEN, {"shift_id": shift_id, "opening_cash": opening_cash}, op_id=shift_id)


def sale_op(device: Device, product_id: str, qty: str, price: int, shift_id: str | None = None) -> dict:
    line = round_som(Decimal(qty) * price)
    sale_id = str(uuid.uuid4())
    payload = {
        "id": sale_id,
        "store_id": STORE_ID,
        "items": [
            {
                "product_id": product_id,
                "qty": qty,
                "product_name": "Un",
                "unit": "kg",
                "unit_price": price,
                "line_total": line,
            }
        ],
        "discount": 0,
        "subtotal": line,
        "total": line,
        "payments": [{"method": "cash", "amount": line}],
        "shift_id": shift_id,
        "number": "T-1",
        "created_at": o.now_ts(),
    }
    return device.op(o.SALE, payload, op_id=sale_id)


def refund_op(owner: Device, sale: dict[str, Any]) -> dict:
    items = [{"product_id": i["product_id"], "qty": i["qty"]} for i in sale["payload"]["items"]]
    return owner.op(o.REFUND, {"sale_id": sale["op_id"], "items": items}, op_id=o.refund_op_id(sale["op_id"]))


def join(owner: Device, cashier: Device, role: str = o.ROLE_CASHIER) -> dict[str, Any]:
    """Juftlash oqimi (docs/sync-mqtt.md, 7-bo'lim): kod -> so'rov -> tasdiq -> snapshot -> bootstrap."""
    cashier.local.set_pairing(STORE_ID, owner.id, owner.identity.public_key_hex)
    request = cashier.local.join_request("kassa")
    assert owner.local.verify_join_request(request)
    approval = device_op(owner, cashier, role=role)
    owner.local.apply_op(approval)
    cashier.local.apply_op(approval)
    snapshot = owner.op(o.SNAPSHOT, owner.local.snapshot_payload(STORE_ID))
    cashier.local.apply_op(snapshot)
    return snapshot


def bootstrapped_pair() -> tuple[Device, Device]:
    """Egasi va bitta kassa qurilmasi, to'liq bootstrap bilan."""
    owner = make_owner(1)
    cashier = Device(2)
    join(owner, cashier)
    return owner, cashier
