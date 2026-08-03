# Architecture

## Overview

Dehqon Ko'makchi ships as two independently complete, independently tested systems that are
**not yet wired together over the network**:

- The **Android app** works entirely offline today. Every feature -- diagnosis, irrigation
  advice, the ledger, and Bozor listings -- runs against on-device mocks/heuristics and a
  local Room database. `retrofit`/`okhttp` are declared as Gradle dependencies (intended for
  the eventual network layer) but no source file currently imports or calls them; there is no
  HTTP client wired to any screen or repository.
- The **FastAPI backend** is a separately complete, separately tested API server that
  implements the server-side half of the same feature set (phone-OTP auth issuing a JWT,
  weather proxy, a parity implementation of the diagnosis heuristic, and the real multi-user
  Bozor marketplace with SQLAlchemy-backed listings/groups/reports). Nothing in the Android
  app calls it yet.

```
   Android app (Kotlin/Compose)              FastAPI backend
   -----------------------------             -----------------------------
   ui -> ViewModel -> Repository             routers -> schemas -> SQLAlchemy
   -> Room (SQLite, on-device)               -> SQLite (dev) / PostgreSQL (prod)

   No network calls between them today. Retrofit/OkHttp are on the Gradle
   classpath but unused -- wiring a real `data/remote/*` implementation that
   calls the endpoints below is the single largest remaining integration
   task (see docs/PRODUCTION_READINESS.md).
```

Diagnosis, irrigation advice, and the ledger all work with **zero network calls** by design --
they run against a local heuristic model (diagnosis), a local rule-based advisor (irrigation),
and Room (ledger), and that should stay true even after the network layer is wired up (they
should remain offline-first). Bozor, by contrast, is inherently multi-user: today each
device's listings are private to that device's Room database, and the backend's fully-working
shared marketplace API is not reachable from the app until the network layer is built -- this
is the one feature where "wire it up" isn't optional polish, it's required for the feature to
do what its name promises.

## Android app (`android/`)

Package root: `uz.dehqonkomakchi.app`.

- **`ui/`** -- one package per feature screen (Compose): `onboarding`, `diagnose`,
  `irrigation`, `ledger`, `market`, `settings`. Each screen has a `XxxViewModel`
  (`androidx.lifecycle.ViewModel`, Hilt-injected) holding a `StateFlow` of UI state, and a
  `XxxScreen.kt` composable that renders it. Navigation graph lives in `ui/nav/AppNav.kt` with
  route constants in `ui/nav/Routes.kt`.
- **`data/db/`** -- Room database (`DehqonDatabase`), entities (`data/db/entity/Entities.kt`),
  and DAOs (`data/db/dao/Daos.kt`). This is the source of truth for ledger entries, cached
  diagnosis records, and cached market listings, so the relevant screens work offline.
- **`data/remote/`** -- one interface + one mock implementation per external capability
  (`auth/AuthOtpProvider` -> `DemoAuthOtpProvider`, `weather/WeatherProvider` ->
  `MockWeatherProvider`, `diagnosis/CropDiagnosisProvider` -> `MockCropDiagnosisProvider`).
  Only the mock implementation exists today; a real network-backed implementation of each
  interface is intended to be added here and swapped in via Hilt (`di/ProviderModule.kt`)
  without touching call sites -- but that real implementation has not been written yet.
- **`data/repo/`** -- repositories (`DiagnosisRepository`, `IrrigationRepository`,
  `LedgerRepository`, `MarketRepository`) that currently talk only to Room -- there is no
  "call backend" branch yet. This is the layer where that branch should be added once a real
  `data/remote` implementation exists.
- **`domain/IrrigationAdvisor.kt`** -- pure Kotlin rule engine (crop type + soil + recent
  rainfall/temperature -> watering recommendation). No Android framework dependency, so it's
  unit-testable in isolation (`app/src/test/.../IrrigationAdvisorTest.kt`).
- **`work/IrrigationReminderWorker.kt`** -- a WorkManager periodic worker that surfaces
  irrigation reminders as local notifications, entirely offline.
- **`di/`** -- Hilt modules. `AppModule` wires the database/DAOs/repositories;
  `ProviderModule` wires which implementation (mock vs. real) satisfies each remote provider
  interface -- the single place you'd touch to point the app at real backends.
- **`core/prefs/UserPrefs.kt`** -- DataStore-backed user preferences (onboarding-complete
  flag, region/district, planting date, notification/dark-mode/text-scale settings, and an
  `authToken`/`phoneNumber` pair that `DemoAuthOtpProvider` populates locally today; there is
  no backend-base-URL setting yet since nothing calls the backend).

State management is unidirectional: DB/network -> Repository -> ViewModel (`StateFlow`) ->
Composable. Screens never talk to Room or Retrofit directly.

## Backend (`backend/`)

FastAPI app factory in `app/main.py`; routers are grouped by domain under `app/routers/`:

| Router | Prefix | Responsibility |
|---|---|---|
| `auth.py` | `/v1/auth` | Phone-number OTP request/verify, issues a JWT |
| `weather.py` | `/v1/weather` | Region -> current + forecast (proxies `WeatherProvider`) |
| `diagnosis.py` | `/v1/diagnosis` | Optional server-side photo diagnosis + usefulness rating |
| `market.py` | `/v1/market` | Bozor: listings (CRUD/list/filter), sell groups, reports |

- **`app/providers/`** -- same pattern as the Android app: an abstract provider per
  integration (`sms_otp.py`, `weather.py`, `diagnosis.py`) with a mock/deterministic default
  implementation, selected via `app/config.py` settings so production can swap in a real
  vendor by setting one env var, with no call-site changes.
- **`app/models.py`** -- SQLAlchemy ORM models (`User`, `OtpRequest`, `SellGroup`, `Listing`,
  `ListingReport`, `DiagnosisLog`, `AuditLog`). All timestamp columns are plain (naive) UTC
  `DateTime`, populated via the shared `utc_now_naive()` helper -- see the "Datetime
  handling" note below.
- **`app/schemas.py`** -- Pydantic request/response models.
- **`app/security.py`** -- JWT issuance/verification and the `get_current_user` /
  `get_optional_user` FastAPI dependencies.
- **`app/rate_limit.py`** -- `slowapi`-based per-route rate limiting (auth endpoints are
  limited to guard the OTP flow against abuse).
- **`app/logging_config.py`** -- structured logging setup plus an `audit()` helper used for
  security-relevant events (OTP requests/verifies, moderation actions).
- **`app/db.py`** -- engine/session setup; `is_sqlite` toggles `check_same_thread` and
  SQLite-only pragmas so the same code path serves local dev (SQLite) and production
  (PostgreSQL, via `psycopg2-binary`).

### Datetime handling

The database layer uses SQLite in development, and SQLite's `DateTime` columns silently drop
timezone info on round-trip (confirmed empirically: writing a tz-aware `datetime` and reading
it back yields a naive one). To avoid ever comparing a naive value against an aware one (which
raises `TypeError`), the backend standardizes on **naive UTC** datetimes everywhere they touch
the database: `app.models.utc_now_naive()` is the single helper used for all
`created_at`/`expires_at` defaults and comparisons, instead of the deprecated
`datetime.utcnow()`. Values that never touch the DB (e.g. a test building a JSON payload) use
timezone-aware `datetime.now(timezone.utc)` instead, which is what should be used going
forward for any *new* timestamptz-backed column if the project migrates to PostgreSQL in
production (see `docs/PRODUCTION_READINESS.md`).

## Data flow example: crop diagnosis

1. User takes/picks a leaf photo in `DiagnoseScreen`.
2. `DiagnoseViewModel` calls `DiagnosisRepository.diagnoseAndSave(photo)`.
3. The repository runs the on-device `MockCropDiagnosisProvider` (RGB/HSV heuristics -- see
   `backend/app/providers/diagnosis.py` for the equivalent server-side algorithm, ported with
   the same category/threshold logic so both sides produce comparable results) and persists a
   `DiagnosisRecordEntity` to Room -- this is the entire flow; the client never calls the
   network for diagnosis, so it works fully offline. `DiagnosisRepository.rate()` records the
   user's later useful/not-useful feedback against the same local row.
4. The backend's `/v1/diagnosis` endpoint is a self-contained parity implementation (same
   heuristics, its own `DiagnosisLog`/rating table) rather than something the current app
   calls. It exists so a future client (web, or an app version that centralizes diagnosis
   quality metrics) has a ready-made, already-tested server path, and so the heuristic
   algorithm can be swapped for a real ML model server-side without an app release.
