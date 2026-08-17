"""Custom window title bar: app name, project context, user and window buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.config import APP_TITLE, APP_VERSION
from app.ui.styles.theme import COLORS, SPACING, SPACING_SM, TITLEBAR_HEIGHT
from app.ui.widgets.common import button
from app.utils.i18n import tr


class TitleBar(QFrame):
    """Draggable title bar with contextual information and window controls."""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()
    drag_started = Signal(object)
    drag_moved = Signal(object)
    drag_finished = Signal()
    language_changed = Signal(str)
    logout_requested = Signal()
    sync_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(TITLEBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING, 0, SPACING_SM, 0)
        layout.setSpacing(SPACING)

        dot = QLabel("◆")
        dot.setStyleSheet(f"color: {COLORS.accent}; font-size: 15px;")
        layout.addWidget(dot)

        self.app_label = QLabel(APP_TITLE)
        self.app_label.setObjectName("TitleBarAppName")
        layout.addWidget(self.app_label)

        self.context_label = QLabel("")
        self.context_label.setObjectName("TitleBarContext")
        layout.addWidget(self.context_label)
        layout.addStretch(1)

        self.sync_btn = button("", "refresh", "Ghost", tr("sync"))
        self.sync_btn.setMinimumWidth(96)
        self.sync_btn.clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_btn)

        self.language_box = QComboBox()
        self.language_box.addItem("O'zbekcha", "uz")
        self.language_box.addItem("English", "en")
        self.language_box.setFixedWidth(120)
        self.language_box.currentIndexChanged.connect(
            lambda: self.language_changed.emit(str(self.language_box.currentData()))
        )
        layout.addWidget(self.language_box)

        user_box = QVBoxLayout()
        user_box.setSpacing(0)
        self.user_label = QLabel("—")
        self.user_label.setObjectName("TitleBarUser")
        self.user_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        user_box.addWidget(self.user_label)
        self.role_label = QLabel("")
        self.role_label.setObjectName("TitleBarRole")
        self.role_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        user_box.addWidget(self.role_label)
        layout.addLayout(user_box)

        self.logout_btn = button("", "logout", "Ghost", tr("logout"))
        self.logout_btn.setFixedWidth(34)
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.logout_btn)

        for text, name, signal in (
            ("—", "WinButton", self.minimize_requested),
            ("□", "WinButton", self.maximize_requested),
            ("✕", "WinButtonClose", self.close_requested),
        ):
            btn = button(text)
            btn.setObjectName(name)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)
            if name == "WinButtonClose":
                btn.setProperty("class", "close")

    # -- content ------------------------------------------------------------ #
    def set_context(self, text: str) -> None:
        """Show the active project / page next to the app name."""
        self.context_label.setText(f"·  {text}" if text else f"·  v{APP_VERSION}")

    def set_user(self, name: str, role: str) -> None:
        """Show the signed-in user."""
        self.user_label.setText(name or "—")
        self.role_label.setText(role or "")
        self.logout_btn.setVisible(bool(name))

    def set_sync_state(self, state: str, detail: str = "", pending: int = 0) -> None:
        """Reflect replication activity: ``off``, ``idle``, ``busy`` or ``error``."""
        text, color = {
            "off": ("—", COLORS.text_faint),
            "idle": ("✓", COLORS.success),
            "busy": ("⟳", COLORS.warning),
            "error": ("!", COLORS.danger),
        }.get(state, ("—", COLORS.text_faint))
        label = f"{text} {tr('sync')}"
        if pending:
            label += f" · {pending}"
        self.sync_btn.setText(label)
        self.sync_btn.setStyleSheet(f"color: {color};")
        self.sync_btn.setToolTip(detail or tr("sync"))
        self.sync_btn.setEnabled(state != "off")

    def set_language(self, language: str) -> None:
        """Reflect the active language without emitting a change signal."""
        self.language_box.blockSignals(True)
        index = self.language_box.findData(language)
        if index >= 0:
            self.language_box.setCurrentIndex(index)
        self.language_box.blockSignals(False)

    # -- dragging ------------------------------------------------------------ #
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_moved.emit(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self.drag_finished.emit()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)
