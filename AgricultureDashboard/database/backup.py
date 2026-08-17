"""Backup / restore of the SQLite database with optional encryption."""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from config import settings
from core.optional import try_import
from core.security import audit

log = logging.getLogger(__name__)


def _encryption_key() -> bytes | None:
    """Derive a Fernet key from the app secret when cryptography is available."""
    crypto = try_import("cryptography")
    if crypto is None:
        return None
    import base64
    import hashlib

    digest = hashlib.sha256(settings.get_storage_secret().encode()).digest()
    return base64.urlsafe_b64encode(digest)


def create_backup(reason: str = "manual", encrypt: bool = False) -> Path | None:
    """Copy the live database into ``backups/`` (optionally Fernet-encrypted)."""
    if not settings.DB_PATH.exists():
        return None
    settings.ensure_directories()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = settings.BACKUP_DIR / f"agriculture_{stamp}_{reason}.db"
    shutil.copy2(settings.DB_PATH, target)

    if encrypt:
        key = _encryption_key()
        if key is not None:
            from cryptography.fernet import Fernet

            encrypted = settings.BACKUP_DIR / (target.name + ".enc")
            encrypted.write_bytes(Fernet(key).encrypt(target.read_bytes()))
            target.unlink()
            target = encrypted

    _rotate_backups()
    audit("backup_created", details=target.name)
    log.info("Zaxira nusxa yaratildi: %s", target.name)
    return target


def list_backups() -> list[dict[str, str]]:
    """Available backups, newest first."""
    if not settings.BACKUP_DIR.exists():
        return []
    items = []
    for path in sorted(settings.BACKUP_DIR.glob("agriculture_*.db*"), reverse=True):
        items.append({
            "name": path.name,
            "size_mb": f"{path.stat().st_size / 1_048_576:.2f}",
            "created": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return items


def restore_backup(name: str) -> bool:
    """Replace the live database with a backup (decrypting when needed)."""
    source = settings.BACKUP_DIR / name
    if not source.exists() or ".." in name:
        return False

    from core.cache import clear_all_caches
    from database.engine import dispose_engine

    dispose_engine()
    if name.endswith(".enc"):
        key = _encryption_key()
        if key is None:
            log.error("Shifrlangan zaxirani tiklash uchun 'cryptography' kerak.")
            return False
        from cryptography.fernet import Fernet

        settings.DB_PATH.write_bytes(Fernet(key).decrypt(source.read_bytes()))
    else:
        shutil.copy2(source, settings.DB_PATH)
    clear_all_caches()
    audit("backup_restored", details=name)
    log.info("Ma'lumotlar bazasi tiklandi: %s", name)
    return True


def _rotate_backups() -> None:
    """Keep only the newest N backups (configured in settings)."""
    from database.engine import get_setting

    keep = int(get_setting("backup_keep", "20") or 20)
    backups = sorted(settings.BACKUP_DIR.glob("agriculture_*.db*"), reverse=True)
    for stale in backups[keep:]:
        try:
            stale.unlink()
        except OSError:
            pass
