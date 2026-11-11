from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import StatementError

from srv1_core.audit import AuditLogger
from srv1_core.db import SCHEMA_VERSION, AuditLog, Database, SchemaMismatchError, SchemaVersion
from srv1_core.events import EventBus
from srv1_core.paths import DataPaths


@pytest.fixture
async def db(paths: DataPaths) -> AsyncIterator[Database]:
    database = Database(paths.db_file)
    await database.start()
    yield database
    await database.stop()


async def test_wal_and_schema_version(db: Database) -> None:
    assert await db.journal_mode() == "wal"
    async with db.session() as session:
        assert await session.scalar(select(SchemaVersion.version)) == SCHEMA_VERSION


async def test_restart_keeps_data_and_detects_mismatch(paths: DataPaths) -> None:
    first = Database(paths.db_file)
    await first.start()
    async with first.session() as session, session.begin():
        await session.execute(update(SchemaVersion).values(version=SCHEMA_VERSION + 1))
    await first.stop()

    second = Database(paths.db_file)
    with pytest.raises(SchemaMismatchError):
        await second.start()
    await second.stop()


async def test_session_before_start_fails(paths: DataPaths) -> None:
    with pytest.raises(RuntimeError):
        Database(paths.db_file).session()


async def test_audit_record_roundtrip(db: Database) -> None:
    bus = EventBus()
    subscription = bus.subscribe("audit")
    audit = AuditLogger(db, bus)

    row_id = await audit.record("file.delete", r"C:\x\a.txt", ok=False, detail={"sabab": "ruxsat"})

    async with db.session() as session:
        row = await session.get_one(AuditLog, row_id)
    assert (row.action, row.target, row.ok, row.actor) == (
        "file.delete",
        r"C:\x\a.txt",
        False,
        "core",
    )
    assert row.detail == {"sabab": "ruxsat"}
    assert row.ts.tzinfo is UTC
    assert datetime.now(UTC) - row.ts < timedelta(seconds=10)
    event = await anext(subscription)
    assert event.data["id"] == row_id


async def test_timestamps_normalised_to_utc(db: Database) -> None:
    tashkent = timezone(timedelta(hours=5))
    local = datetime(2026, 11, 11, 15, 0, tzinfo=tashkent)
    async with db.session() as session, session.begin():
        row = AuditLog(ts=local, actor="t", action="a", target="b", ok=True, detail={})
        session.add(row)
    async with db.session() as session:
        stored = await session.get_one(AuditLog, row.id)
    assert stored.ts == datetime(2026, 11, 11, 10, 0, tzinfo=UTC)


async def test_naive_datetime_rejected(db: Database) -> None:
    naive = datetime(2026, 11, 11, 15, 0)
    async with db.session() as session:
        session.add(AuditLog(ts=naive, actor="t", action="a", target="b", ok=True, detail={}))
        with pytest.raises(StatementError, match="naive"):
            await session.commit()
