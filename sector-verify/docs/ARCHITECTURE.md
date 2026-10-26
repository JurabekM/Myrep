# Arxitektura

## Modullar va bog'liqliklar
```
:app ──► :feature:plan ─────┐
     ├─► :feature:survey ───┤──► :core:ui ──► :core:model
     ├─► :feature:report ───┤──► :core:data ──► :core:format ──► :core:model
     └─► :feature:settings ─┘    :core:telephony, :core:location ──► :core:model
                                 :core:analysis ──► :core:model        (sof Kotlin/JVM)
:tools:replay ──► :core:analysis, :core:format                         (JVM CLI)
```
- **Sof JVM** (`:core:model`, `:core:analysis`, `:core:format`, `:tools:replay`): Android importi yo'q — algoritm, formatlar va
  replay bir xil kod bilan ishlaydi (ilova yozgan ZIP'ni CLI aynan shu kod bilan o'qiydi).
- **Feature modullar bir-biriga bog'liq emas.** Kesishuvlar interfeys orqali: `SessionResumer` (plan → survey) `:app` da bog'lanadi.
- Konventsiya plaginlari: `build-logic/convention` (SDK, Java 17, Lint, detekt, ktlint, Kover, JUnit 5).

## Ma'lumot oqimi (o'lchov)
```
TelephonyManager ─► CellCollector ─(dedup)─► CellNormalizer ─┐
                                                              ├─► SurveyEngine ─► BufferedSampleWriter (1 s, 1 tranzaksiya) ─► Room/SQLCipher
LocationManager(GPS) ─► GnssCollector ───────────────────────┘          │
TrafficGenerator (HTTPS HEAD, 2 s) ─► holat                              └─► LiveAnalyzer (har 5 s, inkremental) ─► SurveyController ─► UI
```
- `SurveyForegroundService` (type `location`, partial WakeLock) — faqat Android "yelimi"; mantiq `SurveyEngine` da (virtual vaqt bilan testlanadi).
- **Tugatish:** bufer yoziladi → sessiya `DONE` → `SessionAnalysis` (Dispatchers.Default, to'liq bootstrap) → `sector_result`, `finding`, `session.result_json`.
- **Tiklash:** jarayon o'ldirilsa sessiya `RUNNING` qoladi; Saytlar ekrani davom ettirishni taklif qiladi (yo'qotish ≤ 2 s, AC-07).

## Hisobot
`ReportJson.build` (schema `sector-verify/report/v1`) → `ReportIntegrity.seal` (kanonik JSON → SHA-256 → `SHA256withECDSA`,
Keystore EC P-256, StrongBox bo'lsa, attestation challenge = install UUID) → `PdfReportWriter` (hisobot tilida) → `SessionZip`.
Fayllar `cacheDir/exports` da va faqat `FileProvider` orqali ulashiladi.

**Imzo nimani isbotlaydi:** `sv-replay verify` hisobot imzolangandan keyin o'zgarmaganini (xesh + imzo) va imzolovchi kalitning
SHA-256 barmoq izini ko'rsatadi. Kalit qaysi telefonniki ekanini barmoq izini telefon ro'yxati bilan solishtirib bilish mumkin.
Attestation zanjiri hisobotda saqlanadi, lekin v1.0 da Google ildiz sertifikatiga nisbatan tekshirilmaydi (v1.1 rejasi).

## Saqlash va xavfsizlik
| Narsa | Qayerda | Himoya |
|---|---|---|
| Sessiyalar, xom o'lchovlar, natijalar | Room (`sector-verify.db`) | SQLCipher; 32 bayt parol Keystore AES-256-GCM bilan o'ralgan, `noBackupFilesDir/db.key.enc` |
| Sozlamalar | DataStore | backup/transfer'dan chiqarilgan |
| Hisobot imzo kaliti | Android Keystore | eksport qilinmaydi |
| Crash log | `filesDir/crash` | faqat stack trace, joylashuvsiz; foydalanuvchi o'zi eksport qiladi |
- `allowBackup=false`, `dataExtractionRules` va `fullBackupContent` — hammasi chiqarib tashlangan.
- `networkSecurityConfig`: cleartext taqiqlangan. Tarmoqqa faqat `TrafficGenerator` chiqadi (§11).
- Ilova telemetriya, analitika, Firebase, Play Services ishlatmaydi.

## Testlar
| Daraja | Qayerda | Nima |
|---|---|---|
| JVM unit | `core/*`, `tools/replay` | algoritm, simulyator, Monte-Karlo (AC-01…04), formatlar, CLI |
| Robolectric | `core/data`, `feature/*`, `app` (`src/test`) | Room DAO, ViewModel, Compose UI oqimi (Hilt test moduli) |
| Instrumental | `core/data`, `feature/report` (`src/androidTest`) | SQLCipher, Keystore, migratsiya, AC-07, PDF, imzolangan hisobot |
| Ishlash | `core/analysis` (`@Tag("perf")`) | jonli < 300 ms, yakuniy < 10 s byudjeti (ADR-015) |
| Smoke | `scripts/smoke-release.sh` (CI) | R8 release APK o'rnatiladi va yiqilmaydi |
