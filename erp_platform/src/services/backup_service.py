# -*- coding: utf-8 -*-
"""
Backup servisi.

* Bir tugmali backup: SQLite baza (online backup API bilan xavfsiz nusxa)
  + config.yaml -> ``backups/uzerp_backup_YYYYmmdd_HHMMSS.zip``
* Restore: zipdan bazani tiklaydi va ulanishni qayta ochadi
* Auto-backup: fon oqimida belgilangan intervalda (config: ``backup.*``),
  eski nusxalar avtomatik tozalanadi (``keep_last``)
"""
from __future__ import annotations

import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

from src.core.errors import UzERPError
from src.modules.base import BaseService

_DB_MEMBER = "data/erp.db"
_CONFIG_MEMBER = "config.yaml"


class BackupService(BaseService):
    """Zaxira nusxalarini yaratish, tiklash va avtomatlashtirish."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.base_dir = Path(container.get("base_dir"))
        self.backups_dir = self.base_dir / "backups"
        self._auto_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ #
    #  Backup / Restore
    # ------------------------------------------------------------------ #

    def create_backup(self, user: dict | None = None) -> Path:
        """Bir tugmali backup: zip fayl yo'lini qaytaradi."""
        if self.db.engine != "sqlite":
            raise UzERPError(
                "Avtomatik backup faqat SQLite uchun. PostgreSQL uchun "
                "pg_dump vositasidan foydalaning.")
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        # Millisekund aniqligi: bir soniya ichida bir nechta backup
        # yaratilganda (masalan, restore oldidan) fayl ustma-ust tushmaydi
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        zip_path = self.backups_dir / f"uzerp_backup_{stamp}.zip"
        temp_db = self.backups_dir / f".tmp_{stamp}.db"

        try:
            self.db.backup_to(temp_db)  # WAL bilan mos xavfsiz nusxa
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(temp_db, _DB_MEMBER)
                config_path = self.base_dir / "config.yaml"
                if config_path.exists():
                    zf.write(config_path, _CONFIG_MEMBER)
        finally:
            temp_db.unlink(missing_ok=True)

        self.audit.log("backup.create", user=user, entity="backup",
                       details=zip_path.name)
        self.log.info("Backup yaratildi: %s", zip_path.name)
        return zip_path

    def restore_backup(self, zip_path: str | Path,
                       user: dict | None = None) -> None:
        """
        Zipdan bazani tiklaydi.

        Tiklashdan oldin joriy holatning xavfsizlik nusxasi olinadi.
        Ulanish avtomatik qayta ochiladi — restart shart emas.
        """
        zip_path = Path(zip_path)
        if not zip_path.exists():
            raise UzERPError(f"Backup fayli topilmadi: {zip_path}")
        if self.db.engine != "sqlite":
            raise UzERPError("Restore faqat SQLite rejimida ishlaydi.")

        # 1. Avval vaqtinchalik faylga chiqarib, butunligini tekshiramiz —
        #    jonli bazaga XATO chiqmaguncha tegilmaydi.
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        temp_restore = self.backups_dir / f".restore_{stamp}.db"
        try:
            with zipfile.ZipFile(zip_path) as zf:
                if _DB_MEMBER not in zf.namelist():
                    raise UzERPError(
                        "Zip ichida baza fayli (data/erp.db) topilmadi.")
                with zf.open(_DB_MEMBER) as src, open(temp_restore, "wb") as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)
            self._verify_sqlite(temp_restore)

            # 2. Hozirgi holatning xavfsizlik nusxasi
            self.create_backup(user)

            # 3. Atomar almashtirish
            db_path = Path(self.db.path)
            self.db.close()
            try:
                import os
                os.replace(temp_restore, db_path)
                for ext in ("-wal", "-shm"):
                    Path(str(db_path) + ext).unlink(missing_ok=True)
            finally:
                self.db.reopen()
        finally:
            temp_restore.unlink(missing_ok=True)

        self.cache.clear()
        self.audit.log("backup.restore", user=user, entity="backup",
                       details=zip_path.name, category="security")
        self.log.info("Backup tiklandi: %s", zip_path.name)

    @staticmethod
    def _verify_sqlite(path: Path) -> None:
        """Tiklanayotgan fayl yaroqli SQLite baza ekanligini tekshiradi."""
        import sqlite3

        try:
            conn = sqlite3.connect(str(path))
            try:
                result = conn.execute("PRAGMA integrity_check").fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise UzERPError(f"Backup fayli buzilgan: {exc}") from exc
        if not result or result[0] != "ok":
            raise UzERPError("Backup bazasi butunlik tekshiruvidan o'tmadi.")

    def list_backups(self) -> list[dict]:
        """Mavjud backup fayllari (yangi -> eski)."""
        if not self.backups_dir.exists():
            return []
        files = sorted(self.backups_dir.glob("uzerp_backup_*.zip"),
                       reverse=True)
        return [{
            "name": f.name,
            "path": str(f),
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(
                f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        } for f in files]

    def prune_old(self) -> int:
        """``backup.keep_last`` dan ortiq eski nusxalarni o'chiradi."""
        keep = int(self.config.get("backup.keep_last", 30))
        backups = self.list_backups()
        removed = 0
        for info in backups[keep:]:
            Path(info["path"]).unlink(missing_ok=True)
            removed += 1
        if removed:
            self.log.info("%s ta eski backup o'chirildi.", removed)
        return removed

    # ------------------------------------------------------------------ #
    #  Auto-backup (fon oqimi)
    # ------------------------------------------------------------------ #

    def start_auto(self) -> None:
        """Auto-backup fon oqimini ishga tushiradi (config yoqilgan bo'lsa)."""
        if not self.config.get("backup.auto_backup", True):
            return
        if self._auto_thread and self._auto_thread.is_alive():
            return
        self._stop_event.clear()
        self._auto_thread = threading.Thread(
            target=self._auto_loop, daemon=True, name="uzerp-autobackup")
        self._auto_thread.start()
        self.log.info("Auto-backup yoqildi (har %s soatda).",
                      self.config.get("backup.interval_hours", 24))

    def stop_auto(self) -> None:
        """Auto-backup oqimini to'xtatadi."""
        self._stop_event.set()

    def _auto_loop(self) -> None:
        """Fon oqimi: interval kutadi, backup oladi, eskilarini tozalaydi."""
        interval = max(float(self.config.get("backup.interval_hours", 24)), 0.1)
        interval_seconds = interval * 3600
        while not self._stop_event.wait(interval_seconds):
            try:
                self.create_backup()
                self.prune_old()
            except Exception:  # noqa: BLE001 - fon oqimi hech qachon yiqilmasin
                self.log.exception("Auto-backup xatosi")
