"""Local-only tables backing the replication engine.

These tables are never replicated themselves — they hold this installation's
pending changes and its position in the shared change log.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.database.base import Base

#: Change operations carried by the log.
OP_UPSERT = "upsert"
OP_DELETE = "delete"


class SyncOutbox(Base):
    """A local change waiting to be pushed to the shared log."""

    __tablename__ = "sync_outbox"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String(48), nullable=False, index=True)
    uid = Column(String(32), nullable=False, index=True)
    op = Column(String(16), nullable=False, default=OP_UPSERT)
    payload = Column(Text, default="")
    ts = Column(DateTime, default=datetime.now, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, default="")


class SyncUidAlias(Base):
    """Maps a foreign uid onto the local uid of the same logical row.

    Two installations can create the same natural row independently (the seeded
    roles, a project code typed on both machines). They merge on the natural
    key, but each keeps its own uid — the alias lets incoming foreign keys that
    still point at the other uid resolve correctly instead of being dropped.
    """

    __tablename__ = "sync_uid_alias"
    __table_args__ = (UniqueConstraint("entity", "foreign_uid", name="uq_alias"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String(48), nullable=False, index=True)
    foreign_uid = Column(String(32), nullable=False, index=True)
    local_uid = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class SyncState(Base):
    """Single-row cursor and diagnostics for the replication engine."""

    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(32), nullable=False, default="")
    device_name = Column(String(96), default="")
    #: Opaque transport cursor: everything up to and including it was applied.
    cursor = Column(String(64), default="")
    last_push_at = Column(DateTime)
    last_pull_at = Column(DateTime)
    last_error = Column(Text, default="")
    pushed_total = Column(Integer, default=0, nullable=False)
    pulled_total = Column(Integer, default=0, nullable=False)
