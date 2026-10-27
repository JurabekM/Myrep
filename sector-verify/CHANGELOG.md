# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalash: SemVer (tag `sector-verify/vX.Y.Z`).
`sector-verify/vX.Y.Z` tag'i push qilinganda shu fayldagi `## [X.Y.Z]` bo'limi GitHub Release izohiga aylanadi (ADR-019).

## [Unreleased]

## [1.0.0] — chiqarilmagan
<!-- Reliz kuni (docs/H3_RELEASE_SIGNING.md, 4-bo'lim): "chiqarilmagan" o'rniga sanani yozing (YYYY-MM-DD);
     H2 kalibrlashi standart AnalysisConfig'ni o'zgartirgan bo'lsa — "O'zgardi" ga qo'shing va "Ma'lum cheklovlar"ni yangilang;
     H1 natijasi bilan "Talablar"ni aniqlashtiring. Keyin sector-verify/v1.0.0 tag'i. Bu izoh Release matnida ko'rinmaydi. -->

### O'zgardi
- **Android 16 (API 36):** targetSdk va compileSdk 36 — Google Play 2026-08-31 dan talab qiladi; AGP 8.10.1.
  Android 16 xatti-harakat o'zgarishlari tekshirildi (edge-to-edge, predictive back, katta ekranlar); native kutubxonalar
  16 KB sahifaga tekislangan; instrumental testlar API 34 va 36 emulyatorlarida (ADR-017).

### Qo'shildi
- **CI'da imzolangan reliz:** `sector-verify/v*` tag → tekshirilgan APK va AAB (v3 imzo, sertifikat barmoq izi,
  versiya, targetSdk — `scripts/verify-release.sh`) va draft GitHub Release; kalit himoyalangan environment'da (ADR-019).
- **Dala ko'rsatmalari:** qurilma sinovi — `docs/H1_DEVICE_TEST.md`, 20 saytlik pilot — `docs/H2_PILOT_GUIDE.md`,
  release imzolash va tarqatish — `docs/H3_RELEASE_SIGNING.md`.

### Tuzatildi
- Build: lint KSP tugashini kutmagani uchun Gradle keshi bilan parallel build'da tasodifan yiqilardi (ADR-018).

### Ma'lum cheklovlar
- Standart chegaralar hozircha faqat simulyatsiyada tasdiqlangan (noto'g'ri FAIL 0%, almashinuvni aniqlash 98–99%);
  haqiqiy saytlarda kalibrlash — H2 pilotidan keyin. Simulyatsiyada xatosiz saytlarning ~40% i PASS, qolgani
  INCONCLUSIVE (qamrov yetarli emas) bo'ladi.
- Qo'llab-quvvatlanadigan qurilmalar ro'yxati (`docs/DEVICES.md`) H1 sinovidan keyin to'ldiriladi.
- Hisobot imzosining Keystore attestation zanjiri Google root sertifikatiga nisbatan tekshirilmaydi.

### Talablar
- Android 10+ (API 29), GPS, LTE yoki NR tarmog'i, reja operatorining SIM kartasi.
- Ruxsatlar: aniq joylashuv, telefon holati; bildirishnomalar (tavsiya etiladi). Fon joylashuvi kerak emas.

## [1.0.0-rc1] — 2026-10-26
### Qo'shildi
- RF reja CSV importi (validatsiya, o'zbekcha/ruscha/inglizcha xatolar, qator raqami bilan).
- Oldindan tekshiruv, foreground service bilan o'lchov (GPS 1 Hz, CellInfo 1 Hz + API 31+ listener), jonli tahlil (5 s).
- Tahlil algoritmi 1.0.0: tozalash, binlash, diagramma moslash (A), bootstrap CI, centroid (B), qamrov, almashinuv (permutatsiya),
  sabab (CELL_CONFIG_SWAP, BAND_PORT_SWAP, ANTENNA_ROTATED, PCI_MISSING, PCI_UNEXPECTED, LOW_COVERAGE), verdikt.
- Natija ekrani (polar diagrammalar, tavsiyalar), imzolangan `report.json` (EC P-256), PDF hisobot (uz/ru/en), sessiya ZIP.
- Sozlamalar: presetlar, qo'lda chegaralar, config JSON import, trafik URL, ilova va hisobot tili, dark/light/quyosh mavzulari.
- `sv-replay` CLI: `analyze`, `calibrate`, `verify`, `simulate`.
- Xavfsizlik: SQLCipher (Keystore bilan o'ralgan kalit), backup taqiqi, faqat HTTPS, FileProvider, lokal crash log.

### Tuzatildi (o'z-o'zini ko'rib chiqish, ADR-016)
- O'lchovni to'xtatish boshlangan bufer yozuvini bekor qilmaydi — oxirgi soniya ma'lumoti yo'qolmaydi.
- Servisga takroriy "Boshlash" ikkinchi o'lchovni boshlamaydi; juda erta "Tugatish" to'g'ri bajariladi.
- Har sessiya o'z RF reja nusxasini saqlaydi — rejani qayta import qilish eski natija, hisobot va ZIP'ni o'zgartirmaydi.
- GNSS uzilgan oraliqda nuqtalar interpolyatsiya qilinmaydi; almashinuv qidiruvi RAT'ni (LTE/NR) hisobga oladi.
- Tiklash dialogi hali yozilayotgan o'lchovni to'xtatishni taklif qilmaydi; Sozlamalardagi probe avval ruxsatni tekshiradi.
- `sv-replay calibrate` har sessiyani o'z config'i bilan baholaydi; qolgan chegaralar (`binDeg`, GPS aniqligi,
  qurilma chastotasi) `AnalysisConfig` ga ko'chirildi.

[Unreleased]: https://github.com/JurabekM/Myrep/compare/sector-verify/v1.0.0...master
[1.0.0]: https://github.com/JurabekM/Myrep/compare/sector-verify/v1.0.0-rc1...sector-verify/v1.0.0
[1.0.0-rc1]: https://github.com/JurabekM/Myrep/releases/tag/sector-verify/v1.0.0-rc1
