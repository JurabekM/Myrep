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
- **Qaror:** `cell_sample.rx_nanos` (ADR-008.1), `session.verdict`, `session.coverage_pct`, `session.subscription_id`, `sector_result.detail_json` (to'liq `SectorResult`). `sector_result` dagi baholash ustunlari INCONCLUSIVE uchun nullable. `sector_result.sector_id` — `ON DELETE SET NULL` (reja qayta import qilinganda natija saqlanadi).
- **Sabab:** Xom jadvallar o'zgarmaydi; qo'shimchalar faqat hosila ma'lumot.

## ADR-011 — Survey arxitekturasi (2-bosqich, 2026-10-26)
- **Qaror:** Android'siz `SurveyEngine` (oqimlar → `BufferedSampleWriter` + xotiradagi nusxa → har 5 s `LiveAnalyzer`), `SurveyForegroundService` faqat "yelim" kod. Holat UI'ga `SurveyController` (singleton StateFlow) orqali. Servis `START_NOT_STICKY`: jarayon o'ldirilsa, keyingi ishga tushishda RUNNING sessiya topilib davom ettirish taklif qilinadi (§7), avtomatik qayta boshlanmaydi.
- **Sabab:** Engine'ni virtual vaqt bilan testlash mumkin; foydalanuvchi bilmagan holda fon yig'ish bo'lmaydi.
