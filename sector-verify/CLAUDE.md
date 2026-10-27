# CLAUDE.md — Sector Verify

Asosiy topshiriq: `docs/PROMPT.md` (to'liq spetsifikatsiya). Holat: `PROGRESS.md`. Qarorlar: `docs/DECISIONS.md`.
Har sessiya boshida shu uchtasini o'qing. Myrep ildizidagi `CLAUDE.md` (dark UI qoidasi, til) ham amal qiladi.

## Build buyruqlari
- Windows: `.\gradlew.bat check` · Linux/CI: `./gradlew check`
- Bitta modul: `./gradlew :core:analysis:test` · sekin Monte-Karlo: `./gradlew :core:analysis:test -Pslow`
- Qamrov: `./gradlew :core:analysis:koverHtmlReport` (AC-10: `koverVerify` ≥ 90 % `check` ichida)
- Format: `./gradlew ktlintFormat` · statik tahlil: `./gradlew detekt`
- Claude bulut sessiyasida (Maven Central 429 beradi): scratchpad'dagi init-skript bilan
  `./gradlew --init-script <scratchpad>/sv-mirror.gradle ...` (GCS ko'zgusi; repoga kirmaydi).

## Modullar
`:app` → `:feature:{plan,survey,report,settings}` → `:core:{ui,data,telephony,location}` → `:core:{analysis,format}` → `:core:model`.
`:core:model`, `:core:analysis`, `:core:format`, `:tools:replay` — **sof Kotlin/JVM**, Android importi taqiqlangan.
Konventsiya plaginlari: `build-logic/convention` (`sv.android.application|library|compose|hilt`, `sv.jvm.library`).

## Qoidalar
- Chegaralar faqat `AnalysisConfig` da. Tasodifiylik faqat `Random(seed)`.
- Kod/identifikator/commit — inglizcha (Conventional Commits); izoh, hujjat, UI matni — o'zbekcha (`strings.xml`, uz/ru/en).
- UI: standart dark (`core/ui/.../theme/Palette.kt`), Noto Sans ilova ichida, tugma ≥ 56 dp.
- Testni o'chirish yoki chegarani yumshatish taqiqlangan. Tag'lar: `sector-verify/phase-N-done` (monorepo).
- Xom jadvallar (`gnss_fix`, `cell_sample`) o'zgartirilmaydi. Tarmoqqa faqat `TrafficGenerator` chiqadi.
