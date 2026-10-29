# mpay-db

Ma'lumotlar bazasi qatlami (2-faza P2.3, ADR-0018): `sqlx::Any` orqali **SQLite** (sandbox, bitta
instansiya) yoki **PostgreSQL** (ko'p instansiya, umumiy ombor). Vault, emitent emulyatori va server
bitta `Db` ni bo'lishadi.

* `Db::open(url, durability, max_connections)` — `sqlite:…` yoki `postgres://…`; `sqlite_url(path)`.
* `Db::begin_write()` — yozuvchi tranzaksiya: SQLite'da jarayon qulfi + `BEGIN IMMEDIATE`,
  PostgreSQL'da oddiy `BEGIN` (parallel).
* `Db::for_update()`, `Db::lock()/lock_all()` — PostgreSQL qator va advisory qulflari (SQLite'da bo'sh).
* `Db::migrate_with(sqlite, postgres)` — har crate o'z `migrations/sqlite` va `migrations/postgres`.

SQL qoidalari: parametrlar `$1, $2, …` birinchi uchrash tartibida; butun sonlar `BIGINT` (`i64`);
yig'indilar `CAST(… AS BIGINT)`; PostgreSQL URL'i (parol) faqat muhit o'zgaruvchisida.
