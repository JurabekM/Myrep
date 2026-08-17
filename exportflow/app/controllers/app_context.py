"""Application context shared by every page.

Holds the signed-in user, the translator, cached reference data and a small
signal bus so pages can react to changes made elsewhere.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from PySide6.QtCore import QObject, Signal
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.services import company_service, integration_service
from app.services.auth_service import CurrentUser
from app.ui.i18n import TR
from app.utils.logging_setup import get_logger

log = get_logger(__name__)

T = TypeVar("T")


class AppContext(QObject):
    """Runtime state and helpers available to the whole UI."""

    data_changed = Signal(str)
    language_changed = Signal(str)
    toast = Signal(str, str)

    def __init__(self, user: CurrentUser) -> None:
        super().__init__()
        self.user = user
        self.translator = TR
        self._company_cache: dict | None = None
        TR.set_language(user.language)
        TR.language_changed.connect(self.language_changed.emit)

    # ---------------------------------------------------------------- data
    def run(self, func: Callable[[Session], T]) -> T:
        """Execute a unit of work inside a transactional session scope."""
        with session_scope() as session:
            return func(session)

    def read(self, func: Callable[[Session], T]) -> T:
        """Alias of :meth:`run` used for read-only calls (same transaction)."""
        return self.run(func)

    def notify(self, topic: str = "*") -> None:
        """Tell other pages that data of ``topic`` has changed."""
        self.data_changed.emit(topic)

    def show_toast(self, message: str, level: str = "info") -> None:
        """Display a transient status message in the main window."""
        self.toast.emit(message, level)

    # ------------------------------------------------------------- company
    def company(self, refresh: bool = False) -> dict:
        """Cached company profile."""
        if self._company_cache is None or refresh:
            self._company_cache = self.run(company_service.company_dict)
        return self._company_cache

    def company_name(self) -> str:
        """Name of the exporting company for the title bar."""
        return self.company().get("name") or "—"

    def invalidate_company(self) -> None:
        """Drop the cached company profile."""
        self._company_cache = None

    # -------------------------------------------------------- integrations
    def integration_states(self) -> list[dict]:
        """Provider status of every integration kind."""

        def _load(session: Session) -> list[dict]:
            return [
                integration_service.provider_status(session, kind)
                for kind in ("llm", "email", "lead_import")
            ]

        try:
            return self.run(_load)
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Could not read integration states: %s", type(exc).__name__)
            return []

    # ------------------------------------------------------------- helpers
    def can(self, permission: str) -> bool:
        """Permission check for the signed-in user."""
        return self.user.can(permission)

    def language(self) -> str:
        """Active interface language."""
        return self.translator.language

    def set_language(self, language: str) -> None:
        """Change the interface language."""
        self.translator.set_language(language)

    def set_user(self, user: CurrentUser) -> None:
        """Replace the signed-in user (used after re-login)."""
        self.user = user

    def value(self, mapping: dict[str, Any], key: str, default: Any = "") -> Any:
        """Safe dictionary access used by table models."""
        value = mapping.get(key, default)
        return default if value is None else value
