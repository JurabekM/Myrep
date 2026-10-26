# PROGRESS — Sector Verify

## Joriy holat
- **Bosqich:** 1 — tugadi (tag `sector-verify/phase-1-done`)
- **Keyingi:** 2-bosqich — Android yig'ish va ma'lumot

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

## Oxirgi test natijalari
- 2026-10-26: `./gradlew check` — BUILD SUCCESSFUL (1-bosqich: model 5 test, analysis 34 test, koverVerify 99.7%).
- 2026-10-26: `./gradlew :core:analysis:test -Pslow` — Monte-Karlo 1000: barcha AC ✅.

## Ochiq savollar
1. **targetSdk:** prompt 35 ni talab qiladi. Google Play 2026-08-31 dan yangi ilova va yangilanishlar uchun targetSdk 36 ni talab qiladi. Play orqali tarqatilsa 36 ga ko'tarish kerak (APK orqali tarqatishga ta'sir qilmaydi). Hozircha 35.
2. **Tag push:** bulut sessiyasining git proksisi faqat ishchi branch'ga push qilishga ruxsat beradi; `sector-verify/phase-N-done` tag'lari lokal yaratilgan, lekin GitHub'ga chiqmadi. Inson: `git push origin --tags` (yoki tag'larni PR merge'dan keyin qo'ying).
3. **Instrumental testlar:** bu muhitda emulyator yo'q (KVM yo'q) — CI'dagi emulyator job'ida yoki H1 da ishga tushiriladi.

## Kutilayotgan inson darvozasi
- yo'q
