# Sector Verify

Baza stansiyalarini montaj qiluvchi muhandislar uchun Android ilova. Oddiy telefon bilan (root, diag port va
vendor ruxsatisiz) sayt atrofida 150–400 m radiusda aylanib, har bir (ARFCN, PCI) qaysi yo'nalishda
nurlanayotganini baholaydi va RF rejaga solishtiradi. Sektor almashinuvi, yo'q PCI va antenna burilishini
brigada saytdan ketmasidan oldin topadi. To'liq offline: ma'lumot qurilmadan chiqmaydi.

## Talablar
- JDK 17, Android SDK (compileSdk 35), Android Studio yoki faqat buyruq qatori.
- `local.properties` da `sdk.dir=...` (Android Studio o'zi yozadi).

## Imkoniyatlar
- RF reja CSV importi → oldindan tekshiruv → sayt atrofida o'lchov (GPS + CellInfo, 1 Hz, foreground service) → jonli tahlil.
- Har bir (ARFCN, PCI) uchun azimut bahosi (±15–20°), sektor almashinuvi, bitta band almashinuvi, yo'q PCI, antenna burilishi.
- Imzolangan `report.json`, PDF hisobot (uz/ru/en), sessiya ZIP; ofisda `sv-replay` bilan qayta tahlil va imzo tekshiruvi.
- Qamrovdan tashqari: tilt, MIMO branch almashinuvi, 5° dan aniq azimut, VSWR/PIM.

## Yig'ish va tekshirish
```
.\gradlew.bat check                         # Windows: barcha testlar, Lint, detekt, ktlint, Kover
./gradlew check                             # Linux / macOS / CI
./gradlew :app:assembleDebug                # debug APK
./gradlew :app:bundleRelease :app:assembleRelease   # release (imzo: docs/DISTRIBUTION_APK.md)
./gradlew :core:analysis:test -Pslow        # Monte-Karlo 1000 iteratsiya
./gradlew :core:analysis:test -Pperf        # ishlash byudjetlari
./gradlew connectedDebugAndroidTest         # instrumental testlar (emulyator/telefon)
```

## Replay CLI
```
./gradlew :tools:replay:installDist
tools/replay/build/install/sv-replay/bin/sv-replay analyze sessiya.zip [--config cfg.json]
tools/replay/build/install/sv-replay/bin/sv-replay calibrate <zip-papka> ground_truth.csv [--out papka]
tools/replay/build/install/sv-replay/bin/sv-replay verify sessiya.zip
tools/replay/build/install/sv-replay/bin/sv-replay simulate <papka> --n 20
```

## Tuzilma
| Modul | Vazifa |
|---|---|
| `:app` | Navigatsiya, Hilt, tema |
| `:feature:plan` | CSV reja importi, saytlar, sayt kartasi |
| `:feature:survey` | Oldindan tekshiruv, jonli o'lchov, servis |
| `:feature:report` | Natija, PDF/JSON/CSV, imzo, ZIP |
| `:feature:settings` | Chegaralar, trafik URL, til, config import |
| `:core:telephony` | CellInfo yig'ish, normallashtirish, qurilma probe, trafik generatori |
| `:core:location` | GNSS (GPS_PROVIDER, 1 Hz) |
| `:core:data` | Room + SQLCipher, DataStore |
| `:core:analysis` | Algoritm va simulyator (sof Kotlin) |
| `:core:format` | CSV/JSON formatlari, kanonik JSON (sof Kotlin) |
| `:core:model` | Domen modellari (sof Kotlin) |
| `:core:ui` | Dark tema, shrift, umumiy Compose komponentlari |
| `:tools:replay` | Sessiyani qayta tahlil, kalibrlash, imzo tekshiruvi (CLI) |

## Hujjatlar
| Fayl | Mazmun |
|---|---|
| `docs/USER_GUIDE_uz.md`, `docs/USER_GUIDE_ru.md` | Foydalanuvchi qo'llanmasi |
| `docs/ARCHITECTURE.md` | Modullar, ma'lumot oqimi, xavfsizlik, testlar |
| `docs/ALGORITHM.md` | Algoritm (§6) va simulyatsiya/kalibrlash natijalari |
| `docs/DECISIONS.md` | Qarorlar (ADR) |
| `docs/RELEASE_CHECKLIST.md` | AC holati va reliz qadamlari |
| `docs/HUMAN_TASKS.md` | Inson darvozalari (H1, H2, H3) |
| `docs/PLAY_STORE.md`, `docs/DISTRIBUTION_APK.md`, `docs/privacy/` | Tarqatish va maxfiylik |
| `PROGRESS.md`, `CHANGELOG.md` | Holat va o'zgarishlar |
