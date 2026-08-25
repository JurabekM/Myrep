"""Alembic muhiti.

Ikki rejimda ishlaydi:

* **Dastur ichida** — `distribos.persistence.migrations.ensure_schema()`
  tayyor `Engine` ni `config.attributes["engine"]` orqali beradi. Bu
  yerda YANGI ulanish OCHILMAYDI — mavjud engine ishlatiladi, chunki
  SQLite bitta faylga ikki xil ulanish sozlamasi bilan kirish (masalan
  PRAGMA'lar) chalkashlikka olib kelishi mumkin.
* **CLI orqali** (`alembic revision --autogenerate`) — `alembic.ini`
  dagi `sqlalchemy.url` ishlatiladi. Bu FAQAT ishlab chiquvchi yangi
  migratsiya yozayotganda kerak, ishlayotgan dasturda hech qachon
  chaqirilmaydi.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from distribos.persistence import models  # noqa: F401  jadvallarni ro'yxatga oladi
from distribos.persistence.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Dastur o'z engine'ini bergan bo'lsa — SHUNI ishlatamiz.
    connectable = config.attributes.get("engine")

    if connectable is not None:
        with connectable.connect() as connection:
            _run_with_connection(connection)
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _run_with_connection(connection)


def _run_with_connection(connection: object) -> None:
    # SQLite ALTER TABLE cheklangan (masalan ustun turi o'zgartirib
    # bo'lmaydi) — batch rejimi Alembic'ga jadvalni qayta qurishga
    # imkon beradi.
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
