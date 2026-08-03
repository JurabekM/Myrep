# Dehqon Ko'makchi

Dehqon Ko'makchi ("Farmer's Assistant") is an Android app + FastAPI backend for smallholder
farmers in Uzbekistan: on-device crop-issue diagnosis from a leaf photo, an irrigation
advisor, a simple income/expense ledger, and Bozor -- a shared produce marketplace where
farmers list what they have to sell.

The whole system runs fully offline-capable / zero-external-account by default: every
third-party integration (SMS OTP, weather, crop diagnosis) has a mock provider wired in, so
you can build, run, and demo the app with nothing but the Android SDK and Python. Swapping in
a real SMS gateway, weather API, or ML diagnosis model is a matter of setting one env var per
provider (see `backend/.env.example`).

## Repository layout

```
dehqon_komakchi/
  android/    Kotlin + Jetpack Compose + Room app (offline-first, Hilt DI, WorkManager)
  backend/    FastAPI + SQLAlchemy backend (auth, weather proxy, diagnosis, Bozor marketplace)
  releases/   Signed release artifacts (APK/AAB) -- see docs/RELEASE.md
  docs/       Architecture, API and production-readiness notes
```

## Quick start

### Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows; use source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`; interactive docs at `/docs`. It defaults to a
local SQLite file (`dehqon.db`) and demo OTP mode (the code is always `123456`), so it runs
with zero external accounts.

Note: the backend is a fully working, fully tested API server, but the Android app does not
call it yet -- see "Current integration status" below.

Run tests and lint:

```bash
python -m pytest -q
python -m ruff check .
```

### Android

Open `android/` in Android Studio (Ladybird+), or from the command line:

```bash
cd android
./gradlew testDebugUnitTest     # unit tests
./gradlew assembleDebug         # debug APK -> app/build/outputs/apk/debug/
```

The app works fully offline today: diagnosis, irrigation, ledger, and Bozor listings all run
against on-device heuristics and a local Room database, with no network calls.

## Current integration status

The Android app and the FastAPI backend are two separately complete, separately tested
systems that are **not yet connected**. `retrofit`/`okhttp` are declared as Gradle
dependencies for this purpose but nothing in `android/app/src/main/java` calls them yet.
Diagnosis, irrigation, and the ledger are meant to stay offline-first regardless -- but Bozor
is a shared marketplace by design, so today's per-device Room-only listings don't actually
sync between users. Wiring a real `data/remote/*` implementation (Retrofit clients against the
endpoints in `docs/API.md`) and swapping it in via `di/ProviderModule.kt` is the largest
remaining task before this is a real product; see `docs/PRODUCTION_READINESS.md` for the full
list.

## Documentation

- `docs/ARCHITECTURE.md` -- module layout, data flow, offline-first design
- `docs/API.md` -- backend endpoint reference
- `docs/RELEASE.md` -- how the artifacts in `releases/` were built and how to rebuild/sign them
- `docs/PRODUCTION_READINESS.md` -- what's demo-mode vs. production-ready, and the checklist
  to flip this from a working prototype to a real deployment
