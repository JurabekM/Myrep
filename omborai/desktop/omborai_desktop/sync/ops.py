"""MQTT operatsiyalari: tuzilishi va yaratish. Protokol: docs/sync-mqtt.md."""

import uuid
from datetime import UTC, datetime
from typing import Any

# Qo'llanadigan operatsiya turlari
SALE = "sale"
REFUND = "refund"
SHIFT_OPEN = "shift_open"
SHIFT_CLOSE = "shift_close"
MOVEMENT = "movement"
PRODUCT = "product"
SNAPSHOT = "snapshot"
SNAPSHOT_REQUEST = "snapshot_request"

APPLIED_TYPES = frozenset({SALE, REFUND, SHIFT_OPEN, SHIFT_CLOSE, MOVEMENT, PRODUCT, SNAPSHOT})


def new_op(
    op_type: str,
    store_id: str,
    payload: dict[str, Any],
    *,
    device_id: str,
    op_id: str | None = None,
) -> dict[str, Any]:
    """Yangi operatsiya. op_id berilsa (masalan, qayta yuborish yoki deterministik refund), u saqlanadi."""
    return {
        "op_id": op_id or str(uuid.uuid4()),
        "type": op_type,
        "device": device_id,
        "ts": datetime.now(UTC).isoformat(),
        "store_id": store_id,
        "payload": payload,
    }


def refund_op_id(sale_id: str) -> str:
    """Bir chek faqat bir marta qaytariladi: barcha qurilmalarda bir xil op_id."""
    return f"refund:{sale_id}"
