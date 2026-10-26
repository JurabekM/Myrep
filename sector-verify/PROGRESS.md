# PROGRESS — Sector Verify

## Joriy holat
- **Bosqich:** 4 — tugadi (tag `sector-verify/phase-4-done`); **H1 va H2 kutilmoqda** (`docs/HUMAN_TASKS.md`)
- **Keyingi:** 5-bosqich — production'ga tayyorlash (H1/H2 bilan parallel)

## Bajarilgan
### 0-bosqich
- ✅ Muhit: JDK 21 (bytecode 17, ADR-003), Android SDK (platform 35, build-tools 35/34), git. `adb` bor, emulyator/KVM yo'q.
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

## Oxirgi test natijalari
- 2026-10-26: `./gradlew check` — BUILD SUCCESSFUL (1-bosqich: model 5 test, analysis 34 test, koverVerify 99.7%).
- 2026-10-26: `./gradlew :core:analysis:test -Pslow` — Monte-Karlo 1000: barcha AC ✅.
- 2026-10-26: CI run #5 (`20209e6`): `check` ✅, `instrumented` (emulyator API 34) ✅ — EncryptedDatabase (4), KeystoreSigner, PdfReportWriter, ReportGenerator.
- 2026-10-26: `./gradlew check` lokal ✅ (barcha modullar, Robolectric UI testlari bilan).

## Ochiq savollar
1. **targetSdk:** prompt 35 ni talab qiladi. Google Play 2026-08-31 dan yangi ilova va yangilanishlar uchun targetSdk 36 ni talab qiladi. Play orqali tarqatilsa 36 ga ko'tarish kerak (APK orqali tarqatishga ta'sir qilmaydi). Hozircha 35.
2. **Tag push:** bulut sessiyasining git proksisi faqat ishchi branch'ga push qilishga ruxsat beradi; `sector-verify/phase-N-done` tag'lari lokal yaratilgan, lekin GitHub'ga chiqmadi. Inson: `git push origin --tags` (yoki tag'larni PR merge'dan keyin qo'ying).
3. **Instrumental testlar:** bu muhitda emulyator yo'q (KVM yo'q) — CI'dagi emulyator job'ida yoki H1 da ishga tushiriladi.

## Kutilayotgan inson darvozasi
- **H1** — 3 chipsetli telefonda probe + 10–15 daqiqalik sessiya → `field-data/h1/` (AC-05).
- **H2** — 20 saytlik pilot + ground truth → `field-data/pilot/` (AC-06, AC-08, AC-09, kalibrlash).
