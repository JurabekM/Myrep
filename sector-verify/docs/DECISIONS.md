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
