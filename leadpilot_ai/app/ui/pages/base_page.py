"""Base class shared by every workspace page."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.controllers.app_context import AppContext
from app.services.auth_service import PermissionDenied
from app.ui.i18n import tr, translator
from app.ui.widgets.common import show_error

logger = logging.getLogger(__name__)


class BasePage(QWidget):
    """Common layout scaffolding, error handling and language support."""

    #: i18n key of the page title.
    title_key: str = ""
    #: i18n key of the page subtitle.
    subtitle_key: str = ""

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.user = context.user
        self._loaded = False

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 14, 18, 14)
        self._root.setSpacing(12)

        self._header = QHBoxLayout()
        self._header.setSpacing(12)
        header_text = QVBoxLayout()
        header_text.setSpacing(1)
        self.title_label = QLabel(tr(self.title_key) if self.title_key else "")
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel(tr(self.subtitle_key) if self.subtitle_key else "")
        self.subtitle_label.setObjectName("PageSubtitle")
        header_text.addWidget(self.title_label)
        header_text.addWidget(self.subtitle_label)
        self._header.addLayout(header_text)
        self._header.addStretch(1)
        self._root.addLayout(self._header)

        translator.language_changed.connect(self._on_language_changed)

    # ------------------------------------------------------------------ #
    def header(self) -> QHBoxLayout:
        """Layout of the page header (add toolbar widgets here)."""
        return self._header

    def body(self) -> QVBoxLayout:
        """Main vertical layout of the page."""
        return self._root

    def ensure_loaded(self) -> None:
        """Load data the first time the page becomes visible."""
        if not self._loaded:
            self._loaded = True
            self.reload()
        else:
            self.reload()

    def reload(self) -> None:
        """Refresh the page content. Overridden by subclasses."""

    def retranslate(self) -> None:
        """Reapply translated captions. Extended by subclasses."""
        if self.title_key:
            self.title_label.setText(tr(self.title_key))
        if self.subtitle_key:
            self.subtitle_label.setText(tr(self.subtitle_key))

    def _on_language_changed(self, _language: str) -> None:
        """Handle a language switch safely."""
        try:
            self.retranslate()
        except Exception:
            logger.exception("Retranslate failed on %s", type(self).__name__)

    # ------------------------------------------------------------------ #
    def handle_error(self, exc: Exception) -> None:
        """Convert a service exception into a localized dialog."""
        code = getattr(exc, "code", None)
        detail = getattr(exc, "detail", "")
        if isinstance(exc, PermissionDenied):
            show_error(self, tr("err.no_permission"))
            return
        if code:
            show_error(self, tr(f"err.{code}", detail=detail))
            return
        logger.exception("Unhandled UI error")
        show_error(self, tr("err.unknown"))

    def require(self, permission: str) -> bool:
        """Check a permission and show a dialog when it is missing."""
        if self.user.can(permission):
            return True
        show_error(self, tr("err.no_permission"))
        return False

    def set_placeholder(self, widget: QWidget) -> None:
        """Center a placeholder widget in the page body."""
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._root.addWidget(widget, 1)
