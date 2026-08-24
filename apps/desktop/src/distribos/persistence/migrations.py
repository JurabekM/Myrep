"""Bazani eng so'nggi sxemaga olib kelish — Alembic ustidagi yupqa qobiq.

## Nega bu alohida modul kerak

`Database.create_all()` (`persistence/base.py`) hozir ham bor — u tez va
testlar/vositalar uchun mos, chunki bitta chaqiruvda barcha jadvalni
yaratadi. Lekin ishlab chiqarishda bu YETARLI EMAS: foydalanuvchi
dasturni yangilaganda, eski bazadagi jadvallar YO'QOTILMASDAN yangi
ustun/jadvalga o'tishi kerak. `create_all()` buni qila olmaydi — u
faqat "hali yo'q" jadvallarni yaratadi, mavjudlarini o'zgartirmaydi.

## Uch holat

`ensure_schema()` uchta holatni farqlaydi:

1. **Bo'sh baza** — Alembic barcha migratsiyalarni ketma-ket qo'llaydi.
2. **Eski (Alembic'siz) baza** — `create_all()` bilan yaratilgan,
   jadvallar bor, lekin `alembic_version` yo'q. Bunday bazada
   boshlang'ich migratsiyani ISHGA TUSHIRISH `CREATE TABLE` xatosiga
   olib keladi (jadval allaqachon bor). Shuning uchun bunday baza
   qayta yaratilmaydi — faqat "head" deb BELGILANADI (stamp).
3. **Migratsiyalangan baza** — oddiy `upgrade`, ortiqcha ish yo'q.
"""

from __future__ import annotations

import logging

from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from alembic import command
from distribos.infrastructure.resources import resource_path

logger = logging.getLogger(__name__)

#: Boshlang'ich migratsiya yaratadigan jadvallardan biri. Bu jadval bor
#: va `alembic_version` yo'q bo'lsa — baza `create_all()` bilan
#: yaratilgan eski baza, deb hisoblanadi.
_LEGACY_SCHEMA_MARKER_TABLE = "catalog_product"


def _alembic_config(engine: Engine) -> Config:
    """Dastur ichidan chaqiriladigan Alembic konfiguratsiyasi.

    `alembic.ini` dagi `sqlalchemy.url` bu yerda ISHLATILMAYDI — u
    faqat CLI orqali yangi migratsiya yozishda (`alembic revision
    --autogenerate`) kerak. Ishlayotgan dastur har doim MAVJUD engine
    orqali ulanadi, chunki SQLite fayliga ikkinchi, boshqacha
    sozlangan ulanish ochish PRAGMA holatini chalkashtirishi mumkin.
    """
    config = Config()
    config.set_main_option("script_location", str(resource_path("alembic")))
    config.attributes["engine"] = engine
    return config


def ensure_schema(engine: Engine) -> None:
    """Bazani eng so'nggi sxemaga olib keladi. Ishga tushishda BIR MARTA
    chaqiriladi (`app_context.build_context`)."""
    inspector = inspect(engine)
    has_alembic_history = inspector.has_table("alembic_version")
    has_legacy_schema = inspector.has_table(_LEGACY_SCHEMA_MARKER_TABLE)

    config = _alembic_config(engine)

    if not has_alembic_history and has_legacy_schema:
        logger.info(
            "Eski (Alembic'siz) baza aniqlandi — sxema allaqachon "
            "boshlang'ich migratsiyaga mos, shuning uchun qayta "
            "yaratilmaydi, faqat 'head' deb belgilanadi."
        )
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")
