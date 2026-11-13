"""APScheduler 3.x o'rami: plagin vazifalarini event loop'da ishga tushiradi."""
# APScheduler 3.x tip ma'lumotisiz keladi; shu fayl uning yagona iste'molchisi.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from srv1_core.log_setup import get_logger
from srv1_sdk.types import Job, JobCallback


def _job_id(owner: str, job_id: str) -> str:
    return f"{owner}:{job_id}"


def _trigger(job: Job) -> Any:  # noqa: ANN401 — APScheduler tipi yo'q
    if job.interval_s is not None:
        return IntervalTrigger(seconds=job.interval_s)  # pyright: ignore[reportArgumentType]
    if job.cron is None:
        raise ValueError(f"vazifa {job.id!r}: trigger yo'q")
    return CronTrigger.from_crontab(job.cron)  # yaroqsiz ifoda -> ValueError


class Scheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._log = get_logger("srv1.scheduler")
        self._owned: dict[str, list[str]] = {}

    def start(self) -> None:
        self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def add(self, owner: str, job: Job) -> None:
        """`owner` (plagin nomi) uchun vazifa qo'shadi. Vazifa xatosi faqat logga tushadi."""
        full_id = _job_id(owner, job.id)
        self._scheduler.add_job(
            self._guard(full_id, job.func),
            trigger=_trigger(job),
            id=full_id,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
            replace_existing=True,
        )
        self._owned.setdefault(owner, []).append(full_id)

    def remove_owner(self, owner: str) -> None:
        for full_id in self._owned.pop(owner, []):
            if self._scheduler.get_job(full_id) is not None:
                self._scheduler.remove_job(full_id)

    def job_ids(self, owner: str) -> list[str]:
        return list(self._owned.get(owner, []))

    def _guard(self, full_id: str, func: JobCallback) -> JobCallback:
        async def run() -> None:
            try:
                await func()
            except Exception:
                self._log.exception("job_failed", job=full_id)

        return run
