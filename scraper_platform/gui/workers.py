# -*- coding: utf-8 -*-
"""
gui/workers.py
==============
GUI'ni bloklamaslik uchun scraping vazifasini alohida oqimda (QThread)
ijro etuvchi ishchilar (worker).
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from scraper.task_runner import ScrapeTask, TaskOptions, TaskProgress
from logs.logger import get_logger

log = get_logger(__name__)


class ScrapeWorker(QThread):
    """ScrapeTask'ni fon oqimda ishga tushiruvchi worker."""

    # Signallar (GUI thread'ga xabar berish uchun)
    progress_updated = pyqtSignal(object)   # TaskProgress
    finished_task = pyqtSignal(dict)        # yakuniy statistika
    error_occurred = pyqtSignal(str)

    def __init__(self, options: TaskOptions) -> None:
        super().__init__()
        self.options = options
        self._stop_requested = False

    def stop(self) -> None:
        """Vazifani to'xtatishni so'raydi."""
        self._stop_requested = True

    def _on_progress(self, progress: TaskProgress) -> None:
        """Task'dan kelgan progress'ni GUI'ga uzatadi."""
        self.progress_updated.emit(progress)

    def run(self) -> None:
        """QThread kirish nuqtasi."""
        try:
            task = ScrapeTask(
                options=self.options,
                on_progress=self._on_progress,
                stop_flag=lambda: self._stop_requested,
            )
            result = task.run()
            self.finished_task.emit(result)
        except Exception as exc:  # noqa: BLE001
            log.exception("Worker xatoligi")
            self.error_occurred.emit(str(exc))
