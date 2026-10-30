# CLAUDE.md — ZANJIR

ZANJIR — elektrolaboratoriyalar va elektriklar uchun **to'liq oflayn** mobil ilova (server va internet yo'q, ADR-0017):
obyektning elektr grafi, dalada o'lchovlar, normaga avtomatik solishtirish,
imzolangan PDF protokol + QR tekshiruv (ilova ichida), 5 ta texnik tadbir bo'yicha ajratish rejasi.

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
| Testlar | `dart test`, `flutter test`, `integration_test`, pytest (`tools/`) |
| Infra | GitHub Actions (`.github/workflows/zanjir*.yml`) — server/deploy yo'q (ADR-0017) |
| Normalar | `norms/*.yaml` + `norms/schema.json` |

## Tuzilma
```
zanjir/
  app/                  # Flutter ilova
  packages/zanjir_core/ # graf, baholash, solver, kanonik JSON, hash-zanjir
  packages/zanjir_data/ # lokal baza (Drift), repozitoriylar, migratsiyalar, protokol imzolash, zaxira, fayl almashish
  packages/zanjir_protocol/ # protokol payload'i → deterministik PDF (QR bilan)
  norms/                # normalar YAML + JSON Schema
  tools/vectors/        # kripto test vektorlari + mustaqil Python implementatsiyasi (zanjir_refcrypto)
  docs/                 # PROMPT, SPEC, PROGRESS, DECISIONS, RUNBOOK, SECURITY, NORMS_REVIEW, RELEASE, PILOT
```

## Buyruqlar
Muhit: Flutter 3.47.8 / Dart 3.13.7 (`/opt/flutter/bin` — yangi konteynerda qayta o'rnatiladi, ADR-0003), Python 3.12 + `uv`.
- Yadro: `cd packages/zanjir_core && dart format --output=none --set-exit-if-changed . && dart analyze --fatal-infos && dart test`
- Coverage: `cd packages/zanjir_core && dart run coverage:test_with_coverage --branch-coverage && dart run tool/check_coverage.dart` (eval/solver/crypto — 100% qator va branch)
- Ma'lumot qatlami: `cd packages/zanjir_data && dart run build_runner build && dart analyze --fatal-infos && dart test`
  (sxema o'zgarsa: `schemaVersion` + `dart run drift_dev make-migrations`, ADR-0008; so'ng test sxemalarini CI buyrug'i bilan
  qayta generatsiya qiling — `dart run drift_dev schema generate drift_schemas/zanjir/ test/drift/zanjir/generated/` va
  `dart format lib/src/db/database.g.dart test/drift`, aks holda CI'dagi "generatsiya qilingan kod" qadami yiqiladi)
- Protokol PDF: `cd packages/zanjir_protocol && python3 -I tool/gen_strings.py --check && dart analyze --fatal-infos && dart test`
  (PDF matnlari ARB'dan generatsiya qilinadi — ARB o'zgarsa `python3 -I tool/gen_strings.py`; mazmun testlari `pdftotext` talab qiladi)
- Ilova: `cd app && flutter pub get && dart format --output=none --set-exit-if-changed lib test && flutter analyze --fatal-infos && flutter test`
- Normalar: `cd tools/norms && uv sync && uv run pytest && uv run python -I check_norms.py ../../norms` (`--release` — release darvozasi)
- Kripto vektorlari (ADR-0007): `cd tools/vectors && uv sync && uv run pytest && uv run python -I generate.py --check`
  (mustaqil Python implementatsiyasi `zanjir_refcrypto`; vektorlar qo'lda tahrirlanmaydi).
- Android (ADR-0016): `app/tool/build_check.sh` (texnik release build, bir martalik kalit — tarqatilmaydi; AAB tekshiruvi),
  `app/tool/build_release.sh` (haqiqiy release — foydalanuvchi kaliti + barcha darvozalar), `python3 -I app/tool/gen_icons.py`.
  Bu konteynerda: `ANDROID_HOME=/opt/android-sdk` (qayta o'rnatiladi) va `~/.gradle/init.d/maven-mirror.gradle`
  (Maven Central 429 — Google ko'zgusi; repoda emas).
- CI: `.github/workflows/zanjir.yml` (repo ildizida) — yuqoridagilarning hammasi; `zanjir-release.yml` — PR'da texnik AAB
  (INTERNET ruxsati yo'qligi tekshiriladi), qo'lda — release; `zanjir-emulator.yml`, `zanjir-audit.yml`.

## O'zgarmas qoidalar (hech qachon buzilmaydi)
1. Ilova hech qachon "ishlash xavfsiz" demaydi — faqat **tavsiya**; javobgarlik naryad beruvchi va ish rahbarida. Bu matn UI'da va PDF'da ko'rinadi.
2. "Kuchlanish yo'qligini tekshirish" qadamini o'tkazib yuborib, yashirib yoki avtomatik belgilab bo'lmaydi.
3. Ma'lumot yetishmasa → NEEDS_REVIEW. PASS hech qachon standart qiymat emas.
4. Norma qiymatlari faqat YAML'da; kodda "magic number" yo'q.
5. `measurement`, `protocol`, `audit_event` — UPDATE/DELETE yo'q (repozitoriy darajasida + SQLite triggerlari; importda ham).
6. Qiyoslash muddati o'tgan asbob bilan olingan o'lchov imzolanmaydi. NEEDS_REVIEW qolgan sessiyani faqat LEAD izoh bilan imzolaydi.
7. Tashkilotlar ajratilgan: `org_id` filtri; fayl importi boshqa tashkilot ma'lumotini qabul qilmaydi (ADR-0017; avval — Postgres RLS).
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
- Mustaqil Python kripto: `tools/vectors/zanjir_refcrypto/` — Dart bilan bir xil; umumiy vektorlar `tools/vectors/`.
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
- QR token — qurilma imzosidan: `qr_sig = Ed25519("zanjir.qr/1\n<org_id>\n<raqam>")`, `qr_token = sha256(qr_sig)[:32]`
  (yadro `qrTokenMessage`/`qrTokenFromSignature`, vektor `protocol_signature.json`, ADR-0014). Tasodifiy token yaratilmaydi.

## Ajratish rejasi (ADR-0006, ADR-0013)
- Yadro: `solver/execution.dart` — qadamlar faqat ketma-ket, aniq tasdiq bilan; kuchlanish tekshiruvi — 2 tasdiq.
- `IsolationPlanRepository`: `save` → `approve` (LEAD/ADMIN) → `completeStep` (audit `PLAN_STEP_DONE`, `<reja>#<tartib>`) →
  `execute`; `refreshStale`. `PLAN_APPROVED` payload'i — `planApprovalPayload` (qadamlar hash'i bilan; import tasdiqni
  shunga bog'laydi). Ilova: `/sites/:id/plans`, `/plans/:id`, quruvchi `/sites/:id/isolation`; oqim testi
  `test/flow/isolation_flow.dart` (widget + `integration_test`).

## Oflayn rejim (ADR-0017)
- Server, sinxronlash, kirish/taklif ekranlari va `INTERNET` ruxsati yo'q (release AAB tekshiruvi talab qiladi). Yangi tarmoq
  kutubxonasi yoki ruxsat qo'shilmaydi.
- `zanjir_data/lib/src/sync/wire.dart` — jadval ↔ JSON (fayl almashish formati uchun). Sxema v5: sinxronlash navbati o'chirilgan.
- Zaxira: `zanjir_data/lib/src/backup/backup.dart` (Argon2id + ChaCha20-Poly1305, faqat bo'sh ilovaga tiklash, audit
  zanjirlari tekshiriladi, qurilma kaliti zaxirada yo'q — ADR-0017 7-band). Formatni o'zgartirsangiz — versiyani oshiring va
  eski fayllarni o'qish testini qoldiring. Parol hech qayerda saqlanmaydi va logga yozilmaydi.
- Fayl tanlash/saqlash — faqat `FileActions` (`file_picker`, SAF, ruxsatsiz); testlarda `FakeFileActions`.
- Telefonlar o'rtasida fayl almashish: `zanjir_data/lib/src/exchange/` (fayl, import, qoidalar, taklif). Import —
  hammasi yoki hech narsa; har bir yangi qoida/jadval uchun import tekshiruvi va insayder soxtalashtirish testi
  (`test/exchange*_test.dart`) qo'shiladi. Yangi audit hodisasi payload'i qatorlardan qayta tiklanadigan bo'lsin (bazada
  faqat hash). Muharrir hodisalari — `editorEvents`.

## Ilova (`app/`) xaritasi
- `lib/core/` — provayderlar (Riverpod), profil (oflayn), qurilma kaliti, son formatlash, `platform.dart` (FLAG_SECURE,
  PDF ulashish — testlarda soxtasi), `config.dart` (QR havola `zanjir://app/v/`); `lib/router.dart` — go_router (`/start`, `/n/:id`, `/v/:token`).
- `lib/features/*` — ekranlar; `lib/l10n/app_{uz,ru}.arb` + `labels.dart` (domen kodlari → matn).
- Testlar: `test/support/harness.dart` (xotiradagi baza, `startWithSession`, `goTo`, `settle`, `reveal`); asosiy oqim —
  `test/flow/main_flow.dart` (widget testi — katta va kichik 360×640 ekran — va `integration_test/`). Lazy ro'yxatdagi
  elementlar uchun `reveal` (vertikal ro'yxat, ekran markaziga). `assets/norms/v0.yaml` = `norms/v0.yaml` (test nazoratida).

## Release (ADR-0016)
- Upload kalitini foydalanuvchi so'rovi bilan Claude yaratdi (2026-10-30, ADR-0017) va foydalanuvchiga topshirdi; keystore va
  parol repoga, logga, hujjatga yozilmaydi (`key.properties` — `.gitignore`). `build_check.sh` dagi bir martalik kalit faqat
  texnik tekshiruv uchun. `build_release.sh` darvozalarini chetlab o'tadigan parametr qo'shilmaydi.
- Yangi Android ruxsati yoki manifest o'zgarishi → `verify_aab.sh` ruxsatlar ro'yxati, `docs/PLAY_LISTING.md` (Data safety).
- Hujjatlar: `docs/RELEASE.md` (checklist), `docs/PILOT.md`, `docs/PLAY_LISTING.md`, `docs/PRIVACY.md` (qoralama).

## Xavfsizlik (ADR-0014)
- `docs/SECURITY.md` — tahdid modeli, MASVS, RBAC, topilmalar reestri (F-*) va qoldiq xavflar (R-*). Yangi topilma yoki
  qabul qilingan xavf — reestrga. Bog'liqliklar: `python3 -I tools/audit/osv_audit.py` (istisno — `allowlist.json`, muddat bilan).

## UI
- Standart mavzu — Myrep dark tokenlari (`../CLAUDE.md` jadvali), light — ixtiyoriy. Shrift: ilova ichidagi Noto Sans.
- Tugmalar ≥ 48 dp, katta shrift rejimi, TalkBack; natija ranglari kontrasti WCAG AA (`success #7DBE8A` — ADR-0009).
- Kiritishda PASS ga olib keladigan standart qiymat yo'q (UZO natijasi, ψ, atributlar — tanlanmaguncha bo'sh).

## Git
- Ishchi branch: `claude/new-session-2w6wwo` (sessiya bo'yicha belgilangan). PR faqat foydalanuvchi so'raganda.
- Har faza oxirida: testlar → `docs/PROGRESS.md`, `CHANGELOG.md`, kerak bo'lsa ADR yangilanadi.
