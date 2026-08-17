"""Background synchronisation driven from the Qt event loop."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from app.sync.engine import SyncReport, synchronize
from app.sync.transports import build_transport
from app.sync.transports.base import TransportError

logger = logging.getLogger(__name__)


class SyncRunner(QThread):
    """Runs one push/pull round off the UI thread."""

    completed = Signal(object)

    def __init__(self, settings: dict, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:  # noqa: D102 - QThread entry point
        report = SyncReport()
        try:
            transport = build_transport(self._settings)
            if transport is None:
                report.errors.append("Sinxronizatsiya o'chirilgan")
            else:
                report = synchronize(transport)
        except TransportError as exc:
            report.errors.append(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            report.errors.append(str(exc))
            logger.exception("sync runner crashed")
        self.completed.emit(report)


class SyncController(QObject):
    """Owns the sync schedule and exposes progress to the interface."""

    started = Signal()
    finished = Signal(object)  # SyncReport

    def __init__(self, settings_provider, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings_provider = settings_provider
        self._runner: SyncRunner | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.sync_now)

    # -- schedule ------------------------------------------------------------- #
    def apply_schedule(self) -> None:
        """(Re)start the auto-sync timer from the current settings."""
        settings = self._settings_provider()
        enabled = settings.get("backend") not in (None, "", "off") and settings.get("auto")
        interval = max(30, int(settings.get("interval") or 300))
        self._timer.stop()
        if enabled:
            self._timer.start(interval * 1000)

    @property
    def busy(self) -> bool:
        return self._runner is not None and self._runner.isRunning()

    # -- run ------------------------------------------------------------------ #
    def sync_now(self) -> bool:
        """Start a round; returns False when one is already running."""
        if self.busy:
            return False
        settings = self._settings_provider()
        if settings.get("backend") in (None, "", "off"):
            return False
        self._runner = SyncRunner(settings, self)
        self._runner.completed.connect(self._on_completed)
        self.started.emit()
        self._runner.start()
        return True

    def _on_completed(self, report: SyncReport) -> None:
        self.finished.emit(report)
        if self._runner is not None:
            self._runner.deleteLater()
            self._runner = None

    def stop(self) -> None:
        """Stop the timer and wait for a running round to finish."""
        self._timer.stop()
        if self._runner is not None and self._runner.isRunning():
            self._runner.wait(5000)
