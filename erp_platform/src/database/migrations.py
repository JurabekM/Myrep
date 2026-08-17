# -*- coding: utf-8 -*-
"""
Avtomatik migratsiya tizimi.

Har bir migratsiya versiya raqamiga ega; bajarilganlari
``schema_migrations`` jadvalida qayd etiladi. Dastur har ishga
tushganda yangi migratsiyalar avtomatik qo'llanadi — foydalanuvchi
hech narsa qilmaydi.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from src.core.logger import get_logger
from src.core.utils import now_str
from src.database.schema import initial_schema, seed_defaults


@dataclass(frozen=True)
class Migration:
    """Bitta migratsiya: SQL ro'yxati yoki Python funksiyasi."""

    version: int
    name: str
    statements: Sequence[str] | None = None
    func: Callable | None = None


def get_migrations(engine: str) -> list[Migration]:
    """Barcha migratsiyalar ro'yxati (versiya tartibida)."""
    return [
        Migration(1, "initial_schema", statements=initial_schema(engine)),
        Migration(2, "seed_defaults", func=seed_defaults),
        # seed_defaults idempotent — yangi qo'shilgan hisoblarni (4410)
        # mavjud bazalarga ham yetkazish uchun qayta ishga tushiriladi
        Migration(3, "seed_defaults_v2", func=seed_defaults),
    ]


class MigrationRunner:
    """Migratsiyalarni tartib bilan, tranzaksiya ichida qo'llaydi."""

    def __init__(self, db) -> None:
        self._db = db
        self._log = get_logger("migrations")

    def run(self) -> int:
        """Yangi migratsiyalarni qo'llaydi; qo'llanganlar sonini qaytaradi."""
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT)"
        )
        applied = {
            row["version"]
            for row in self._db.query("SELECT version FROM schema_migrations")
        }

        count = 0
        for migration in get_migrations(self._db.engine):
            if migration.version in applied:
                continue
            self._log.info("Migratsiya qo'llanmoqda: v%s %s",
                           migration.version, migration.name)
            with self._db.transaction():
                if migration.statements:
                    for sql in migration.statements:
                        self._db.execute(sql)
                if migration.func:
                    migration.func(self._db)
                self._db.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) "
                    "VALUES (?, ?, ?)",
                    (migration.version, migration.name, now_str()),
                )
            count += 1
        if count:
            self._log.info("%s ta migratsiya qo'llandi.", count)
        return count
