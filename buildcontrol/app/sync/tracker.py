"""Change capture.

Every local insert/update/delete of a replicated entity lands in
:class:`~app.sync.models.SyncOutbox` inside the *same* transaction as the change
itself, so a committed change is never lost and a rolled back one is never sent.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import event, insert
from sqlalchemy.orm import Session

from app.sync.models import OP_DELETE, OP_UPSERT, SyncOutbox
from app.sync.registry import entity_name, is_syncable, serialise

logger = logging.getLogger(__name__)

#: Session.info key set while remote changes are being applied.
APPLYING = "sync_applying"
_PENDING = "sync_pending"

_installed = False


def install() -> None:
    """Attach the session listeners (idempotent)."""
    global _installed
    if _installed:
        return
    event.listen(Session, "before_flush", _before_flush)
    event.listen(Session, "after_flush", _after_flush)
    _installed = True


def is_applying(session: Session) -> bool:
    """True while the engine is writing changes received from other devices."""
    return bool(session.info.get(APPLYING))


def _before_flush(session: Session, _flush_context, _instances) -> None:
    """Snapshot what is about to change; deletes are captured before removal."""
    if is_applying(session):
        return
    upserts = [obj for obj in session.new if is_syncable(obj)]
    upserts += [
        obj
        for obj in session.dirty
        if is_syncable(obj) and session.is_modified(obj, include_collections=False)
    ]
    deletes = [
        {
            "entity": entity_name(obj),
            "uid": getattr(obj, "uid", None),
            "op": OP_DELETE,
            "payload": "",
            "ts": datetime.now(),
        }
        for obj in session.deleted
        if is_syncable(obj) and getattr(obj, "uid", None)
    ]
    if upserts or deletes:
        session.info[_PENDING] = {"upserts": upserts, "deletes": deletes}


def _after_flush(session: Session, _flush_context) -> None:
    """Serialise the snapshotted objects now that their keys and uids exist."""
    pending = session.info.pop(_PENDING, None)
    if not pending:
        return
    rows: list[dict] = list(pending["deletes"])
    with session.no_autoflush:
        for obj in pending["upserts"]:
            uid = getattr(obj, "uid", None)
            if not uid:
                continue
            try:
                payload = serialise(session, obj)
            except Exception:  # pragma: no cover - defensive, never block a write
                logger.exception("sync: failed to serialise %s", obj)
                continue
            rows.append(
                {
                    "entity": entity_name(obj),
                    "uid": uid,
                    "op": OP_UPSERT,
                    "payload": json.dumps(payload, ensure_ascii=False),
                    "ts": datetime.now(),
                }
            )
    if rows:
        session.execute(insert(SyncOutbox), rows)


def pending_count(session: Session) -> int:
    """Number of local changes waiting to be pushed."""
    from sqlalchemy import func, select

    return int(session.scalar(select(func.count()).select_from(SyncOutbox)) or 0)
