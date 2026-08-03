# Production readiness

Honest status as of this build: **two well-tested prototypes, not yet a shippable product.**
The Android app and the backend each work and are each tested in isolation. The thing keeping
this from being real software farmers can use is integration and hardening, not missing
features within either half.

## What's solid today

- **Backend**: 25/25 pytest tests pass, `ruff check .` is clean (see `backend/pyproject.toml`
  for the lint config -- `B008` is intentionally ignored as FastAPI's documented `Depends()`
  idiom). Every route has explicit status codes and error handling; validation errors and
  unhandled exceptions both return a uniform, safe JSON envelope that never leaks internals.
  Rate limiting is applied to every mutating/sensitive route. Auth uses phone+OTP -> JWT, with
  OTP expiry, single-use consumption, and audit logging of request/verify/failure events.
- **Android**: 18/18 JVM unit tests pass (`./gradlew testDebugUnitTest`), covering the
  irrigation rule engine, the on-device diagnosis heuristic, ledger summary math, and the
  diagnosis repository; one Compose UI test exists for the legal/settings screens
  (`LegalScreensUiTest`). The app builds a debug APK, a release APK, and a release AAB without
  errors. Every core feature (diagnosis, irrigation, ledger, Bozor listings) works fully
  offline via Room, with no crash-on-first-launch dependency on any network or account.
- **Design for swappability**: both sides consistently isolate "mock implementation of an
  external integration" behind an interface (`CropDiagnosisProvider`, `WeatherProvider`,
  `AuthOtpProvider` on Android; `app/providers/*.py` on the backend), so replacing a mock with
  a real vendor is additive, not a rewrite.

## The one big gap: the app and backend aren't connected

This is the headline finding of this pass, worth repeating from `docs/ARCHITECTURE.md`: the
Android app does not call the backend. `retrofit`/`okhttp` are Gradle dependencies but no
Kotlin file imports them. Concretely:

- **Bozor is not actually shared.** The backend implements a real multi-user marketplace
  (`/v1/market/listings`, moderation via report-threshold auto-hide, sell groups with live
  aggregated quantity). The app's `MarketRepository` only reads/writes local Room tables. Two
  farmers running the app today cannot see each other's listings. This is the single
  highest-priority integration task -- everything else in this doc is hardening; this one is a
  missing feature.
- Auth, weather, and (optionally) diagnosis are also unconnected, but those are lower-priority
  since the app already delivers correct value fully offline for them.

**To close this gap**: add a real Retrofit `ApiService` interface matching `docs/API.md`,
implement it against each `data/remote/*` interface (`RetrofitAuthOtpProvider`,
`RetrofitWeatherProvider`, keep diagnosis on-device), wire the chosen implementation in
`di/ProviderModule.kt`, and add a real "sync with backend" path to `MarketRepository` (e.g.
push on create/delete, pull-to-refresh or periodic WorkManager pull for `GET /listings`).
`UserPrefs` will need a backend base URL / auth-token field wired to the real `AuthOtpProvider`
instead of `DemoAuthOtpProvider`. `API_BASE_URL` in `app/build.gradle.kts` is already a
placeholder waiting to be pointed at a deployed backend.

## Security and correctness items to address before real users

1. **Release signing**: the release APK/AAB in `releases/` are signed with the Android debug
   keystore (see `docs/RELEASE.md`). Not acceptable for Play Store distribution or for any
   build a user is expected to trust as "official." Generate a real upload keystore before
   shipping.
2. **No code shrinking**: `isMinifyEnabled = false` on the release build type. Turning on R8
   shrinking/obfuscation needs a pass to confirm Hilt-generated and kotlinx.serialization
   reflection-based code still works (add keep rules as needed) -- deferred here because it
   needs a real device/emulator run to validate, not just a compile.
3. **JWT secret**: `JWT_SECRET_KEY` defaults to a placeholder
   (`dev-only-insecure-secret-change-me`) in `.env.example` and `app/config.py`. Must be set to
   a real random secret (`python -c "import secrets; print(secrets.token_hex(32))"`) via
   environment variable in any real deployment -- there's no runtime check preventing the app
   from starting with the placeholder, which would be worth adding (a startup assertion when
   `environment != "development"`).
4. **CORS defaults to `*`** (`CORS_ALLOW_ORIGINS=*`). Fine for local development; must be
   scoped to the real app's origin(s) before production (mobile clients aren't
   origin-restricted the same way browsers are, but an open CORS policy is still unnecessary
   surface area if any web client is ever added).
5. **SQLite in production is not recommended** despite `is_sqlite`/`DATABASE_URL` making it
   trivial to point at PostgreSQL (`psycopg2-binary` is already a dependency) -- SQLite's
   single-writer model doesn't suit a multi-user marketplace under real concurrent load. Flip
   `DATABASE_URL` to a managed PostgreSQL instance for production; no code changes needed
   beyond that (see `app/db.py`).
6. **No database migrations tool** (no Alembic). `init_db()` currently does
   `Base.metadata.create_all()`, which is fine for a fresh dev DB but cannot evolve a live
   production schema safely (adding a column, changing a constraint) without downtime or data
   loss. Add Alembic before the first production schema change.
7. **OTP demo mode must be turned off**: `AUTH_OTP_MODE=demo` makes every phone number's OTP
   `123456` -- correct for zero-account development/demoing, but it is not authentication if
   left on in production. Switching to `AUTH_OTP_MODE=sms` requires implementing a real SMS
   gateway in `app/providers/sms_otp.py` (currently only the demo/mock path exists) and setting
   `SMS_PROVIDER_API_KEY`.
8. **JWT expiry is long** (`JWT_EXPIRE_MINUTES=10080`, 7 days) with no refresh-token or
   revocation mechanism -- acceptable for a v1 low-friction UX decision, but means a leaked
   token is valid for a week and there's no way to invalidate a specific session. Worth a
   revocation list (or shorter expiry + refresh tokens) before this handles anything sensitive
   beyond marketplace listings.
9. **Diagnosis heuristic is not medical/agronomic-grade**: `app/providers/diagnosis.py` and its
   Android counterpart are simple RGB/HSV color-and-edge heuristics, explicitly documented as
   "never assert high confidence when the signal is weak" (confidence capped at 0.95) and every
   response carries a disclaimer directing the user to a real agronomist. This is a
   deliberate, honest design choice, not a bug -- but it means the "diagnosis" feature's value
   is directional guidance, not a substitute for expert judgment, and marketing/UX copy should
   keep saying so.

## Operational gaps

- **No CI configured.** `pytest`, `ruff check .`, and `./gradlew testDebugUnitTest` all need
  to be run manually; there's no GitHub Actions/other workflow wired up yet to run them on
  push/PR.
- **No structured deploy path** for the backend (no Dockerfile, no `docker-compose.yml`, no
  hosting-specific config). `app/logging_config.py` gives structured logs, which is a good
  start for whatever platform is chosen (Fly.io, Railway, a plain VM behind nginx, etc.), but
  the container/deploy artifact itself doesn't exist yet.
- **No crash reporting / analytics wired into the Android app** (no Crashlytics or
  equivalent). Fine for internal review; worth adding before a public release so real-device
  issues are visible.

## Suggested order of operations for a real launch

1. Wire the Android network layer end-to-end for Bozor (the one feature that's actually broken
   without it), starting with `GET /v1/market/listings` (read-only, lowest risk) and then
   `POST`/`DELETE`/report.
2. Point `AuthOtpProvider` at the real backend so listings are attributable to a real
   authenticated user rather than only working in a hypothetical connected state.
3. Move the backend to PostgreSQL + Alembic, set a real `JWT_SECRET_KEY`, scope CORS, and
   deploy behind HTTPS.
4. Generate a real Android upload keystore, turn on R8 shrinking, validate on a real device.
5. Decide on SMS OTP vendor and implement `app/providers/sms_otp.py`'s real path (or keep demo
   mode intentionally for a soft-launch/pilot region and be explicit about that choice).
6. Add CI (lint + tests on every push) before onboarding additional contributors.
