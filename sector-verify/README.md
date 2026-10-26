# Sector Verify

Baza stansiyalarini montaj qiluvchi muhandislar uchun Android ilova. Oddiy telefon bilan (root, diag port va
vendor ruxsatisiz) sayt atrofida 150–400 m radiusda aylanib, har bir (ARFCN, PCI) qaysi yo'nalishda
nurlanayotganini baholaydi va RF rejaga solishtiradi. Sektor almashinuvi, yo'q PCI va antenna burilishini
brigada saytdan ketmasidan oldin topadi. To'liq offline: ma'lumot qurilmadan chiqmaydi.

## Talablar
- JDK 17, Android SDK (compileSdk 35), Android Studio yoki faqat buyruq qatori.
- `local.properties` da `sdk.dir=...` (Android Studio o'zi yozadi).

## Yig'ish va tekshirish
```
.\gradlew.bat check            # Windows
./gradlew check                # Linux / macOS / CI
./gradlew :app:assembleDebug   # debug APK
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

Batafsil: `docs/PROMPT.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
