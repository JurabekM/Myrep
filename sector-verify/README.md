# Sector Verify

Baza stansiyalarini montaj qiluvchi muhandislar uchun Android ilova. Oddiy telefon bilan (root, diag port va
vendor ruxsatisiz) sayt atrofida 150–400 m radiusda aylanib, har bir (ARFCN, PCI) qaysi yo'nalishda
nurlanayotganini baholaydi va RF rejaga solishtiradi. Sektor almashinuvi, yo'q PCI va antenna burilishini
brigada saytdan ketmasidan oldin topadi. To'liq offline: ma'lumot qurilmadan chiqmaydi.

**Holat:** `1.0.0` relizga tayyorlanmoqda (`1.0.0-rc1` — release-kandidat). Simulyatsiya va CI'da tekshiriladigan barcha
qabul mezonlari bajarilgan; qolgani — inson darvozalari: real telefonlar (H1), 20 saytlik pilot (H2), imzolash va
tarqatish (H3). Batafsil: `PROGRESS.md`, `docs/RELEASE_CHECKLIST.md`.

## Talablar
**Telefon:** Android 10+ (API 29; targetSdk 36 — Android 16), GPS, LTE yoki NR, reja operatorining SIM kartasi.
Qo'llab-quvvatlanadigan qurilmalar: `docs/DEVICES.md` (H1 dan keyin to'ldiriladi).

**Ishlab chiqish:**
- JDK 17, Android SDK (compileSdk 36, build-tools 35+), Android Studio yoki faqat buyruq qatori.
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
./gradlew :app:bundleRelease :app:assembleRelease   # release (imzo: docs/H3_RELEASE_SIGNING.md)
./gradlew :core:analysis:test -Pslow        # Monte-Karlo 1000 iteratsiya
./gradlew :core:analysis:test -Pperf        # ishlash byudjetlari
./gradlew connectedDebugAndroidTest         # instrumental testlar (emulyator/telefon)
```

## Reliz va imzolash
- **CI (tavsiya):** `sector-verify/vX.Y.Z` tag'ini push qiling → `sector-verify-release` workflow inson tasdig'idan keyin
  imzolangan APK va AAB yig'adi, `scripts/verify-release.sh` bilan tekshiradi (v3 imzo, sertifikat barmoq izi, versiya,
  targetSdk) va **draft** GitHub Release yaratadi; izoh — `CHANGELOG.md` dagi shu versiya bo'limi. Kalit faqat himoyalangan
  `sector-verify-release` environment'ida (bir martalik sozlash: `docs/H3_RELEASE_SIGNING.md`, 10-bo'lim; ADR-019).
- **Qo'lda:** `keystore.properties` (gitignore qilingan) yoki `SV_KEYSTORE_*` muhit o'zgaruvchilari — `docs/H3_RELEASE_SIGNING.md`.
- **Versiya:** `versionName` — eng so'nggi `sector-verify/v*` tag'idan, `versionCode` — commitlar soni (to'liq klon kerak).
- Imzo kaliti hech qachon repoga tushmaydi (`*.jks`, `*.p12`, `*.keystore`, `keystore.properties` gitignore qilingan).

## CI
| Workflow | Qachon | Nima qiladi |
|---|---|---|
| `.github/workflows/sector-verify.yml` | `sector-verify/**` o'zgarganda (push, PR) | `check` + ishlash testlari, Kover; instrumental testlar API 34 va 36 emulyatorlarida + release smoke test; imzosiz release AAB/APK + `lintRelease` |
| `.github/workflows/sector-verify-release.yml` | `sector-verify/v*` tag push qilinganda | imzolangan reliz, tekshiruv, draft GitHub Release |

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
| `docs/HUMAN_TASKS.md` | Inson darvozalari (H1, H2, H3) — umumiy ko'rinish |
| `docs/H1_DEVICE_TEST.md` | H1: real telefonlarda qurilma sinovi (dala ko'rsatmasi) |
| `docs/H2_PILOT_GUIDE.md` | H2: 20 saytlik pilot, ground truth, kalibrlash |
| `docs/H3_RELEASE_SIGNING.md` | H3: imzo kaliti, versiya, tekshirish, CI'da imzolash, tarqatish |
| `docs/BATTERY_TEST.md`, `docs/DEVICES.md` | Batareya sinovi (AC-06), qo'llab-quvvatlanadigan qurilmalar |
| `docs/reports/`, `docs/samples/plan-example.csv` | Monte-Karlo/kalibrlash hisobotlari, RF reja CSV namunasi |
| `docs/PLAY_STORE.md`, `docs/DISTRIBUTION_APK.md`, `docs/privacy/` | Tarqatish va maxfiylik |
| `docs/PROMPT.md` | Asl spetsifikatsiya |
| `PROGRESS.md`, `CHANGELOG.md` | Holat va o'zgarishlar |
