# CLAUDE.md — ZANJIR

ZANJIR — elektrolaboratoriyalar va elektriklar uchun offline-first mobil ilova:
obyektning elektr grafi, dalada o'lchovlar, normaga avtomatik solishtirish,
imzolangan PDF protokol + QR tekshiruv sahifasi, 5 ta texnik tadbir bo'yicha ajratish rejasi.

To'liq topshiriq: `docs/PROMPT.md` (o'zgartirilmaydi; qaror o'zgarsa — `docs/DECISIONS.md` ga ADR).
Ildizdagi `../CLAUDE.md` (Myrep umumiy qoidalari) ham amal qiladi.

## Har sessiya boshida
1. Shu fayl → `docs/PROGRESS.md` (joriy faza, ochiq savollar, inson darvozalari).
2. Kerak bo'lsa: `docs/DECISIONS.md` (ADR), `docs/PROMPT.md` ning tegishli bo'limi.
3. Joriy fazadan davom et. Faqat `🛑 INSON DARVOZASI` da yoki elektr xavfsizligi bo'yicha noaniqlikda to'xta.

## Stek (o'zgartirish — faqat ADR + foydalanuvchi roziligi bilan)
| Qatlam | Tanlov |
|---|---|
| Mobil | Flutter 3 (stable), Dart 3, Riverpod, go_router |
| Lokal baza | Drift (SQLite), versiyalangan migratsiyalar |
| Yadro | `packages/zanjir_core` — sof Dart, Flutter'ga bog'liq emas |
| PDF / QR | `pdf`, `printing`, `qr_flutter` |
| Kripto | `cryptography` (SHA-256, Ed25519), `flutter_secure_storage` |
| Server | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2 |
| Server bazasi | PostgreSQL 16 + Row-Level Security |
| Testlar | `dart test`, `flutter test`, `integration_test`, pytest, testcontainers |
| Infra | Docker, docker compose, Caddy, GitHub Actions (`.github/workflows/zanjir.yml`) |
| Normalar | `norms/*.yaml` + `norms/schema.json` |

## Tuzilma
```
zanjir/
  app/                  # Flutter ilova
  packages/zanjir_core/ # graf, baholash, solver, kanonik JSON, hash-zanjir
  packages/zanjir_data/ # lokal baza (Drift), repozitoriylar, migratsiyalar, protokol imzolash
  packages/zanjir_protocol/ # protokol payload'i → deterministik PDF (QR bilan)
  server/               # FastAPI
  norms/                # normalar YAML + JSON Schema
  tools/vectors/        # Dart va Python uchun umumiy kripto test vektorlari
  deploy/               # Dockerfile, compose, Caddyfile, backup skriptlari
  docs/                 # PROMPT, SPEC, PROGRESS, DECISIONS, DEPLOY, RUNBOOK, SECURITY, NORMS_REVIEW
```

## Buyruqlar
Muhit: Flutter 3.47.8 / Dart 3.13.7 (`/opt/flutter/bin` — yangi konteynerda qayta o'rnatiladi, ADR-0003), Python 3.12 + `uv`.
- Yadro: `cd packages/zanjir_core && dart format --output=none --set-exit-if-changed . && dart analyze --fatal-infos && dart test`
- Coverage: `cd packages/zanjir_core && dart run coverage:test_with_coverage --branch-coverage && dart run tool/check_coverage.dart` (eval/solver/crypto — 100% qator va branch)
- Ma'lumot qatlami: `cd packages/zanjir_data && dart run build_runner build && dart analyze --fatal-infos && dart test`
  (sxema o'zgarsa: `schemaVersion` + `dart run drift_dev make-migrations`, ADR-0008)
- Protokol PDF: `cd packages/zanjir_protocol && python3 -I tool/gen_strings.py --check && dart analyze --fatal-infos && dart test`
  (PDF matnlari ARB'dan generatsiya qilinadi — ARB o'zgarsa `python3 -I tool/gen_strings.py`; mazmun testlari `pdftotext` talab qiladi)
- Ilova: `cd app && flutter pub get && dart format --output=none --set-exit-if-changed lib test && flutter analyze --fatal-infos && flutter test`
- Server: `cd server && uv sync && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest --cov=zanjir_server --cov-branch`
  (Docker kerak — testcontainers PostgreSQL 16; Docker o'rniga `ZANJIR_TEST_DATABASE_URL`; konteynerda `dockerd &` va
  `TESTCONTAINERS_RYUK_DISABLED=true`). Migratsiya: `uv run alembic upgrade head` (`ZANJIR_DATABASE_URL`).
- Normalar: `cd tools/norms && uv sync && uv run pytest && uv run python -I check_norms.py ../../norms` (`--release` — release darvozasi)
- Kripto vektorlari: `cd server && uv run python -I ../tools/vectors/generate.py --check` (qo'lda tahrirlanmaydi, ADR-0007)
- CI: `.github/workflows/zanjir.yml` (repo ildizida) — yuqoridagilarning hammasi.

## O'zgarmas qoidalar (hech qachon buzilmaydi)
1. Ilova hech qachon "ishlash xavfsiz" demaydi — faqat **tavsiya**; javobgarlik naryad beruvchi va ish rahbarida. Bu matn UI'da va PDF'da ko'rinadi.
2. "Kuchlanish yo'qligini tekshirish" qadamini o'tkazib yuborib, yashirib yoki avtomatik belgilab bo'lmaydi.
3. Ma'lumot yetishmasa → NEEDS_REVIEW. PASS hech qachon standart qiymat emas.
4. Norma qiymatlari faqat YAML'da; kodda "magic number" yo'q.
5. `measurement`, `protocol`, `audit_event` — UPDATE/DELETE yo'q (serverda DB trigger, ilovada repozitoriy darajasida).
6. Qiyoslash muddati o'tgan asbob bilan olingan o'lchov imzolanmaydi. NEEDS_REVIEW qolgan sessiyani faqat LEAD izoh bilan imzolaydi.
7. Tashkilotlar ajratilgan: `org_id` filtri + Postgres RLS birga.
8. Maxfiy ma'lumot (parol, token, kalit, shaxsiy ma'lumot) logga yozilmaydi.
9. `zanjir_core` uchun avval test, keyin kod.
10. Elektr xavfsizligi bo'yicha noaniqlik → to'xta va so'ra.
11. `norms/*.yaml` dagi `reviewed_by` / `reviewed_at` ni Claude **hech qachon** to'ldirmaydi — faqat litsenziyali muhandis.

## Til
- Izohlar, commit xabarlari (ushbu loyiha uchun foydalanuvchi talabi), README, `docs/*`, hisobotlar — o'zbekcha (lotin).
- Kod, identifikatorlar, buyruqlar, log kalitlari — inglizcha.
- UI: `uz` (standart) va `ru`, `gen-l10n` + ARB; qattiq yozilgan matn yo'q.

## Yadro (`zanjir_core`) xaritasi
- `lib/src/model/` — enumlar va entitylar; `lib/src/graph/` — graf, BFS, yuqoridagi himoya apparati.
- `lib/src/norms/` — normalar modeli, qat'iy YAML yuklovchi, qo'llanish sharti.
- `lib/src/eval/` — `evaluate()`, `rule_check.dart` (umumiy qoida tekshiruvi), `evaluators/*` (o'lchov turlari bo'yicha).
- `lib/src/solver/` — `planIsolation()`, Edmonds–Karp, qadamlar, ogohlantirishlar, `graph_snapshot_hash` (ADR-0006).
- `lib/src/crypto/` — kanonik JSON (RFC 8785), SHA-256, Ed25519 `Signer`, hash-zanjir, protokol imzosi (ADR-0007).
- Server kripto: `server/zanjir_server/crypto/` — Dart bilan bir xil; umumiy vektorlar `tools/vectors/`.
- Benchmark: `dart run benchmark/solver_bench.dart` (2000 tugun < 500 ms Android talabi).
- Golden testlar: `test/golden/*.cases.yaml` + `graphs.yaml`; har normaga ≥ 3 holat (meta-test tekshiradi).
- Baholash semantikasi: ADR-0002, ADR-0005. Sabab kodlari (`reason`) — barqaror inglizcha kalitlar.

## Protokol (ADR-0010)
- `zanjir_protocol`: `renderProtocolPdf(payload, fonts)` — metama'lumotsiz, `/ID` = `payload_sha256`; `ProtocolTexts`, `summarizeValues`.
- `zanjir_data` `ProtocolRepository`: `prepare` → `ProtocolDraft{payload, blockers}` → `sign(draft, fonts)` → `protocol` +
  `protocol_document` (PDF saqlanadi) + `PROTOCOL_SIGNED`; `verify`, `revoke` (LEAD/ADMIN, sabab bilan).
- Bloklash kodlari (`ProtocolBlocker.code`) — barqaror inglizcha; UI matni `labels.dart` `blockerText`. Yangi shart qo'shilsa —
  ARB, `labels_test.dart` `blockerCodes`, ADR.
- Testlarda tekshirilgan normalar faqat test nusxasi ("TEST FIXTURE", versiya `0.1.1`); `norms/v0.yaml` ga tegilmaydi.

## Server (`server/`, ADR-0011) xaritasi
- `zanjir_server/db/` — modellar (ustunlar ilova bilan bir xil), `session.py` (`org_session` — RLS, `lookup_org`),
  `migrations/` (Alembic; RLS, append-only va `server_rev` triggerlari, `zanjir_app` roli).
- `api/` — `auth` (kirish, refresh rotatsiya, taklif, ro'yxatdan o'tish), `org` (takliflar, foydalanuvchilar, qurilmalar),
  `sync`, `public` (`/v/{qr_token}`, health, metrics); `deps.py` — `Viewer/Engineer/Lead/Admin` rol talablari.
- `sync/` — `wire.py` (sim formati), `service.py` (push qoidalari, pull), `protocol_rules.py` (6-qoida serverda).
- Yangi endpoint → `tests/test_rbac_matrix.py` `MATRIX` va `docs/SECURITY.md` jadvali (aks holda test yiqiladi).
- Testlar: `tests/support/api.py` (tashkilot/rollar), `tests/support/field.py` (dala qurilmasi taqlidi: audit zanjiri, imzo).

## Ilova (`app/`) xaritasi
- `lib/core/` — provayderlar (Riverpod), profil (oflayn), qurilma kaliti, son formatlash, `platform.dart` (FLAG_SECURE,
  PDF ulashish — testlarda soxtasi), `config.dart` (`ZANJIR_VERIFY_BASE_URL`); `lib/router.dart` — go_router (`/n/:id`, `/v/:token`).
- `lib/features/*` — ekranlar; `lib/l10n/app_{uz,ru}.arb` + `labels.dart` (domen kodlari → matn).
- Testlar: `test/support/harness.dart` (xotiradagi baza, `startWithSession`, `goTo`, `settle`, `reveal`); asosiy oqim —
  `test/flow/main_flow.dart` (widget testi va `integration_test/`). `assets/norms/v0.yaml` = `norms/v0.yaml` (test nazoratida).

## UI
- Standart mavzu — Myrep dark tokenlari (`../CLAUDE.md` jadvali), light — ixtiyoriy. Shrift: ilova ichidagi Noto Sans.
- Tugmalar ≥ 48 dp, katta shrift rejimi, TalkBack; natija ranglari kontrasti WCAG AA (`success #7DBE8A` — ADR-0009).
- Kiritishda PASS ga olib keladigan standart qiymat yo'q (UZO natijasi, ψ, atributlar — tanlanmaguncha bo'sh).

## Git
- Ishchi branch: `claude/new-session-2w6wwo` (sessiya bo'yicha belgilangan). PR faqat foydalanuvchi so'raganda.
- Har faza oxirida: testlar → `docs/PROGRESS.md`, `CHANGELOG.md`, kerak bo'lsa ADR yangilanadi.
