# Qarorlar (ADR)

Har bir yozuv: kontekst → qaror → sabab. Promptdan chetga chiqishlar albatta shu yerda.

## ADR-001 — Monorepo ichida joylashuv (2026-10-26)
- **Kontekst:** Prompt alohida Windows papkasini (`C:\...\sector-verify`) va ildizda `.github/workflows/ci.yml` ni nazarda tutadi. Ish Myrep monoreposida (`Myrep/sector-verify/`) bajarilmoqda; GitHub faqat repo ildizidagi `.github/workflows` ni o'qiydi.
- **Qaror:** Loyiha `Myrep/sector-verify/`; CI — `Myrep/.github/workflows/sector-verify.yml` (`paths: sector-verify/**`). Tag'lar prefiksli: `sector-verify/phase-N-done`, `sector-verify/v1.0.0-rc1`.
- **Sabab:** Boshqa loyihalar tag'lari bilan to'qnashmaslik; CI faqat shu loyiha o'zgarganda ishlaydi.

## ADR-002 — Qo'shimcha modullar `:core:format` va `:core:ui` (2026-10-26)
- **Kontekst:** Reja CSV, sessiya ZIP (CSV/JSON) va kanonik `report.json` formatlarini ham ilova (`:feature:*`, `:core:data`), ham `:tools:replay` (JVM CLI) o'qishi kerak. Tema va umumiy komponentlar 4 ta feature modulida kerak.
- **Qaror:** `:core:format` (sof Kotlin/JVM: CSV/JSON kodeklar, `report/v1` sxemasi, kanonik JSON, ZIP tarkibi) va `:core:ui` (Android lib: dark tema, Noto Sans, umumiy Compose komponentlari).
- **Sabab:** Formatlar uchun yagona manba (ilova yozgan ZIP'ni replay aynan shu kod bilan o'qiydi); `:core:analysis` faqat algoritmga mas'ul bo'lib qoladi.

## ADR-003 — JDK 17 bytecode, toolchain'siz (2026-10-26)
- **Kontekst:** Claude bulut muhitida faqat JDK 21 bor; Gradle toolchain JDK 17 ni topa olmaydi va yuklab ololmaydi.
- **Qaror:** Toolchain ishlatilmaydi; `sourceCompatibility/targetCompatibility = 17`, Kotlin `jvmTarget = 17`. CI va inson muhiti JDK 17 da.
- **Sabab:** Bytecode baribir Java 17 ga mos; muhitlar orasida build bir xil.

## ADR-004 — Versiyalar (2026-10-26)
- **Qaror:** AGP 8.7.3, Gradle 8.11.1, Kotlin 2.1.0, KSP 2.1.0-1.0.29, Hilt 2.54, Room 2.6.1, Compose BOM 2024.12.01, SQLCipher 4.6.1, detekt 1.23.7, ktlint 1.4.1, Kover 0.9.1, JUnit 5.11.4, Kotest 5.9.1, Robolectric 4.14.1.
- **Sabab:** Bir-biri bilan sinalgan barqaror to'plam. Yangilash — alohida vazifa (5-bosqichdan keyin), har biri `check` bilan.

## ADR-005 — Xarita: MVP'da asosiy xarita qatlami yo'q (2026-10-26)
- **Kontekst:** OSM tile'larini ommaviy yuklab olish OSM tile siyosatiga zid; ilova to'liq offline.
- **Qaror:** Canvas'da sayt, halqa, iz (rang = serving PCI), shimol strelkasi va masshtab chiziladi. Foydalanuvchi bergan MBTiles faylini import qilish — v1.1.
- **Sabab:** Litsenziya/siyosat xavfi yo'q, tarmoq so'rovi yo'q (11-bo'lim).

## ADR-006 — Android testlari: Robolectric (JVM) + instrumental (emulyator CI) (2026-10-26)
- **Kontekst:** Bulut muhitida KVM yo'q, emulyator ishlamaydi. Room DAO va Compose UI testlarini `check` ichida ishlatish foydali.
- **Qaror:** Room DAO, ViewModel, Compose UI testlari — Robolectric bilan `src/test` da (JUnit 4 → vintage engine, qolgani JUnit 5). SQLCipher, migratsiya va AC-07 testlari — `src/androidTest` da, CI'da emulyatorda.
- **Sabab:** `check` mahalliy ravishda haqiqiy UI/DB mantiqini tekshiradi; native SQLCipher faqat haqiqiy Android'da ishlaydi.

## ADR-007 — UI mavzusi (2026-10-26)
- **Kontekst:** Myrep qoidasi: barcha ilovalar standart holda Claude Code dark theme uslubida; prompt "quyosh" yuqori kontrastli rejimni talab qiladi.
- **Qaror:** `ThemeMode { DARK (standart), LIGHT, SUN }`. Tokenlar `baraka_oilasi/shared/design-tokens/tokens.json` dan; SUN — qora fon, oq matn (kontrast ≥ 15:1). Noto Sans ilova ichida (`core/ui/res/font`, OFL).
- **Sabab:** Foydalanuvchi qarori 2026-10-15 + dala sharoiti talabi.

## ADR-008 — Algoritm talqinlari (1-bosqich, 2026-10-26)
Promptdagi noaniq joylar uchun qabul qilingan talqinlar (barchasi `SessionAnalyzer`/`AnalysisConfig` da):
1. **Namuna yoshi (6.1.2):** `CellSample` ga `rxNanos` (ilova namunani olgan vaqt, `elapsedRealtimeNanos`) qo'shildi; yosh = `rxNanos − tNanos`. Room `cell_sample` jadvalida `rx_nanos` ustuni bo'ladi.
2. **GNSS sifati (6.1.4):** `accM > 15` yoki `speedMps > 8` bo'lgan fix'lar interpolyatsiyadan **oldin** chiqariladi; natijada yaqin fix bo'lmagan namuna 6.1.3 bo'yicha tashlanadi.
3. **Bin markazi:** `(i + 0.5)·binDeg`; sektor oynasi — reja azimutiga eng yaqin 18 bin.
4. **Umumiy qamrov yetarli bo'lmasa** almashinuv qidirilmaydi va barcha sektorlar INCONCLUSIVE/LOW_COVERAGE ("qamrov yo'q bo'lsa FAIL berilmaydi").
5. **Almashinuv (6.7) kirishi:** "bahosi bor" = bin ≥ 6 bo'lgan har qanday sektor (sektor qamrovidan qat'i nazar). Almashgan sektor qamrovi u **haqiqatda nurlanayotgan** sektorning reja oynasi bo'yicha tekshiriladi.
6. **Sabab (6.8):** sektor label'ining boshqa ARFCN'lari bo'lmasa → `CELL_CONFIG_SWAP`; qolganlari almashmagan va PASS → `BAND_PORT_SWAP`; hammasi bir xil nishonga almashgan → `CELL_CONFIG_SWAP`; aralash holat → `BAND_PORT_SWAP`.
7. **Burilish:** `20 < |δ| ≤ 45`, barcha baholangan ARFCN'larda bir xil ishora, farq ≤ 10° (bitta ARFCN ham yetarli).
8. **PCI_MISSING** ustuvorligi bin < 6 dan yuqori (namuna < 20 bo'lsa bin ham kam bo'ladi), lekin faqat umumiy qamrov yetarli bo'lganda.
9. **PCI_UNEXPECTED:** ≤ 300 m dagi namunalar soni ≥ `minSamplesPresent` (20) bo'lishi ham talab qilinadi (shovqindan himoya); natija `label = null`, INCONCLUSIVE, sayt verdiktiga ta'sir qilmaydi.
10. **Sayt verdikti:** biror sektor FAIL yoki CRITICAL topilma → FAIL; aks holda INCONCLUSIVE bo'lsa → INCONCLUSIVE; WARN → WARN; aks holda PASS.
11. **Bootstrap seed:** har bir cell uchun `Random(seed xor stableHash(key))` — natija xarita tartibiga bog'liq emas.

## ADR-009 — Monte-Karlo AC ta'riflari (2026-10-26)
- **AC-01:** xato = to'liq almashinuv (2/3 sektor aylanmasi, barcha ARFCN) yoki bitta band almashinuvi; qamrov 70–100%. "Aniqlandi" = har bir almashgan cell kutilgan nishon label'i bilan SWAP topilmasida bor.
- **AC-02:** xato yo'q (20% holatda PCI'ni qayta ishlatuvchi qo'shni sayt), qamrov 50–100%; sayt verdikti FAIL → noto'g'ri FAIL.
- **AC-03:** xato yo'q, qamrov 70–100%; |α̂ − haqiqiy α| medianasi (haqiqiy α = reja + o'rnatish xatosi σ = 3°).
- **AC-04:** qamrov 30–60% (yarmi almashinuvli); sayt va barcha rejadagi sektorlar INCONCLUSIVE.
- Tasodifiy parametrlar: 3–6 sektor, 1–3 ARFCN, halqa/to'rtburchak, radius 150–400 m, 80% piyoda (1.4 m/s) / 20% 5 m/s, soya σ 6–8 dB, `pNeighbor` 0.5–1.0, bootstrap 50.

## ADR-010 — Room sxemasiga qo'shimcha ustunlar (2-bosqich, 2026-10-26)
- **Kontekst:** 5.2 jadvali saytlar ro'yxatidagi "oxirgi verdikt", natija ekranidagi CI yarim kengligi/qamrov/yetishmayotgan binlar va tiklashda SIM'ni bilish uchun yetarli emas.
- **Qaror:** `cell_sample.rx_nanos` (ADR-008.1), `session.verdict`, `session.coverage_pct`, `session.subscription_id`, `session.result_json` (to'liq `SessionResult` — hisobot uchun), `sector_result.detail_json` (to'liq `SectorResult`). `sector_result` dagi baholash ustunlari INCONCLUSIVE uchun nullable. `sector_result.sector_id` — `ON DELETE SET NULL` (reja qayta import qilinganda natija saqlanadi).
- **Sabab:** Xom jadvallar o'zgarmaydi; qo'shimchalar faqat hosila ma'lumot.

## ADR-011 — Survey arxitekturasi (2-bosqich, 2026-10-26)
- **Qaror:** Android'siz `SurveyEngine` (oqimlar → `BufferedSampleWriter` + xotiradagi nusxa → har 5 s `LiveAnalyzer`), `SurveyForegroundService` faqat "yelim" kod. Holat UI'ga `SurveyController` (singleton StateFlow) orqali. Servis `START_NOT_STICKY`: jarayon o'ldirilsa, keyingi ishga tushishda RUNNING sessiya topilib davom ettirish taklif qilinadi (§7), avtomatik qayta boshlanmaydi.
- **Sabab:** Engine'ni virtual vaqt bilan testlash mumkin; foydalanuvchi bilmagan holda fon yig'ish bo'lmaydi.

## ADR-012 — Host testlar faqat debug variantida (3-bosqich, 2026-10-26)
- **Kontekst:** Compose UI testlari `ui-test-manifest` (test activity) ni talab qiladi; u faqat `debugImplementation` — release APK'ga test activity kirmasligi kerak. `testReleaseUnitTest` shu sababli ishlamaydi va vaqtni ikki baravar oshiradi.
- **Qaror:** Barcha Android modullarida release uchun `enableUnitTest = false`. Release build'ning to'g'riligi 5-bosqichda `assembleRelease`/`bundleRelease` va emulyatordagi smoke test bilan tekshiriladi.

## ADR-013 — Til va hisobot (3-bosqich, 2026-10-26)
- **Ilova tili:** `LocaleStore` (SharedPreferences ko'zgusi) + `attachBaseContext` da kontekstni o'rash (Activity va SurveyForegroundService). Standart — o'zbek, tizim tilidan qat'i nazar. Til o'zgarganda Activity qayta yaratiladi.
- **Hisobot tili** ilovadan mustaqil: PDF `createConfigurationContext(locale)` bilan chiziladi.
- **PDF ranglari:** qog'ozga chop etish uchun Myrep light tokenlari (oq fon); ilova UI esa standart dark.
- **Testda til:** Robolectric tizim tili inglizcha bo'lgani uchun UI testlari `qualifiers = "b+uz"` yoki MainActivity orqali ishlaydi.

## ADR-014 — Kalibrlash vositasi (4-bosqich, 2026-10-26)
- **Grid:** `n` ∈ {3.0, 3.5, 4.0}, PASS |δ| ∈ {15, 20, 25}, WARN |δ| ∈ {40, 45, 50}, `swapMaxErrDeg` ∈ {25, 30, 35}, `minSectorCoverage` ∈ {0.5, 0.6} → 162 (PASS < WARN). Grid bootstrap 50, tanlangan config yakunda standart bootstrap (200) bilan qayta baholanadi.
- **Tanlash:** shart — noto'g'ri FAIL ≤ 3%; so'ng AC-08 aniqlash ↑, noto'g'ri FAIL ↓, sog' cell'lar PASS ↑, standartdan eng kam o'zgarish.
- **"Aniqlandi"** ta'rifi AC-01 bilan bir xil: cell o'z ARFCN'idagi SWAP topilmasida bor (yoki sektor sababi swap).
- **Simulyatsiya ma'lumoti standartni o'zgartirish uchun asos emas** (§11): `docs/reports/calibration-sim-demo.md` faqat vosita ishlashini ko'rsatadi. Standart config faqat pilot (H2) ma'lumoti bilan yangilanadi.

## ADR-015 — Jonli tahlil inkremental; ishlash testlari alohida (5-bosqich, 2026-10-26)
- **Kontekst:** 18 cell'li eng og'ir holatda jonli yangilanish JVM'da 25–70 ms edi (tozalash ~60%); o'rta telefon ~5× sekin → 300 ms byudjetga yaqin/ortiq.
- **Qaror:** `LiveAnalyzer` inkremental: GNSS oralig'i endi o'zgarmaydigan namunalar bir marta tozalanadi; natija to'liq qayta hisoblash bilan aynan teng (test). Natija: ~9 ms (JVM). Yakuniy tahlil ~0.5 s.
- **Testlar:** `PerformanceTest` (`@Tag("perf")`) JVM'da byudjetning 1/5 qismini talab qiladi (telefon zaxirasi). Parallel `check` ichida vaqt shovqinli bo'lgani uchun u CI'da alohida qadamda (`-Pperf --no-parallel`) ishlaydi — o'chirilmagan, chegara yumshatilmagan. Haqiqiy telefondagi raqamlar H2 da tasdiqlanadi.

## ADR-016 — PR #21 o'z-o'zini ko'rib chiqish tuzatishlari (2026-10-26)
- **Sessiya rejasi nusxasi:** sessiya yaratilganda saytning o'sha paytdagi RF rejasi `session.plan_json` ga yoziladi (config kabi). Tahlil, hisobot, ZIP va jonli ekran shu nusxani ishlatadi — keyingi qayta import eski natijalarni o'zgartirmaydi. Eski yozuvlar uchun zaxira — saytning joriy rejasi.
- **Bufer:** yozuv `NonCancellable` va ketma-ket; `stop()` boshlangan yozuvni kutadi (Tugatish paytida 1 soniyalik ma'lumot yo'qolmaydi).
- **Servis:** sessiya id darhol band qilinadi (takroriy START ikkinchi engine yaratmaydi), engine tayyor bo'lmasdan kelgan STOP keyin bajariladi.
- **Interpolyatsiya:** ikkinchi qo'shni fix ham `maxFixGap` dan uzoq bo'lsa (GNSS uzilishi) interpolyatsiya qilinmaydi — yaqin fix olinadi; bu jonli inkremental tahlilning "to'liq qayta hisoblash bilan teng" kafolatini ham saqlaydi.
- **RAT:** almashinuv nishoni va kalibrlash/Monte-Karlo'dagi SWAP moslash RAT bo'yicha ham tekshiriladi.
- **Kalibrlash:** har sessiya o'z yozilgan config'i bilan baholanadi (grid faqat 5 parametrni almashtiradi); tavsiya eng ko'p ishlatilgan config ustiga quriladi.
- **Chegaralar faqat `AnalysisConfig` da:** `binDeg` (yo'nalish oraliqlari), `maxAccuracyM` (oldindan tekshiruv), yangi `minDeviceRateHz = 0.5`.
- **Room Gradle plagini:** debug va release KSP bitta sxema fayliga parallel yozib uni buzardi.
- **UI:** faol yozilayotgan sessiya "uzilgan" deb taklif qilinmaydi (faqat ochish); Sozlamalardagi probe ruxsatni tekshiradi; dialog tugmalari ≥ 56 dp.

## ADR-017 — targetSdk va compileSdk 36 (2026-10-27)
- **Kontekst:** prompt §3 targetSdk/compileSdk 35 ni belgilagan, lekin Google Play 2026-08-31 dan yangi ilova va yangilanishlar uchun targetSdk 36 ni talab qiladi. Foydalanuvchi qarori: 36 ga ko'tarish.
- **Qaror:** `Sdk.COMPILE = 36`, `Sdk.TARGET = 36` (`build-logic/.../Common.kt`); minSdk 29 o'zgarmaydi. API 36 ni AGP 8.7.3 bilmaydi → AGP 8.10.1 (Gradle 8.11.1 yetarli). AGP 8.10 da eskirgan `enableUnitTest` o'rniga `hostTests[UNIT_TEST_TYPE].enable`.
- **Android 16 xatti-harakat o'zgarishlari tekshirildi:** edge-to-edge'dan voz kechish (`windowOptOutEdgeToEdgeEnforcement`) ishlatilmaydi; `onBackPressed`/`KEYCODE_BACK` yo'q (orqaga qaytish Navigation Compose orqali — predictive back bilan mos); `screenOrientation`/`resizeableActivity`/aspect ratio cheklovlari yo'q (katta ekranlarda e'tiborsiz qoldirilishi ta'sir qilmaydi); JobScheduler, ordered broadcast, `elegantTextHeight`, intent redirection ishlatilmaydi.
- **16 KB sahifa:** release APK'dagi barcha 64-bitli `.so` (SQLCipher, DataStore, androidx.graphics) LOAD segmentlari 0x4000 ga tekislangan, `zipalign -c -P 16` OK.
- **Testlar:** Robolectric 4.14.1 qoldirildi — host testlar SDK 34 (`@Config`) yoki kutubxona minSdk'ida ishlaydi, SDK 36 jar kerak emas. CI `instrumented` job'i endi API 34 va API 36 emulyatorlarida (matritsa) ishlaydi; release smoke test ham ikkalasida.

## ADR-018 — Lint KSP'dan keyin ishlaydi (2026-10-27)
- **Muammo:** AGP 8.10 da `lintAnalyze<Variant>UnitTest` / `…AndroidTest` KSP yaratgan test manbalarini (`build/generated/ksp/<variant>UnitTest`) o'qiydi, lekin `ksp<Variant>UnitTestKotlin` ga bog'liq emas. Parallel build'da (CI, Gradle keshi bilan) lint KSP ishlayotgan paytdagi vaqtinchalik `byRounds/N/` fayllarini ko'radi va ular o'chganda `FileNotFoundException` bilan yiqiladi (`master`, PR #23 merge'idan keyin; PR'larning o'zida kesh bo'sh bo'lgani uchun ko'rinmagan).
- **Qaror:** `sv.android.hilt` plagini har `lint[Vital]Analyze<X>` task'iga `ksp<X>Kotlin` bog'liqligini qo'shadi. Lint tekshiruvlari kamaytirilmagan.

## ADR-019 — Imzolangan reliz CI'da, tag bo'yicha (2026-10-27)
- **Kontekst:** foydalanuvchi CI'da imzolashni so'radi. Kalit eng qimmatli sir: PR, fork yoki oddiy push unga yetmasligi, kesh yoki logga tushmasligi kerak; noto'g'ri kalit yoki versiya bilan reliz chiqmasligi kerak.
- **Qaror:** alohida `sector-verify-release` workflow faqat `sector-verify/v*` tag push'ida ishlaydi va `sector-verify-release` environment'idagi secret'larni (`SV_KEYSTORE_BASE64`, `SV_KEYSTORE_PASSWORD`, `SV_KEY_ALIAS`, `SV_KEY_PASSWORD`) ishlatadi; environment faqat shu tag'larga ruxsat beradi va inson tasdig'ini talab qiladi. Kalit `$RUNNER_TEMP` ga tiklanadi va `if: always()` bilan o'chiriladi, Gradle keshi o'chiq. Build'dan keyin `scripts/verify-release.sh` (v3 imzo, debug kalit emas, sertifikat = `SV_CERT_SHA256` variable, `versionName` = tag, targetSdk 36; AAB imzo va sertifikat). Natija — artefakt va **draft** Release; nashr qilishni inson hal qiladi.
- **v3:** minSdk 29 ≥ 28 bo'lgani uchun `apksigner` faqat v3 bilan imzolaydi (v1/v2 = false) — tekshiruv shuni talab qiladi (lokal sinovda topildi; H3 hujjatidagi "v2 ham true" xatosi tuzatildi).
- **Sinov:** bir martalik test kaliti (scratchpad'da, keyin o'chirilgan) bilan lokal: imzolangan APK/AAB → OK; boshqa sertifikat, boshqa versiya, debug kalit → rad. `actionlint` toza.
