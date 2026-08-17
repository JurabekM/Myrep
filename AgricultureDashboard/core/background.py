"""Background execution: shared thread pool and periodic daemon jobs."""
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

log = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agro-bg")
_periodic_stops: dict[str, threading.Event] = {}


def submit(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
    """Run a task on the shared background pool with error logging."""

    def safe() -> Any:
        try:
            return func(*args, **kwargs)
        except Exception:  # noqa: BLE001
            log.exception("Background task '%s' failed", getattr(func, "__name__", func))
            return None

    return _executor.submit(safe)


def start_periodic(name: str, interval_seconds: float, func: Callable[[], Any],
                   run_immediately: bool = False) -> None:
    """Start (or restart) a named periodic daemon job."""
    stop_periodic(name)
    stop = threading.Event()
    _periodic_stops[name] = stop

    def loop() -> None:
        if run_immediately:
            submit(func)
        while not stop.wait(interval_seconds):
            submit(func)

    thread = threading.Thread(target=loop, name=f"periodic-{name}", daemon=True)
    thread.start()
    log.info("Periodic job '%s' started (every %.0fs)", name, interval_seconds)


def stop_periodic(name: str) -> None:
    """Signal a periodic job to stop."""
    event = _periodic_stops.pop(name, None)
    if event:
        event.set()


def start_default_jobs() -> None:
    """Kick off the platform's standing background jobs."""
    from database import backup as db_backup
    from database.engine import get_setting
    from weather.service import refresh_all_districts

    hours = float(get_setting("auto_backup_hours", "24") or 24)
    start_periodic("auto-backup", hours * 3600, lambda: db_backup.create_backup("auto"))
    start_periodic("weather-refresh", 3600, refresh_all_districts, run_immediately=True)
