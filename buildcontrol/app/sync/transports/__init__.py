"""Replication backends."""

from __future__ import annotations

from app.sync.transports.base import Change, SyncTransport, TransportError  # noqa: F401
from app.sync.transports.folder import FolderTransport  # noqa: F401
from app.sync.transports.mqtt import (  # noqa: F401
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    PUBLIC_BROKERS,
    MqttTransport,
)
from app.sync.transports.supabase import SETUP_SQL, SupabaseTransport  # noqa: F401

#: Backend key -> label shown in the settings page.
TRANSPORT_LABELS: dict[str, str] = {
    "mqtt": "MQTT broker (bepul, ro'yxatdan o'tmasdan)",
    "supabase": "Supabase (internet, bepul Postgres)",
    "folder": "Umumiy papka / lokal tarmoq",
    "off": "O'chirilgan (faqat lokal)",
}


def build_transport(settings: dict):
    """Create the transport described by the sync settings, or ``None``."""
    backend = str(settings.get("backend") or "off")
    tenant = str(settings.get("tenant") or "default")
    if backend == "mqtt":
        return MqttTransport(
            host=str(settings.get("mqtt_host") or DEFAULT_HOST),
            port=int(settings.get("mqtt_port") or DEFAULT_PORT),
            tenant=tenant,
            prefix=str(settings.get("mqtt_prefix") or DEFAULT_PREFIX),
            use_tls=bool(settings.get("mqtt_tls", True)),
            username=str(settings.get("mqtt_user") or ""),
            password=str(settings.get("mqtt_password") or ""),
            passphrase=str(settings.get("passphrase") or ""),
        )
    if backend == "supabase":
        return SupabaseTransport(
            url=str(settings.get("url") or ""),
            api_key=str(settings.get("api_key") or ""),
            tenant=tenant,
        )
    if backend == "folder":
        path = str(settings.get("folder") or "")
        if not path:
            raise TransportError("Papka manzili ko'rsatilmagan")
        return FolderTransport(path, tenant)
    return None
