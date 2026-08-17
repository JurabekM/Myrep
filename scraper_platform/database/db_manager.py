# -*- coding: utf-8 -*-
"""
database/db_manager.py
======================
Ma'lumotlar bazasi bilan ishlash uchun yuqori darajali menejer.

- SQLAlchemy engine va sessiyalarni boshqaradi
- Parametrlashtirilgan so'rovlar orqali SQL Injection dan himoyalangan
  (ORM darajasida barcha qiymatlar avtomatik escape qilinadi)
- Sessiya/sahifa/item yozuvlarini yaratish va yangilash usullari
- Dublikatlarni content_hash orqali aniqlash
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session as OrmSession, sessionmaker

from config.settings import CONFIG
from config.secure import SECURE_STORE
from database.models import Base, Session, Page, Item, ScheduledJob
from logs.logger import get_logger

log = get_logger(__name__)


def compute_hash(data: dict[str, Any]) -> str:
    """Ma'lumot yozuvidan barqaror SHA-256 hash hisoblaydi (dublikat aniqlash uchun)."""
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class DatabaseManager:
    """Ma'lumotlar bazasi operatsiyalarini boshqaruvchi asosiy klass."""

    def __init__(self) -> None:
        password = SECURE_STORE.get("pg_password", "")
        url = CONFIG.database.url(password)
        # SQLite uchun ko'p oqimdan foydalanishga ruxsat beramiz
        connect_args = {"check_same_thread": False} if CONFIG.database.engine == "sqlite" else {}
        self.engine = create_engine(url, echo=False, future=True, connect_args=connect_args)
        self._Session = sessionmaker(bind=self.engine, expire_on_commit=False, class_=OrmSession)
        self.init_db()
        log.info("Ma'lumotlar bazasi ulandi: {}", CONFIG.database.engine)

    # -----------------------------------------------------------------
    def init_db(self) -> None:
        """Jadvallarni yaratadi (agar mavjud bo'lmasa)."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self) -> Iterator[OrmSession]:
        """Tranzaksiyani avtomatik commit/rollback qiluvchi kontekst menejeri."""
        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # -----------------------------------------------------------------
    # Sessiya operatsiyalari
    # -----------------------------------------------------------------
    def create_session(self, name: str, start_url: str, engine: str,
                        config_snapshot: dict[str, Any] | None = None) -> int:
        """Yangi scraping sessiyasini yaratadi va uning ID sini qaytaradi."""
        with self.session_scope() as s:
            obj = Session(
                name=name or start_url,
                start_url=start_url,
                engine=engine,
                config_snapshot=config_snapshot,
            )
            s.add(obj)
            s.flush()
            return obj.id

    def finish_session(self, session_id: int, status: str = "done") -> None:
        """Sessiyani yakunlaydi va statistikani yangilaydi."""
        with self.session_scope() as s:
            obj = s.get(Session, session_id)
            if obj is None:
                return
            obj.status = status
            obj.finished_at = _dt.datetime.now(_dt.timezone.utc)
            # Statistikani agregatlab hisoblaymiz
            obj.total_pages = s.scalar(
                select(func.count()).select_from(Page).where(Page.session_id == session_id)
            ) or 0
            obj.success_pages = s.scalar(
                select(func.count()).select_from(Page)
                .where(Page.session_id == session_id, Page.status == "ok")
            ) or 0
            obj.failed_pages = obj.total_pages - obj.success_pages
            obj.total_items = s.scalar(
                select(func.count()).select_from(Item).where(Item.session_id == session_id)
            ) or 0

    # -----------------------------------------------------------------
    # Sahifa operatsiyalari
    # -----------------------------------------------------------------
    def record_page(self, session_id: int, url: str, status_code: int | None,
                    status: str, engine_used: str = "", depth: int = 0,
                    content_type: str = "", response_time: float = 0.0,
                    error: str = "") -> None:
        """Bitta sahifa (URL) natijasini bazaga yozadi."""
        with self.session_scope() as s:
            s.add(Page(
                session_id=session_id, url=url, status_code=status_code,
                status=status, engine_used=engine_used, depth=depth,
                content_type=content_type, response_time=response_time, error=error,
            ))

    # -----------------------------------------------------------------
    # Item operatsiyalari
    # -----------------------------------------------------------------
    def save_items(self, session_id: int, items: list[dict[str, Any]],
                   source_url: str = "", item_type: str = "generic",
                   deduplicate: bool = True) -> int:
        """
        Ajratib olingan ma'lumotlarni saqlaydi.

        Returns:
            Haqiqatda saqlangan (dublikat bo'lmagan) yozuvlar soni.
        """
        saved = 0
        with self.session_scope() as s:
            for data in items:
                h = compute_hash(data)
                if deduplicate:
                    exists = s.scalar(
                        select(Item.id).where(
                            Item.session_id == session_id, Item.content_hash == h
                        ).limit(1)
                    )
                    if exists:
                        continue
                s.add(Item(
                    session_id=session_id, source_url=source_url,
                    data=data, content_hash=h, item_type=item_type,
                ))
                saved += 1
        return saved

    # -----------------------------------------------------------------
    # O'qish / statistika
    # -----------------------------------------------------------------
    def get_dashboard_stats(self) -> dict[str, Any]:
        """Dashboard uchun umumiy statistikani qaytaradi."""
        with self.session_scope() as s:
            total_sessions = s.scalar(select(func.count()).select_from(Session)) or 0
            total_items = s.scalar(select(func.count()).select_from(Item)) or 0
            total_pages = s.scalar(select(func.count()).select_from(Page)) or 0
            ok_pages = s.scalar(
                select(func.count()).select_from(Page).where(Page.status == "ok")
            ) or 0
            success_rate = round(ok_pages / total_pages * 100, 2) if total_pages else 0.0
            return {
                "total_sessions": total_sessions,
                "total_items": total_items,
                "total_pages": total_pages,
                "success_rate": success_rate,
            }

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        """Oxirgi sessiyalar ro'yxatini qaytaradi."""
        with self.session_scope() as s:
            rows = s.scalars(
                select(Session).order_by(Session.started_at.desc()).limit(limit)
            ).all()
            return [{
                "id": r.id, "name": r.name, "start_url": r.start_url,
                "engine": r.engine, "status": r.status,
                "started_at": r.started_at, "total_items": r.total_items,
                "success_rate": r.success_rate,
            } for r in rows]

    def get_items(self, session_id: int | None = None, search: str = "",
                  limit: int = 1000) -> list[dict[str, Any]]:
        """Ma'lumot yozuvlarini (ixtiyoriy filtr bilan) qaytaradi."""
        with self.session_scope() as s:
            stmt = select(Item)
            if session_id is not None:
                stmt = stmt.where(Item.session_id == session_id)
            stmt = stmt.order_by(Item.id.desc()).limit(limit)
            rows = s.scalars(stmt).all()
            result = []
            for r in rows:
                record = {"_id": r.id, "_source": r.source_url, **r.data}
                if search:
                    # Oddiy matnli qidiruv (barcha qiymatlar bo'ylab)
                    haystack = json.dumps(record, ensure_ascii=False, default=str).lower()
                    if search.lower() not in haystack:
                        continue
                result.append(record)
            return result

    # -----------------------------------------------------------------
    # Scheduled jobs
    # -----------------------------------------------------------------
    def add_job(self, name: str, url: str, schedule_type: str,
                cron_expr: str = "", task_config: dict[str, Any] | None = None) -> int:
        """Rejalashtirilgan vazifa qo'shadi."""
        with self.session_scope() as s:
            job = ScheduledJob(
                name=name, url=url, schedule_type=schedule_type,
                cron_expr=cron_expr, task_config=task_config,
            )
            s.add(job)
            s.flush()
            return job.id

    def list_jobs(self) -> list[dict[str, Any]]:
        """Barcha rejalashtirilgan vazifalarni qaytaradi."""
        with self.session_scope() as s:
            rows = s.scalars(select(ScheduledJob).order_by(ScheduledJob.id.desc())).all()
            return [{
                "id": j.id, "name": j.name, "url": j.url,
                "schedule_type": j.schedule_type, "cron_expr": j.cron_expr,
                "enabled": j.enabled, "last_run": j.last_run, "next_run": j.next_run,
                "task_config": j.task_config,
            } for j in rows]

    def delete_job(self, job_id: int) -> None:
        """Rejalashtirilgan vazifani o'chiradi."""
        with self.session_scope() as s:
            obj = s.get(ScheduledJob, job_id)
            if obj:
                s.delete(obj)

    def update_job_run(self, job_id: int, last_run: _dt.datetime,
                       next_run: _dt.datetime | None = None) -> None:
        """Vazifa oxirgi ishga tushish vaqtini yangilaydi."""
        with self.session_scope() as s:
            obj = s.get(ScheduledJob, job_id)
            if obj:
                obj.last_run = last_run
                obj.next_run = next_run


# Global singleton
DB = DatabaseManager()
