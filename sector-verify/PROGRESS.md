# PROGRESS — Sector Verify

## Joriy holat
- **Bosqich:** 0 — tugadi (tag `sector-verify/phase-0-done`)
- **Keyingi:** 1-bosqich — model, algoritm, simulyator

## Bajarilgan
### 0-bosqich
- ✅ Muhit: JDK 21 (bytecode 17, ADR-003), Android SDK (platform 35, build-tools 35/34), git. `adb` bor, emulyator/KVM yo'q.
- ✅ Gradle wrapper 8.11.1 (`gradlew`, `gradlew.bat`), version catalog, `build-logic` konventsiya plaginlari.
- ✅ 13 modul (4.1 + `:core:format`, `:core:ui` — ADR-002), detekt, ktlint, Kover, Android Lint (`abortOnError = true`).
- ✅ `.gitignore`, CI (`.github/workflows/sector-verify.yml`, ADR-001), `CLAUDE.md`, `README.md`, `docs/DECISIONS.md`.
- ✅ Dark tema tokenlari + Noto Sans (`:core:ui`).

## Oxirgi test natijalari
- 2026-10-26: `./gradlew check` — BUILD SUCCESSFUL (barcha modullar: compile, unit test, detekt, ktlint, lint, koverVerify).

## Ochiq savollar
1. **targetSdk:** prompt 35 ni talab qiladi. Google Play 2026-08-31 dan yangi ilova va yangilanishlar uchun targetSdk 36 ni talab qiladi. Play orqali tarqatilsa 36 ga ko'tarish kerak (APK orqali tarqatishga ta'sir qilmaydi). Hozircha 35.
2. **Instrumental testlar:** bu muhitda emulyator yo'q (KVM yo'q) — CI'dagi emulyator job'ida yoki H1 da ishga tushiriladi.

## Kutilayotgan inson darvozasi
- yo'q
