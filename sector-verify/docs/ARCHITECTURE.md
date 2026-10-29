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
- Konventsiya plaginlari: `build-logic/convention` — SDK (`compileSdk`/`targetSdk` 36, `minSdk` 29; ADR-017), Java 17 bytecode,
  Lint, detekt, ktlint, Kover, JUnit 5. AGP 8.10.1. Host testlar faqat `debug` variantida (ADR-012).
- `sv.android.hilt` KSP'ni ulaydi va har `lint[Vital]Analyze<X>` ni `ksp<X>Kotlin` dan keyin ishlatadi — aks holda parallel
  build'da lint KSP'ning vaqtinchalik `byRounds/` fayllarini o'qib yiqiladi (ADR-018).
- Room sxemasi `core/data/schemas/` da, Room Gradle plagini orqali (variantlar bitta faylga parallel yozmaydi).

## Ma'lumot oqimi (o'lchov)
```
TelephonyManager ─► CellCollector ─(dedup)─► CellNormalizer ─┐
                                                              ├─► SurveyEngine ─► BufferedSampleWriter (1 s, 1 tranzaksiya) ─► Room/SQLCipher
LocationManager(GPS) ─► GnssCollector ───────────────────────┘          │
TrafficGenerator (HTTPS HEAD, 2 s) ─► holat                              └─► LiveAnalyzer (har 5 s, inkremental) ─► SurveyController ─► UI
```
- **Sessiya yaratilganda** sayt rejasi (`session.plan_json`) va config (`session.config_json`) nusxalanadi. Jonli ekran, yakuniy
  tahlil, hisobot va ZIP faqat `SessionRepository.plan(sessionId)` dagi nusxani ishlatadi — rejani qayta import qilish eski
  natijalarni o'zgartirmaydi (ADR-016). Nusxasi yo'q eski yozuvlar uchun zaxira — saytning joriy rejasi.
- `SurveyForegroundService` (type `location`, partial WakeLock) — faqat Android "yelimi"; mantiq `SurveyEngine` da (virtual vaqt bilan testlanadi).
  Har `startForegroundService()` dan keyin `startForeground()` chaqiriladi; sessiya id korutinadan oldin band qilinadi
  (takroriy START ikkinchi engine yaratmaydi), engine tayyor bo'lmasdan kelgan STOP keyin bajariladi.
- `BufferedSampleWriter`: 1 s taymer va `stop()` yozuvlari `Mutex` bilan ketma-ket; yozuv `NonCancellable` — bekor qilish
  boshlangan tranzaksiyani uzmaydi, `stop()` uni kutib, qolganini yozadi.
- **Tugatish:** bufer yoziladi → sessiya `DONE` → `SessionAnalysis` (Dispatchers.Default, to'liq bootstrap) → `sector_result`, `finding`, `session.result_json`.
- **Tiklash:** jarayon o'ldirilsa sessiya `RUNNING` qoladi; Saytlar ekrani `SessionResumer` orqali davom ettirishni taklif qiladi
  (yo'qotish ≤ 2 s, AC-07). Servis hali yozayotgan bo'lsa (`isRecording`) — faqat "O'lchovni ochish", qayta boshlash yoki
  tashlab yuborish yo'q; joylashuv ruxsati olib qo'yilgan bo'lsa servis ishga tushirilmaydi (`resumeBlocked`) va foydalanuvchidan oldindan tekshiruvdan o'tish so'raladi.

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
| Sessiyalar (reja va config nusxasi bilan), xom o'lchovlar, natijalar | Room (`sector-verify.db`) | SQLCipher; 32 bayt parol Keystore AES-256-GCM bilan o'ralgan, `noBackupFilesDir/db.key.enc` |
| Sozlamalar | DataStore | backup/transfer'dan chiqarilgan |
| Hisobot imzo kaliti | Android Keystore | eksport qilinmaydi |
| Ilova (APK/AAB) imzo kaliti | qurilmada emas — inson (`keystore.properties`) yoki CI environment secret'lari | repoga tushmaydi (H3, ADR-019) |
| Crash log | `filesDir/crash` | faqat stack trace, joylashuvsiz; foydalanuvchi o'zi eksport qiladi |
- `allowBackup=false`, `dataExtractionRules` va `fullBackupContent` — hammasi chiqarib tashlangan.
- `networkSecurityConfig`: cleartext taqiqlangan. Tarmoqqa faqat `TrafficGenerator` chiqadi (§11).
- Ilova telemetriya, analitika, Firebase, Play Services ishlatmaydi.

## Testlar
| Daraja | Qayerda | Nima |
|---|---|---|
| JVM unit | `core/*`, `tools/replay` | algoritm, simulyator, Monte-Karlo (AC-01…04), formatlar, CLI |
| Robolectric | `core/data`, `feature/*`, `app` (`src/test`) | Room DAO, ViewModel, Compose UI oqimi (Hilt test moduli) |
| Instrumental | `core/data`, `feature/report` (`src/androidTest`) | SQLCipher, Keystore, migratsiya, AC-07, PDF, imzolangan hisobot — CI'da API 34 va API 36 emulyatorlarida |
| Ishlash | `core/analysis` (`@Tag("perf")`) | jonli < 300 ms, yakuniy < 10 s byudjeti (ADR-015) |
| Smoke | `scripts/smoke-release.sh` (CI, API 34 va 36) | R8 release APK o'rnatiladi va yiqilmaydi |
| Reliz | `scripts/verify-release.sh` (`sector-verify-release`) | imzolangan APK/AAB: v3 imzo, debug kalit emas, sertifikat SHA-256, versiya, targetSdk |

## CI va reliz
| Workflow | Qachon | Job'lar |
|---|---|---|
| `.github/workflows/sector-verify.yml` | `sector-verify/**` o'zgarganda (push, PR) | `check` (+ `-Pperf`, Kover) · `instrumented (34)`, `instrumented (36)` (emulyator + release smoke) · `release` (imzosiz AAB/APK, `lintRelease`) |
| `.github/workflows/sector-verify-release.yml` | `sector-verify/v*` tag push | `signed-release`: `sector-verify-release` environment (tag qoidasi, inson tasdig'i) → kalit `$RUNNER_TEMP` ga, Gradle keshi o'chiq → `check` + imzolangan build → `verify-release.sh` → artefakt + draft GitHub Release (izoh — `CHANGELOG.md`) → kalit o'chiriladi |

- **Versiya:** `versionName` — `git describe --match 'sector-verify/v*'`, `versionCode` — `HEAD` dagi commitlar soni (CI `fetch-depth: 0`).
- **Imzo:** `app/build.gradle.kts` kalitni `keystore.properties` yoki `SV_KEYSTORE_*` muhit o'zgaruvchilaridan oladi; topilmasa release
  imzosiz yig'iladi (ogohlantirish bilan). minSdk 29 ≥ 28 bo'lgani uchun APK faqat v3 sxema bilan imzolanadi. Batafsil: `docs/H3_RELEASE_SIGNING.md`.
