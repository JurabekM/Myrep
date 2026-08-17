"""Frameless window base with edge resizing and drag support."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QWidget

MARGIN = 6


class FramelessWindow(QWidget):
    """A borderless top-level window the user can still resize and move."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMouseTracking(True)
        self._resizing = False
        self._edge = ""
        self._start_geometry = QRect()
        self._start_pos = QPoint()
        self._drag_offset: QPoint | None = None

    # -- dragging (called by the title bar) --------------------------------- #
    def start_drag(self, global_pos: QPoint) -> None:
        """Begin moving the window from a title bar press."""
        if self.isMaximized():
            return
        self._drag_offset = global_pos - self.frameGeometry().topLeft()

    def continue_drag(self, global_pos: QPoint) -> None:
        """Move the window while the title bar is dragged."""
        if self._drag_offset is not None:
            self.move(global_pos - self._drag_offset)

    def end_drag(self) -> None:
        """Finish a title bar drag."""
        self._drag_offset = None

    def toggle_maximized(self) -> None:
        """Switch between maximized and normal geometry."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # -- resizing ------------------------------------------------------------ #
    def _edge_at(self, pos: QPoint) -> str:
        rect = self.rect()
        left = pos.x() <= MARGIN
        right = pos.x() >= rect.width() - MARGIN
        top = pos.y() <= MARGIN
        bottom = pos.y() >= rect.height() - MARGIN
        return "".join(
            [
                "t" if top else "",
                "b" if bottom else "",
                "l" if left else "",
                "r" if right else "",
            ]
        )

    def _cursor_for(self, edge: str) -> Qt.CursorShape:
        if edge in ("tl", "br", "lt", "rb"):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in ("tr", "bl", "rt", "lb"):
            return Qt.CursorShape.SizeBDiagCursor
        if edge in ("l", "r"):
            return Qt.CursorShape.SizeHorCursor
        if edge in ("t", "b"):
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            edge = self._edge_at(event.position().toPoint())
            if edge:
                self._resizing = True
                self._edge = edge
                self._start_geometry = self.geometry()
                self._start_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if self._resizing:
            self._perform_resize(event.globalPosition().toPoint())
            event.accept()
            return
        if not self.isMaximized():
            self.setCursor(QCursor(self._cursor_for(self._edge_at(event.position().toPoint()))))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self._resizing = False
        self._edge = ""
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def _perform_resize(self, global_pos: QPoint) -> None:
        delta = global_pos - self._start_pos
        rect = QRect(self._start_geometry)
        minimum = self.minimumSize()
        if "l" in self._edge:
            rect.setLeft(min(rect.left() + delta.x(), rect.right() - minimum.width()))
        if "r" in self._edge:
            rect.setRight(max(rect.right() + delta.x(), rect.left() + minimum.width()))
        if "t" in self._edge:
            rect.setTop(min(rect.top() + delta.y(), rect.bottom() - minimum.height()))
        if "b" in self._edge:
            rect.setBottom(max(rect.bottom() + delta.y(), rect.top() + minimum.height()))
        self.setGeometry(rect)
