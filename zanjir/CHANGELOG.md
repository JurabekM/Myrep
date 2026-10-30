# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalash: [SemVer](https://semver.org/).

## [Unreleased]

### Qo'shildi
- 13-faza — to'liq oflayn (ADR-0017): **shifrlangan zaxira fayli** `zanjir.backup/1` (butun lokal baza, Argon2id +
  ChaCha20-Poly1305, alohida isolate'da); tiklash faqat bo'sh ilovaga — yaxlitlik, migratsiya, barcha audit zanjirlari
  tekshiriladi, telefon yangi qurilma sifatida `BACKUP_RESTORED` bilan ro'yxatdan o'tadi. Ilovada Sozlamalar → "Zaxira nusxa"
  (oxirgi zaxira sanasi, ogohlantirish) va boshlang'ich ekranda "Zaxiradan tiklash"; fayllar tizim oynasi orqali
  (`file_picker`, ruxsatsiz). `docs/RUNBOOK.md` oflayn ish uchun qayta yozildi.
- 13-faza — **telefonlar o'rtasida fayl almashish** (ADR-0017 8-band): imzolangan, laboratoriya kaliti bilan shifrlangan
  to'liq surat; import serverdagi barcha push tekshiruvlarini telefonda bajaradi (audit zanjirlari, qurilmaga ishonch,
  append-only, LWW, o'lchov/protokol/reja/normalar/sozlama qoidalari) — hammasi yoki hech narsa. Xodim qo'shish va bir
  martalik parolli **taklif fayli**, taklif bilan qo'shilish, zaxiradan tiklangan telefonni tasdiqlash, **qurilmani bekor
  qilish** (LEAD ham — F-25). Ilovada "Xodimlar va almashish" ekrani, boshlang'ich ekranda "Taklif fayli bilan qo'shilish".
- 12-faza — release (ADR-0016): `app/tool/build_release.sh` (foydalanuvchi upload kaliti, normalar release darvozasi,
  testlar, R8 + Dart obfuskatsiyasi, simbollar alohida), `build_check.sh` (texnik release build, bir martalik kalit),
  `verify_aab.sh` (imzo, manifest, SDK, ruxsatlar, obfuskatsiya); ilova ikonkasi (`gen_icons.py`, adaptive + Play 512 px);
  CI `zanjir-release`; `docs/RELEASE.md` (versiyalash, checklist, Play internal testing), `docs/PILOT.md`,
  `docs/PLAY_LISTING.md`, `docs/PRIVACY.md` (qoralamalar).
- 11-faza — deploy (ADR-0015): `deploy/` — server Dockerfile (root emas, faqat o'qiladigan FS), `compose.yaml` (PostgreSQL 16,
  bir martalik Alembic migratsiyasi, API, Caddy TLS/HSTS, kunlik zaxira), staging/prod muhit namunalari, `deploy/zanjir`
  boshqaruv skripti (bitta buyruq bilan ko'tarish, zaxira, tiklash, kalit yaratish), baza rollari (`zanjir_owner`,
  `zanjir_api`), `age` bilan shifrlangan `pg_dump` va tiklash; `deploy/check-staging.sh` qabul sinovi va CI `zanjir-deploy`;
  `docs/DEPLOY.md`, `docs/RUNBOOK.md`; E2E testlari TLS bilan staging'ga qarshi ishlay oladi (`ZANJIR_E2E_CA`).
- 10-faza — mustahkamlash (ADR-0014): `docs/SECURITY.md` (STRIDE tahdid modeli, OWASP MASVS L1, topilmalar reestri F-01…F-19,
  qoldiq xavflar R-01…R-10); bog'liqliklar auditi `tools/audit/osv_audit.py` (OSV.dev, istisnolar muddat bilan) va CI
  `zanjir-audit`; unumdorlik testlari (2000 tugunli obyekt, 2900 yozuvli sync, server push); accessibility testlari
  (Android/yorliq/kontrast guideline'lari, ×2 shrift); `key.properties.example`.
- 9-faza — ajratish rejasi (ADR-0013): yadroda bajarish qoidalari (`checkStepCompletion`, `StepConfirmation`,
  `PlanStep/PlanWarning.fromJson`); `IsolationPlanRepository` — qadamlarni ketma-ket bajarish (`PLAN_STEP_DONE` audit
  hodisalari), barcha qadamlar bajarilgandagina yakunlash, rollar, STALE; ilovada rejalar ro'yxati, qoralama saqlash,
  reja ekrani (tasdiqlash, checklist, kuchlanish tekshiruvi uchun ikki tasdiq, yakunlash, bekor qilish, STALE);
  `integration_test/isolation_flow_test.dart`; E2E: tasdiq bir qurilmada, qadamlar boshqasida.
- 8-faza — ilova ↔ server sinxronlash (ADR-0012): `zanjir_data` sxemasi v4 (`sync_outbox`, SQLite triggerlari), `SyncEngine`
  (push paketlari, bitta tranzaksiyali pull, LWW, javob yo'qolsa takrorlanmaslik), `ServerApi` (HTTP, token refresh),
  `ServerAccount` (laboratoriyani ro'yxatdan o'tkazish, taklif bilan qo'shilish, yangi qurilmada kirish); sim formati
  shartnomasi `tools/vectors/sync_schema.json`; ilovada kirish va qo'shilish ekranlari, sozlamalarda "Server" bo'limi,
  fonda sinxronlash, tokenlar Keystore'da; E2E `tools/e2e/run.sh` va CI `e2e` jobi; server `/auth/register` litsenziya muddati.
- 7-faza — server (ADR-0011): PostgreSQL 16 sxemasi (Alembic), RLS + imtiyozsiz ilova roli, append-only va `server_rev`
  triggerlari, kompozit FK; auth (argon2id, JWT 15 daqiqa, refresh rotatsiya va qayta ishlatishni aniqlash, taklif kodlari,
  laboratoriyani ro'yxatdan o'tkazish, SMS OTP interfeysi — o'chiq); foydalanuvchilar, rollar, qurilmalar; `/sync/pull`,
  `/sync/push` (idempotent, LWW, append-only, audit zanjiri, o'lchov/protokol ↔ audit hodisasi, protokolni qayta tekshirish);
  ochiq tekshirish sahifasi `/v/{qr_token}` (uz/ru, PDF yuklash va brauzerda hash tekshiruvi); rate limiting, so'rov hajmi,
  CORS, JSON log, Prometheus, `/healthz`, `/readyz`; RBAC matritsasi (`docs/SECURITY.md`) testlari; CI: testcontainers,
  qamrov ≥ 95%.
- 6-faza — protokol (ADR-0010): `packages/zanjir_protocol` — payload `zanjir.protocol/1` → deterministik PDF (metama'lumotsiz,
  `/ID` = payload hash, Noto Sans + NotoSansMath, QR, har sahifada ogohlantirish, uz/ru matnlar ARB'dan generatsiya);
  `ProtocolRepository.prepare/sign/verify/revoke` — 12 ta bloklash sharti (ochiq sessiya, muddati o'tgan asbob, tekshirilmagan
  normalar, litsenziya, NEEDS_REVIEW → faqat LEAD izoh bilan, rol, qurilma, amaldagi protokol...), eskirgan qoralama himoyasi;
  sxema v3 (`protocol_document`, append-only); ilova protokol ekrani (shartlar, izoh, tasdiqlash, QR, hash'lar, tekshiruv,
  ulashish/chop etish, bekor qilish), FLAG_SECURE, `/v/:token` havolasi, laboratoriya litsenziyasini tahrirlash; CI `protocol` jobi.
- 5-faza — ilova UI (ADR-0009): oflayn laboratoriya profili, kirish ekrani (server 7-fazada), obyektlar, graf (daraxt/graf),
  tugun formasi va kartasi (QR `zanjir://app/n/<id>`, nusxalash), sessiya, tez o'lchov kiritish (rangli natija, avtomatik
  keyingi nuqta, qayta o'lchash), sessiya xulosasi va yopish, ajratish rejasi ko'rinishi, sozlamalar (til uz/ru, katta shrift,
  asboblar, normalar holati, LEAD uchun `k_corr`/zaxira); 255+ l10n kalit; Noto Sans; widget va asosiy oqim testlari,
  emulyator integration jobi.
- `EvalSettings.marginPct` — laboratoriya zaxirasi (effektiv = max); `zanjir_data` sxemasi v2 (`org_setting`, `local_pref`).
- 4-faza — `packages/zanjir_data` (ADR-0008): Drift sxemasi (13 jadval), append-only triggerlar, eksport qilingan sxema va
  migratsiya testlari, org bo'yicha filtrlangan repozitoriylar (obyekt, graf, asbob, sessiya, o'lchov + baholash + audit,
  normalar to'plami, protokol, ajratish rejasi holatlari va STALE), apparatni nusxalash (QF1 → QF2).
- 3-faza — kanonik JSON (RFC 8785), audit hash-zanjiri va Ed25519 imzo Dart va Python'da (ADR-0007):
  `tools/vectors/` umumiy vektorlari (RFC 8785 va RFC 8032 rasmiy natijalari bilan tekshirilgan generator, CI `--check`),
  zanjirni davom ettirish (anchor), 12 ta buzish holati, PDF/imzoning har bir bayti o'zgarishi aniqlanadi.
- 2-faza — ajratish solveri (`planIsolation`, ADR-0006): tugunlarni bo'lish + Edmonds–Karp, zonaga eng yaqin minimal kesim,
  mustaqil BFS tekshiruvi, 5 ta texnik tadbir tartibidagi qadamlar, ogohlantirishlar, `graph_snapshot_hash` va STALE;
  7 ta stsenariy, 1000 ta tasodifiy grafda brute force bilan property test, 2000 tugunli unumdorlik testi va benchmark.
- Kanonik JSON (RFC 8785) va SHA-256 — Dart qismi (Python va umumiy vektorlar — 3-fazada).
- Coverage darvozasi evaluator, solver va crypto uchun (100% qator va branch).
- 1-faza — `zanjir_core`:
  - domen modellari (enumlar, Site/Node/Edge/MeasurementSession/Measurement, UUIDv7);
  - o'zgarmas graf va BFS: yuqoridagi himoya apparati, UZO barcha ta'minot yo'llaridami, bog'langan komponent;
  - normalar modeli va qat'iy YAML yuklovchi (`NormSet.fromYaml`);
  - `evaluate()`: izolyatsiya, sirtmoq, UZO, yerga ulash, metallik bog'lanish (ADR-0005);
  - 147 ta golden holat (har normaga ≥ 3), evaluator uchun 100% qator va branch coverage darvozasi (`tool/check_coverage.dart`).
- `docs/NORMS_REVIEW.md` — muhandis tekshiruv varag'i (M1–M10 savollar, imzo bloki).
- 0-faza — monorepo skeleti (`app/`, `packages/zanjir_core/`, `server/`, `norms/`, `tools/`, `deploy/`, `docs/`),
  `docs/PROMPT.md`, `CLAUDE.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md` (ADR-0001…0005).
- CI: `.github/workflows/zanjir.yml` — Dart analyze/test/coverage, Flutter analyze/test, ruff/mypy/pytest,
  normalar schema tekshiruvi, release darvozasi.

### Tuzatildi
- PR code review (F-20…F-24): o'lchov paytidagi asbob qiyoslash muddati saqlanadi va protokolda tekshiriladi (6-qoida —
  keyingi qayta qiyoslash eski o'lchovni "tozalamaydi"); laboratoriyani ro'yxatdan o'tkazish o'rtada uzilsa qayta urinish va
  kirish tiklaydi; LWW'da yutqazgan qurilma server versiyasini qayta oladi; cheklovlar tozalashi O(n) emas; serverda
  litsenziya raqami tekshiriladi.

### Olib tashlandi
- 13-faza (ADR-0017): server (`server/`), deploy (`deploy/`), E2E testlari, sinxronlash (`SyncEngine`, `ServerApi`,
  `ServerAccount`, `sync_outbox` — sxema v5), kirish/taklif ekranlari, `http` bog'liqligi va `INTERNET` ruxsati (release AAB
  tekshiruvi uni taqiqlaydi). 2-darvoza (domen/server) yo'q. Kripto vektorlari — `tools/vectors/zanjir_refcrypto`.

### O'zgardi
- **1-darvoza olib tashlandi** (ADR-0019, foydalanuvchi qarori): muhandis tekshirmagan normalar protokol imzolash va
  release'ni to'xtatmaydi; protokol ekranida ogohlantirish, PDF'da "muhandis tekshiruvidan o'tmagan", `check_norms.py
  --release` — faqat ogohlantirish, `release-info.txt` da normalar holati. `reviewed_by` to'ldirilmaydi.
- Normalar `0.3.0`: INS-SWGR (shitlar) ≥ **1,0 MΩ** hamma sessiyada (K1 javobi).
- Normalar `0.2.0` (ADR-0018, mustaqil AI ko'rigi 2026-10-30 — muhandis tekshiruvi emas): U0 220–230 V va 380–400 V diapazonlari, ГОСТ IEC
  61009-1 (RCBO), ПТЭЭП/ПУЭ/ГОСТ manbalari aniqlashtirildi; qiymatlar o'zgarmadi. `docs/NORMS_REVIEW.md` qayta generatsiya
  qilindi, ochiq savollar K1–K5. 1-darvoza ochiq.
- Xavfsizlik (10-faza): Android `allowBackup=false`, faqat HTTPS (`network_security_config`), release imzo faqat
  `key.properties` dan; server `/metrics` token bilan, hisob bo'yicha kirish cheklovi, xavfsizlik sarlavhalari, `clock_skew`
  (faqat LWW jadvallari). Ajratish rejasi: server holat o'tishlarini va mazmunni qulflaydi, tasdiq — LEAD/ADMIN ning qadamlar
  hash'iga imzolangan `PLAN_APPROVED` hodisasi bilan. Protokol: server qoidalarni bazadagi yozuvlar bo'yicha tekshiradi
  (o'lchovlarni tushirib qoldirib bo'lmaydi); QR token qurilma imzosidan (`qr_sig`), raqam qurilma belgisi bilan. Sync:
  rad etilganda ham pull, qotgan yozuv UI'da (`SyncRejected`), bitta oqimli refresh; tashkilot/sozlama o'zgarishi — imzolangan
  hodisa bilan; NaN va katta sonlar aniq rad etiladi.
- `IsolationPlanRepository.approve(id)` — tasdiqlovchi joriy foydalanuvchi (`approvedBy` parametri olib tashlandi);
  serverda `PLAN_APPROVED` hodisasi faqat LEAD/ADMIN dan.
- Ilovadagi vaqtinchalik `AuthGateway` (oflayn shlyuz) olib tashlandi — kirish `ServerAccount` orqali.
- `ProtocolRepository.insert` olib tashlandi — protokol faqat `prepare` → `sign` orqali; bekor qilish faqat LEAD/ADMIN, sabab bilan.
- `summarizeValues`, `formatDecimal` — `zanjir_protocol` ga ko'chirildi (ilova va PDF bir xil ko'rinish).
- `norms/v0.yaml`: izolyatsiya normasini tanlash uchun yagona `circuit_class` atributi; INS-SECONDARY faqat CABLE uchun.
