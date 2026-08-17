"""Process-wide access to the background synchronisation controller."""

from __future__ import annotations

from app.controllers.app_state import app_state
from app.sync.worker import SyncController

_controller: SyncController | None = None


def get_sync_controller() -> SyncController:
    """Return the shared controller, creating it on first use.

    Created lazily because it owns a ``QTimer`` and therefore requires a running
    ``QApplication``.
    """
    global _controller
    if _controller is None:
        _controller = SyncController(lambda: app_state.sync_settings)
        _controller.apply_schedule()
    return _controller


def shutdown_sync() -> None:
    """Stop the timer and wait for an in-flight round (called on exit)."""
    global _controller
    if _controller is not None:
        _controller.stop()
        _controller = None
