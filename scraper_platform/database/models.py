# -*- coding: utf-8 -*-
"""
database/models.py
==================
SQLAlchemy ORM modellari. SQLite (default) va PostgreSQL bilan ishlaydi.

Jadvallar:
    - sessions      : har bir scraping sessiyasi (task) haqida umumiy ma'lumot
    - pages         : sessiya davomida so'ralgan har bir URL/sahifa
    - items         : sahifalardan ajratib olingan ma'lumot yozuvlari
    - scheduled_jobs: rejalashtirilgan vazifalar
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow() -> _dt.datetime:
    """Vaqt zonasini hisobga olgan hozirgi UTC vaqti."""
    return _dt.datetime.now(_dt.timezone.utc)


class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass."""


class Session(Base):
    """Bitta scraping sessiyasi (bir marta ishga tushirilgan task)."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    start_url: Mapped[str] = mapped_column(Text, nullable=False)
    engine: Mapped[str] = mapped_column(String(50), default="auto")
    status: Mapped[str] = mapped_column(String(30), default="running")  # running|done|failed|stopped
    started_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[_dt.datetime | None] = mapped_column(DateTime, nullable=True)

    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    success_pages: Mapped[int] = mapped_column(Integer, default=0)
    failed_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)

    config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    pages: Mapped[list["Page"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    items: Mapped[list["Item"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    @property
    def success_rate(self) -> float:
        """Muvaffaqiyat foizi (0-100)."""
        if self.total_pages == 0:
            return 0.0
        return round(self.success_pages / self.total_pages * 100, 2)


class Page(Base):
    """Sessiya davomida so'ralgan bitta URL (sahifa)."""

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending|ok|error
    engine_used: Mapped[str] = mapped_column(String(50), default="")
    depth: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(120), default="")
    response_time: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[_dt.datetime] = mapped_column(DateTime, default=_utcnow)

    session: Mapped["Session"] = relationship(back_populates="pages")


class Item(Base):
    """Sahifadan ajratib olingan bitta ma'lumot yozuvi (dinamik struktura)."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    source_url: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # ixtiyoriy struktura
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)  # dublikat aniqlash
    item_type: Mapped[str] = mapped_column(String(60), default="generic")
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=_utcnow)

    session: Mapped["Session"] = relationship(back_populates="items")


class ScheduledJob(Base):
    """Rejalashtirilgan scraping vazifasi."""

    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(30), default="once")  # once|hourly|daily|cron
    cron_expr: Mapped[str] = mapped_column(String(120), default="")
    task_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[_dt.datetime | None] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[_dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=_utcnow)
