"""
Backup Manager Module
=====================

Provides database backup and restore functionality for the Enterprise ERP
platform.  Supports both SQLite (direct file copy) and PostgreSQL
(``pg_dump`` / ``pg_restore``) backends.

Features:
    * Timestamped backup files (``erp_backup_YYYYMMDD_HHMMSS.db``).
    * Optional description metadata persisted alongside each backup.
    * Listing, deletion, and size inspection of existing backups.
    * Automatic backup scheduling based on configurable intervals.
    * Event-bus notifications on backup/restore completion.

Classes:
    BackupManager: Full backup lifecycle management.

Usage::

    manager = BackupManager(db_engine)
    path = manager.create_backup(description="Pre-deployment snapshot")
    backups = manager.list_backups()
    manager.restore_backup(path)
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import shutil
import subprocess
from typing import Any

from src.core.exceptions import BackupError
from src.core.utils import get_backup_dir
from src.database.engine import DatabaseEngine

logger = logging.getLogger(__name__)

# Try to import the event bus; gracefully degrade if unavailable.
try:
    from src.core.events import event_bus

    _HAS_EVENT_BUS = True
except ImportError:
    _HAS_EVENT_BUS = False


class BackupManager:
    """Manage database backups, restores, and retention.

    Delegates to backend-specific strategies (file copy for SQLite,
    ``pg_dump`` for PostgreSQL) while presenting a unified public API.

    Attributes:
        db_engine: The :class:`DatabaseEngine` whose data is backed up.
    """

    # Default auto-backup interval (24 hours).
    AUTO_BACKUP_INTERVAL_HOURS: int = 24

    def __init__(self, db_engine: DatabaseEngine) -> None:
        """Initialise the backup manager.

        Args:
            db_engine: A connected :class:`DatabaseEngine`.
        """
        self.db_engine: DatabaseEngine = db_engine
        self._backup_dir: str = str(get_backup_dir())
        os.makedirs(self._backup_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_backup(self, description: str = "") -> str:
        """Create a new database backup.

        Args:
            description: Optional human-readable description stored in a
                sidecar metadata file alongside the backup.

        Returns:
            The absolute path to the created backup file.

        Raises:
            BackupError: If the backup operation fails.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"erp_backup_{timestamp}"

        try:
            if self.db_engine.is_postgresql():
                backup_path = self._backup_postgresql(backup_name)
            else:
                backup_path = self._backup_sqlite(backup_name)

            # Write sidecar metadata.
            self._write_metadata(backup_path, description)

            logger.info("Backup created: %s", backup_path)
            self._emit_event("backup_created", backup_path, description)
            return backup_path

        except Exception as exc:
            raise BackupError(f"Backup creation failed: {exc}") from exc

    def restore_backup(self, backup_path: str) -> bool:
        """Restore the database from a previous backup.

        Args:
            backup_path: Absolute path to the backup file.

        Returns:
            ``True`` if the restore completed successfully.

        Raises:
            BackupError: If the backup file is missing or restore fails.
        """
        if not os.path.exists(backup_path):
            raise BackupError(f"Backup file not found: {backup_path}")

        try:
            if self.db_engine.is_postgresql():
                self._restore_postgresql(backup_path)
            else:
                self._restore_sqlite(backup_path)

            logger.info("Database restored from %s", backup_path)
            self._emit_event("backup_restored", backup_path)
            return True

        except Exception as exc:
            raise BackupError(f"Restore failed: {exc}") from exc

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups ordered by date descending.

        Returns:
            A list of dictionaries with keys ``name``, ``path``, ``date``,
            ``size`` (bytes), and ``description``.
        """
        backups: list[dict[str, Any]] = []

        if not os.path.exists(self._backup_dir):
            return backups

        for entry in os.listdir(self._backup_dir):
            full_path = os.path.join(self._backup_dir, entry)
            if not os.path.isfile(full_path):
                continue
            # Skip metadata sidecar files.
            if entry.endswith(".meta.json"):
                continue
            if not entry.startswith("erp_backup_"):
                continue

            stat = os.stat(full_path)
            meta = self._read_metadata(full_path)
            backups.append(
                {
                    "name": entry,
                    "path": full_path,
                    "date": datetime.datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                    "size": stat.st_size,
                    "description": meta.get("description", ""),
                }
            )

        # Most recent first.
        backups.sort(key=lambda b: b["date"], reverse=True)
        return backups

    def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup file and its metadata sidecar.

        Args:
            backup_path: Absolute path to the backup file.

        Returns:
            ``True`` if the file was deleted; ``False`` if not found.

        Raises:
            BackupError: If deletion fails for reasons other than absence.
        """
        try:
            if not os.path.exists(backup_path):
                return False

            os.remove(backup_path)

            meta_path = f"{backup_path}.meta.json"
            if os.path.exists(meta_path):
                os.remove(meta_path)

            logger.info("Backup deleted: %s", backup_path)
            return True

        except Exception as exc:
            raise BackupError(f"Failed to delete backup: {exc}") from exc

    def auto_backup_check(self) -> str | None:
        """Create a backup if the configured interval has elapsed.

        Checks the most recent backup timestamp and creates a new one if
        more than :attr:`AUTO_BACKUP_INTERVAL_HOURS` have passed.

        Returns:
            The path to the new backup if one was created, otherwise
            ``None``.
        """
        backups = self.list_backups()
        if backups:
            latest_date = datetime.datetime.fromisoformat(backups[0]["date"])
            elapsed = datetime.datetime.now() - latest_date
            if elapsed.total_seconds() < self.AUTO_BACKUP_INTERVAL_HOURS * 3600:
                logger.debug("Auto-backup skipped — last backup is recent.")
                return None

        logger.info("Auto-backup triggered.")
        return self.create_backup(description="Automatic scheduled backup")

    @staticmethod
    def get_backup_size(path: str) -> int:
        """Return the size of a backup file in bytes.

        Args:
            path: Absolute path to the backup file.

        Returns:
            File size in bytes, or ``0`` if the file does not exist.
        """
        if os.path.exists(path):
            return os.path.getsize(path)
        return 0

    # ------------------------------------------------------------------
    # SQLite backend
    # ------------------------------------------------------------------

    def _backup_sqlite(self, backup_name: str) -> str:
        """Create an SQLite backup by copying the database file.

        Args:
            backup_name: Base name (without extension) for the backup file.

        Returns:
            Absolute path to the backup copy.

        Raises:
            BackupError: If the source database file cannot be located.
        """
        db_url = str(self.db_engine.engine.url)
        # Extract the filesystem path from ``sqlite:///path``.
        db_path = db_url.replace("sqlite:///", "")

        if not os.path.exists(db_path):
            raise BackupError(f"SQLite database not found at {db_path}")

        backup_path = os.path.join(self._backup_dir, f"{backup_name}.db")
        shutil.copy2(db_path, backup_path)
        return backup_path

    def _restore_sqlite(self, backup_path: str) -> None:
        """Restore an SQLite database from a file copy.

        The current database file is replaced by the backup.  The engine
        is reconnected afterwards.

        Args:
            backup_path: Absolute path to the backup file.

        Raises:
            BackupError: If the source file is missing or copy fails.
        """
        db_url = str(self.db_engine.engine.url)
        db_path = db_url.replace("sqlite:///", "")

        # Close the engine to release file handles.
        self.db_engine.close()

        shutil.copy2(backup_path, db_path)

        # Reconnect.
        self.db_engine.connect()

    # ------------------------------------------------------------------
    # PostgreSQL backend
    # ------------------------------------------------------------------

    def _backup_postgresql(self, backup_name: str) -> str:
        """Create a PostgreSQL backup using ``pg_dump``.

        Args:
            backup_name: Base name for the output file.

        Returns:
            Absolute path to the dump file.

        Raises:
            BackupError: If ``pg_dump`` is unavailable or fails.
        """
        pg_config: dict[str, Any] = self.db_engine.config.get("postgresql", {})
        backup_path = os.path.join(self._backup_dir, f"{backup_name}.sql")

        env = os.environ.copy()
        env["PGPASSWORD"] = pg_config.get("password", "")

        cmd = [
            "pg_dump",
            "-h", pg_config.get("host", "localhost"),
            "-p", str(pg_config.get("port", 5432)),
            "-U", pg_config.get("user", "erp_user"),
            "-d", pg_config.get("name", "erp_db"),
            "-f", backup_path,
            "--format=plain",
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise BackupError(
                    f"pg_dump exited with code {result.returncode}: "
                    f"{result.stderr}"
                )
        except FileNotFoundError:
            raise BackupError(
                "pg_dump is not available.  Ensure PostgreSQL client tools "
                "are installed and on PATH."
            )

        return backup_path

    def _restore_postgresql(self, backup_path: str) -> None:
        """Restore a PostgreSQL database from a dump file.

        Args:
            backup_path: Absolute path to the SQL dump file.

        Raises:
            BackupError: If ``psql`` is unavailable or the restore fails.
        """
        pg_config: dict[str, Any] = self.db_engine.config.get("postgresql", {})

        env = os.environ.copy()
        env["PGPASSWORD"] = pg_config.get("password", "")

        cmd = [
            "psql",
            "-h", pg_config.get("host", "localhost"),
            "-p", str(pg_config.get("port", 5432)),
            "-U", pg_config.get("user", "erp_user"),
            "-d", pg_config.get("name", "erp_db"),
            "-f", backup_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise BackupError(
                    f"psql restore exited with code {result.returncode}: "
                    f"{result.stderr}"
                )
        except FileNotFoundError:
            raise BackupError(
                "psql is not available.  Ensure PostgreSQL client tools "
                "are installed and on PATH."
            )

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_metadata(backup_path: str, description: str) -> None:
        """Persist backup metadata in a JSON sidecar file.

        Args:
            backup_path: Absolute path to the backup file.
            description: User-provided description.
        """
        meta_path = f"{backup_path}.meta.json"
        meta = {
            "description": description,
            "created_at": datetime.datetime.now().isoformat(),
            "backup_file": os.path.basename(backup_path),
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Could not write backup metadata: %s", exc)

    @staticmethod
    def _read_metadata(backup_path: str) -> dict[str, Any]:
        """Read backup metadata from a JSON sidecar file.

        Args:
            backup_path: Absolute path to the backup file.

        Returns:
            The metadata dictionary, or an empty dict on failure.
        """
        meta_path = f"{backup_path}.meta.json"
        if not os.path.exists(meta_path):
            return {}
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read backup metadata: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_event(
        event_name: str, backup_path: str, description: str = ""
    ) -> None:
        """Emit a backup-related event via the event bus.

        Args:
            event_name: Event identifier (e.g. ``'backup_created'``).
            backup_path: Path to the relevant backup file.
            description: Optional description.
        """
        if not _HAS_EVENT_BUS:
            return

        try:
            event_bus.emit(
                event_name,
                {
                    "backup_path": backup_path,
                    "description": description,
                    "timestamp": datetime.datetime.now().isoformat(),
                },
            )
        except Exception as exc:
            logger.warning("Failed to emit '%s' event: %s", event_name, exc)
