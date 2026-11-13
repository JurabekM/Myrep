"""Audit jurnali: xavfli amallar bazaga, log fayliga va hodisalar shinasiga yoziladi."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from srv1_core.db import AuditLog, Database
from srv1_core.events import EventBus
from srv1_core.log_setup import get_logger

AUDIT_TOPIC = "audit"


class AuditLogger:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self._db = db
        self._bus = bus
        self._log = get_logger("srv1.audit")

    async def record(
        self,
        action: str,
        target: str,
        *,
        actor: str = "core",
        ok: bool = True,
        detail: Mapping[str, Any] | None = None,
    ) -> int:
        """Yozuv qo'shadi va uning `id` sini qaytaradi. `detail` ga sir yozilmaydi."""
        row = AuditLog(
            ts=datetime.now(UTC),
            actor=actor,
            action=action,
            target=target,
            ok=ok,
            detail=dict(detail or {}),
        )
        async with self._db.session() as session, session.begin():
            session.add(row)
        self._log.info("audit", audit_id=row.id, actor=actor, action=action, target=target, ok=ok)
        self._bus.publish(
            AUDIT_TOPIC,
            {"id": row.id, "actor": actor, "action": action, "target": target, "ok": ok},
        )
        return row.id
