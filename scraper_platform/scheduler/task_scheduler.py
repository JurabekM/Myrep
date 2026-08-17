# -*- coding: utf-8 -*-
"""
scheduler/task_scheduler.py
===========================
Vazifalarni rejalashtirish (APScheduler asosida).

Qo'llab-quvvatlanadigan rejalar:
    - once   : bir martalik
    - hourly : har soatda
    - daily  : har kuni (belgilangan vaqtda)
    - cron   : to'liq cron ifodasi (masalan "0 */6 * * *")

Rejalashtirilgan vazifalar ma'lumotlar bazasida (scheduled_jobs)
saqlanadi va dastur qayta ishga tushganda tiklanadi.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from database.db_manager import DB
from scraper.task_runner import ScrapeTask, TaskOptions
from logs.logger import get_logger

log = get_logger(__name__)


class TaskScheduler:
    """Rejalashtirilgan scraping vazifalarini boshqaruvchi klass."""

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()
        self._started = False

    # -----------------------------------------------------------------
    def start(self) -> None:
        """Scheduler'ni ishga tushiradi va saqlangan vazifalarni tiklaydi."""
        if self._started:
            return
        self.scheduler.start()
        self._started = True
        self._restore_jobs()
        log.info("Scheduler ishga tushdi")

    def shutdown(self) -> None:
        """Scheduler'ni to'xtatadi."""
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    # -----------------------------------------------------------------
    def _restore_jobs(self) -> None:
        """Bazadagi barcha yoqilgan vazifalarni scheduler'ga qo'shadi."""
        for job in DB.list_jobs():
            if job["enabled"] and job["schedule_type"] != "once":
                self._register(job)

    def _build_trigger(self, schedule_type: str, cron_expr: str):
        """Reja turiga qarab APScheduler trigger yasaydi."""
        if schedule_type == "hourly":
            return IntervalTrigger(hours=1)
        if schedule_type == "daily":
            return IntervalTrigger(days=1)
        if schedule_type == "cron":
            return CronTrigger.from_crontab(cron_expr)
        # once
        return DateTrigger(run_date=_dt.datetime.now() + _dt.timedelta(seconds=2))

    def _register(self, job: dict[str, Any]) -> None:
        """Bitta vazifani APScheduler'ga ro'yxatdan o'tkazadi."""
        try:
            trigger = self._build_trigger(job["schedule_type"], job.get("cron_expr", ""))
        except ValueError as exc:
            log.error("Noto'g'ri cron ifodasi (job {}): {}", job["id"], exc)
            return

        self.scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            args=[job["id"]],
            id=f"job_{job['id']}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        log.info("Vazifa rejalashtirildi: #{} ({})", job["id"], job["schedule_type"])

    # -----------------------------------------------------------------
    def _execute_job(self, job_id: int) -> None:
        """Rejalashtirilgan vazifani ijro etadi."""
        jobs = {j["id"]: j for j in DB.list_jobs()}
        job = jobs.get(job_id)
        if not job or not job["enabled"]:
            return

        log.info("Rejalashtirilgan vazifa ishga tushdi: #{}", job_id)
        cfg = job.get("task_config") or {}
        options = TaskOptions(
            url=job["url"],
            name=job["name"],
            engine=cfg.get("engine", "auto"),
            crawl=cfg.get("crawl", False),
            export_format=cfg.get("export_format", ""),
        )
        try:
            ScrapeTask(options).run()
        except Exception as exc:  # noqa: BLE001
            log.error("Rejalashtirilgan vazifa xatoligi #{}: {}", job_id, exc)
        finally:
            DB.update_job_run(job_id, last_run=_dt.datetime.now(_dt.timezone.utc))

    # -----------------------------------------------------------------
    def add_job(self, name: str, url: str, schedule_type: str,
                cron_expr: str = "", task_config: dict[str, Any] | None = None) -> int:
        """Yangi rejalashtirilgan vazifa qo'shadi (bazaga + scheduler'ga)."""
        job_id = DB.add_job(name, url, schedule_type, cron_expr, task_config)
        job = {"id": job_id, "name": name, "url": url,
               "schedule_type": schedule_type, "cron_expr": cron_expr,
               "task_config": task_config, "enabled": True}
        if self._started:
            self._register(job)
        return job_id

    def remove_job(self, job_id: int) -> None:
        """Vazifani o'chiradi (bazadan + scheduler'dan)."""
        try:
            self.scheduler.remove_job(f"job_{job_id}")
        except Exception:  # noqa: BLE001 - job scheduler'da bo'lmasligi mumkin
            pass
        DB.delete_job(job_id)
        log.info("Vazifa o'chirildi: #{}", job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        """Barcha rejalashtirilgan vazifalarni qaytaradi."""
        return DB.list_jobs()


# Global singleton
SCHEDULER = TaskScheduler()
