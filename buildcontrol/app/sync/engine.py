"""Replication engine: push local changes, pull remote ones, apply them.

Model
-----
* Every installation keeps its own SQLite database and works fully offline.
* Local writes are captured into ``sync_outbox`` (see :mod:`app.sync.tracker`).
* ``push`` appends them to a shared append-only log on the server.
* ``pull`` reads the log from the device's cursor forward and applies the rows.

Conflicts are resolved **last-write-wins** on ``sync_ts``: if the incoming row is
older than the local one, the local value stays and nothing is lost silently —
the skip is counted in the sync report.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.base import new_uid
from app.database.session import session_scope
from app.sync.models import OP_DELETE, SyncOutbox, SyncState, SyncUidAlias
from app.sync.registry import (
    ENTITY_BY_NAME,
    ENTITY_ORDER,
    SYNC_ENTITIES,
    UnresolvedReference,
    deserialise,
    resolve_alias,
    serialise,
)
from app.sync.tracker import APPLYING
from app.sync.transports.base import Change, TransportError

logger = logging.getLogger(__name__)

PUSH_CHUNK = 200
PULL_LIMIT = 500
MAX_PULL_BATCHES = 40

#: Natural keys used to merge rows that two devices created independently
#: (for example the roles and the demo users seeded on every installation).
NATURAL_KEYS: dict[str, tuple[str, ...]] = {
    "Role": ("code",),
    "User": ("username",),
    "Project": ("code",),
    "Material": ("sku",),
    "RefItem": ("kind", "code"),
}

#: Entities that must never exist twice on one installation.
SINGLETON_ENTITIES = {"CompanySettings"}


@dataclass
class SyncReport:
    """Outcome of one synchronisation round."""

    pushed: int = 0
    pulled: int = 0
    applied: int = 0
    skipped_older: int = 0
    skipped_own: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        return (
            f"↑{self.pushed} ↓{self.pulled} ✓{self.applied} "
            f"↺{self.skipped_older} ✕{self.failed}"
        )


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #


def get_state(session: Session) -> SyncState:
    """Return the singleton sync state row, creating it on first use."""
    state = session.scalar(select(SyncState).limit(1))
    if state is None:
        state = SyncState(device_id=new_uid()[:16], device_name="", cursor="")
        session.add(state)
        session.flush()
    if not state.device_id:
        state.device_id = new_uid()[:16]
        session.flush()
    return state


def device_id() -> str:
    """This installation's stable device identifier."""
    with session_scope() as session:
        return get_state(session).device_id


def pending_changes() -> int:
    """How many local changes are waiting to be pushed."""
    with session_scope() as session:
        return int(session.scalar(select(func.count()).select_from(SyncOutbox)) or 0)


def status() -> dict:
    """Return the diagnostics shown on the synchronisation settings tab."""
    with session_scope() as session:
        state = get_state(session)
        return {
            "device_id": state.device_id,
            "device_name": state.device_name or "",
            "cursor": state.cursor or "",
            "pending": int(session.scalar(select(func.count()).select_from(SyncOutbox)) or 0),
            "last_push_at": state.last_push_at,
            "last_pull_at": state.last_pull_at,
            "last_error": state.last_error or "",
            "pushed_total": state.pushed_total,
            "pulled_total": state.pulled_total,
        }


def set_device_name(name: str) -> None:
    """Label this installation so other users recognise it in the log."""
    with session_scope() as session:
        get_state(session).device_name = name.strip()[:96]


def reset_cursor() -> None:
    """Replay the whole shared log on the next pull."""
    with session_scope() as session:
        get_state(session).cursor = ""


def queue_full_upload() -> int:
    """Re-queue every local row for pushing (used to seed a fresh server)."""
    queued = 0
    with session_scope() as session:
        session.execute(delete(SyncOutbox))
        for model in SYNC_ENTITIES:
            for row in session.scalars(select(model)).all():
                if not getattr(row, "uid", None):
                    row.uid = new_uid()
                session.add(
                    SyncOutbox(
                        entity=model.__name__,
                        uid=row.uid,
                        op="upsert",
                        payload=json.dumps(serialise(session, row), ensure_ascii=False),
                        ts=getattr(row, "sync_ts", None) or datetime.now(),
                    )
                )
                queued += 1
    return queued


# --------------------------------------------------------------------------- #
# Push
# --------------------------------------------------------------------------- #


def push(transport, report: SyncReport) -> None:
    """Send queued local changes to the shared log."""
    while True:
        with session_scope() as session:
            state = get_state(session)
            rows = session.scalars(
                select(SyncOutbox).order_by(SyncOutbox.id).limit(PUSH_CHUNK)
            ).all()
            if not rows:
                return
            changes = [
                Change(
                    entity=row.entity,
                    uid=row.uid,
                    op=row.op,
                    payload=json.loads(row.payload or "{}"),
                    ts=(row.ts or datetime.now()).isoformat(),
                    device=state.device_id,
                )
                for row in rows
            ]
            sent = transport.push(changes)
            ids = [row.id for row in rows]
            session.execute(delete(SyncOutbox).where(SyncOutbox.id.in_(ids)))
            state.pushed_total = (state.pushed_total or 0) + sent
            state.last_push_at = datetime.now()
            report.pushed += sent
            if len(rows) < PUSH_CHUNK:
                return


# --------------------------------------------------------------------------- #
# Pull / apply
# --------------------------------------------------------------------------- #


def pull(transport, report: SyncReport) -> None:
    """Fetch and apply everything new in the shared log."""
    for _ in range(MAX_PULL_BATCHES):
        with session_scope() as session:
            state = get_state(session)
            cursor = state.cursor or ""
        batch = transport.pull(cursor, PULL_LIMIT)
        if not batch:
            return
        report.pulled += len(batch)
        _apply_batch(batch, report)
        if len(batch) < PULL_LIMIT:
            return


def _apply_batch(batch: list[Change], report: SyncReport) -> None:
    """Apply one pulled batch inside a single transaction."""
    with session_scope() as session:
        state = get_state(session)
        own = state.device_id
        session.info[APPLYING] = True
        try:
            deferred: list[Change] = []
            for change in sorted(batch, key=lambda c: (int(c.cursor or 0),)):
                if change.device and change.device == own:
                    report.skipped_own += 1
                    state.cursor = change.cursor or state.cursor
                    continue
                outcome = _apply_one(session, change, report)
                if outcome == "defer":
                    deferred.append(change)
                state.cursor = change.cursor or state.cursor

            # Rows whose parent arrived later in the same batch.
            for _ in range(3):
                if not deferred:
                    break
                retry, deferred = deferred, []
                retry.sort(key=lambda c: (ENTITY_ORDER.get(c.entity, 99), int(c.cursor or 0)))
                for change in retry:
                    if _apply_one(session, change, report) == "defer":
                        deferred.append(change)
            for change in deferred:
                report.failed += 1
                report.errors.append(f"{change.entity}/{change.uid}: bog'liq yozuv topilmadi")

            state.last_pull_at = datetime.now()
            state.pulled_total = (state.pulled_total or 0) + len(batch)
        finally:
            session.info[APPLYING] = False


def _apply_one(session: Session, change: Change, report: SyncReport) -> str:
    """Apply a single change. Returns ``ok``, ``skip``, ``defer`` or ``fail``."""
    model = ENTITY_BY_NAME.get(change.entity)
    if model is None:
        return "skip"
    savepoint = session.begin_nested()
    try:
        if change.op == OP_DELETE:
            row = session.scalar(select(model).where(model.uid == change.uid))
            if row is not None:
                session.delete(row)
                report.applied += 1
            savepoint.commit()
            return "ok"

        values = deserialise(session, model, change.payload)
        incoming_ts = values.get("sync_ts") or datetime.now()
        row = _find_row(session, model, change.uid, values)

        if row is None:
            values["uid"] = change.uid
            session.add(model(**values))
            session.flush()
            report.applied += 1
            savepoint.commit()
            return "ok"

        # Merged on a natural key: keep our uid and remember theirs, so their
        # foreign keys keep resolving on this device.
        if row.uid != change.uid:
            _record_alias(session, change.entity, change.uid, row.uid)

        local_ts = getattr(row, "sync_ts", None)
        if local_ts is not None and incoming_ts <= local_ts:
            report.skipped_older += 1
            savepoint.commit()
            return "skip"

        values.pop("uid", None)
        for key, value in values.items():
            setattr(row, key, value)
        session.flush()
        report.applied += 1
        savepoint.commit()
        return "ok"
    except UnresolvedReference:
        savepoint.rollback()
        return "defer"
    except IntegrityError as exc:
        savepoint.rollback()
        report.failed += 1
        report.errors.append(f"{change.entity}/{change.uid}: {_short(exc)}")
        return "fail"
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        savepoint.rollback()
        report.failed += 1
        report.errors.append(f"{change.entity}/{change.uid}: {_short(exc)}")
        logger.exception("sync: failed to apply %s/%s", change.entity, change.uid)
        return "fail"


def _record_alias(session: Session, entity: str, foreign_uid: str, local_uid: str) -> None:
    """Remember that ``foreign_uid`` denotes the same row as ``local_uid`` here."""
    existing = session.scalar(
        select(SyncUidAlias).where(
            SyncUidAlias.entity == entity, SyncUidAlias.foreign_uid == foreign_uid
        )
    )
    if existing is None:
        session.add(SyncUidAlias(entity=entity, foreign_uid=foreign_uid, local_uid=local_uid))
        session.flush()
    elif existing.local_uid != local_uid:
        existing.local_uid = local_uid
        session.flush()


def _find_row(session: Session, model, uid: str, values: dict):
    """Locate the local row for an incoming change.

    Falls back to the entity's natural key so rows that two installations
    created independently (seeded roles, demo users, a project code typed on
    both machines) merge instead of duplicating.
    """
    row = session.scalar(select(model).where(model.uid == uid))
    if row is not None:
        return row
    alias = resolve_alias(session, model.__name__, uid)
    if alias:
        row = session.scalar(select(model).where(model.uid == alias))
        if row is not None:
            return row
    if model.__name__ in SINGLETON_ENTITIES:
        return session.scalar(select(model).limit(1))
    keys = NATURAL_KEYS.get(model.__name__)
    if not keys:
        return None
    conditions = []
    for key in keys:
        if key not in values:
            return None
        conditions.append(getattr(model, key) == values[key])
    return session.scalar(select(model).where(*conditions))


def _short(exc: Exception) -> str:
    text = str(getattr(exc, "orig", exc))
    return text.splitlines()[0][:160]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def synchronize(transport) -> SyncReport:
    """Run a full push + pull round against ``transport``."""
    report = SyncReport()
    if transport is None:
        report.errors.append("Sinxronizatsiya o'chirilgan")
        return report
    try:
        push(transport, report)
        pull(transport, report)
    except TransportError as exc:
        report.errors.append(str(exc))
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        report.errors.append(_short(exc))
        logger.exception("sync round failed")
    finally:
        # Connection-oriented backends (MQTT) hold a socket for the round.
        closer = getattr(transport, "close", None)
        if callable(closer):
            closer()
    with session_scope() as session:
        state = get_state(session)
        state.last_error = "; ".join(report.errors[:3])
    return report
