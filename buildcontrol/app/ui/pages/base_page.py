"""Shared page scaffolding."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.controllers.app_state import app_state
from app.services.auth_service import CurrentUser
from app.services.permissions import PermissionDenied
from app.ui.dialogs.base_dialog import show_error
from app.ui.styles.theme import SPACING, SPACING_LG
from app.ui.widgets.common import SectionHeader, toast
from app.utils.i18n import tr


class BasePage(QWidget):
    """Common behaviour for every full-screen page."""

    #: Permission required to open the page (empty means always allowed).
    permission: str = ""

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: QWidget | None = None,
        show_header: bool = True,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self.root = QVBoxLayout(self)
        margin = 0 if compact else SPACING_LG
        self.root.setContentsMargins(
            margin, 0 if compact else SPACING, margin, 0 if compact else SPACING
        )
        self.root.setSpacing(SPACING)
        self.header = SectionHeader(title, subtitle)
        self.header.setVisible(show_header)
        self.root.addWidget(self.header)

    # -- helpers ------------------------------------------------------------ #
    @property
    def actor(self) -> CurrentUser:
        """Return the signed-in user."""
        return app_state.require_user()

    def can(self, permission: str) -> bool:
        """True when the signed-in user holds ``permission``."""
        user = app_state.user
        return bool(user and user.can(permission))

    def notify(self, text: str, kind: str = "success") -> None:
        """Show a transient toast on this page."""
        toast(self, text, kind)

    def handle(self, error: Exception) -> None:
        """Present an exception to the user in a readable dialog."""
        if isinstance(error, PermissionDenied):
            show_error(self, tr("permission_denied"))
            return
        key = getattr(error, "key", None)
        show_error(self, tr(key) if key else str(error))

    def refresh(self) -> None:
        """Reload the page content. Overridden by subclasses."""

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self.refresh()
