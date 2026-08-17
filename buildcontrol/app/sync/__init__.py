"""Offline-first replication between BuildControl installations.

Each computer keeps a complete local SQLite database and stays fully usable
without a network. Changes travel through a shared append-only log hosted on a
server (Supabase by default) or on a shared folder for local networks.
"""

from app.sync.engine import (  # noqa: F401
    SyncReport,
    device_id,
    pending_changes,
    queue_full_upload,
    reset_cursor,
    set_device_name,
    status,
    synchronize,
)
from app.sync.models import SyncOutbox, SyncState  # noqa: F401
from app.sync.tracker import install as install_tracker  # noqa: F401
from app.sync.transports import (  # noqa: F401
    SETUP_SQL,
    TRANSPORT_LABELS,
    FolderTransport,
    SupabaseTransport,
    TransportError,
    build_transport,
)
