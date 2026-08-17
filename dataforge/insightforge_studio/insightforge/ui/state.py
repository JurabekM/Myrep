from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..core.workspace import Workspace


class AppState(QObject):
    workspace_changed = Signal()
    active_changed = Signal()
    data_changed = Signal()
    message = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.workspace = Workspace()
        self.figures: list[tuple[str, object]] = []
        self.model_run = None
        self.workspace_path: str | None = None

    def set_workspace(self, workspace: Workspace, path: str | None = None) -> None:
        self.workspace = workspace
        self.workspace_path = path
        self.workspace_changed.emit()
        self.active_changed.emit()
        self.data_changed.emit()

    def notify_added(self) -> None:
        self.workspace_changed.emit()
        self.active_changed.emit()
        self.data_changed.emit()

    def notify_data(self) -> None:
        self.data_changed.emit()
        self.workspace_changed.emit()

