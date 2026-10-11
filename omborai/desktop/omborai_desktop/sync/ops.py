"""MQTT operatsiyalari: turlar, ruxsat jadvali, vaqt formati. Protokol: docs/sync-mqtt.md (v2)."""

import uuid
from datetime import UTC, datetime
from typing import Any

# Operatsiya turlari (6-bo'lim)
DEVICE = "device"
JOIN_REQUEST = "join_request"
STORE = "store"
USER = "user"
PRODUCT = "product"
MOVEMENT = "movement"
SALE = "sale"
SHIFT_OPEN = "shift_open"
SHIFT_CLOSE = "shift_close"
REFUND = "refund"
SNAPSHOT = "snapshot"
SNAPSHOT_REQUEST = "snapshot_request"

ROLE_OWNER = "owner"
ROLE_CASHIER = "cashier"
ROLES = frozenset({ROLE_OWNER, ROLE_CASHIER})

# Faqat egasi qurilmasi imzolaydi
OWNER_ONLY = frozenset({DEVICE, STORE, USER, PRODUCT, MOVEMENT, REFUND, SNAPSHOT})
KNOWN_TYPES = OWNER_ONLY | {JOIN_REQUEST, SALE, SHIFT_OPEN, SHIFT_CLOSE, SNAPSHOT_REQUEST}
MOVEMENT_KINDS = frozenset({"receipt", "adjustment", "writeoff"})

TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
TS_LENGTH = 27  # YYYY-MM-DDTHH:MM:SS.ffffffZ


def now_ts() -> str:
    """UTC, aniq 6 ta kasr raqamli vaqt. Solishtirish satr bo'yicha (LWW)."""
    return datetime.now(UTC).strftime(TS_FORMAT)


def new_op(
    op_type: str,
    store_id: str,
    payload: dict[str, Any],
    *,
    device_id: str,
    op_id: str | None = None,
) -> dict[str, Any]:
    """Imzosiz operatsiya. Imzo LocalStore.new_op() da qo'yiladi."""
    return {
        "op_id": op_id or str(uuid.uuid4()),
        "type": op_type,
        "device": device_id,
        "ts": now_ts(),
        "store_id": store_id,
        "payload": payload,
    }


def refund_op_id(sale_id: str) -> str:
    """Bir chek faqat bir marta qaytariladi: barcha qurilmalarda bir xil op_id."""
    return f"refund:{sale_id}"
