"""Collapsible navigation sidebar."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_VERSION
from app.ui.styles.theme import (
    SIDEBAR_WIDTH,
    SIDEBAR_WIDTH_COLLAPSED,
    SPACING,
    SPACING_SM,
)
from app.ui.widgets.icons import icon
from app.utils.i18n import tr


@dataclass(frozen=True)
class NavItem:
    """One navigation entry."""

    key: str
    label_key: str
    icon: str
    permission: str = ""


class Sidebar(QFrame):
    """Vertical navigation with icon-only collapsed mode."""

    navigated = Signal(str)
    collapse_toggled = Signal(bool)

    def __init__(self, items: list[NavItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self._collapsed = False
        self._buttons: dict[str, QPushButton] = {}
        self._items = items

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING, SPACING_SM, SPACING_SM)
        layout.setSpacing(4)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("NavButton")
        self.toggle_btn.setIcon(icon("menu"))
        self.toggle_btn.setText("  " + tr("collapse_menu"))
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)

        self.section_label = QLabel(tr("nav_projects").upper())
        self.section_label.setObjectName("SidebarSection")
        self.section_label.setContentsMargins(10, 10, 0, 4)
        layout.addWidget(self.section_label)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for item in items:
            btn = QPushButton("  " + tr(item.label_key))
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setIcon(icon(item.icon))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tr(item.label_key))
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _=False, key=item.key: self.navigated.emit(key))
            self._group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[item.key] = btn

        layout.addStretch(1)
        self.footer = QLabel(f"v{APP_VERSION}")
        self.footer.setObjectName("SidebarFooter")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer)

    # -- API ---------------------------------------------------------------- #
    def set_active(self, key: str) -> None:
        """Check the button of the active page."""
        button = self._buttons.get(key)
        if button is not None:
            button.setChecked(True)

    def apply_permissions(self, can: callable) -> None:
        """Enable/disable entries according to the signed-in user's role."""
        for item in self._items:
            button = self._buttons.get(item.key)
            if button is None:
                continue
            allowed = not item.permission or bool(can(item.permission))
            button.setEnabled(allowed)
            button.setToolTip(
                tr(item.label_key)
                if allowed
                else f"{tr(item.label_key)} — {tr('permission_denied')}"
            )

    def toggle(self) -> None:
        """Collapse / expand the sidebar with a short animation."""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Apply the collapsed state."""
        self._collapsed = collapsed
        target = SIDEBAR_WIDTH_COLLAPSED if collapsed else SIDEBAR_WIDTH
        animation = QPropertyAnimation(self, b"minimumWidth", self)
        animation.setDuration(160)
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.finished.connect(lambda: self.setFixedWidth(target))
        animation.start()
        self.setMaximumWidth(max(target, self.width()))
        for key, button in self._buttons.items():
            item = next(i for i in self._items if i.key == key)
            button.setText("" if collapsed else "  " + tr(item.label_key))
        self.toggle_btn.setText("" if collapsed else "  " + tr("collapse_menu"))
        self.section_label.setVisible(not collapsed)
        self.footer.setVisible(not collapsed)
        self.collapse_toggled.emit(collapsed)

    @property
    def collapsed(self) -> bool:
        return self._collapsed
