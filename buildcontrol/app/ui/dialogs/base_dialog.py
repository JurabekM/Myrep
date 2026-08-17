"""Frameless dialog shell with a custom header and footer."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.ui.styles.theme import COLORS, RADIUS, SPACING, SPACING_SM
from app.ui.widgets.common import Separator, button
from app.utils.i18n import tr


class BaseDialog(QDialog):
    """Modal dialog matching the application's dark shell.

    Subclasses populate :meth:`body` and may override :meth:`validate` and
    :meth:`on_accept`.
    """

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
        width: int = 560,
        with_footer: bool = True,
        ok_text: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setMinimumWidth(width)
        self._drag_offset: QPoint | None = None

        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self._frame = QFrame()
        self._frame.setObjectName("Panel")
        self._frame.setStyleSheet(
            f"#Panel {{ background: {COLORS.bg_alt}; border: 1px solid {COLORS.border_strong};"
            f" border-radius: {RADIUS}px; }}"
        )
        shell.addWidget(self._frame)

        outer = QVBoxLayout(self._frame)
        outer.setContentsMargins(SPACING + 4, SPACING, SPACING + 4, SPACING)
        outer.setSpacing(SPACING_SM)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("DialogHeader")
        titles.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        self.subtitle_label.setVisible(bool(subtitle))
        titles.addWidget(self.subtitle_label)
        header.addLayout(titles)
        header.addStretch(1)
        close_btn = button("✕", variant="Ghost")
        close_btn.setFixedWidth(32)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        outer.addLayout(header)
        outer.addWidget(Separator())

        self._body = QVBoxLayout()
        self._body.setSpacing(SPACING_SM)
        outer.addLayout(self._body, 1)

        self.error_label = QLabel("")
        self.error_label.setObjectName("FieldError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        outer.addWidget(self.error_label)

        if with_footer:
            outer.addWidget(Separator())
            footer = QHBoxLayout()
            footer.addStretch(1)
            self.cancel_btn = button(tr("cancel"), variant="Ghost")
            self.cancel_btn.clicked.connect(self.reject)
            footer.addWidget(self.cancel_btn)
            self.ok_btn = button(ok_text or tr("save"), "save", "Primary")
            self.ok_btn.clicked.connect(self._try_accept)
            self.ok_btn.setDefault(True)
            footer.addWidget(self.ok_btn)
            outer.addLayout(footer)
        else:
            self.ok_btn = None  # type: ignore[assignment]
            self.cancel_btn = None  # type: ignore[assignment]

    # -- API ---------------------------------------------------------------- #
    def body(self) -> QVBoxLayout:
        """Return the dialog's content layout."""
        return self._body

    def show_error(self, message: str) -> None:
        """Display an inline validation message."""
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def validate(self) -> str | None:
        """Return an error message when the dialog cannot be accepted."""
        return None

    def on_accept(self) -> None:
        """Hook executed after successful validation."""

    def _try_accept(self) -> None:
        problem = self.validate()
        if problem:
            self.show_error(problem)
            return
        self.show_error("")
        try:
            self.on_accept()
        except Exception as exc:  # surfaced to the user, never swallowed
            self.show_error(str(exc))
            return
        self.accept()

    # -- window dragging ---------------------------------------------------- #
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 56:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self._drag_offset = None
        super().mouseReleaseEvent(event)


def confirm(parent: QWidget, text: str, title: str = "") -> bool:
    """Show a themed yes/no confirmation dialog."""
    box = QMessageBox(parent)
    box.setWindowTitle(title or tr("confirm"))
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    yes = box.addButton(tr("yes"), QMessageBox.ButtonRole.YesRole)
    box.addButton(tr("no"), QMessageBox.ButtonRole.NoRole)
    box.exec()
    return box.clickedButton() is yes


def show_error(parent: QWidget, message: str, title: str = "") -> None:
    """Show a themed error dialog."""
    box = QMessageBox(parent)
    box.setWindowTitle(title or tr("error"))
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Warning)
    box.addButton(tr("ok"), QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def show_info(parent: QWidget, message: str, title: str = "") -> None:
    """Show a themed information dialog."""
    box = QMessageBox(parent)
    box.setWindowTitle(title or tr("info"))
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Information)
    box.addButton(tr("ok"), QMessageBox.ButtonRole.AcceptRole)
    box.exec()
