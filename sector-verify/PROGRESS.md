# PROGRESS — Sector Verify

## Joriy holat
- **Bosqich:** 6 — yakuniy audit tugadi; `master` da (PR #21–#28 merge qilingan), CI yashil. Release-kandidat: `sector-verify/v1.0.0-rc1` → `44cf963` (tag hali GitHub'da emas, pastda 2-savol).
- **Kutilmoqda:** **H1** (real telefonlar), **H2** (20 saytlik pilot), **H3** (imzolash va tarqatish). Har biri uchun dala ko'rsatmasi tayyor:
  `docs/H1_DEVICE_TEST.md`, `docs/H2_PILOT_GUIDE.md`, `docs/H3_RELEASE_SIGNING.md` (umumiy: `docs/HUMAN_TASKS.md`, `docs/RELEASE_CHECKLIST.md`).

## Bajarilgan
### 0-bosqich
- ✅ Muhit: JDK 21 (bytecode 17, ADR-003), Android SDK (platform 35/36, build-tools 34/35/36), git. `adb` bor, emulyator/KVM yo'q.
- ✅ Gradle wrapper 8.11.1 (`gradlew`, `gradlew.bat`), version catalog, `build-logic` konventsiya plaginlari.
- ✅ 13 modul (4.1 + `:core:format`, `:core:ui` — ADR-002), detekt, ktlint, Kover, Android Lint (`abortOnError = true`).
- ✅ `.gitignore`, CI (`.github/workflows/sector-verify.yml`, ADR-001), `CLAUDE.md`, `README.md`, `docs/DECISIONS.md`.
- ✅ Dark tema tokenlari + Noto Sans (`:core:ui`).

### 1-bosqich (G1)
- ✅ `:core:model` — 5.1 domen modellari, `AnalysisConfig` (barcha chegaralar, presetlar, validatsiya).
- ✅ `:core:analysis` — 6.1–6.10 to'liq: tozalash, binlash, A usul, bootstrap, B usul, qamrov, almashinuv, sabab, verdikt, jonli tahlil.
- ✅ Simulyator (6.11): halqa/to'rtburchak, Gudmundson soyasi, Rayleigh, histerezis, 6 ta xato ssenariysi, deterministik.
- ✅ Testlar: Geo (ma'lum koordinatalar), har bir Verdict va CauseCode uchun ssenariy, Kotest property (aylantirishga invariantlik), Monte-Karlo 200 (CI) va 1000 (`-Pslow`).
- ✅ Kover qator qamrovi `:core:analysis`: **99.7%** (AC-10 ≥ 90%).

| AC | 200 iter. | 1000 iter. | Maqsad |
|---|---|---|---|
| AC-01 almashinuvni aniqlash | 99.0% | 98.1% | ≥ 95% ✅ |
| AC-02 noto'g'ri FAIL | 0.0% | 0.0% | ≤ 3% ✅ |
| AC-03 azimut xatosi medianasi | 4.6° | 4.6° | ≤ 10° ✅ |
| AC-04 qamrov yetarli emas → INCONCLUSIVE | 100% | 100% | 100% ✅ |

To'liq jadval: `docs/reports/montecarlo-200.md`, `docs/reports/montecarlo-1000.md` (har build'da `core/analysis/build/reports/montecarlo.md`).
**Ma'lumot uchun (AC emas):** umumiy qamrov yetarli bo'lgan xatosiz simulyatsiyalarda sektor PASS ≈ 81%, sayt PASS ≈ 38–41%
(sayt PASS uchun 3–18 ta cell'ning hammasi PASS bo'lishi kerak; qolganlari asosan INCONCLUSIVE — sektor oynasida qamrov < 60% yoki A/B farqi > 30°).
Pilotdan keyin kalibrlashda (4-bosqich, H2) shu ko'rsatkichni ham kuzatish kerak.

### 2-bosqich
- ✅ `:core:telephony` — CellCollector (requestCellInfoUpdate 1 s + API 31+ CellInfoListener, dedup), CellNormalizer, SubscriptionSelector (dual-SIM), TrafficGenerator (HTTPS HEAD, 2 s), DeviceCapabilityProbe (60 s).
- ✅ `:core:location` — GnssCollector (GPS_PROVIDER, 1 s, 0 m, Play Services'siz).
- ✅ `:core:format` — reja CSV (validatsiya, o'zbekcha xatolar), sessiya CSV/ZIP, `session.json`, `report.json` v1, kanonik JSON, imzo/tekshiruv.
- ✅ `:core:data` — Room v1 (5.2 + `rx_nanos`, `verdict`, `coverage_pct`, `subscription_id`, `detail_json` — ADR-010), SQLCipher (32 bayt parol, Keystore AES-GCM bilan o'ralgan, `noBackupFilesDir`), DataStore sozlamalari, 1 s buferli yozuvchi, ZIP eksport.
- ✅ `:feature:survey` — SurveyForegroundService (location FGS, partial WakeLock, bildirishnoma: namunalar soni, qamrov %, "Natija tayyor"), SurveyEngine (jonli tahlil har 5 s), yakuniy tahlil, RUNNING sessiyani tiklash API, oldindan tekshiruv mantiqi.
- ✅ Debug ekran (faqat debug build): chastota, namunalar, ko'rinayotgan PCI'lar, probe, CSV import, boshlash/tugatish, ZIP eksport.
- ✅ Testlar: normalizer (Robolectric CellInfo builder'lari bilan), DAO/repozitoriy (Robolectric), AC-07 (virtual vaqt: o'ldirilganda ≤ 2 s yo'qotish), engine, pre-check, saqlangan sessiyadan yakuniy tahlil.
- ✅ Instrumental testlar (`core/data/src/androidTest`): SQLCipher fayli shifrlangan, Keystore wrapper, sxema v1 (MigrationTestHelper), AC-07 haqiqiy DB'da. Bu muhitda emulyator yo'q → CI `instrumented` job'ida (GitHub, KVM).

### 3-bosqich (G3)
- ✅ 7 ekran: Saytlar (qidiruv, oxirgi verdikt, CSV import, tugallanmagan sessiyani tiklash), Sayt kartasi (reja + polar), Oldindan tekshiruv (9 tekshiruv, to'sqinlik/ogohlantirish), Jonli o'lchov (xarita canvas, 36 binli radar, PCI kartalari, "Natija tayyor"), Natija (ARFCN bo'yicha polar + 95% yoy, jadval, topilmalar va tavsiyalar, qayta tekshiruv), Hisobot (PDF ko'rish/ulashish, ZIP), Sozlamalar.
- ✅ `report.json` v1 + Keystore EC P-256 imzo (StrongBox bo'lsa, attestation challenge = install UUID), PDF (PdfDocument, hisobot tili ilovadan mustaqil), ZIP (FileProvider orqali).
- ✅ 3 til (uz standart, ru, en) — barcha satrlar `strings.xml` da; dark/light/quyosh mavzulari; tugmalar ≥ 56 dp; ikonlarda contentDescription.
- ✅ Debug ekran faqat debug build'da (`app/src/debug`).
- ✅ Testlar: ViewModel (Turbine), Compose oqim testi (reja → oldindan tekshiruv → sessiya → natija FAIL, Hilt + Robolectric), Sites ekrani, PDF (3 tilda, PdfRenderer bilan sahifalar soni), imzo round-trip (Keystore), hisobot → ZIP → verify (emulyatorda).

### 4-bosqich
- ✅ `:tools:replay` CLI: `analyze`, `calibrate` (162 konfiguratsiyali grid, ADR-014), `verify`, `simulate` (ZIP + ground truth).
- ✅ Simulyator ZIP'larida `calibrate` ishlaydi va testlangan (`ReplayCliTest`); namoyish: `docs/reports/calibration-sim-demo.md` (20 sessiya, 30 s).
- ✅ Ilovada Sozlamalar → Config JSON import (kalibrlash natijasi).

### 5-bosqich
- ✅ Release: R8 minify + shrinkResources, ProGuard qoidalari; AAB til bo'linishi o'chirilgan (ilova ichida til almashtirish); 64-bit `.so` 16 KB tekislangan.
- ✅ Imzolash: `keystore.properties` / `SV_KEYSTORE_*` (kalit repoda yo'q; yo'q bo'lsa imzosiz + ogohlantirish). Versiya git tag + commit sonidan. `CHANGELOG.md`.
- ✅ Xavfsizlik: backup/transfer taqiqi, cleartext taqiqi, FileProvider, SQLCipher kaliti Keystore bilan o'ralgan, loglarsiz.
- ✅ Barqarorlik: lokal crash log (Sozlamalardan eksport), StrictMode debug'da, DB fonda ochiladi, tiklashda ruxsat tekshiruvi.
- ✅ Ruxsatlar UX: har ruxsat uchun izoh, rad etilganda tizim sozlamalariga o'tish; POST_NOTIFICATIONS faqat API 33+.
- ✅ Ishlash: jonli tahlil inkremental (ADR-015): eng og'ir holat ~10–14 ms, yakuniy ~0.45 s (JVM); `docs/BATTERY_TEST.md`.
- ✅ Hujjatlar: README, USER_GUIDE_uz/ru, ARCHITECTURE, ALGORITHM, PLAY_STORE (FGS deklaratsiyasi, Data safety), DISTRIBUTION_APK, privacy uz/ru/en, RELEASE_CHECKLIST.
- ✅ CI: `check` + perf qadami, `instrumented` (emulyator + release smoke test), `release` (bundleRelease, assembleRelease, lintRelease, artefaktlar).

### 6-bosqich (audit)
- ✅ TODO/FIXME yo'q, `Log`/`println` yo'q, qattiq kodlangan UI matni yo'q, Lint 0 muammo (debug va release), detekt toza.
- ✅ Ruxsatlar §7 ga aynan mos; tarmoqqa faqat `TrafficGenerator` chiqadi.
- ✅ Topilib tuzatilgan: AAB til bo'linishi (ilova ichida ru/en ishlamasligi mumkin edi), servis bildirishnomalari tizim tilida chiqishi, tiklashda ruxsatsiz `startForeground` (API 34+ yiqilish), `plan_err_*` format argumentlari.
- ✅ AC holati jadvali: `docs/RELEASE_CHECKLIST.md`.

### PR #21 self-review (Claude, root CLAUDE.md qoidasi)
- ✅ 1–9-topilmalar tuzatildi (`74ba232`, ADR-016): `BufferedSampleWriter` stop/flush poygasi, servisda takroriy START/erta STOP, sessiyaga plan snapshot'i (`plan_json`), sozlamalar probe ruxsat tekshiruvi, tiklash dialogi (yozilayotgan sessiya), swap qidiruvida RAT mosligi, Cleaner interpolatsiya chegarasi, `calibrate` sessiya config'idan, PreCheck chegaralari `AnalysisConfig` dan, `binDeg` hisobot/ekranda config'dan.
- ✅ 10-topilma: barcha Kotlin/Gradle/XML/skript izohlari o'zbekchaga o'tkazildi (faqat izohlar; kod bayt-baayt o'zgarmagan).

### Reliz oldidan (2026-10-27)
- ✅ **targetSdk/compileSdk 36** (PR #22, ADR-017): AGP 8.10.1; Android 16 xatti-harakat o'zgarishlari tekshirildi; CI `instrumented` API 34 va 36 matritsasi; `.so` 16 KB tekislangan.
- ✅ **Lint ↔ KSP poygasi** (PR #24, ADR-018): `lintAnalyze*UnitTest` KSP'ning vaqtinchalik `byRounds/` fayllarini o'qib yiqilardi (`master` PR #23 dan keyin qizil edi) → `sv.android.hilt` lint'ni `ksp<Variant>Kotlin` ga bog'laydi.
- ✅ **Inson darvozalari uchun dala ko'rsatmalari:** H1 (PR #23), H2 (PR #24), H3 (PR #26) — joriy UI va kod bilan solishtirilgan.
- ✅ **CI'da imzolangan reliz** (PR #28, ADR-019): `sector-verify-release` workflow, `sector-verify/v*` tag'ida; kalit himoyalangan environment'da; `scripts/verify-release.sh` (v3 imzo, sertifikat, versiya, targetSdk); draft GitHub Release. Bir martalik test kaliti bilan lokal sinaldi.
- ✅ **Codex ishlatilmaydi** — ildiz `CLAUDE.md` da qat'iy qoida (PR #26): review va barcha ishni Claude bajaradi.

## Oxirgi test natijalari
- 2026-10-26: `./gradlew check` — BUILD SUCCESSFUL (1-bosqich: model 5 test, analysis 34 test, koverVerify 99.7%).
- 2026-10-26: `./gradlew :core:analysis:test -Pslow` — Monte-Karlo 1000: barcha AC ✅.
- 2026-10-26: CI run #5 (`20209e6`): `check` ✅, `instrumented` (emulyator API 34) ✅ — EncryptedDatabase (4), KeystoreSigner, PdfReportWriter, ReportGenerator.
- 2026-10-26: `./gradlew check` lokal ✅ (barcha modullar, Robolectric UI testlari bilan).
- 2026-10-26: CI run #8 (`046a49e`) to'liq yashil (release smoke: OK); self-review tuzatishlaridan keyin `./gradlew check` lokal ✅.
- 2026-10-27: targetSdk 36 — `./gradlew check :app:assembleRelease :app:bundleRelease :app:lintRelease` lokal ✅; APK `targetSdkVersion:'36'`, `.so` 16 KB tekislangan.
- 2026-10-27: PR #22–#28 CI: `check`, `release`, `instrumented (34)`, `instrumented (36)` ✅ (kesh bilan ham — ADR-018 dan keyin); `master` push run'lari PR #24 dan beri yashil (#24, #26, #28).
- 2026-10-27: `verify-release.sh` — test kaliti bilan imzolangan APK/AAB OK; boshqa sertifikat / versiya / debug kalit → rad; `actionlint` toza.

## Ochiq savollar
1. **targetSdk:** ✅ 36 ga ko'tarildi (2026-10-27, foydalanuvchi qarori, ADR-017): AGP 8.10.1, CI'da API 34 va 36 emulyatorlari.
2. **Tag push:** bulut sessiyasining git proksisi tag push qilishni rad etadi (HTTP 403), shuning uchun `sector-verify/phase-0..4-done` va `v1.0.0-rc1` GitHub'da yo'q. Inson (commit'lar `master` da):
   `phase-0-done e6606c3`, `phase-1-done caa4f7d`, `phase-2-done d766d4b`, `phase-3-done 20209e6`, `phase-4-done 97861d7`, `v1.0.0-rc1 44cf963` → `git tag <nom> <sha>` va `git push origin 'refs/tags/sector-verify/*'`.
   Eslatma: `v1.0.0` tag'i push qilinsa `sector-verify-release` workflow ishga tushadi — avval H3 ning 10-bo'limini sozlang.
3. **Instrumental testlar:** bu muhitda emulyator yo'q (KVM yo'q) — CI'dagi emulyator job'ida (API 34 va 36) yoki H1 da ishga tushiriladi.
4. **Simulyatsiyada sayt PASS ≈ 40%** (xatosiz saytlar, qolgani INCONCLUSIVE) — H2 kalibrlashi hal qiladi.
5. **Attestation zanjiri** Google root sertifikatiga nisbatan tekshirilmaydi (hisobot imzosi qurilma kaliti bilan tekshiriladi).
6. **Codex izohlari** PR'larda hali chiqadi — Codex connector'ni foydalanuvchi o'chirishi kerak (chatgpt.com sozlamalari yoki GitHub App).

## Kutilayotgan inson darvozasi
- **H1** — 3 chipsetli telefonda probe + 10–15 daqiqalik sessiya → `field-data/h1/` (AC-05).
- **H2** — 20 saytlik pilot + ground truth → `field-data/pilot/` (AC-06, AC-08, AC-09, kalibrlash).
- **H3** — release kaliti, `sector-verify/v1.0.0` tag'i, imzolangan APK/AAB (qo'lda yoki CI), arxiv va tarqatish.
