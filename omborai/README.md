# OmborAI

Kichik do'konlar uchun ombor, kassa (savdo), qarz daftari va hisobotlar tizimi.

## Holat

| Faza | Natija | Holat |
|---|---|---|
| 0 | Reja, 3 ekran eskizi (kassa, tovarlar, bosh sahifa; yorug'/tungi, uz/ru) | tayyor |
| 1 | Backend skeleti, auth (JWT + refresh rotatsiya), tenant izolyatsiyasi (RLS), CI | tayyor |
| 2 | Tovar, shtrix-kod, kirim, qoldiq ledger'i (o'zgarmas), parallel oversell'dan himoya | tayyor |
| 3 | Smena, savdo (server narxlari, idempotent), to'lov, qaytarish; desktop kassa (PySide6) | tayyor |
| 4 | Offline sinxronizatsiya (push/pull, op_id dedupe), desktop offline navbat | tayyor |
| 5 | Mobil ilova: Flutter UI + Kotlin (CameraX + ML Kit skaner), offline kassa | tayyor (Dart testlari va Kotlin kompilyatsiyasi; qurilmada sinalmagan) |

Keyingi fazalar (6+): qarz daftari, hisobotlar, Click/Payme, Telegram bot, fon sinxronizatsiyasi, iOS, AI prognoz.

## Papkalar

- `backend/` — FastAPI + PostgreSQL (RLS bilan tenant izolyatsiyasi). Batafsil: `backend/README` bo'limlari ichida.
- `desktop/` — Python + PySide6 (kassa va ofis ilovasi). Batafsil: `desktop/README.md`.
- `mobile/` — Flutter + Kotlin (Android). Batafsil: `mobile/README.md`.
- `shared/` — API shartnomasi (`openapi.json`), CI tekshiradi.
- `infra/` — Docker Compose, Caddy (TLS), PostgreSQL init.
- `design/` — ekran eskizlari (HTML prototip).
- `docs/reja.md` — to'liq loyiha rejasi.

## Tez ishga tushirish (lokal)

Talablar: Python 3.12+, PostgreSQL 16.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Lokal baza: superuser (migratsiya) va ilova roli (RLS cheklovli)
export OMBORAI_MIGRATION_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/omborai
export OMBORAI_DATABASE_URL=postgresql+asyncpg://omborai_app:omborai_app@localhost:5432/omborai
alembic upgrade head
uvicorn app.main:app --reload
```

Hujjatlar: http://127.0.0.1:8000/docs (faqat `OMBORAI_ENV=dev` da).

## Testlar

```bash
cd backend
export OMBORAI_TEST_ADMIN_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
pytest -q
ruff check . && ruff format --check . && mypy app
```

Testlar `omborai_test` bazasini qayta yaratadi. Haqiqiy PostgreSQL talab qilinadi, chunki RLS mock bilan tekshirilmaydi.

## Docker bilan (production'ga yaqin)

```bash
cd infra
cp .env.example .env   # qiymatlarni almashtiring
docker compose up -d --build
```

Stack: PostgreSQL 16, Redis 7, migratsiya, API, Caddy (avtomatik HTTPS).

## Xavfsizlik eslatmalari

- Ilova `omborai_app` roli bilan ulanadi (superuser emas, RLS unga qo'llanadi).
- Migratsiyalar owner (`postgres`) roli bilan ishlaydi. Productionda alohida owner rol tavsiya etiladi.
- `OMBORAI_JWT_SECRET` productionda kamida 32 belgi bo'lishi shart, aks holda ilova ishga tushmaydi.
- Refresh token'lar hash holida saqlanadi, qayta ishlatilsa butun oila bekor qilinadi.

## Keyingi fazalar

- Faza 2: tovar, shtrix-kod, `stock_movements` (qoldiq ledger'i)
- Faza 3: desktop kassa
- Faza 4: offline sinxronizatsiya (`/v1/sync/push`, `/v1/sync/pull`)
