"""Application state shared by the UI: bootstrap, session and preferences."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QSettings, Signal
from sqlalchemy import delete

from app.config import (
    APP_NAME,
    DEFAULT_LANGUAGE,
    LOG_PATH,
    ORG_NAME,
    SYNC_DEFAULT_INTERVAL,
    SYNC_DEFAULT_TENANT,
)
from app.database.migrations import run_migrations
from app.database.session import init_engine, session_scope
from app.services import demo_data
from app.services.auth_service import CurrentUser, ensure_roles
from app.sync.models import SyncOutbox
from app.sync.tracker import install as install_tracker
from app.sync.transports.mqtt import (
    DEFAULT_HOST as MQTT_DEFAULT_HOST,
)
from app.sync.transports.mqtt import (
    DEFAULT_PORT as MQTT_DEFAULT_PORT,
)
from app.sync.transports.mqtt import (
    DEFAULT_PREFIX as MQTT_DEFAULT_PREFIX,
)
from app.utils.i18n import i18n

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Send warnings and errors to the per-user log file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
    )


def bootstrap(seed_demo: bool = True) -> None:
    """Initialise the database, apply migrations, seed demo data, arm replication."""
    init_engine()
    run_migrations()
    install_tracker()
    with session_scope() as session:
        ensure_roles(session)
    if seed_demo:
        was_seeded = demo_data.is_seeded()
        demo_data.seed_demo_data()
        if not was_seeded:
            # Demo rows are local scaffolding, not something to broadcast to the
            # team. Use "upload everything" in the settings to publish real data.
            with session_scope() as session:
                session.execute(delete(SyncOutbox))


class AppState(QObject):
    """Holds the signed-in user and user preferences (QSettings backed)."""

    user_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings(ORG_NAME, APP_NAME)
        self._user: CurrentUser | None = None
        i18n.set_language(self.language)

    # -- session ------------------------------------------------------------ #
    @property
    def user(self) -> CurrentUser | None:
        return self._user

    def set_user(self, user: CurrentUser | None) -> None:
        """Set (or clear) the signed-in user."""
        self._user = user
        self.user_changed.emit(user)

    def require_user(self) -> CurrentUser:
        """Return the signed-in user, raising when the session is empty."""
        if self._user is None:
            raise RuntimeError("no active session")
        return self._user

    # -- preferences -------------------------------------------------------- #
    @property
    def language(self) -> str:
        return str(self._settings.value("ui/language", DEFAULT_LANGUAGE))

    @language.setter
    def language(self, value: str) -> None:
        self._settings.setValue("ui/language", value)
        i18n.set_language(value)

    @property
    def remembered_username(self) -> str:
        return str(self._settings.value("auth/username", ""))

    def remember(self, username: str, enabled: bool) -> None:
        """Persist (or forget) the username for the login form."""
        if enabled:
            self._settings.setValue("auth/username", username)
        else:
            self._settings.remove("auth/username")
        self._settings.setValue("auth/remember", enabled)

    @property
    def remember_enabled(self) -> bool:
        value = self._settings.value("auth/remember", False)
        return str(value).lower() in ("true", "1")

    @property
    def sidebar_collapsed(self) -> bool:
        return str(self._settings.value("ui/sidebar_collapsed", False)).lower() in ("true", "1")

    @sidebar_collapsed.setter
    def sidebar_collapsed(self, value: bool) -> None:
        self._settings.setValue("ui/sidebar_collapsed", value)

    def save_geometry(self, data: bytes) -> None:
        """Persist the main window geometry."""
        self._settings.setValue("ui/geometry", data)

    def restore_geometry(self) -> bytes | None:
        value = self._settings.value("ui/geometry")
        return value if isinstance(value, (bytes, bytearray)) else None

    # -- synchronisation ---------------------------------------------------- #
    @property
    def sync_settings(self) -> dict:
        """Return the replication configuration of this installation."""

        def flag(key: str, default: bool) -> bool:
            return str(self._settings.value(key, default)).lower() in ("true", "1")

        return {
            "backend": str(self._settings.value("sync/backend", "off")),
            "url": str(self._settings.value("sync/url", "")),
            "api_key": str(self._settings.value("sync/api_key", "")),
            "folder": str(self._settings.value("sync/folder", "")),
            "tenant": str(self._settings.value("sync/tenant", SYNC_DEFAULT_TENANT)),
            "auto": flag("sync/auto", True),
            "interval": int(self._settings.value("sync/interval", SYNC_DEFAULT_INTERVAL)),
            "device_name": str(self._settings.value("sync/device_name", "")),
            "mqtt_host": str(self._settings.value("sync/mqtt_host", MQTT_DEFAULT_HOST)),
            "mqtt_port": int(self._settings.value("sync/mqtt_port", MQTT_DEFAULT_PORT)),
            "mqtt_prefix": str(self._settings.value("sync/mqtt_prefix", MQTT_DEFAULT_PREFIX)),
            "mqtt_tls": flag("sync/mqtt_tls", True),
            "mqtt_user": str(self._settings.value("sync/mqtt_user", "")),
            "mqtt_password": str(self._settings.value("sync/mqtt_password", "")),
            "passphrase": str(self._settings.value("sync/passphrase", "")),
        }

    def save_sync_settings(self, values: dict) -> None:
        """Persist the replication configuration."""
        text_keys = (
            "backend",
            "url",
            "api_key",
            "folder",
            "tenant",
            "device_name",
            "mqtt_host",
            "mqtt_prefix",
            "mqtt_user",
            "mqtt_password",
            "passphrase",
        )
        for key in text_keys:
            if key in values:
                self._settings.setValue(f"sync/{key}", values[key])
        if "mqtt_port" in values:
            self._settings.setValue("sync/mqtt_port", int(values["mqtt_port"]))
        if "mqtt_tls" in values:
            self._settings.setValue("sync/mqtt_tls", bool(values["mqtt_tls"]))
        if "auto" in values:
            self._settings.setValue("sync/auto", bool(values["auto"]))
        if "interval" in values:
            self._settings.setValue("sync/interval", int(values["interval"]))
        self._settings.sync()

    @property
    def sync_enabled(self) -> bool:
        return self.sync_settings["backend"] not in ("", "off")


#: Process-wide state instance.
app_state = AppState()
